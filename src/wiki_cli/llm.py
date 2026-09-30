"""Thin client for the local Ollama server that runs Gemma and the embedding model.

Only the standard library is used. Every failure becomes an LLMError with a
message that tells the user what to do next.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Iterator


class LLMError(RuntimeError):
    pass


@dataclass
class ChatResult:
    text: str
    stats: dict = field(default_factory=dict)


class OllamaClient:
    def __init__(self, host: str, keep_alive: str = "10m", timeout: float = 600, base_options: dict | None = None):
        self.host = host.rstrip("/")
        self.keep_alive = keep_alive
        self.timeout = timeout
        self.base_options = base_options or {}   # sent with every generation call (e.g. use_mmap)

    @classmethod
    def from_settings(cls, settings) -> "OllamaClient":
        return cls(settings.ollama_host, settings.keep_alive, base_options={"use_mmap": settings.use_mmap})

    # ------------------------------------------------------------------ transport
    def _request(self, path: str, payload: dict | None = None, stream: bool = False, timeout: float | None = None):
        url = f"{self.host}{path}"
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req, timeout=timeout or self.timeout)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code == 404 and "not found" in body:
                model = (payload or {}).get("model", "?")
                raise LLMError(f"Model '{model}' is not downloaded. Run:  ollama pull {model}") from None
            raise LLMError(f"Ollama returned HTTP {e.code}: {body[:300]}") from None
        except (urllib.error.URLError, ConnectionError, socket.timeout) as e:
            raise LLMError(
                f"Cannot reach the local Ollama server at {self.host} ({getattr(e, 'reason', e)}).\n"
                "Start it by opening the Ollama app or running:  ollama serve"
            ) from None
        if stream:
            return resp
        with resp:
            return json.loads(resp.read().decode())

    # ------------------------------------------------------------------ info
    def is_up(self) -> bool:
        try:
            self._request("/api/version", timeout=2)
            return True
        except LLMError:
            return False

    def version(self) -> str:
        return self._request("/api/version", timeout=5).get("version", "?")

    def show(self, model: str) -> dict:
        return self._request("/api/show", {"model": model}, timeout=30)

    def ps(self) -> list[dict]:
        return self._request("/api/ps", timeout=5).get("models", [])

    def model_info(self, model: str) -> dict:
        """Identity of the model actually used, for evidence cards."""
        info = self.show(model)
        d = info.get("details", {})
        digest = ""
        for m in self._request("/api/tags", timeout=10).get("models", []):
            if model in (m.get("name"), m.get("model")) or f"{model}:latest" in (m.get("name"), m.get("model")):
                digest = m.get("digest", "")
        return {
            "name": model,
            "family": d.get("family"),
            "parameter_size": d.get("parameter_size"),
            "quantization": d.get("quantization_level"),
            "format": d.get("format"),
            "digest": digest[:12],
            "runtime": f"Ollama {self.version()}",
        }

    # ------------------------------------------------------------------ generation
    def chat(self, model: str, messages: list[dict], *, options: dict | None = None,
             format: dict | str | None = None, stream_to=None) -> ChatResult:
        """Run a chat completion. If stream_to is a callable, tokens are passed to it as they arrive."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream_to is not None,
            "keep_alive": self.keep_alive,
            "think": False,           # Gemma 4 can "think"; we disable it for speed and plain answers
            "options": {**self.base_options, **(options or {})},
        }
        if format is not None:
            payload["format"] = format
        start = time.perf_counter()
        if stream_to is None:
            out = self._request("/api/chat", payload)
            text = out.get("message", {}).get("content", "")
            final = out
        else:
            text, final = self._stream_chat(payload, stream_to)
        return ChatResult(text=text, stats=_stats(final, time.perf_counter() - start))

    def _stream_chat(self, payload: dict, on_token) -> tuple[str, dict]:
        resp = self._request("/api/chat", payload, stream=True)
        parts, final = [], {}
        with resp:
            for line in _lines(resp):
                chunk = json.loads(line)
                if "error" in chunk:
                    raise LLMError(f"Ollama error: {chunk['error']}")
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    parts.append(piece)
                    on_token(piece)
                if chunk.get("done"):
                    final = chunk
        return "".join(parts), final

    def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        out = self._request("/api/embed", {"model": model, "input": texts, "keep_alive": self.keep_alive})
        return out.get("embeddings", [])


def _lines(resp) -> Iterator[bytes]:
    for raw in resp:
        raw = raw.strip()
        if raw:
            yield raw


def _stats(final: dict, wall: float) -> dict:
    ns = 1e9
    return {
        "wall_seconds": round(wall, 2),
        "load_seconds": round(final.get("load_duration", 0) / ns, 2),
        "prompt_tokens": final.get("prompt_eval_count"),
        "prompt_seconds": round(final.get("prompt_eval_duration", 0) / ns, 2),
        "output_tokens": final.get("eval_count"),
        "output_seconds": round(final.get("eval_duration", 0) / ns, 2),
        "tokens_per_second": round(final["eval_count"] / (final["eval_duration"] / ns), 1)
        if final.get("eval_count") and final.get("eval_duration") else None,
    }


def network_status(timeout: float = 4.0) -> str:
    """Probe whether the internet is reachable. Used only to label evidence (offline proof)."""
    for host, port in (("1.1.1.1", 443), ("8.8.8.8", 53)):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return "online (internet reachable)"
        except OSError:
            continue
    return "offline (no internet connection)"
