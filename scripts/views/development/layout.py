from __future__ import annotations

import argparse
import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from views.development.validate import validate_development_view
except ModuleNotFoundError:
    from scripts.views.development.validate import validate_development_view


NODE_WIDTH = 340
MIN_NODE_HEIGHT = 180
MAX_NODE_HEIGHT = 240
TITLE_HEIGHT = 34
SECTION_HEADER_HEIGHT = 22
LINE_HEIGHT = 18
CARD_PADDING = 18
GRID_X_STEP = 445
GRID_Y_STEP = 258
MARGIN_X = 64
MARGIN_Y = 128
GROUP_PADDING = 32
LEGEND_WIDTH = 240
LEGEND_HEIGHT = 150
RELATIONSHIP_LEGEND_WIDTH = 360
RELATIONSHIP_LEGEND_ROW_HEIGHT = 38
RELATIONSHIP_LEGEND_MIN_HEIGHT = 180
PALETTE_ROLES = ("blue", "green", "purple", "yellow")
EDGE_NODE_PENALTY = 100_000
EDGE_EDGE_PENALTY = 80_000
MISSING_ROUTE_PENALTY = 250_000
WARNING_PENALTY = 5_000
EPSILON = 1e-6


@dataclass(frozen=True)
class Frame:
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + (self.width / 2)

    @property
    def center_y(self) -> float:
        return self.y + (self.height / 2)


@dataclass(frozen=True)
class Route:
    source_port: str
    target_port: str
    start: tuple[float, float]
    end: tuple[float, float]
    score: float
    blocked: int


def load_model(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        model = json.load(handle)
    if not isinstance(model, dict):
        raise ValueError(f"Expected JSON object in {path}")
    if str(model.get("view") or "").strip().lower() != "development":
        raise ValueError("Development layout solver only accepts view='development'.")
    return model


def write_model(path: Path, model: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(model, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def text_units(value: str) -> int:
    total = 0
    for char in str(value or ""):
        total += 2 if "\u3400" <= char <= "\u9fff" else 1
    return total


def estimate_node_height(element: dict[str, Any]) -> int:
    responsibility = str(element.get("responsibility") or "")
    exposes = [str(item) for item in (element.get("exposes") or []) if str(item).strip()]
    responsibility_lines = max(2, math.ceil(text_units(responsibility) / 34))
    expose_lines = max(1, len(exposes))
    height = (
        TITLE_HEIGHT
        + CARD_PADDING
        + SECTION_HEADER_HEIGHT
        + responsibility_lines * LINE_HEIGHT
        + CARD_PADDING
        + SECTION_HEADER_HEIGHT
        + expose_lines * LINE_HEIGHT
        + CARD_PADDING
    )
    return max(MIN_NODE_HEIGHT, min(MAX_NODE_HEIGHT, height))


def rendered_relationships(model: dict[str, Any]) -> list[dict[str, Any]]:
    relationships: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for index, relationship in enumerate(model.get("relationships") or [], start=1):
        if not isinstance(relationship, dict) or relationship.get("render") is False:
            continue
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        if not source or not target or source == target:
            continue
        kind = str(relationship.get("kind") or "dependency")
        label = str(relationship.get("label") or "")
        signature = (source, target, kind, label)
        if signature in seen:
            continue
        seen.add(signature)
        copied = copy.deepcopy(relationship)
        copied["source"] = source
        copied["target"] = target
        copied["kind"] = kind
        copied.setdefault("id", f"rel-{safe_id(source)}-to-{safe_id(target)}-{index}")
        copied.setdefault("core", True)
        relationships.append(copied)
    return relationships


def safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in str(value or ""))
    return cleaned.strip("-") or "item"


def element_ids(model: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for element in model.get("elements") or []:
        if isinstance(element, dict) and str(element.get("id") or "").strip():
            ids.append(str(element["id"]))
    return ids


def elements_by_id(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(element.get("id")): element
        for element in model.get("elements") or []
        if isinstance(element, dict) and str(element.get("id") or "").strip()
    }


def group_order(model: dict[str, Any]) -> dict[str, int]:
    groups = [group for group in (model.get("groups") or []) if isinstance(group, dict)]
    ordered = sorted(
        groups,
        key=lambda group: (
            int((group.get("layout_hint") or {}).get("order") or 999)
            if isinstance(group.get("layout_hint"), dict)
            else 999,
            str(group.get("label") or group.get("id") or ""),
        ),
    )
    return {str(group.get("id") or ""): index for index, group in enumerate(ordered)}


def degree_map(ids: Iterable[str], relationships: list[dict[str, Any]]) -> dict[str, int]:
    degrees = {item: 0 for item in ids}
    for relationship in relationships:
        degrees[str(relationship.get("source"))] = degrees.get(str(relationship.get("source")), 0) + 1
        degrees[str(relationship.get("target"))] = degrees.get(str(relationship.get("target")), 0) + 1
    return degrees


def grid_positions(columns: int, rows: int) -> list[tuple[int, int]]:
    return [(column, row) for row in range(rows) for column in range(columns)]


def frame_for_cell(cell: tuple[int, int], height: int) -> Frame:
    column, row = cell
    return Frame(
        x=MARGIN_X + column * GRID_X_STEP,
        y=MARGIN_Y + row * GRID_Y_STEP,
        width=NODE_WIDTH,
        height=height,
    )


def build_initial_layouts(
    model: dict[str, Any],
    relationships: list[dict[str, Any]],
    columns: int,
    rows: int,
) -> list[dict[str, tuple[int, int]]]:
    ids = element_ids(model)
    by_id = elements_by_id(model)
    degrees = degree_map(ids, relationships)
    hub = max(ids, key=lambda item: (degrees.get(item, 0), -ids.index(item))) if ids else ""
    groups = group_order(model)
    sorted_by_group = sorted(
        ids,
        key=lambda item: (
            groups.get(str(by_id[item].get("group") or ""), 999),
            -degrees.get(item, 0),
            ids.index(item),
        ),
    )

    layouts: list[dict[str, tuple[int, int]]] = []
    center_column = max(0, columns // 2)
    preferred: dict[str, tuple[int, int]] = {}
    used_preferred: set[tuple[int, int]] = set()
    for item in ids:
        cell = preferred_semantic_cell(item, by_id[item], hub, center_column, columns - 1, rows - 1)
        if cell in used_preferred:
            for fallback in grid_positions(columns, rows):
                if fallback not in used_preferred:
                    cell = fallback
                    break
        preferred[item] = cell
        used_preferred.add(cell)
    layouts.append(preferred)

    semantic: dict[str, tuple[int, int]] = {}
    occupied: set[tuple[int, int]] = set()
    if hub:
        semantic[hub] = (center_column, 0)
        occupied.add(semantic[hub])
    buckets = classify_nodes(ids, by_id, relationships, hub)
    preferred_cells = {
        "upstream": [(min(columns - 1, center_column + 1), 0), (max(0, center_column - 1), 0), (columns - 1, 1)],
        "left": [(0, 1), (0, 2), (1, 2), (0, 3)],
        "middle": [(center_column, 2), (center_column, 3), (max(0, center_column - 1), 2)],
        "right": [(columns - 1, 1), (columns - 1, 2), (columns - 1, 3)],
        "bottom": [(center_column, rows - 2), (max(0, center_column - 1), rows - 1), (center_column, rows - 1)],
    }
    for bucket_name in ("upstream", "left", "middle", "right", "bottom"):
        for item in buckets[bucket_name]:
            if item in semantic:
                continue
            for cell in preferred_cells[bucket_name] + grid_positions(columns, rows):
                if cell not in occupied and 0 <= cell[0] < columns and 0 <= cell[1] < rows:
                    semantic[item] = cell
                    occupied.add(cell)
                    break
    layouts.append(semantic)

    by_group: dict[str, tuple[int, int]] = {}
    for index, item in enumerate(sorted_by_group):
        by_group[item] = (index % columns, index // columns)
    layouts.append(by_group)

    by_degree: dict[str, tuple[int, int]] = {}
    degree_order = sorted(ids, key=lambda item: (-degrees.get(item, 0), ids.index(item)))
    spiral = spiral_cells(columns, rows)
    for item, cell in zip(degree_order, spiral):
        by_degree[item] = cell
    layouts.append(by_degree)

    return [complete_layout(layout, ids, columns, rows) for layout in layouts]


def classify_nodes(
    ids: list[str],
    by_id: dict[str, dict[str, Any]],
    relationships: list[dict[str, Any]],
    hub: str,
) -> dict[str, list[str]]:
    incoming_to_hub = {str(rel.get("source")) for rel in relationships if str(rel.get("target")) == hub}
    outgoing_from_hub = {str(rel.get("target")) for rel in relationships if str(rel.get("source")) == hub}
    result = {"upstream": [], "left": [], "middle": [], "right": [], "bottom": []}
    for item in ids:
        if item == hub:
            continue
        group = str(by_id[item].get("group") or "").lower()
        label = str(by_id[item].get("label") or item).lower()
        text = f"{group} {label}"
        if item in incoming_to_hub and item not in outgoing_from_hub:
            result["left"].append(item)
        elif item in outgoing_from_hub and any(token in text for token in ("eval", "harness", "workflow")):
            result["left"].append(item)
        elif any(token in text for token in ("agent", "tool")):
            result["bottom"].append(item)
        elif any(token in text for token in ("support", "prompt", "evo", "state", "container", "runtime", "utils")):
            result["right"].append(item)
        elif item in outgoing_from_hub:
            result["middle"].append(item)
        else:
            result["upstream"].append(item)
    return result


def spiral_cells(columns: int, rows: int) -> list[tuple[int, int]]:
    center = ((columns - 1) / 2, (rows - 1) / 2)
    cells = grid_positions(columns, rows)
    return sorted(cells, key=lambda cell: ((cell[0] - center[0]) ** 2 + (cell[1] - center[1]) ** 2, cell[1], cell[0]))


def complete_layout(
    layout: dict[str, tuple[int, int]],
    ids: list[str],
    columns: int,
    rows: int,
) -> dict[str, tuple[int, int]]:
    result = dict(layout)
    used = set(result.values())
    for item in ids:
        if item in result:
            continue
        for cell in grid_positions(columns, rows):
            if cell not in used:
                result[item] = cell
                used.add(cell)
                break
    return result


def orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return ((b[0] - a[0]) * (c[1] - a[1])) - ((b[1] - a[1]) * (c[0] - a[0]))


def on_segment(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    return (
        min(a[0], c[0]) - EPSILON <= b[0] <= max(a[0], c[0]) + EPSILON
        and min(a[1], c[1]) - EPSILON <= b[1] <= max(a[1], c[1]) + EPSILON
    )


def points_equal(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) <= EPSILON and abs(a[1] - b[1]) <= EPSILON


def overlap_length(
    first: tuple[tuple[float, float], tuple[float, float]],
    second: tuple[tuple[float, float], tuple[float, float]],
) -> float:
    (ax1, ay1), (ax2, ay2) = first
    (bx1, by1), (bx2, by2) = second
    if abs(ax1 - ax2) >= abs(ay1 - ay2):
        return min(max(ax1, ax2), max(bx1, bx2)) - max(min(ax1, ax2), min(bx1, bx2))
    return min(max(ay1, ay2), max(by1, by2)) - max(min(ay1, ay2), min(by1, by2))


def segments_conflict(
    first: tuple[tuple[float, float], tuple[float, float]],
    second: tuple[tuple[float, float], tuple[float, float]],
) -> bool:
    p1, q1 = first
    p2, q2 = second
    shared_points = [point for point in (p1, q1) if points_equal(point, p2) or points_equal(point, q2)]
    if len(shared_points) == 2:
        return False

    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)
    if (
        ((o1 > EPSILON and o2 < -EPSILON) or (o1 < -EPSILON and o2 > EPSILON))
        and ((o3 > EPSILON and o4 < -EPSILON) or (o3 < -EPSILON and o4 > EPSILON))
    ):
        return True
    if abs(o1) <= EPSILON and abs(o2) <= EPSILON and abs(o3) <= EPSILON and abs(o4) <= EPSILON:
        return overlap_length(first, second) > EPSILON
    for point, start, end in ((p2, p1, q1), (q2, p1, q1), (p1, p2, q2), (q1, p2, q2)):
        if abs(orientation(start, end, point)) <= EPSILON and on_segment(start, point, end):
            if any(points_equal(point, shared) for shared in shared_points):
                continue
            return True
    return False


def point_in_frame(point: tuple[float, float], frame: Frame) -> bool:
    return frame.left <= point[0] <= frame.right and frame.top <= point[1] <= frame.bottom


def segment_intersects_frame(start: tuple[float, float], end: tuple[float, float], frame: Frame) -> bool:
    if point_in_frame(start, frame) or point_in_frame(end, frame):
        return True
    corners = [
        (frame.left, frame.top),
        (frame.right, frame.top),
        (frame.right, frame.bottom),
        (frame.left, frame.bottom),
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
    return point_in_frame(midpoint, frame)


def port_points(frame: Frame) -> dict[str, tuple[float, float]]:
    return {
        "left": (frame.left, frame.center_y),
        "right": (frame.right, frame.center_y),
        "top": (frame.center_x, frame.top),
        "bottom": (frame.center_x, frame.bottom),
    }


def route_relationship(
    relationship: dict[str, Any],
    frames: dict[str, Frame],
    reserved: list[tuple[str, tuple[tuple[float, float], tuple[float, float]]]],
) -> Route:
    source = str(relationship.get("source") or "")
    target = str(relationship.get("target") or "")
    source_frame = frames[source]
    target_frame = frames[target]
    candidates: list[Route] = []
    for source_port, start in port_points(source_frame).items():
        for target_port, end in port_points(target_frame).items():
            blocked = 0
            for obstacle_id, obstacle in frames.items():
                if obstacle_id in {source, target}:
                    continue
                if segment_intersects_frame(start, end, obstacle):
                    blocked += 1
            crossings = sum(1 for _, segment in reserved if segments_conflict((start, end), segment))
            length = math.dist(start, end)
            direction_score = directional_port_score(source_frame, target_frame, source_port, target_port)
            score = length + direction_score + blocked * EDGE_NODE_PENALTY + crossings * EDGE_EDGE_PENALTY
            candidates.append(Route(source_port, target_port, start, end, score, blocked))
    return min(candidates, key=lambda route: route.score)


def directional_port_score(source: Frame, target: Frame, source_port: str, target_port: str) -> float:
    dx = target.center_x - source.center_x
    dy = target.center_y - source.center_y
    preferred_source = "right" if abs(dx) >= abs(dy) and dx >= 0 else "left" if abs(dx) >= abs(dy) else "bottom" if dy >= 0 else "top"
    preferred_target = "left" if preferred_source == "right" else "right" if preferred_source == "left" else "top" if preferred_source == "bottom" else "bottom"
    score = 0.0
    if source_port != preferred_source:
        score += 120.0
    if target_port != preferred_target:
        score += 120.0
    return score


def frames_from_layout(
    model: dict[str, Any],
    layout: dict[str, tuple[int, int]],
    heights: dict[str, int],
) -> dict[str, Frame]:
    return {item: frame_for_cell(layout[item], heights[item]) for item in element_ids(model)}


def score_layout(
    model: dict[str, Any],
    relationships: list[dict[str, Any]],
    layout: dict[str, tuple[int, int]],
    heights: dict[str, int],
) -> float:
    frames = frames_from_layout(model, layout, heights)
    reserved: list[tuple[str, tuple[tuple[float, float], tuple[float, float]]]] = []
    score = 0.0
    ordered_relationships = sorted(
        relationships,
        key=lambda rel: (
            0 if rel.get("core") is True else 1,
            -degree_pair(rel, relationships),
            str(rel.get("id") or ""),
        ),
    )
    for relationship in ordered_relationships:
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        if source not in frames or target not in frames:
            score += MISSING_ROUTE_PENALTY
            continue
        route = route_relationship(relationship, frames, reserved)
        reserved.append((str(relationship.get("id") or ""), (route.start, route.end)))
        score += route.score
    score += balance_penalty(layout)
    score += semantic_shape_penalty(model, relationships, layout)
    return score


def degree_pair(relationship: dict[str, Any], relationships: list[dict[str, Any]]) -> int:
    source = str(relationship.get("source") or "")
    target = str(relationship.get("target") or "")
    count = 0
    for item in relationships:
        if source in {str(item.get("source")), str(item.get("target"))}:
            count += 1
        if target in {str(item.get("source")), str(item.get("target"))}:
            count += 1
    return count


def balance_penalty(layout: dict[str, tuple[int, int]]) -> float:
    if not layout:
        return 0.0
    columns = [cell[0] for cell in layout.values()]
    rows = [cell[1] for cell in layout.values()]
    return (max(columns) - min(columns) + max(rows) - min(rows)) * 20.0


def semantic_shape_penalty(
    model: dict[str, Any],
    relationships: list[dict[str, Any]],
    layout: dict[str, tuple[int, int]],
) -> float:
    ids = element_ids(model)
    if not ids:
        return 0.0
    by_id = elements_by_id(model)
    degrees = degree_map(ids, relationships)
    hub = max(ids, key=lambda item: (degrees.get(item, 0), -ids.index(item)))
    max_column = max(cell[0] for cell in layout.values())
    max_row = max(cell[1] for cell in layout.values())
    center_column = max_column // 2
    penalty = 0.0
    for item, cell in layout.items():
        preferred = preferred_semantic_cell(item, by_id[item], hub, center_column, max_column, max_row)
        penalty += (abs(cell[0] - preferred[0]) + abs(cell[1] - preferred[1])) * 650.0
    return penalty


def preferred_semantic_cell(
    element_id: str,
    element: dict[str, Any],
    hub: str,
    center_column: int,
    max_column: int,
    max_row: int,
) -> tuple[int, int]:
    text = f"{element_id} {element.get('label') or ''} {element.get('group') or ''}".lower()
    if element_id == hub:
        return center_column, min(max_row, 1)
    if any(token in text for token in ("outer", "orchestration", "编排")):
        return max_column, 0
    if any(token in text for token in ("swe", "polyglot", "harness", "eval", "评测")):
        if "polyglot" in text:
            return max(0, center_column - 1), min(max_row, 2)
        return 0, min(max_row, 2)
    if any(token in text for token in ("container", "runtime", "docker")):
        return min(max_column, center_column + 1), min(max_row, 3)
    if any(token in text for token in ("evo", "state", "utils", "archive")):
        return min(max_column, center_column + 1), min(max_row, 1)
    if any(token in text for token in ("prompt", "提示")):
        return max_column, min(max_row, 3)
    if any(token in text for token in ("tool", "工具")):
        return max(0, center_column - 1), max_row
    if any(token in text for token in ("agent", "代理")):
        return center_column, max_row
    return center_column, min(max_row, 1)


def improve_layout(
    model: dict[str, Any],
    relationships: list[dict[str, Any]],
    layout: dict[str, tuple[int, int]],
    heights: dict[str, int],
    columns: int,
    rows: int,
) -> dict[str, tuple[int, int]]:
    ids = element_ids(model)
    current = dict(layout)
    current_score = score_layout(model, relationships, current, heights)
    cells = grid_positions(columns, rows)
    for _ in range(6):
        improved = False
        occupied = {cell: item for item, cell in current.items()}
        for item in ids:
            original_cell = current[item]
            for cell in cells:
                if cell == original_cell:
                    continue
                candidate = dict(current)
                other = occupied.get(cell)
                if other:
                    candidate[other] = original_cell
                candidate[item] = cell
                candidate_score = score_layout(model, relationships, candidate, heights)
                if candidate_score + 1 < current_score:
                    current = candidate
                    current_score = candidate_score
                    improved = True
                    occupied = {next_cell: next_item for next_item, next_cell in current.items()}
        if not improved:
            break
    return current


def normalized_frames(frames: dict[str, Frame]) -> tuple[dict[str, Frame], float, float]:
    min_x = min(frame.left for frame in frames.values())
    min_y = min(frame.top for frame in frames.values())
    shift_x = MARGIN_X - min_x
    shift_y = MARGIN_Y - min_y
    shifted = {
        item: Frame(frame.x + shift_x, frame.y + shift_y, frame.width, frame.height)
        for item, frame in frames.items()
    }
    return shifted, shift_x, shift_y


def canvas_for(frames: dict[str, Frame], routes: list[Route], annotation_frames: list[Frame] | None = None) -> dict[str, int]:
    annotation_frames = annotation_frames or []
    max_right = max(frame.right for frame in frames.values())
    max_bottom = max(frame.bottom for frame in frames.values())
    if annotation_frames:
        max_right = max(max_right, max(frame.right for frame in annotation_frames))
        max_bottom = max(max_bottom, max(frame.bottom for frame in annotation_frames))
    max_edge = max((math.dist(route.start, route.end) for route in routes), default=0.0)
    width = int(math.ceil(max(max_right + MARGIN_X, max_edge / 0.74)))
    height = int(math.ceil(max(max_bottom + MARGIN_Y, 900)))
    return {"width": width, "height": height}


def apply_geometry(
    model: dict[str, Any],
    relationships: list[dict[str, Any]],
    layout: dict[str, tuple[int, int]],
    heights: dict[str, int],
) -> dict[str, Any]:
    solved = copy.deepcopy(model)
    frames, _, _ = normalized_frames(frames_from_layout(model, layout, heights))
    reserved: list[tuple[str, tuple[tuple[float, float], tuple[float, float]]]] = []
    routes_by_id: dict[str, Route] = {}
    ordered_relationships = sorted(
        relationships,
        key=lambda rel: (
            0 if rel.get("core") is True else 1,
            -degree_pair(rel, relationships),
            str(rel.get("id") or ""),
        ),
    )
    for relationship in ordered_relationships:
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        route = route_relationship(relationship, frames, reserved)
        relationship_id = str(relationship.get("id") or "")
        routes_by_id[relationship_id] = route
        reserved.append((relationship_id, (route.start, route.end)))

    legend_frame, relationship_legend_frame = annotation_frames_for(frames, relationships)
    canvas = canvas_for(frames, list(routes_by_id.values()), [legend_frame, relationship_legend_frame])
    solved["canvas"] = canvas
    ensure_groups(solved)
    apply_group_styles(solved)

    for element in solved.get("elements") or []:
        if not isinstance(element, dict):
            continue
        element_id = str(element.get("id") or "")
        if element_id not in frames:
            continue
        frame = frames[element_id]
        element["frame"] = frame_to_mapping(frame)
        element["ports"] = {name: point_to_mapping(point) for name, point in port_points(frame).items()}

    relationships_by_signature = {
        relationship_signature(item): item
        for item in relationships
    }
    relationship_legend_items: list[dict[str, str]] = []
    code_by_signature = {
        relationship_signature(relationship): f"R{index}"
        for index, relationship in enumerate(relationships, start=1)
    }
    for index, relationship in enumerate(solved.get("relationships") or [], start=1):
        if not isinstance(relationship, dict) or relationship.get("render") is False:
            continue
        signature = relationship_signature(relationship)
        solved_relationship = relationships_by_signature.get(signature)
        if solved_relationship is None:
            continue
        relationship_id = str(solved_relationship.get("id") or f"rel-{index}")
        route = routes_by_id[relationship_id]
        code = code_by_signature.get(signature, f"R{index}")
        relationship["id"] = relationship_id
        relationship["code"] = code
        relationship["kind"] = str(relationship.get("kind") or "dependency")
        relationship.setdefault("core", True)
        relationship["source_port"] = route.source_port
        relationship["target_port"] = route.target_port
        relationship["segments"] = [{"start": point_to_mapping(route.start), "end": point_to_mapping(route.end)}]
        relationship["label_box"] = label_box_for_route(route, code)
        label = str(relationship.get("label") or "").strip()
        source = str(relationship.get("source") or "").strip()
        target = str(relationship.get("target") or "").strip()
        if label:
            relationship_legend_items.append({"code": code, "label": f"{source} -> {target}: {label}"})

    apply_group_frames(solved, frames)
    solved["legend"] = legend_for(solved, legend_frame)
    solved["relationship_legend"] = {
        "title": "关系说明",
        "frame": frame_to_mapping(relationship_legend_frame),
        "items": relationship_legend_items,
    }
    return solved


def label_box_for_route(route: Route, code: str) -> dict[str, float]:
    width = max(24, 14 + len(code) * 8)
    height = 18
    midpoint_x = (route.start[0] + route.end[0]) / 2
    midpoint_y = (route.start[1] + route.end[1]) / 2
    return {
        "x": round(midpoint_x - (width / 2), 1),
        "y": round(midpoint_y - (height / 2), 1),
        "width": float(width),
        "height": float(height),
    }


def relationship_signature(relationship: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(relationship.get("source") or ""),
        str(relationship.get("target") or ""),
        str(relationship.get("kind") or "dependency"),
        str(relationship.get("label") or ""),
    )


def frame_to_mapping(frame: Frame) -> dict[str, float]:
    return {
        "x": round(frame.x, 1),
        "y": round(frame.y, 1),
        "width": round(frame.width, 1),
        "height": round(frame.height, 1),
    }


def point_to_mapping(point: tuple[float, float]) -> dict[str, float]:
    return {"x": round(point[0], 1), "y": round(point[1], 1)}


def ensure_groups(model: dict[str, Any]) -> None:
    existing = {str(group.get("id") or "") for group in (model.get("groups") or []) if isinstance(group, dict)}
    element_group_ids = {
        str(element.get("group") or "")
        for element in (model.get("elements") or [])
        if isinstance(element, dict) and str(element.get("group") or "")
    }
    groups = [group for group in (model.get("groups") or []) if isinstance(group, dict)]
    for group_id in sorted(element_group_ids - existing):
        groups.append({"id": group_id, "label": group_id})
    model["groups"] = groups


def apply_group_styles(model: dict[str, Any]) -> None:
    for index, group in enumerate(model.get("groups") or []):
        if not isinstance(group, dict):
            continue
        group.setdefault("color_role", PALETTE_ROLES[index % len(PALETTE_ROLES)])


def apply_group_frames(model: dict[str, Any], frames: dict[str, Frame]) -> None:
    members_by_group: dict[str, list[Frame]] = {}
    for element in model.get("elements") or []:
        if not isinstance(element, dict):
            continue
        element_id = str(element.get("id") or "")
        group_id = str(element.get("group") or "")
        if element_id in frames and group_id:
            members_by_group.setdefault(group_id, []).append(frames[element_id])
    for group in model.get("groups") or []:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("id") or "")
        members = members_by_group.get(group_id) or []
        if not members:
            continue
        left = min(frame.left for frame in members) - GROUP_PADDING
        top = min(frame.top for frame in members) - GROUP_PADDING
        right = max(frame.right for frame in members) + GROUP_PADDING
        bottom = max(frame.bottom for frame in members) + GROUP_PADDING
        group["frame"] = frame_to_mapping(Frame(left, top, right - left, bottom - top))


def annotation_frames_for(frames: dict[str, Frame], relationships: list[dict[str, Any]]) -> tuple[Frame, Frame]:
    max_right = max(frame.right for frame in frames.values())
    x = max_right + 32
    legend_frame = Frame(x, 32, LEGEND_WIDTH, LEGEND_HEIGHT)
    relationship_height = max(
        RELATIONSHIP_LEGEND_MIN_HEIGHT,
        48 + len(relationships) * RELATIONSHIP_LEGEND_ROW_HEIGHT,
    )
    relationship_frame = Frame(
        x,
        legend_frame.bottom + 16,
        RELATIONSHIP_LEGEND_WIDTH,
        relationship_height,
    )
    return legend_frame, relationship_frame


def legend_for(model: dict[str, Any], frame: Frame) -> dict[str, Any]:
    items = []
    for group in model.get("groups") or []:
        if not isinstance(group, dict):
            continue
        label = str(group.get("label") or group.get("id") or "")
        role = str(group.get("color_role") or "")
        if label and role:
            items.append({"label": label, "color_role": role})
    return {
        "title": "颜色图例",
        "items": items,
        "frame": frame_to_mapping(frame),
    }


def solve_development_view_layout(model: dict[str, Any]) -> dict[str, Any]:
    relationships = rendered_relationships(model)
    ids = element_ids(model)
    if not ids:
        raise ValueError("Development view model has no elements to lay out.")
    heights = {
        element_id: estimate_node_height(elements_by_id(model)[element_id])
        for element_id in ids
    }
    columns = max(3, min(5, math.ceil(math.sqrt(len(ids))) + 1))
    if len(ids) >= 8:
        columns = max(columns, 5)
    rows = max(3, math.ceil(len(ids) / columns) + 3)

    best_layout: dict[str, tuple[int, int]] | None = None
    best_score = float("inf")
    initial_layouts = build_initial_layouts(model, relationships, columns, rows)
    for initial in initial_layouts:
        candidate = apply_geometry(model, relationships, initial, heights)
        candidate_report = validate_development_view(candidate)
        if not candidate_report.errors and not candidate_report.warnings:
            return candidate
    for initial in initial_layouts:
        improved = improve_layout(model, relationships, initial, heights, columns, rows)
        score = score_layout(model, relationships, improved, heights)
        if score < best_score:
            best_score = score
            best_layout = improved
    if best_layout is None:
        raise ValueError("No candidate layout was produced.")

    solved = apply_geometry(model, relationships, best_layout, heights)
    report = validate_development_view(solved)
    if report.errors or report.warnings:
        # Try a wider board before giving up; straight-line layouts sometimes need one extra column.
        wide_columns = min(6, columns + 1)
        wide_rows = max(rows, math.ceil(len(ids) / wide_columns) + 2)
        for initial in build_initial_layouts(model, relationships, wide_columns, wide_rows):
            improved = improve_layout(model, relationships, initial, heights, wide_columns, wide_rows)
            candidate = apply_geometry(model, relationships, improved, heights)
            candidate_report = validate_development_view(candidate)
            candidate_score = len(candidate_report.errors) * EDGE_NODE_PENALTY + len(candidate_report.warnings) * WARNING_PENALTY
            candidate_score += score_layout(model, relationships, improved, heights)
            if candidate_score < best_score or (not candidate_report.errors and not candidate_report.warnings):
                best_score = candidate_score
                solved = candidate
                report = candidate_report
            if not report.errors and not report.warnings:
                break
    if report.errors:
        messages = "; ".join(f"{message.rule_id}: {message.message}" for message in report.errors[:5])
        raise ValueError(f"Unable to solve a valid development layout: {messages}")
    return solved


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve development-view geometry for the fixed validator and renderer.")
    parser.add_argument("input", help="Input development-view JSON model.")
    parser.add_argument(
        "output",
        nargs="?",
        help="Output solved JSON path. Defaults to <input-stem>-solved.json beside the input.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_name(f"{input_path.stem}-solved.json")
    try:
        model = load_model(input_path)
        solved = solve_development_view_layout(model)
        write_model(output_path, solved)
        report = validate_development_view(solved)
        print(f"Solved {input_path} -> {output_path}")
        print(f"Validation passed with {len(report.warnings)} warning(s).")
    except Exception as exc:
        print(f"solve_development_view_layout.py failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
