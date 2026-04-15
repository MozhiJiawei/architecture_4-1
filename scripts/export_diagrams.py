from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


BACKGROUND = "#ffffff"
DEFAULT_GROUP_FILL = "#f8f9fa"
DEFAULT_GROUP_STROKE = "#6c757d"
DEFAULT_NODE_FILL = "#ffffff"
DEFAULT_NODE_STROKE = "#1f2937"
DEFAULT_EDGE_STROKE = "#374151"
DEFAULT_TEXT_COLOR = "#111827"
FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/msyhbd.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/simsun.ttc"),
]


def parse_style(style: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in style.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        result[key] = value
    return result


def iter_targets(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(target.glob("*.drawio"))
    raise FileNotFoundError(f"Target not found: {target}")


def get_canvas_size(root: ET.Element) -> tuple[int, int]:
    model = root.find("./diagram/mxGraphModel")
    if model is None:
        return 1600, 1200
    width = int(float(model.attrib.get("pageWidth", "1600")))
    height = int(float(model.attrib.get("pageHeight", "1200")))
    return width, height


def load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = FONT_CANDIDATES[1:] + FONT_CANDIDATES[:1] if bold else FONT_CANDIDATES
    for font_path in candidates:
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def split_tokens(raw_line: str) -> list[str]:
    if " " in raw_line:
        return raw_line.split()
    return list(raw_line)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    for raw_line in text.replace("&#10;", "\n").splitlines():
        tokens = split_tokens(raw_line)
        if not tokens:
            lines.append("")
            continue
        current = tokens[0]
        for token in tokens[1:]:
            separator = " " if len(token) > 1 and " " in raw_line else ""
            candidate = f"{current}{separator}{token}"
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = token
        lines.append(current)
    return lines


def draw_multiline_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
    *,
    line_height: int,
    fill: str,
) -> None:
    x, y, width, height = box
    lines = wrap_text(draw, text, font, max_width=max(40, width - 16))
    text_y = y + 8
    for line in lines:
        if text_y + line_height > y + height - 4:
            break
        draw.text((x + 8, text_y), line, fill=fill, font=font)
        text_y += line_height


def choose_anchor_points(
    source_box: tuple[int, int, int, int],
    target_box: tuple[int, int, int, int],
) -> tuple[tuple[int, int], tuple[int, int]]:
    sx, sy, sw, sh = source_box
    tx, ty, tw, th = target_box
    source_center = (sx + sw // 2, sy + sh // 2)
    target_center = (tx + tw // 2, ty + th // 2)
    dx = target_center[0] - source_center[0]
    dy = target_center[1] - source_center[1]

    if abs(dx) >= abs(dy):
        if dx >= 0:
            return (sx + sw, sy + sh // 2), (tx, ty + th // 2)
        return (sx, sy + sh // 2), (tx + tw, ty + th // 2)
    if dy >= 0:
        return (sx + sw // 2, sy + sh), (tx + tw // 2, ty)
    return (sx + sw // 2, sy), (tx + tw // 2, ty + th)


def point_from_relative(box: tuple[int, int, int, int], rx: float, ry: float) -> tuple[int, int]:
    x, y, w, h = box
    return int(x + (w * rx)), int(y + (h * ry))


def choose_anchor_points_from_style(
    source_box: tuple[int, int, int, int],
    target_box: tuple[int, int, int, int],
    style: dict[str, str],
) -> tuple[tuple[int, int], tuple[int, int]]:
    if {"exitX", "exitY", "entryX", "entryY"} <= style.keys():
        start = point_from_relative(
            source_box,
            float(style["exitX"]),
            float(style["exitY"]),
        )
        end = point_from_relative(
            target_box,
            float(style["entryX"]),
            float(style["entryY"]),
        )
        return start, end
    return choose_anchor_points(source_box, target_box)


def orthogonal_path(
    start: tuple[int, int],
    end: tuple[int, int],
) -> list[tuple[int, int]]:
    sx, sy = start
    tx, ty = end
    if abs(sx - tx) >= abs(sy - ty):
        mid_x = (sx + tx) // 2
        return [start, (mid_x, sy), (mid_x, ty), end]
    mid_y = (sy + ty) // 2
    return [start, (sx, mid_y), (tx, mid_y), end]


def parse_waypoints(cell: ET.Element) -> list[tuple[int, int]]:
    points_parent = cell.find("./mxGeometry/Array[@as='points']")
    if points_parent is None:
        return []
    points: list[tuple[int, int]] = []
    for point in points_parent.findall("./mxPoint"):
        try:
            x = int(float(point.attrib["x"]))
            y = int(float(point.attrib["y"]))
        except (KeyError, ValueError):
            continue
        points.append((x, y))
    return points


def draw_polyline(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    *,
    fill: str,
    width: int,
    dashed: bool,
) -> None:
    for start, end in zip(points, points[1:]):
        if dashed:
            draw.line([start, end], fill=fill, width=width)
        else:
            draw.line([start, end], fill=fill, width=width)


def label_position(points: list[tuple[int, int]]) -> tuple[int, int]:
    middle_index = len(points) // 2
    ax, ay = points[middle_index - 1]
    bx, by = points[middle_index]
    x = (ax + bx) // 2
    y = (ay + by) // 2
    return x + 8, y - 18


def export_drawio_to_png(drawio_path: Path, output_path: Path) -> None:
    root = ET.parse(drawio_path).getroot()
    width, height = get_canvas_size(root)
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    group_font = load_font(18, bold=True)
    node_font = load_font(17)
    edge_font = load_font(15)

    cells = root.findall(".//mxCell")
    geometries: dict[str, tuple[int, int, int, int]] = {}
    edges: list[ET.Element] = []

    for cell in cells:
        geometry = cell.find("./mxGeometry")
        if geometry is None:
            continue
        cell_id = cell.attrib.get("id", "")
        if cell.attrib.get("edge") == "1":
            edges.append(cell)
            continue
        if cell.attrib.get("vertex") != "1":
            continue
        x = int(float(geometry.attrib.get("x", "0")))
        y = int(float(geometry.attrib.get("y", "0")))
        w = int(float(geometry.attrib.get("width", "0")))
        h = int(float(geometry.attrib.get("height", "0")))
        parent = cell.attrib.get("parent", "")
        if parent in geometries:
            px, py, _, _ = geometries[parent]
            x += px
            y += py
        geometries[cell_id] = (x, y, w, h)

        style = parse_style(cell.attrib.get("style", ""))
        value = cell.attrib.get("value", "")
        if "swimlane" in cell.attrib.get("style", ""):
            group_fill = style.get("fillColor", DEFAULT_GROUP_FILL)
            group_stroke = style.get("strokeColor", DEFAULT_GROUP_STROKE)
            draw.rounded_rectangle((x, y, x + w, y + h), radius=4, outline=group_stroke, fill=group_fill, width=2)
            start_size = int(style.get("startSize", "36"))
            draw.rectangle((x, y, x + w, y + start_size), outline=group_stroke, fill=group_fill, width=2)
            draw_multiline_text(
                draw,
                (x + 4, y + 4, w - 8, start_size - 8),
                value,
                group_font,
                line_height=22,
                fill=style.get("fontColor", DEFAULT_TEXT_COLOR),
            )
        else:
            node_fill = style.get("fillColor", DEFAULT_NODE_FILL)
            node_stroke = style.get("strokeColor", DEFAULT_NODE_STROKE)
            draw.rounded_rectangle((x, y, x + w, y + h), radius=8, outline=node_stroke, fill=node_fill, width=2)
            draw_multiline_text(
                draw,
                (x + 4, y + 4, w - 8, h - 8),
                value,
                node_font,
                line_height=20,
                fill=style.get("fontColor", DEFAULT_TEXT_COLOR),
            )

    for cell in edges:
        source = cell.attrib.get("source", "")
        target = cell.attrib.get("target", "")
        if source not in geometries or target not in geometries:
            continue
        style = parse_style(cell.attrib.get("style", ""))
        start, end = choose_anchor_points_from_style(geometries[source], geometries[target], style)
        dashed = style.get("dashed") == "1"
        edge_stroke = style.get("strokeColor", DEFAULT_EDGE_STROKE)
        edge_font_color = style.get("fontColor", edge_stroke)
        waypoints = parse_waypoints(cell)
        points = [start, *waypoints, end] if waypoints else orthogonal_path(start, end)
        if dashed:
            draw_polyline(draw, points, fill=edge_stroke, width=2, dashed=True)
        else:
            draw_polyline(draw, points, fill=edge_stroke, width=3, dashed=False)
        label = cell.attrib.get("value", "")
        if label:
            label_x, label_y = label_position(points)
            bbox = draw.textbbox((label_x, label_y), label, font=edge_font)
            draw.rounded_rectangle(
                (bbox[0] - 4, bbox[1] - 2, bbox[2] + 4, bbox[3] + 2),
                radius=4,
                fill=BACKGROUND,
                outline=None,
            )
            draw.text((label_x, label_y), label, fill=edge_font_color, font=edge_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


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
        choices=["png"],
        help="Export format",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for exported previews (defaults to <target>/exports)",
    )
    args = parser.parse_args()

    target = Path(args.target)
    try:
        files = iter_targets(target)
    except Exception as exc:
        print(f"export_diagrams.py failed: {exc}")
        return 1

    if not files:
        print(f"export_diagrams.py failed: no .drawio files found in {target}")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else (target.parent / "exports" if target.is_file() else target / "exports")
    output_dir.mkdir(parents=True, exist_ok=True)

    for drawio_path in files:
        output_path = output_dir / f"{drawio_path.stem}.png"
        export_drawio_to_png(drawio_path, output_path)
        print(f"Exported {drawio_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
