"""`wiki ingest`: read original notes, ask local Gemma for structured page content,
and render linked Obsidian pages plus index.md.

Pipeline per source file in vault/raw/:
  1. hash the file; if unchanged and already extracted, reuse the saved extraction
  2. otherwise send the note + ingest-instructions.md + the allowed concept list to Gemma
     with a JSON schema (concept names and section headings are enums, so Gemma cannot
     invent page names or cite sections that don't exist)
  3. save the extraction to data/extractions/<source_id>.json and a review report
     to data/reviews/<source_id>.md (statements with weak word overlap are flagged)
Then, for all sources, deterministically render:
  wiki/Sources/<wiki_title>.md, wiki/Concepts/<concept>.md, wiki/Investors/<person>.md, index.md
Pages are keyed by stable names, so re-ingesting overwrites the same files instead of
creating duplicates, and generated pages that are no longer needed are removed.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path

from .chunking import PAGE_RE, parse_frontmatter, split_sections
from .config import (CATALOG, EXTRACTIONS, INDEX_MD, RAW, REVIEWS, ROOT, VAULT, WIKI, Settings,
                     load_prompt, load_taxonomy)
from .index import tokenize
from .llm import LLMError, OllamaClient

GENERATED_MARK = "wiki-cli"
SUPPORTED = {".md", ".txt"}


# ---------------------------------------------------------------------- helpers
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def readable_title(stem: str) -> str:
    return " ".join(w.capitalize() for w in re.split(r"[-_ ]+", stem) if w)


def load_catalog() -> dict:
    return json.loads(CATALOG.read_text()) if CATALOG.exists() else {}


def save_catalog(cat: dict) -> None:
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(dict(sorted(cat.items())), indent=2, ensure_ascii=False))


def person_for(author: str, people: list[dict]) -> str | None:
    a = author.lower()
    for p in people:
        if p["name"].lower() in a or any(alias in a for alias in p.get("aliases", [])):
            return p["name"]
    return None


def support_ratio(statement: str, source_tokens: set[str]) -> float:
    toks = [t for t in tokenize(statement) if len(t) > 3]
    return sum(t in source_tokens for t in toks) / len(toks) if toks else 1.0


def find_sources(target: Path) -> list[Path]:
    if not target.exists():
        raise FileNotFoundError(f"Path not found: {target}")
    files = [target] if target.is_file() else sorted(p for p in target.iterdir() if p.is_file())
    bad = [p.name for p in files if p.suffix.lower() == ".pdf"]
    if bad:
        raise ValueError(f"PDFs are not ingested directly ({', '.join(bad)}). Convert to Markdown study notes in vault/raw/ first.")
    files = [p for p in files if p.suffix.lower() in SUPPORTED and not p.name.startswith(".")]
    for p in files:
        if RAW.resolve() not in p.resolve().parents:
            raise ValueError(f"{p} is outside vault/raw/. Copy originals into vault/raw/ (unchanged) and ingest from there.")
    return files


# ---------------------------------------------------------------------- Gemma extraction
def extraction_schema(concept_names: list[str], sections: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "key_points": {"type": "array", "items": {
                "type": "object",
                "properties": {"point": {"type": "string"}, "section": {"type": "string", "enum": sections}},
                "required": ["point", "section"]}},
            "concepts": {"type": "array", "items": {
                "type": "object",
                "properties": {"name": {"type": "string", "enum": concept_names},
                               "what_the_source_says": {"type": "string"}},
                "required": ["name", "what_the_source_says"]}},
        },
        "required": ["summary", "key_points", "concepts"],
    }


def concept_hits(concepts: list[dict], text: str) -> dict[str, int]:
    """How often each concept's name or aliases occur in a text (harness-side keyword signal)."""
    low = text.lower()
    return {c["name"]: sum(len(re.findall(rf"\b{re.escape(t)}\b", low))
                           for t in {c["name"].lower(), *c.get("aliases", [])}) for c in concepts}


def extract(client: OllamaClient, settings: Settings, meta: dict, body: str, taxonomy: dict) -> tuple[dict, dict]:
    concepts = taxonomy["concept"]
    parts = [(PAGE_RE.sub("", h).strip(), t) for h, t in split_sections(body) if h != "Overview"]
    sections = [h for h, _ in parts]
    # Rank the allowed concepts by keyword hits so a small model sees the likely ones first.
    hits = concept_hits(concepts, body)
    ranked = sorted(concepts, key=lambda c: -hits[c["name"]])
    allowed = "\n".join(f"- {c['name']}: {c['description']}"
                        + (f" (terms for it appear {hits[c['name']]}x in this note)" if hits[c["name"]] else "")
                        for c in ranked)
    user = (
        f"ALLOWED CONCEPT NAMES (most relevant first):\n{allowed}\n\n"
        f"SECTION HEADINGS IN THIS NOTE:\n" + "\n".join(f"- {s}" for s in sections) + "\n\n"
        f"NOTE ({meta.get('wiki_title')}, by {meta.get('author')}):\n{body}"
    )
    messages = [{"role": "system", "content": load_prompt("ingest-instructions.md")},
                {"role": "user", "content": user}]
    opts = {"temperature": settings.ingest_temperature, "num_ctx": settings.ingest_num_ctx}
    result = client.chat(settings.chat_model, messages, options=opts,
                         format=extraction_schema([c["name"] for c in concepts], sections))
    try:
        data = json.loads(result.text)
    except json.JSONDecodeError as e:
        raise LLMError(f"Gemma returned invalid JSON for {meta.get('source_id')}: {e}") from None
    # normalise: merge duplicate concepts, cap list sizes
    merged: dict[str, str] = {}
    for c in data.get("concepts", []):
        merged.setdefault(c["name"], c["what_the_source_says"].strip())
    # A concept named in a section heading is clearly discussed; if Gemma skipped it, ask about
    # that section alone (small, focused follow-up call).
    stats = dict(result.stats)
    for c in concepts:
        if c["name"] in merged:
            continue
        section = next(((h, t) for h, t in parts if concept_hits([c], h)[c["name"]]), None)
        if section is None:
            continue
        follow = client.chat(settings.chat_model, [
            {"role": "system", "content": load_prompt("ingest-instructions.md")},
            {"role": "user", "content": f"In 1-2 sentences, what does this section of {meta.get('author')}'s note say "
                                        f"about the concept '{c['name']}'? Use only the section.\n\n"
                                        f"SECTION '{section[0]}':\n{section[1]}"}],
            options=opts, format={"type": "object", "properties": {"what_the_source_says": {"type": "string"}},
                                  "required": ["what_the_source_says"]})
        merged[c["name"]] = json.loads(follow.text)["what_the_source_says"].strip()
        stats["wall_seconds"] = round(stats["wall_seconds"] + follow.stats["wall_seconds"], 2)
        stats["followups"] = stats.get("followups", 0) + 1
    data["concepts"] = [{"name": n, "what_the_source_says": t} for n, t in list(merged.items())[:8]]
    data["key_points"] = data.get("key_points", [])[:7]
    return data, stats


def review_report(source_id: str, body: str, data: dict) -> tuple[str, int]:
    """Flag generated statements whose content words barely appear in the source note."""
    src = set(tokenize(body))
    rows, flagged = [], 0
    items = [("summary", data["summary"])]
    items += [(f"key point ({k['section']})", k["point"]) for k in data["key_points"]]
    items += [(f"concept: {c['name']}", c["what_the_source_says"]) for c in data["concepts"]]
    for where, text in items:
        r = support_ratio(text, src)
        mark = "CHECK" if r < 0.6 else "ok"
        flagged += mark == "CHECK"
        rows.append(f"| {mark} | {r:.0%} | {where} | {text.replace('|', '/')} |")
    head = (f"# Review: {source_id}\n\nWord-overlap check of Gemma's statements against the original note "
            f"(share of content words found in the note). Rows marked CHECK must be read against the source.\n\n"
            "| flag | overlap | field | statement |\n|---|---|---|---|\n")
    return head + "\n".join(rows) + "\n", flagged


# ---------------------------------------------------------------------- rendering
def fm(fields: dict) -> str:
    lines = ["---"]
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            lines += [f"  - {json.dumps(x, ensure_ascii=False)}" for x in v]
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines + ["---", ""])


def raw_link(entry: dict) -> str:
    return f"[[{entry['raw_path'][:-3] if entry['raw_path'].endswith('.md') else entry['raw_path']}|{Path(entry['raw_path']).name}]]"


def render_all(catalog: dict, taxonomy: dict, model: str) -> list[Path]:
    concepts = {c["name"]: c for c in taxonomy["concept"]}
    people = {p["name"]: p for p in taxonomy["person"]}
    ex = {sid: json.loads((ROOT / e["extraction_path"]).read_text()) for sid, e in catalog.items()}
    # concept -> [(source_id, text)]
    mentions: dict[str, list[tuple[str, str]]] = {}
    for sid, data in ex.items():
        for c in data["concepts"]:
            mentions.setdefault(c["name"], []).append((sid, c["what_the_source_says"]))
    source_concepts = {sid: [c["name"] for c in d["concepts"]] for sid, d in ex.items()}
    written: list[Path] = []
    stamp = datetime.now().strftime("%Y-%m-%d")

    def write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        written.append(path)

    # ---- source pages
    for sid, e in catalog.items():
        d, meta = ex[sid], e["meta"]
        person = e.get("person")
        related = []
        for other, oc in source_concepts.items():
            shared = [c for c in source_concepts[sid] if c in oc]
            if other != sid and shared:
                related.append((len(shared), catalog[other]["wiki_title"], shared))
        related.sort(key=lambda x: (-x[0], x[1]))
        body = [fm({
            "type": "source", "source_id": sid, "author": meta.get("author", ""), "date": meta.get("date", ""),
            "raw_note": e["raw_path"], "original": f"{meta.get('original_file', '')}, PDF pp. {meta.get('original_pages', '')}",
            "public_original": meta.get("public_original", ""), "raw_sha256": e["sha256"][:16],
            "generated_by": f"{GENERATED_MARK} ingest ({e['model']})", "generated_at": e["extracted_at"][:10],
            "review_status": "reviewed" if d.get("reviewed") else "unreviewed"}),
            f"# {e['wiki_title']}\n",
            f"**Author:** {f'[[{person}]]' if person else meta.get('author', '')} · **Date:** {meta.get('date', '')} · "
            f"**Original note:** {raw_link(e)} · **Original document:** {meta.get('original_file', '')} (PDF pp. {meta.get('original_pages', '')})\n",
            "## Summary\n", d["summary"].strip() + "\n",
            "## Key points\n"]
        body += [f"- {k['point'].strip()} *(note section: {k['section']})*" for k in d["key_points"]]
        body += ["", "## Concepts in this source\n"]
        body += [f"- [[{c['name']}]]: {c['what_the_source_says']}" for c in d["concepts"]]
        if related:
            body += ["", "## Related sources\n"]
            body += [f"- [[{t}]]: also discusses {', '.join(f'[[{c}]]' for c in shared)}" for _, t, shared in related[:4]]
        body += ["", f"*Generated from the original note by local Gemma; see [[index]] for navigation.*\n"]
        write(WIKI / "Sources" / f"{e['wiki_title']}.md", "\n".join(body))

    # ---- concept pages
    for name, items in mentions.items():
        c = concepts[name]
        body = [fm({"type": "concept", "group": c["group"], "aliases": c.get("aliases", []),
                    "sources": [s for s, _ in items], "generated_by": f"{GENERATED_MARK} ingest ({model})",
                    "generated_at": stamp}),
                f"# {name}\n", f"*Topic group: {c['group']}.* {c['description']}\n", "## What the sources say\n"]
        for sid, text in items:
            e = catalog[sid]
            who = f" ({e['person']})" if e.get("person") else ""
            body.append(f"- **[[{e['wiki_title']}]]**{who}: {text}")
        rel = [(n, why) for n, why in c.get("related", []) if n in mentions]
        if rel:
            body += ["", "## Related concepts\n"] + [f"- [[{n}]]: {why}" for n, why in rel]
        body += ["", "## Original notes\n"] + [f"- {raw_link(catalog[sid])}" for sid, _ in items]
        write(WIKI / "Concepts" / f"{name}.md", "\n".join(body) + "\n")

    # ---- investor pages
    by_person: dict[str, list[str]] = {}
    for sid, e in catalog.items():
        if e.get("person"):
            by_person.setdefault(e["person"], []).append(sid)
    for name, sids in by_person.items():
        p = people[name]
        pcs = sorted({c for s in sids for c in source_concepts[s]})
        body = [fm({"type": "investor", "aliases": p.get("aliases", []), "generated_by": f"{GENERATED_MARK} ingest",
                    "generated_at": stamp}),
                f"# {name}\n", p["description"] + "\n", "## Sources in this wiki\n"]
        body += [f"- [[{catalog[s]['wiki_title']}]] ({catalog[s]['meta'].get('date', '')[:4]}): {_first_sentence(ex[s]['summary'])}"
                 for s in sorted(sids, key=lambda s: catalog[s]['meta'].get('date', ''))]
        body += ["", "## Concepts discussed\n", ", ".join(f"[[{c}]]" for c in pcs)]
        others = []
        for other, osids in by_person.items():
            if other == name:
                continue
            shared = sorted(set(pcs) & {c for s in osids for c in source_concepts[s]})
            if shared:
                others.append((len(shared), other, shared))
        if others:
            body += ["", "## Investors with overlapping ideas\n"]
            body += [f"- [[{o}]]: both discuss {', '.join(f'[[{c}]]' for c in sh[:4])}"
                     for _, o, sh in sorted(others, key=lambda x: (-x[0], x[1]))]
        write(WIKI / "Investors" / f"{name}.md", "\n".join(body) + "\n")

    write(INDEX_MD, render_index(catalog, ex, taxonomy, mentions, by_person))
    return written


def _first_sentence(text: str) -> str:
    m = re.match(r"(.+?[.!?])(\s|$)", text.strip())
    return m.group(1) if m else text.strip()


def render_index(catalog, ex, taxonomy, mentions, by_person) -> str:
    out = [
        "# Investing Wisdom Wiki\n",
        "A personal study wiki built from my own notes on primary sources by five investors: Warren Buffett, "
        "Howard Marks, Charlie Munger, Nick Sleep and François Rochon. Start with a concept that interests you, follow "
        "its links to the sources that discuss it, and from any source page open the original note in `raw/`.\n",
        "Folders: `raw/` holds the unchanged original notes (the evidence), `wiki/Sources` has one page per source, "
        "`wiki/Concepts` has one page per idea, and `wiki/Investors` has one page per author.\n",
        "## Concepts by topic\n",
    ]
    for group in taxonomy["groups"]["order"]:
        items = [c for c in taxonomy["concept"] if c["group"] == group and c["name"] in mentions]
        if items:
            out.append(f"### {group}\n")
            out += [f"- [[{c['name']}]]: {c['description']} ({len(mentions[c['name']])} source{'s' if len(mentions[c['name']]) != 1 else ''})" for c in items]
            out.append("")
    out.append("## Sources by investor\n")
    for person in [p["name"] for p in taxonomy["person"] if p["name"] in by_person]:
        out.append(f"### [[{person}]]\n")
        for sid in sorted(by_person[person], key=lambda s: catalog[s]["meta"].get("date", "")):
            out.append(f"- [[{catalog[sid]['wiki_title']}]]: {_first_sentence(ex[sid]['summary'])}")
        out.append("")
    out += ["## Source catalog\n", "| Wiki page | Source ID (original filename) | Original document | Review |",
            "|---|---|---|---|"]
    for sid, e in sorted(catalog.items(), key=lambda kv: kv[1]["wiki_title"]):
        m = e["meta"]
        status = "reviewed" if ex[sid].get("reviewed") else "unreviewed"
        out.append(f"| [[{e['wiki_title']}]] | {raw_link(e).replace('|', chr(92) + '|')} | {m.get('original_file', '')}, PDF pp. {m.get('original_pages', '')} | {status} |")
    return "\n".join(out) + "\n"


def remove_stale(written: list[Path]) -> list[Path]:
    keep = {p.resolve() for p in written}
    removed = []
    for path in WIKI.rglob("*.md"):
        if path.resolve() in keep:
            continue
        meta, _ = parse_frontmatter(path.read_text())
        if meta.get("generated_by", "").startswith(GENERATED_MARK):   # never touch hand-written notes
            path.unlink()
            removed.append(path)
    return removed


# ---------------------------------------------------------------------- entry point
def ingest(target: Path, settings: Settings, client: OllamaClient, force: bool = False, log=print) -> dict:
    taxonomy = load_taxonomy()
    files = find_sources(target)
    if not files:
        raise ValueError(f"No .md or .txt sources found in {target}")
    catalog = load_catalog()
    EXTRACTIONS.mkdir(parents=True, exist_ok=True)
    REVIEWS.mkdir(parents=True, exist_ok=True)
    report = {"started": datetime.now().isoformat(timespec="seconds"), "model": settings.chat_model,
              "target": str(target), "sources": []}
    t0 = time.perf_counter()
    for path in files:
        text = path.read_text()
        meta, body = parse_frontmatter(text)
        sid = meta.get("source_id") or path.stem
        title = meta.get("wiki_title") or readable_title(path.stem)
        digest = sha256(path)
        xpath = EXTRACTIONS / f"{sid}.json"
        prev = catalog.get(sid)
        existing = json.loads(xpath.read_text()) if xpath.exists() else None
        unchanged = prev and prev["sha256"] == digest and existing
        reviewed_ok = existing and existing.get("reviewed") and prev and prev["sha256"] == digest
        entry = {"source_id": sid, "wiki_title": title, "raw_path": path.resolve().relative_to(VAULT.resolve()).as_posix(),
                 "sha256": digest, "meta": meta, "person": person_for(meta.get("author", ""), taxonomy["person"]),
                 "extraction_path": xpath.relative_to(ROOT).as_posix()}
        if (unchanged or reviewed_ok) and not force:
            why = "reviewed extraction kept" if reviewed_ok else "unchanged, reused saved extraction"
            log(f"  = {title:<34} {why}")
            catalog[sid] = {**prev, **entry}
            report["sources"].append({"source_id": sid, "status": why})
            continue
        log(f"  … {title:<34} sending {len(body.split())} words to {settings.chat_model}")
        data, stats = extract(client, settings, meta, body, taxonomy)
        data.update({"source_id": sid, "model": settings.chat_model, "reviewed": False,
                     "extracted_at": datetime.now().isoformat(timespec="seconds")})
        review, flagged = review_report(sid, body, data)
        summary = (f"{len(data['concepts'])} concepts, {len(data['key_points'])} key points, "
                   f"{flagged} statements to check · {stats['wall_seconds']}s, {stats['output_tokens']} tokens out")
        if reviewed_ok:
            # Human review is a gate: a fresh Gemma run never silently replaces reviewed content.
            cand = EXTRACTIONS / f"{sid}.candidate.json"
            cand.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            (REVIEWS / f"{sid}.candidate.md").write_text(review)
            catalog[sid] = {**prev, **entry}
            log(f"  + {title:<34} {summary}")
            log(f"    reviewed extraction kept for the wiki; new output saved as {cand.relative_to(ROOT)} for comparison")
            report["sources"].append({"source_id": sid, "status": "re-extracted candidate (reviewed kept)",
                                      "stats": stats, "flagged": flagged})
            continue
        xpath.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        (REVIEWS / f"{sid}.md").write_text(review)
        catalog[sid] = {**entry, "model": settings.chat_model, "extracted_at": data["extracted_at"]}
        log(f"  + {title:<34} {summary}")
        report["sources"].append({"source_id": sid, "status": "extracted", "stats": stats, "flagged": flagged,
                                  "concepts": [c["name"] for c in data["concepts"]]})
    for sid, e in catalog.items():
        e.setdefault("model", settings.chat_model)
        e.setdefault("extracted_at", datetime.now().isoformat(timespec="seconds"))
    save_catalog(catalog)
    written = render_all(catalog, taxonomy, settings.chat_model)
    removed = remove_stale(written)
    report.update({"pages_written": len(written), "pages_removed": [str(p) for p in removed],
                   "seconds": round(time.perf_counter() - t0, 1)})
    return report
