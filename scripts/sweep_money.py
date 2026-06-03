"""One-shot sweep — replace `${{ EXPR|floatformat:N }}` with `{{ EXPR|money }}`.

Run from repo root:  python scripts/sweep_money.py
Idempotent — running twice is a no-op (only matches `floatformat`).
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIRS = [
    ROOT / "src" / "apps" / "ui" / "templates",
    ROOT / "src" / "templates",
]

# ${{  EXPR  |floatformat:0..2 [maybe more filters]  }}
# EXPR ⇒ anything except {, }, |
MONEY_RE = re.compile(r"\$\{\{\s*([^{}|]+?)\s*\|\s*floatformat[^}]*\}\}")

LOAD_TAG = "{% load money %}"


def inject_load(text: str) -> str:
    """Make sure `{% load money %}` is in the file once, after the first `{% extends %}` line."""
    if LOAD_TAG in text:
        return text
    m = re.search(r"\{%\s*extends\s+[^%]+%\}", text)
    if m:
        end = m.end()
        return text[:end] + "\n" + LOAD_TAG + text[end:]
    return LOAD_TAG + "\n" + text


def sweep_file(path: Path) -> int:
    raw = path.read_text(encoding="utf-8")
    new = MONEY_RE.sub(lambda m: "{{ " + m.group(1).strip() + "|money }}", raw)
    if new == raw:
        return 0
    new = inject_load(new)
    path.write_text(new, encoding="utf-8")
    return len(MONEY_RE.findall(raw))


def main() -> int:
    total_files = 0
    total_replacements = 0
    for root in TEMPLATE_DIRS:
        if not root.exists():
            continue
        for html in root.rglob("*.html"):
            n = sweep_file(html)
            if n:
                total_files += 1
                total_replacements += n
                rel = html.relative_to(ROOT)
                print(f"  {rel}  ({n})")
    print(f"\nDone. {total_replacements} replacements in {total_files} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
