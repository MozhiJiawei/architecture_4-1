from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect exported diagram previews for obvious failures."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="docs/architecture",
        help="Directory containing exported previews",
    )
    args = parser.parse_args()

    target = Path(args.target)
    print("inspect_exports.py placeholder")
    print(f"target={target}")
    print("TODO: detect blank images, missing exports, and other gross failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
