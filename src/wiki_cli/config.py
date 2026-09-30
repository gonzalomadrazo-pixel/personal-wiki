"""Paths and settings. Everything the harness reads or writes is located from here."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(os.environ.get("WIKI_ROOT", Path(__file__).resolve().parents[2]))

VAULT = ROOT / "vault"             # the Obsidian vault (open this folder in Obsidian)
RAW = VAULT / "raw"                # unchanged original study notes = the evidence
WIKI = VAULT / "wiki"              # generated, reviewed wiki pages
INDEX_MD = VAULT / "index.md"      # human landing page

PROMPTS = ROOT / "prompts"         # persona.md, wiki-instructions.md, ingest-instructions.md
CONFIG = ROOT / "config"           # settings.toml, taxonomy.toml
DATA = ROOT / "data"               # machine files: catalog, extractions, retrieval index
RUNS = ROOT / "runs"               # saved outputs of every ask / search / chat / ingest run
EVIDENCE = ROOT / "evidence"       # evidence cards for grading

CATALOG = DATA / "catalog.json"
EXTRACTIONS = DATA / "extractions"
REVIEWS = DATA / "reviews"
INDEX_DIR = DATA / "index"


@dataclass(frozen=True)
class Settings:
    chat_model: str
    embed_model: str
    ollama_host: str
    keep_alive: str
    use_mmap: bool
    ask_temperature: float
    chat_temperature: float
    ingest_temperature: float
    ask_num_ctx: int
    chat_num_ctx: int
    ingest_num_ctx: int
    chunk_max_words: int
    top_k: int
    chat_top_k: int
    rrf_k: int
    chat_retrieval_min_bm25: float
    history_messages: int


def load_settings() -> Settings:
    raw = tomllib.loads((CONFIG / "settings.toml").read_text())
    m, g, r, c = raw["model"], raw["generation"], raw["retrieval"], raw["chat"]
    return Settings(
        chat_model=os.environ.get("WIKI_MODEL", m["chat_model"]),
        embed_model=os.environ.get("WIKI_EMBED_MODEL", m["embed_model"]),
        ollama_host=os.environ.get("OLLAMA_HOST", m["ollama_host"]),
        keep_alive=m["keep_alive"],
        use_mmap=m.get("use_mmap", True),
        ask_temperature=g["ask_temperature"],
        chat_temperature=g["chat_temperature"],
        ingest_temperature=g["ingest_temperature"],
        ask_num_ctx=g["ask_num_ctx"],
        chat_num_ctx=g["chat_num_ctx"],
        ingest_num_ctx=g["ingest_num_ctx"],
        chunk_max_words=r["chunk_max_words"],
        top_k=r["top_k"],
        chat_top_k=r["chat_top_k"],
        rrf_k=r["rrf_k"],
        chat_retrieval_min_bm25=r["chat_retrieval_min_bm25"],
        history_messages=c["history_messages"],
    )


def load_prompt(name: str) -> str:
    """Instruction files are plain Markdown; the harness passes them to Gemma explicitly."""
    path = PROMPTS / name
    if not path.exists():
        raise FileNotFoundError(f"Missing instruction file: {path}")
    return path.read_text()


def load_taxonomy() -> dict:
    return tomllib.loads((CONFIG / "taxonomy.toml").read_text())
