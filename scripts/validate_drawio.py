from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from orthogonal_router import Box


ALLOWED_FONT_SIZES = {"12"}
ALLOWED_START_SIZES = {"36", "44"}
MAX_NODE_LABEL_CHARS = 80
MAX_GROUP_LABEL_CHARS = 80
MAX_EDGE_LABEL_CHARS = 44
MAX_NODE_LINES = 3
MAX_GROUP_LINES = 2
MAX_EDGE_LINES = 2
GEOMETRY_EPSILON = 1e-6
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
NON_BUDGET_FILL_COLORS = {"#f8f9fa", "#ffffff"}
NON_BUDGET_STROKE_COLORS = {"#6c757d", "#1f2937", "#374151"}
SEMANTIC_COLOR_BUDGET = 4
MIN_NESTED_GROUP_SIDE_GAP = 32.0
MIN_NESTED_GROUP_TOP_GAP = 28.0
MIN_NESTED_GROUP_BOTTOM_GAP = 32.0


def is_valid_color(value: str | None) -> bool:
    if not value:
        return False
    if value.lower() == "none":
        return True
    return bool(HEX_COLOR_PATTERN.fullmatch(value))


def format_color_list(colors: list[str]) -> str:
    return ", ".join(colors) if colors else "(none)"


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


def get_root(xml_path: Path) -> ET.Element:
    tree = ET.parse(xml_path)
    return tree.getroot()


def normalize_value(value: str) -> str:
    return value.replace("&#10;", "\n").strip()


def count_lines(value: str) -> int:
    text = normalize_value(value)
    return len(text.splitlines()) if text else 0


def plain_length(value: str) -> int:
    text = normalize_value(value)
    return len(text.replace("\n", " ").strip())


def point_from_relative(box: tuple[float, float, float, float], rx: float, ry: float) -> tuple[float, float]:
    x, y, width, height = box
    return x + (width * rx), y + (height * ry)


def orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return ((b[0] - a[0]) * (c[1] - a[1])) - ((b[1] - a[1]) * (c[0] - a[0]))


def is_close(value: float, target: float = 0.0) -> bool:
    return abs(value - target) <= GEOMETRY_EPSILON


def points_equal(first: tuple[float, float], second: tuple[float, float]) -> bool:
    return is_close(first[0], second[0]) and is_close(first[1], second[1])


def point_in_box(point: tuple[float, float], box: Box) -> bool:
    x, y = point
    return (
        box.left <= x <= box.right
        and box.top <= y <= box.bottom
    )


def on_segment(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    return (
        min(a[0], c[0]) - GEOMETRY_EPSILON <= b[0] <= max(a[0], c[0]) + GEOMETRY_EPSILON
        and min(a[1], c[1]) - GEOMETRY_EPSILON <= b[1] <= max(a[1], c[1]) + GEOMETRY_EPSILON
    )


def segment_overlap_length(
    first: tuple[tuple[float, float], tuple[float, float]],
    second: tuple[tuple[float, float], tuple[float, float]],
) -> float:
    (ax1, ay1), (ax2, ay2) = first
    (bx1, by1), (bx2, by2) = second
    if abs(ax1 - ax2) >= abs(ay1 - ay2):
        start = max(min(ax1, ax2), min(bx1, bx2))
        end = min(max(ax1, ax2), max(bx1, bx2))
    else:
        start = max(min(ay1, ay2), min(by1, by2))
        end = min(max(ay1, ay2), max(by1, by2))
    return end - start


def segments_conflict(
    first: tuple[tuple[float, float], tuple[float, float]],
    second: tuple[tuple[float, float], tuple[float, float]],
) -> bool:
    p1, q1 = first
    p2, q2 = second

    shared_points = [
        candidate
        for candidate in (p1, q1)
        if points_equal(candidate, p2) or points_equal(candidate, q2)
    ]
    if len(shared_points) == 2:
        return False

    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    if (
        ((o1 > GEOMETRY_EPSILON and o2 < -GEOMETRY_EPSILON) or (o1 < -GEOMETRY_EPSILON and o2 > GEOMETRY_EPSILON))
        and ((o3 > GEOMETRY_EPSILON and o4 < -GEOMETRY_EPSILON) or (o3 < -GEOMETRY_EPSILON and o4 > GEOMETRY_EPSILON))
    ):
        return True

    collinear = is_close(o1) and is_close(o2) and is_close(o3) and is_close(o4)
    if collinear:
        return segment_overlap_length(first, second) > GEOMETRY_EPSILON

    for point, start, end in ((p2, p1, q1), (q2, p1, q1), (p1, p2, q2), (q1, p2, q2)):
        if is_close(orientation(start, end, point)) and on_segment(start, point, end):
            if any(points_equal(point, shared) for shared in shared_points):
                continue
            return True

    return False


def segment_intersects_box(
    start: tuple[float, float],
    end: tuple[float, float],
    box: Box,
) -> bool:
    if point_in_box(start, box) or point_in_box(end, box):
        return True

    corners = [
        (box.left, box.top),
        (box.right, box.top),
        (box.right, box.bottom),
        (box.left, box.bottom),
    ]
    edges = [
        (corners[0], corners[1]),
        (corners[1], corners[2]),
        (corners[2], corners[3]),
        (corners[3], corners[0]),
    ]
    if any(segments_conflict((start, end), edge) for edge in edges):
        return True

    midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    return point_in_box(midpoint, box)


def parse_waypoints(cell: ET.Element) -> list[tuple[float, float]]:
    points_parent = cell.find("./mxGeometry/Array[@as='points']")
    if points_parent is None:
        return []
    points: list[tuple[float, float]] = []
    for point in points_parent.findall("./mxPoint"):
        try:
            x = float(point.attrib["x"])
            y = float(point.attrib["y"])
        except (KeyError, ValueError):
            continue
        points.append((x, y))
    return points


def edge_points(
    cell: ET.Element,
    boxes: dict[str, tuple[float, float, float, float]],
) -> list[tuple[float, float]]:
    source = cell.attrib.get("source", "")
    target = cell.attrib.get("target", "")
    if source not in boxes or target not in boxes:
        return []
    style = parse_style(cell.attrib.get("style", ""))
    source_box = boxes[source]
    target_box = boxes[target]
    try:
        start = point_from_relative(source_box, float(style.get("exitX", "0.5")), float(style.get("exitY", "0.5")))
        end = point_from_relative(target_box, float(style.get("entryX", "0.5")), float(style.get("entryY", "0.5")))
    except ValueError:
        return []
    return [start, *parse_waypoints(cell), end]


def box_overlap_area(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> float:
    fx, fy, fw, fh = first
    sx, sy, sw, sh = second
    overlap_x = min(fx + fw, sx + sw) - max(fx, sx)
    overlap_y = min(fy + fh, sy + sh) - max(fy, sy)
    if overlap_x <= GEOMETRY_EPSILON or overlap_y <= GEOMETRY_EPSILON:
        return 0.0
    return overlap_x * overlap_y


def box_contains(
    outer: tuple[float, float, float, float],
    inner: tuple[float, float, float, float],
) -> bool:
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return (
        ix >= ox - GEOMETRY_EPSILON
        and iy >= oy - GEOMETRY_EPSILON
        and ix + iw <= ox + ow + GEOMETRY_EPSILON
        and iy + ih <= oy + oh + GEOMETRY_EPSILON
    )


def is_ancestor(cell_id: str, ancestor_id: str, parent_map: dict[str, str]) -> bool:
    current = parent_map.get(cell_id, "")
    while current:
        if current == ancestor_id:
            return True
        current = parent_map.get(current, "")
    return False


def validate_file(xml_path: Path) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    try:
        root = get_root(xml_path)
    except ET.ParseError as exc:
        return [], [f"{xml_path}: XML parse error: {exc}"]

    cells = root.findall(".//mxCell")
    if not cells:
        return [], [f"{xml_path}: no mxCell elements found"]

    parent_map = {cell.attrib.get("id", ""): cell.attrib.get("parent", "") for cell in cells}
    vertex_cells = [cell for cell in cells if cell.attrib.get("vertex") == "1"]
    edge_cells = [cell for cell in cells if cell.attrib.get("edge") == "1"]
    swimlanes = [cell for cell in vertex_cells if "swimlane" in cell.attrib.get("style", "")]
    node_cells = [cell for cell in vertex_cells if cell not in swimlanes]

    if not swimlanes:
        errors.append(f"{xml_path}: diagram has no grouping swimlanes")
    if not node_cells:
        errors.append(f"{xml_path}: diagram has no rendered nodes")
    diagram_kind = xml_path.stem.lower()
    if not edge_cells and diagram_kind != "use-case-catalog-view":
        warnings.append(f"{xml_path}: diagram has no edges")

    fill_counter: Counter[str] = Counter()
    stroke_counter: Counter[str] = Counter()
    font_size_counter: Counter[str] = Counter()

    for cell in vertex_cells:
        style = parse_style(cell.attrib.get("style", ""))
        fill = style.get("fillColor")
        stroke = style.get("strokeColor")
        font_size = style.get("fontSize")
        value = cell.attrib.get("value", "")
        cell_id = cell.attrib.get("id")
        is_group = "swimlane" in cell.attrib.get("style", "")

        if fill:
            fill_counter[fill] += 1
            if not is_valid_color(fill):
                errors.append(f"{xml_path}: invalid fillColor {fill!r} on cell {cell_id}")
        if stroke:
            stroke_counter[stroke] += 1
            if not is_valid_color(stroke):
                errors.append(f"{xml_path}: invalid strokeColor {stroke!r} on cell {cell_id}")
        font_color = style.get("fontColor")
        if font_color and not is_valid_color(font_color):
            errors.append(f"{xml_path}: invalid fontColor {font_color!r} on cell {cell_id}")
        if font_size:
            font_size_counter[font_size] += 1
            if font_size not in ALLOWED_FONT_SIZES:
                errors.append(f"{xml_path}: disallowed fontSize {font_size!r} on cell {cell_id}")

        if "fontFamily" in style:
            warnings.append(f"{xml_path}: explicit fontFamily on {cell_id} - prefer default draw.io font stack")

        if is_group:
            start_size = style.get("startSize")
            if start_size not in ALLOWED_START_SIZES:
                errors.append(f"{xml_path}: unexpected swimlane startSize {start_size!r} on cell {cell_id}")

        label_length = plain_length(value)
        line_count = count_lines(value)
        if is_group:
            if label_length > MAX_GROUP_LABEL_CHARS:
                warnings.append(f"{xml_path}: group label on {cell_id} is long ({label_length} chars)")
            if line_count > MAX_GROUP_LINES:
                warnings.append(f"{xml_path}: group label on {cell_id} has too many lines ({line_count})")
        else:
            if label_length > MAX_NODE_LABEL_CHARS:
                warnings.append(f"{xml_path}: node label on {cell_id} is long ({label_length} chars)")
            if line_count > MAX_NODE_LINES:
                warnings.append(f"{xml_path}: node label on {cell_id} has too many lines ({line_count})")
            normalized = normalize_value(value)
            if normalized.endswith("."):
                warnings.append(f"{xml_path}: node label on {cell_id} ends like prose; prefer terse noun phrases")

    budget_fill_colors = sorted(color for color in fill_counter if color.lower() not in NON_BUDGET_FILL_COLORS)
    budget_stroke_colors = sorted(color for color in stroke_counter if color.lower() not in NON_BUDGET_STROKE_COLORS)
    if len(budget_fill_colors) > SEMANTIC_COLOR_BUDGET:
        warnings.append(
            f"{xml_path}: semantic fill palette uses {len(budget_fill_colors)} families "
            f"(budget {SEMANTIC_COLOR_BUDGET}). Counted: {format_color_list(budget_fill_colors)}. "
            f"Ignored baseline fills: {format_color_list(sorted(NON_BUDGET_FILL_COLORS))}."
        )
    if len(budget_stroke_colors) > SEMANTIC_COLOR_BUDGET:
        warnings.append(
            f"{xml_path}: semantic stroke palette uses {len(budget_stroke_colors)} families "
            f"(budget {SEMANTIC_COLOR_BUDGET}). Counted: {format_color_list(budget_stroke_colors)}. "
            f"Ignored baseline strokes: {format_color_list(sorted(NON_BUDGET_STROKE_COLORS))}."
        )
    if len(font_size_counter) > 1:
        warnings.append(f"{xml_path}: inconsistent font sizes ({sorted(font_size_counter)})")

    edge_styles = [parse_style(cell.attrib.get("style", "")) for cell in edge_cells]
    if edge_styles:
        end_arrows = {style.get("endArrow") for style in edge_styles}
        allowed_use_case_arrows = {"none", "open", "block"}
        use_case_arrow_mix = diagram_kind == "use-case-view" and end_arrows.issubset(allowed_use_case_arrows)
        if len(end_arrows) > 1 and not use_case_arrow_mix:
            warnings.append(f"{xml_path}: inconsistent edge arrow styles ({sorted(end_arrows)})")
        dashed_values = {style.get("dashed", "0") for style in edge_styles}
        if dashed_values - {"0", "1"}:
            warnings.append(f"{xml_path}: unexpected dashed values in edges ({sorted(dashed_values)})")
    for cell in edge_cells:
        edge_value = cell.attrib.get("value", "")
        edge_id = cell.attrib.get("id")
        label_length = plain_length(edge_value)
        line_count = count_lines(edge_value)
        if label_length > MAX_EDGE_LABEL_CHARS:
            warnings.append(f"{xml_path}: edge label on {edge_id} is long ({label_length} chars)")
        if line_count > MAX_EDGE_LINES:
            warnings.append(f"{xml_path}: edge label on {edge_id} has too many lines ({line_count})")
        if normalize_value(edge_value).endswith("."):
            warnings.append(f"{xml_path}: edge label on {edge_id} ends like prose; prefer short verbs or nouns")

    geometries: dict[str, tuple[float, float, float, float]] = {}
    group_headers: dict[str, float] = {}
    node_obstacles: list[Box] = []
    header_obstacles: list[Box] = []
    for cell in vertex_cells:
        geometry = cell.find("./mxGeometry")
        if geometry is None:
            continue
        cell_id = cell.attrib.get("id", "")
        x = float(geometry.attrib.get("x", "0"))
        y = float(geometry.attrib.get("y", "0"))
        width = float(geometry.attrib.get("width", "0"))
        height = float(geometry.attrib.get("height", "0"))
        parent = cell.attrib.get("parent", "")
        if parent in geometries:
            px, py, _, _ = geometries[parent]
            x += px
            y += py
        geometries[cell_id] = (x, y, width, height)
        is_group = "swimlane" in cell.attrib.get("style", "")
        if is_group:
            style = parse_style(cell.attrib.get("style", ""))
            header_height = float(style.get("startSize", "44"))
            group_headers[cell_id] = header_height
            header_obstacles.append(Box(id=cell_id, x=x, y=y, width=width, height=header_height, kind="group-header"))
        else:
            node_obstacles.append(Box(id=cell_id, x=x, y=y, width=width, height=height, kind="node"))

    group_boxes = {
        cell.attrib.get("id", ""): geometries[cell.attrib.get("id", "")]
        for cell in swimlanes
        if cell.attrib.get("id", "") in geometries
    }
    group_ids = [cell.attrib.get("id", "") for cell in swimlanes if cell.attrib.get("id", "")]

    for group_id in group_ids:
        parent_id = parent_map.get(group_id, "")
        if parent_id not in group_boxes:
            continue
        parent_box = group_boxes[parent_id]
        child_box = group_boxes[group_id]
        if not box_contains(parent_box, child_box):
            errors.append(f"{xml_path}: group {group_id} is not fully contained within parent group {parent_id}")
            continue
        px, py, pw, ph = parent_box
        cx, cy, cw, ch = child_box
        required_top = py + group_headers.get(parent_id, 44.0) + MIN_NESTED_GROUP_TOP_GAP
        required_left = px + MIN_NESTED_GROUP_SIDE_GAP
        required_right = px + pw - MIN_NESTED_GROUP_SIDE_GAP
        required_bottom = py + ph - MIN_NESTED_GROUP_BOTTOM_GAP
        if cx < required_left - GEOMETRY_EPSILON:
            errors.append(f"{xml_path}: group {group_id} is too close to the left edge of parent group {parent_id}")
        if cy < required_top - GEOMETRY_EPSILON:
            errors.append(f"{xml_path}: group {group_id} overlaps or crowds the header area of parent group {parent_id}")
        if cx + cw > required_right + GEOMETRY_EPSILON:
            errors.append(f"{xml_path}: group {group_id} is too close to the right edge of parent group {parent_id}")
        if cy + ch > required_bottom + GEOMETRY_EPSILON:
            errors.append(f"{xml_path}: group {group_id} is too close to the bottom edge of parent group {parent_id}")

    for index, first_id in enumerate(group_ids):
        first_box = group_boxes.get(first_id)
        if first_box is None:
            continue
        for second_id in group_ids[index + 1 :]:
            second_box = group_boxes.get(second_id)
            if second_box is None:
                continue
            if is_ancestor(first_id, second_id, parent_map) or is_ancestor(second_id, first_id, parent_map):
                continue
            if box_overlap_area(first_box, second_box) > GEOMETRY_EPSILON:
                errors.append(f"{xml_path}: groups {first_id} and {second_id} overlap")

    all_segments: list[tuple[str, tuple[tuple[float, float], tuple[float, float]]]] = []
    for cell in edge_cells:
        edge_id = cell.attrib.get("id", "")
        source = cell.attrib.get("source", "")
        target = cell.attrib.get("target", "")
        points = edge_points(cell, geometries)
        if len(points) < 2:
            continue
        for start, end in zip(points, points[1:]):
            segment = (start, end)
            for obstacle in node_obstacles:
                if obstacle.id in {source, target}:
                    continue
                if segment_intersects_box(start, end, obstacle):
                    errors.append(f"{xml_path}: edge {edge_id} overlaps node {obstacle.id}")
            all_segments.append((edge_id, segment))

    for index, (edge_id, segment) in enumerate(all_segments):
        for other_edge_id, other_segment in all_segments[index + 1 :]:
            if edge_id == other_edge_id:
                continue
            if segments_conflict(segment, other_segment):
                errors.append(f"{xml_path}: edges {edge_id} and {other_edge_id} intersect or overlap")

    return warnings, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate generated draw.io files for the 3+1 skill."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="docs/architecture",
        help="File or directory to validate",
    )
    args = parser.parse_args()

    target = Path(args.target)
    try:
        files = iter_targets(target)
    except Exception as exc:
        print(f"validate_drawio.py failed: {exc}")
        return 1

    if not files:
        print(f"validate_drawio.py failed: no .drawio files found in {target}")
        return 1

    all_warnings: list[str] = []
    all_errors: list[str] = []
    for xml_path in files:
        warnings, errors = validate_file(xml_path)
        all_warnings.extend(warnings)
        all_errors.extend(errors)

    for warning in all_warnings:
        print(f"WARNING: {warning}")
    for error in all_errors:
        print(f"ERROR: {error}")

    if all_errors:
        print(f"Validation failed with {len(all_errors)} error(s) and {len(all_warnings)} warning(s).")
        return 1

    print(f"Validation passed for {len(files)} file(s) with {len(all_warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
