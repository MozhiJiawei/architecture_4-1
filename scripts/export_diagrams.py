from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export generated draw.io diagrams to preview formats."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="docs/architecture",
        help="Directory containing .drawio files",
    )
    parser.add_argument(
        "--format",
        default="png",
        choices=["png", "svg"],
        help="Export format",
    )
    args = parser.parse_args()

    target = Path(args.target)
    print("export_diagrams.py placeholder")
    print(f"target={target}")
    print(f"format={args.format}")
    print("TODO: export draw.io files via draw.io CLI or compatible renderer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
