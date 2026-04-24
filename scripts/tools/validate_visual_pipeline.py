from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_step(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run draw.io validation, export previews, and visual inspection sequentially."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="docs/architecture",
        help="File or directory containing .drawio files",
    )
    parser.add_argument(
        "--exports-dir",
        help="Directory for exported previews (defaults to <target>/exports or sibling exports directory)",
    )
    args = parser.parse_args()

    target = Path(args.target)
    exports_dir = Path(args.exports_dir) if args.exports_dir else (
        target.parent / "exports" if target.is_file() else target / "exports"
    )

    tools_root = Path(__file__).resolve().parent
    python = sys.executable

    run_step([python, str(tools_root / "validate_drawio.py"), str(target)])
    run_step([
        python,
        str(tools_root / "export_diagrams.py"),
        str(target),
        "--output-dir",
        str(exports_dir),
    ])
    run_step([python, str(tools_root / "inspect_exports.py"), str(exports_dir)])
    print(f"Visual validation pipeline passed. Exports: {exports_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
