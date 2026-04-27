from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from tools.export_diagrams import crop_png_whitespace, flatten_png_background


TEST_OUTPUT_DIR = REPO_ROOT / "tmp-artifacts" / "test-rendered" / "test_export_diagrams"


def test_crop_png_whitespace_trims_canvas_and_keeps_margin() -> None:
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image_path = TEST_OUTPUT_DIR / "wide-margin.png"

    image = Image.new("RGBA", (200, 160), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 60, 119, 99), fill=(31, 41, 55, 255))
    image.save(image_path)

    crop_png_whitespace(image_path, margin=10)

    with Image.open(image_path) as cropped:
        assert cropped.size == (60, 60)


def test_flatten_png_background_preserves_cropped_size() -> None:
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image_path = TEST_OUTPUT_DIR / "transparent-margin.png"

    image = Image.new("RGBA", (100, 100), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 59, 59), fill=(31, 41, 55, 255))
    image.save(image_path)

    crop_png_whitespace(image_path, margin=5)
    flatten_png_background(image_path)

    with Image.open(image_path) as cropped:
        assert cropped.size == (30, 30)
        assert cropped.mode == "RGB"
