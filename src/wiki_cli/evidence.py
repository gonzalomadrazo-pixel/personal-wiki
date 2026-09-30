"""Save every run so a reader can inspect results without rerunning the model."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from .config import RUNS


def slug(text: str, n: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:n] or "run"


def save_run(mode: str, title: str, record: dict) -> Path:
    """Write runs/<mode>/<timestamp>-<slug>.json. The mode label (ask/search/chat/ingest) and
    execution setting (local) are part of every record."""
    folder = RUNS / mode
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = folder / f"{stamp}-{slug(title)}.json"
    record = {"mode": mode, "execution": "local", "saved_at": datetime.now().isoformat(timespec="seconds"), **record}
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    return path


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
