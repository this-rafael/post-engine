#!/usr/bin/env python3
"""Move cada spec_NNN.md para specs/spec-NNN/spec_NNN.md e atualiza links.

Uso: python scripts/reorganize_specs.py
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "specs"

SPEC_FILE_RE = re.compile(r"^spec_(\d{3})\.md$")
SPEC_LINK_RE = re.compile(r"\(spec_(\d{3})\.md\)")
SPEC_HEADING_RE = re.compile(r"^##\s+SPEC-(\d{3})\b")


def main() -> None:
    moved: list[tuple[str, str]] = []
    for src in sorted(SPECS.glob("spec_*.md")):
        m = SPEC_FILE_RE.match(src.name)
        if not m:
            continue
        num = m.group(1)
        target_dir = SPECS / f"spec-{num}"
        target_dir.mkdir(exist_ok=True)
        target = target_dir / src.name
        shutil.move(str(src), str(target))
        moved.append((num, str(target.relative_to(ROOT))))

    rewrite_checklist(moved)
    rewrite_global(moved)

    print(f"Movidas {len(moved)} specs para pastas próprias.")
    for num, path in moved[:5]:
        print(f"  SPEC-{num} -> {path}")
    if len(moved) > 5:
        print(f"  ... e mais {len(moved) - 5}")


def rewrite_checklist(moved: list[tuple[str, str]]) -> None:
    path = SPECS / "checklist.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")

    def repl(match: re.Match[str]) -> str:
        num = match.group(1)
        return f"(spec-{num}/spec_{num}.md)"

    new_text = SPEC_LINK_RE.sub(repl, text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print(f"  Links atualizados em {path.name}")


def rewrite_global(moved: list[tuple[str, str]]) -> None:
    path = SPECS / "global.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")

    def repl(match: re.Match[str]) -> str:
        return f"## SPEC-{match.group(1)}"

    new_text = SPEC_HEADING_RE.sub(repl, text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print(f"  Headings atualizados em {path.name}")


if __name__ == "__main__":
    main()
