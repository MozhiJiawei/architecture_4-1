from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render draw.io files from intermediate 4+1 view models."
    )
    parser.add_argument("input", nargs="?", help="Path to a view model or model directory")
    parser.add_argument(
        "--output-dir",
        default="docs/architecture",
        help="Directory for rendered .drawio files",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("render_drawio.py placeholder")
    print(f"input={args.input!r}")
    print(f"output_dir={output_dir}")
    print("TODO: load intermediate models and emit draw.io XML")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
