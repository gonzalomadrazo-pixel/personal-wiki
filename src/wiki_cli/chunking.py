"""Read Markdown notes and split them into retrievable passages.

A passage keeps its source path, section heading and original PDF page range, so
every search result and citation can be traced back to the evidence.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

PAGE_RE = re.compile(r"\((PDF pp?\.[^)]*)\)")


@dataclass
class Passage:
    id: str              # "<source_id>#<n>"
    source_id: str
    kind: str            # "source" (raw evidence) or "wiki" (generated page)
    path: str            # path relative to the vault, e.g. raw/buffett-1987-letter.md
    title: str           # human title of the document or page
    section: str         # section heading the passage came from
    pages: str           # original PDF page range for that section, if known
    text: str

    def to_dict(self) -> dict:
        return asdict(self)

    def label(self) -> str:
        loc = f", {self.pages}" if self.pages else ""
        return f"{self.path} › {self.section}{loc}"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Minimal YAML frontmatter reader (key: value lines), enough for our notes."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    meta = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"')
    return meta, text[end + 4:].lstrip("\n")


def split_sections(body: str) -> list[tuple[str, str]]:
    """Split on '## ' headings. Text before the first heading is the 'Overview' section."""
    sections, heading, buf = [], "Overview", []
    for line in body.splitlines():
        if line.startswith("## "):
            if "".join(buf).strip():
                sections.append((heading, "\n".join(buf).strip()))
            heading, buf = line[3:].strip(), []
        elif line.startswith("# "):
            continue  # document title; already known from frontmatter
        else:
            buf.append(line)
    if "".join(buf).strip():
        sections.append((heading, "\n".join(buf).strip()))
    return sections


def _pack(blocks: list[str], max_words: int) -> list[str]:
    """Group paragraphs/bullets into passages of at most ~max_words, never splitting a bullet."""
    out, cur, n = [], [], 0
    for block in blocks:
        w = len(block.split())
        if cur and n + w > max_words:
            out.append("\n".join(cur))
            cur, n = [], 0
        cur.append(block)
        n += w
    if cur:
        out.append("\n".join(cur))
    return out


def _blocks(text: str) -> list[str]:
    """Paragraphs and top-level bullets (with their indented sub-lines) as units."""
    blocks, cur = [], []
    for line in text.splitlines():
        top_level_item = re.match(r"^(- |\d+\. |\*\*)", line)
        if not line.strip() or (top_level_item and cur):
            if cur:
                blocks.append("\n".join(cur))
            cur = [line] if line.strip() else []
        else:
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return [b for b in blocks if b.strip()]


def chunk_note(path: Path, vault: Path, kind: str, max_words: int) -> list[Passage]:
    text = path.read_text()
    meta, body = parse_frontmatter(text)
    rel = path.relative_to(vault).as_posix()
    source_id = meta.get("source_id") or path.stem
    title = meta.get("wiki_title") or meta.get("title") or path.stem
    passages = []
    for heading, section_text in split_sections(body):
        # A note's short intro line ("These are my notes on ...") describes the note rather than the
        # source. As a passage it matched almost any question and crowded real evidence out of the
        # top-k (found in eval dry run 1, test 3), so it is not indexed.
        if heading == "Overview" and len(section_text.split()) < 60:
            continue
        m = PAGE_RE.search(heading)
        pages = m.group(1) if m else ""
        clean_heading = PAGE_RE.sub("", heading).strip()
        for part in _pack(_blocks(section_text), max_words):
            passages.append(Passage(
                id=f"{source_id}#{len(passages) + 1}",
                source_id=source_id, kind=kind, path=rel, title=title,
                section=clean_heading, pages=pages, text=part,
            ))
    return passages
