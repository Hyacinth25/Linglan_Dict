#!/usr/bin/env python3
"""Detect suspicious placeholder text (e.g. ???) in key UI source files."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "pages" / "study.py",
    ROOT / "pages" / "study_actions.py",
    ROOT / "pages" / "add_actions.py",
]


def suspicious_strings(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [(-1, f"PARSE_ERROR: {e}")]
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if "???" in value:
                issues.append((getattr(node, "lineno", -1), value))
    return issues


def main() -> int:
    failed = False
    for path in TARGETS:
        if not path.exists():
            continue
        issues = suspicious_strings(path)
        if issues:
            failed = True
            print(f"[FAIL] {path.as_posix()}")
            for line, text in issues:
                snippet = text.replace("\n", "\\n")
                if len(snippet) > 80:
                    snippet = snippet[:77] + "..."
                print(f"  line {line}: {snippet}")
    if failed:
        print("\nText integrity check failed. Please fix corrupted UI strings before shipping.")
        return 1
    print("Text integrity check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
