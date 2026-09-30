"""The retrieval tool: a local hybrid index (BM25 keywords + nomic embeddings).

Retrieval only finds evidence; it never generates text. `wiki search` shows its
results directly. `ask` and `chat` hand its results to Gemma.

Stored in data/index/ (outside the vault):
  passages.json    every passage with its source path, section and PDF pages
  embeddings.json  vectors keyed by a hash of the passage text (reused across rebuilds)
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .chunking import Passage, chunk_note
from .config import INDEX_DIR, RAW, VAULT, WIKI, Settings
from .llm import LLMError, OllamaClient

STOPWORDS = set("""
a an the and or but if of to in on at by for with from as is are was were be been being it its this that these
those he she they them his her their we our you your i me my do does did done not no so than then there here what
which who whom how why when where can could should would will may might must also into about over under more most
very just only such any all each other some same own s t
""".split())


def tokenize(text: str) -> list[str]:
    tokens = []
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        if tok in STOPWORDS or len(tok) < 2:
            continue
        # light stemming so "cycles"/"cycle" and "companies"/"company" match
        if tok.endswith("ies") and len(tok) > 4:
            tok = tok[:-3] + "y"
        elif tok.endswith("s") and not tok.endswith("ss") and len(tok) > 3:
            tok = tok[:-1]
        tokens.append(tok)
    return tokens


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def _doc_text(p: Passage) -> str:
    # The title and section are indexed too, so "Mr. Market" also matches the section named after it.
    return f"{p.title}. {p.section}. {p.text}"


@dataclass
class Hit:
    passage: Passage
    score: float          # fused rank score used for ordering
    bm25: float
    cosine: float | None

    def to_dict(self) -> dict:
        return {**self.passage.to_dict(), "score": round(self.score, 4),
                "bm25": round(self.bm25, 3), "cosine": None if self.cosine is None else round(self.cosine, 3)}


# ---------------------------------------------------------------------- build
def collect_passages(settings: Settings) -> list[Passage]:
    passages: list[Passage] = []
    for path in sorted(RAW.glob("*.md")):
        passages += chunk_note(path, VAULT, "source", settings.chunk_max_words)
    for path in sorted(WIKI.rglob("*.md")):
        passages += chunk_note(path, VAULT, "wiki", settings.chunk_max_words)
    return passages


def build_index(settings: Settings, client: OllamaClient | None, log=print) -> dict:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    passages = collect_passages(settings)
    (INDEX_DIR / "passages.json").write_text(json.dumps([p.to_dict() for p in passages], indent=1))

    emb_path = INDEX_DIR / "embeddings.json"
    cache = json.loads(emb_path.read_text()) if emb_path.exists() else {}
    vectors = cache.get("vectors", {}) if cache.get("model") == settings.embed_model else {}
    needed = [p for p in passages if _hash(_doc_text(p)) not in vectors]
    embedded = False
    if client is not None and needed:
        try:
            for i in range(0, len(needed), 16):
                batch = needed[i:i + 16]
                vecs = client.embed(settings.embed_model, [f"search_document: {_doc_text(p)}" for p in batch])
                for p, v in zip(batch, vecs):
                    vectors[_hash(_doc_text(p))] = v
            embedded = True
        except LLMError as e:
            log(f"  ! embeddings skipped ({e.__str__().splitlines()[0]}); keyword search still works")
    keep = {_hash(_doc_text(p)) for p in passages}
    vectors = {h: v for h, v in vectors.items() if h in keep}
    emb_path.write_text(json.dumps({"model": settings.embed_model, "vectors": vectors}))
    stats = {
        "passages": len(passages),
        "source_passages": sum(p.kind == "source" for p in passages),
        "wiki_passages": sum(p.kind == "wiki" for p in passages),
        "embedded": len(vectors),
        "newly_embedded": len(needed) if embedded else 0,
    }
    (INDEX_DIR / "stats.json").write_text(json.dumps(stats, indent=1))
    return stats


# ---------------------------------------------------------------------- query
class Retriever:
    def __init__(self, settings: Settings, client: OllamaClient | None):
        path = INDEX_DIR / "passages.json"
        if not path.exists():
            raise FileNotFoundError("No retrieval index yet. Run:  wiki ingest vault/raw   (or  wiki index)")
        self.settings = settings
        self.client = client
        self.passages = [Passage(**d) for d in json.loads(path.read_text())]
        emb = json.loads((INDEX_DIR / "embeddings.json").read_text()) if (INDEX_DIR / "embeddings.json").exists() else {}
        self.vectors = emb.get("vectors", {}) if emb.get("model") == settings.embed_model else {}
        self._docs = [Counter(tokenize(_doc_text(p))) for p in self.passages]
        self._lens = [sum(c.values()) for c in self._docs]
        self._df = Counter(t for c in self._docs for t in c)
        self.embedding_note = ""

    # BM25 (k1=1.5, b=0.75) over the selected passages
    def _bm25(self, query: str, idx: list[int]) -> dict[int, float]:
        q = tokenize(query)
        n = len(self.passages)
        avg = sum(self._lens) / max(n, 1)
        scores = {}
        for i in idx:
            doc, s = self._docs[i], 0.0
            for t in q:
                if t not in doc:
                    continue
                idf = math.log(1 + (n - self._df[t] + 0.5) / (self._df[t] + 0.5))
                tf = doc[t]
                s += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * self._lens[i] / avg))
            scores[i] = s
        return scores

    def _cosines(self, query: str, idx: list[int]) -> dict[int, float] | None:
        if self.client is None or not self.vectors:
            self.embedding_note = "embeddings unavailable: keyword (BM25) search only"
            return None
        try:
            qv = self.client.embed(self.settings.embed_model, [f"search_query: {query}"])[0]
        except LLMError:
            self.embedding_note = "Ollama not reachable: keyword (BM25) search only"
            return None
        qn = math.sqrt(sum(x * x for x in qv)) or 1.0
        out = {}
        for i in idx:
            v = self.vectors.get(_hash(_doc_text(self.passages[i])))
            if v is None:
                continue
            vn = math.sqrt(sum(x * x for x in v)) or 1.0
            out[i] = sum(a * b for a, b in zip(qv, v)) / (qn * vn)
        return out

    def search(self, query: str, k: int, kinds: tuple[str, ...] = ("source",)) -> list[Hit]:
        idx = [i for i, p in enumerate(self.passages) if p.kind in kinds]
        bm = self._bm25(query, idx)
        cos = self._cosines(query, idx)
        rrf_k = self.settings.rrf_k
        fused = {i: 0.0 for i in idx}
        for i, r in _ranks({i: s for i, s in bm.items() if s > 0}).items():
            fused[i] += 1 / (rrf_k + r)
        if cos:
            for i, r in _ranks(cos).items():
                fused[i] += 1 / (rrf_k + r)
        order = sorted(idx, key=lambda i: fused[i], reverse=True)
        hits = [Hit(self.passages[i], fused[i], bm.get(i, 0.0), None if cos is None else cos.get(i)) for i in order]
        return [h for h in hits if h.score > 0][:k]

    def best_bm25(self, query: str, kinds: tuple[str, ...] = ("source",)) -> float:
        idx = [i for i, p in enumerate(self.passages) if p.kind in kinds]
        return max(self._bm25(query, idx).values(), default=0.0)


def _ranks(scores: dict[int, float]) -> dict[int, int]:
    return {i: r for r, i in enumerate(sorted(scores, key=scores.get, reverse=True), start=1)}
