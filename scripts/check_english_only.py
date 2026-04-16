from __future__ import annotations

import re
import sys
from pathlib import Path


HAN_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
TEXT_SUFFIXES = {".md", ".py", ".html", ".js", ".ts", ".yaml", ".yml"}


def iter_targets(repo_root: Path) -> list[Path]:
    targets = [repo_root / "SKILL.md"]
    scan_roots = [repo_root / "scripts", repo_root / "references"]
    for root in scan_roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts:
                continue
            if path.suffix.lower() in TEXT_SUFFIXES:
                targets.append(path)
    return targets


def scan_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if HAN_PATTERN.search(line):
            errors.append(f"{path}:{line_number}: contains Han characters")
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    failures: list[str] = []
    for path in iter_targets(repo_root):
        failures.extend(scan_file(path))

    if failures:
        print("English-only check failed for SKILL.md, scripts/, or references/:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("English-only check passed for SKILL.md, scripts/, and references/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
