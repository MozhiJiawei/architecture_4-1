from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate generated draw.io files for the 4+1 skill."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="docs/architecture",
        help="File or directory to validate",
    )
    args = parser.parse_args()

    target = Path(args.target)
    print("validate_drawio.py placeholder")
    print(f"target={target}")
    print("TODO: add XML parse checks and style-profile validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
