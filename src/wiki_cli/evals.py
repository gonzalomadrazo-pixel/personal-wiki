"""`wiki eval`: run the fixed ask-mode tests and write one evidence card per test.

A test = fixed question + expected behaviour/evidence (written before running) + actual result.
The expectations live in evals/, outside the vault, so retrieval can never find the answer key.
Automated checks here are objective ones (was the expected source retrieved? do the citations
point at retrieved passages?). Whether the answer is actually correct is judged by a person
reading the cited passages, in the card's Assessment section.
"""

from __future__ import annotations

import json
import tomllib
from datetime import datetime
from pathlib import Path

from .config import ROOT, Settings
from .index import Retriever
from .llm import OllamaClient, network_status
from .modes import run_ask


def run_evals(file: Path, settings: Settings, client: OllamaClient, out_dir: Path, log=print) -> list[dict]:
    tests = tomllib.loads(file.read_text())["test"]
    out_dir.mkdir(parents=True, exist_ok=True)
    net = network_status()
    model = client.model_info(settings.chat_model)
    embed = client.model_info(settings.embed_model)
    retriever = Retriever(settings, client)
    results = []
    log(f"Network: {net}")
    for t in tests:
        log(f"\n▶ {t['id']}: {t['question']}")
        res = run_ask(client, retriever, settings, t["question"])
        mem = client.ps()
        ranks = {h.passage.source_id: n for n, h in reversed(list(enumerate(res.hits, 1)))}
        expected = t.get("expected_sources", [])
        found = {s: ranks.get(s) for s in expected}
        cited_sources = sorted({res.hits[i - 1].passage.source_id for i in res.check.cited if 0 < i <= len(res.hits)})
        record = {
            "id": t["id"], "kind": t["kind"], "question": t["question"], "mode": "ask", "execution": "local",
            "network": net, "run_at": datetime.now().isoformat(timespec="seconds"),
            "model": model, "embedding_model": embed,
            "expected_behavior": t["expected_behavior"], "expected_sources": expected,
            "expected_evidence": t.get("expected_evidence", ""),
            "retrieval_check": found, "retrieved": [h.to_dict() for h in res.hits],
            "answer": res.answer, "citation_check": res.check.to_dict(), "cited_sources": cited_sources,
            "stats": res.stats,
            "memory": [{"model": m["name"], "size_gb": round(m.get("size", 0) / 1e9, 2),
                        "gpu_gb": round(m.get("size_vram", 0) / 1e9, 2)} for m in mem],
        }
        (out_dir / f"{t['id']}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
        (out_dir / f"{t['id']}.md").write_text(card(record))
        status = res.check.status
        log(f"  retrieval: {', '.join(f'{s} → rank {r}' if r else f'{s} → NOT retrieved' for s, r in found.items()) or 'n/a'}")
        log(f"  answer status: {status} · cited {res.check.cited} · {res.stats['wall_seconds']}s")
        results.append(record)
    (out_dir / "summary.json").write_text(json.dumps(
        [{k: r[k] for k in ("id", "question", "retrieval_check", "cited_sources", "run_at", "network")}
         | {"status": r["citation_check"]["status"], "seconds": r["stats"]["wall_seconds"]} for r in results], indent=2))
    log(f"\nEvidence cards written to {out_dir.relative_to(ROOT)}/")
    return results


def card(r: dict) -> str:
    m, s = r["model"], r["stats"]
    lines = [
        f"# Ask-mode test {r['id']}: {r['kind']}\n",
        f"**Question:** {r['question']}\n",
        "| | |", "|---|---|",
        f"| Mode | `ask` (standalone, no chat history) |",
        f"| Execution | local: {m['runtime']} on this Mac |",
        f"| Network at run time | {r['network']} |",
        f"| Model | `{m['name']}` ({m['family']}, {m['parameter_size']}, {m['quantization']}, digest {m['digest']}) |",
        f"| Embeddings | `{r['embedding_model']['name']}` ({r['embedding_model']['quantization']}) |",
        f"| Run at | {r['run_at']} |",
        f"| Response time | {s['wall_seconds']} s total ({s['prompt_tokens']} prompt tokens, {s['output_tokens']} output tokens, {s['tokens_per_second']} tok/s) |",
        f"| Model memory (Ollama) | {', '.join(f'{x['model']}: {x['size_gb']} GB' for x in r['memory'])} |",
        "",
        "## Expected (written before running)\n",
        f"- **Behaviour:** {r['expected_behavior']}",
        f"- **Expected sources:** {', '.join(f'`{x}`' for x in r['expected_sources']) or 'none — the wiki does not contain this'}",
        f"- **Expected evidence:** {r['expected_evidence'] or '—'}",
        "",
        "## Retrieved passages\n",
    ]
    for n, h in enumerate(r["retrieved"], 1):
        cited = " **(cited)**" if n in r["citation_check"]["cited"] else ""
        lines.append(f"**[S{n}]** `vault/{h['path']}` › {h['section']}{', ' + h['pages'] if h['pages'] else ''} "
                     f"(bm25 {h['bm25']}, cosine {h['cosine']}){cited}\n")
        lines.append("> " + h["text"].replace("\n", "\n> ") + "\n")
    rc = r["retrieval_check"]
    lines += [
        "## Actual Gemma answer\n",
        "```text", r["answer"], "```\n",
        "## Automated checks\n",
        f"- Expected source retrieved: " + ("; ".join(f"`{k}` at rank {v}" if v else f"`{k}` NOT retrieved" for k, v in rc.items()) or "n/a (unanswerable test)"),
        f"- Citation check: **{r['citation_check']['status']}**; cited {', '.join(f'[S{i}]' for i in r['citation_check']['cited']) or 'nothing'}"
        + (f"; invalid {r['citation_check']['invalid']}" if r['citation_check']['invalid'] else ""),
        f"- Sources cited: {', '.join(f'`{x}`' for x in r['cited_sources']) or 'none'}",
        "",
        "## Assessment (human)\n",
        "_To be written after opening the cited passages: does each material claim follow from them?_\n",
    ]
    return "\n".join(lines)
