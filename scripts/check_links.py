"""Check that every [[wikilink]] in the vault resolves to exactly one note (Obsidian rules)."""
import re
import sys
from collections import Counter
from pathlib import Path

VAULT = Path(__file__).resolve().parents[1] / "vault"
notes = [p for p in VAULT.rglob("*.md") if ".obsidian" not in p.parts]
by_name = Counter(p.stem for p in notes)
paths = {p.relative_to(VAULT).with_suffix("").as_posix() for p in notes}
bad, total = [], 0
for p in notes:
    for target in re.findall(r"\[\[([^\]|#]+)", p.read_text()):
        total += 1
        t = target.strip().rstrip("\\")
        if "/" in t:
            ok = t in paths
        else:
            ok = by_name[t] == 1
        if not ok:
            bad.append(f"{p.relative_to(VAULT)} → [[{t}]] ({'ambiguous' if by_name[t] > 1 else 'missing'})")
dupes = [n for n, c in by_name.items() if c > 1]
print(f"{len(notes)} notes, {total} links checked, {len(bad)} broken, duplicate names: {dupes or 'none'}")
print("\n".join(bad))
sys.exit(1 if bad or dupes else 0)
