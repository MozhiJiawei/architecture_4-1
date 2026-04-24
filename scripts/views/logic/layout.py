from __future__ import annotations

import copy
from typing import Any

from ..drawio_common import Box, route_edge, sanitize_id, style_for_ports, style_pairs

PAGE_MIN_SIDE = 1500
GROUP_MARGIN_X = 60
GROUP_MARGIN_Y = 48
GROUP_GAP_Y = 88
GROUP_WIDTH = 1680
MAIN_STACK_WIDTH = 980
SIDE_WING_WIDTH = 360
SIDE_WING_GAP_X = 40
GROUP_HEADER_HEIGHT = 44
ELEMENT_GAP_Y = 22
ELEMENT_HEIGHT = 96
ELEMENT_WIDTH = 260
ELEMENT_GAP_X = 28
GROUP_PADDING_X = 28
GROUP_PADDING_Y = 22
MAX_COLUMNS = 4
EDGE_STUB = 28
EDGE_LANE_STEP = 48
DIRECT_LAYOUT_GAP_MULTIPLIERS = (1.0, 1.25, 1.5, 1.75, 2.0, 2.5)

def max_columns_for_group_width(group_width: int) -> int:
    inner_width = group_width - (2 * GROUP_PADDING_X)
    return max(1, (inner_width + ELEMENT_GAP_X) // (ELEMENT_WIDTH + ELEMENT_GAP_X))


def compute_grid_columns(element_count: int, group_width: int) -> int:
    if element_count <= 0:
        return 1
    max_columns = max_columns_for_group_width(group_width)
    if element_count <= 2:
        return min(element_count, max_columns)
    if element_count <= 4:
        return min(3, element_count, max_columns)
    return min(MAX_COLUMNS, element_count, max_columns)


def compute_group_height(element_count: int, group_width: int) -> int:
    columns = compute_grid_columns(element_count, group_width)
    rows = max(1, (element_count + columns - 1) // columns)
    content_height = rows * ELEMENT_HEIGHT + max(0, rows - 1) * ELEMENT_GAP_Y
    return GROUP_HEADER_HEIGHT + (2 * GROUP_PADDING_Y) + content_height


def compute_page_height(group_heights: list[int]) -> int:
    total_height = GROUP_MARGIN_Y + sum(group_heights) + max(0, len(group_heights) - 1) * GROUP_GAP_Y + GROUP_MARGIN_Y
    return total_height


def compute_column_x_positions(group_width: int, columns: int, gap_x: int = ELEMENT_GAP_X) -> list[int]:
    inner_width = group_width - (2 * GROUP_PADDING_X)
    used_width = columns * ELEMENT_WIDTH + max(0, columns - 1) * gap_x
    start_x = GROUP_PADDING_X + max(0, (inner_width - used_width) // 2)
    return [start_x + index * (ELEMENT_WIDTH + gap_x) for index in range(columns)]


def get_layout_strategy(view_model: dict[str, Any]) -> str:
    render_hints = view_model.get("render_hints")
    if isinstance(render_hints, dict):
        logic_hints = render_hints.get("logic")
        if isinstance(logic_hints, dict):
            strategy = logic_hints.get("layout_strategy")
            if isinstance(strategy, str) and strategy.strip():
                return strategy.strip()
    layout_suggestion = view_model.get("layout_suggestion")
    if isinstance(layout_suggestion, dict):
        strategy = layout_suggestion.get("strategy")
        if isinstance(strategy, str) and strategy.strip():
            return strategy.strip()
    return "stacked-groups"


def group_layout_hint(group: dict[str, Any]) -> dict[str, Any]:
    hint = group.get("layout_hint")
    return hint if isinstance(hint, dict) else {}


def ordered_group_ids(groups: list[dict[str, Any]]) -> list[str]:
    valid_groups = [group for group in groups if isinstance(group, dict) and group.get("id")]
    ordered = sorted(
        valid_groups,
        key=lambda group: (
            int(group_layout_hint(group).get("order") or 999),
            str(group.get("label") or group.get("id") or ""),
        ),
    )
    return [str(group["id"]) for group in ordered]


def relationship_allowed_by_layers(
    relationship: dict[str, Any],
    element_groups: dict[str, str],
    group_ranks: dict[str, int],
) -> bool:
    source = str(relationship.get("source") or "")
    target = str(relationship.get("target") or "")
    source_group = element_groups.get(source)
    target_group = element_groups.get(target)
    if not source_group or not target_group:
        return False
    if source_group == target_group:
        return True
    if source_group not in group_ranks or target_group not in group_ranks:
        return False
    return abs(group_ranks[source_group] - group_ranks[target_group]) == 1


def connection_stats(
    element_id: str,
    relationships: list[dict[str, Any]],
    element_groups: dict[str, str],
    group_ranks: dict[str, int],
) -> tuple[int, int]:
    cross_layer = 0
    same_layer = 0
    own_group = element_groups.get(element_id)
    own_rank = group_ranks.get(own_group or "", -999)
    for relationship in relationships:
        if not isinstance(relationship, dict):
            continue
        if relationship.get("render") is False:
            continue
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        if element_id not in {source, target}:
            continue
        peer = target if source == element_id else source
        peer_group = element_groups.get(peer)
        if not peer_group:
            continue
        peer_rank = group_ranks.get(peer_group, -999)
        if peer_group == own_group:
            same_layer += 1
        elif abs(peer_rank - own_rank) == 1:
            cross_layer += 1
    return cross_layer, same_layer


def ordered_group_elements(
    group_id: str,
    elements_by_group: dict[str, list[dict[str, Any]]],
    relationships: list[dict[str, Any]],
    element_groups: dict[str, str],
    group_ranks: dict[str, int],
) -> list[dict[str, Any]]:
    items = list(elements_by_group.get(group_id, []))
    if not items:
        return items
    if group_ranks.get(group_id) in {0, max(group_ranks.values())}:
        return items
    indexed = []
    for original_index, element in enumerate(items):
        element_id = str(element.get("id") or "")
        cross_layer, same_layer = connection_stats(element_id, relationships, element_groups, group_ranks)
        indexed.append((-(cross_layer * 10 + same_layer), original_index, element))
    indexed.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in indexed]


def same_layer_relationship_count(
    group_id: str,
    relationships: list[dict[str, Any]],
    element_groups: dict[str, str],
    group_ranks: dict[str, int],
) -> int:
    count = 0
    for relationship in relationships:
        if not isinstance(relationship, dict):
            continue
        if relationship.get("render") is False:
            continue
        if not relationship_allowed_by_layers(relationship, element_groups, group_ranks):
            continue
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        if element_groups.get(source) == group_id and element_groups.get(target) == group_id:
            count += 1
    return count


def group_gap_x(
    group_id: str,
    group_width: int,
    element_count: int,
    relationships: list[dict[str, Any]],
    element_groups: dict[str, str],
    group_ranks: dict[str, int],
) -> int:
    if element_count <= 1:
        return ELEMENT_GAP_X
    same_layer_count = same_layer_relationship_count(group_id, relationships, element_groups, group_ranks)
    if same_layer_count <= 0:
        return ELEMENT_GAP_X
    inner_width = group_width - (2 * GROUP_PADDING_X)
    max_gap = max(ELEMENT_GAP_X, (inner_width - (element_count * ELEMENT_WIDTH)) // max(1, element_count - 1))
    preferred_gap = 120 + ((same_layer_count - 1) * 20)
    return min(max_gap, preferred_gap)


def orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return ((b[0] - a[0]) * (c[1] - a[1])) - ((b[1] - a[1]) * (c[0] - a[0]))


def on_segment(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    return (
        min(a[0], c[0]) <= b[0] <= max(a[0], c[0])
        and min(a[1], c[1]) <= b[1] <= max(a[1], c[1])
    )


def straight_segments_conflict(
    first: tuple[tuple[float, float], tuple[float, float]],
    second: tuple[tuple[float, float], tuple[float, float]],
) -> bool:
    p1, q1 = first
    p2, q2 = second
    if len({p1, q1, p2, q2}) < 4:
        return False
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)
    if (o1 > 0 > o2 or o1 < 0 < o2) and (o3 > 0 > o4 or o3 < 0 < o4):
        return True
    if o1 == 0 and on_segment(p1, p2, q1):
        return True
    if o2 == 0 and on_segment(p1, q2, q1):
        return True
    if o3 == 0 and on_segment(p2, p1, q2):
        return True
    if o4 == 0 and on_segment(p2, q1, q2):
        return True
    return False


def point_in_box(point: tuple[float, float], box: tuple[int, int, int, int]) -> bool:
    x, y = point
    bx, by, bw, bh = box
    return bx <= x <= bx + bw and by <= y <= by + bh


def straight_segment_intersects_box(
    start: tuple[float, float],
    end: tuple[float, float],
    box: tuple[int, int, int, int],
) -> bool:
    if point_in_box(start, box) or point_in_box(end, box):
        return True
    bx, by, bw, bh = box
    corners = [
        (bx, by),
        (bx + bw, by),
        (bx + bw, by + bh),
        (bx, by + bh),
    ]
    edges = [
        (corners[0], corners[1]),
        (corners[1], corners[2]),
        (corners[2], corners[3]),
        (corners[3], corners[0]),
    ]
    return any(straight_segments_conflict((start, end), edge) for edge in edges)


def direct_anchor_points(
    source: str,
    target: str,
    relationship: dict[str, Any],
    source_siblings: list[dict[str, Any]],
    target_siblings: list[dict[str, Any]],
    element_groups: dict[str, str],
    group_ranks: dict[str, int],
    element_positions: dict[str, tuple[int, int, int, int]],
) -> tuple[tuple[float, float], tuple[float, float], int, int, int, int]:
    source_group = element_groups[source]
    target_group = element_groups[target]
    source_delta = layer_delta_for_relationship(
        relationship,
        source,
        target,
        element_groups,
        group_ranks,
    )
    directional_source_siblings = [
        sibling
        for sibling in source_siblings
        if layer_delta_for_relationship(
            sibling,
            source,
            str(sibling.get("target") or ""),
            element_groups,
            group_ranks,
        ) == source_delta
    ]
    source_index = directional_source_siblings.index(relationship)
    source_total = len(directional_source_siblings)
    target_delta = layer_delta_for_relationship(
        relationship,
        source,
        target,
        element_groups,
        group_ranks,
    )
    directional_target_siblings = [
        sibling
        for sibling in target_siblings
        if layer_delta_for_relationship(
            sibling,
            str(sibling.get("source") or ""),
            target,
            element_groups,
            group_ranks,
        ) == target_delta
    ]
    target_index = directional_target_siblings.index(relationship)
    target_total = len(directional_target_siblings)
    source_slot = slot_ratio(source_index, source_total)
    target_slot = slot_ratio(target_index, target_total)
    if source_group == target_group:
        source_box = element_positions[source]
        target_box = element_positions[target]
        if source_box[0] <= target_box[0]:
            start = (source_box[0] + source_box[2], source_box[1] + (source_box[3] / 2))
            end = (target_box[0], target_box[1] + (target_box[3] / 2))
        else:
            start = (source_box[0], source_box[1] + (source_box[3] / 2))
            end = (target_box[0] + target_box[2], target_box[1] + (target_box[3] / 2))
        return start, end, source_index, source_total, target_index, target_total
    source_box = element_positions[source]
    target_box = element_positions[target]
    if group_ranks[target_group] > group_ranks[source_group]:
        start = (source_box[0] + (source_box[2] * source_slot), source_box[1] + source_box[3])
        end = (target_box[0] + (target_box[2] * source_slot), target_box[1])
    else:
        start = (source_box[0] + (source_box[2] * source_slot), source_box[1])
        end = (target_box[0] + (target_box[2] * source_slot), target_box[1] + target_box[3])
    return start, end, source_index, source_total, target_index, target_total


def compute_direct_conflicts(
    relationships: list[dict[str, Any]],
    element_groups: dict[str, str],
    group_ranks: dict[str, int],
    element_positions: dict[str, tuple[int, int, int, int]],
) -> list[str]:
    usable = []
    outgoing_edges: dict[str, list[dict[str, Any]]] = {}
    incoming_edges: dict[str, list[dict[str, Any]]] = {}
    for relationship in relationships:
        if not isinstance(relationship, dict):
            continue
        if relationship.get("render") is False:
            continue
        if not relationship_allowed_by_layers(relationship, element_groups, group_ranks):
            continue
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        if source not in element_positions or target not in element_positions:
            continue
        usable.append(relationship)
        outgoing_edges.setdefault(source, []).append(relationship)
        incoming_edges.setdefault(target, []).append(relationship)

    direct_segments: list[tuple[str, str, str, tuple[tuple[float, float], tuple[float, float]]]] = []
    for relationship in usable:
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        start, end, _, _, _, _ = direct_anchor_points(
            source,
            target,
            relationship,
            outgoing_edges[source],
            incoming_edges[target],
            element_groups,
            group_ranks,
            element_positions,
        )
        direct_segments.append((f"edge-{sanitize_id(source)}-{sanitize_id(target)}", source, target, (start, end)))

    conflicts: list[str] = []
    for index, (edge_id, source, target, segment) in enumerate(direct_segments):
        for element_id, box in element_positions.items():
            if element_id in {source, target}:
                continue
            if straight_segment_intersects_box(segment[0], segment[1], box):
                conflicts.append(f"{edge_id} overlaps node {element_id}")
        for other_edge_id, _, _, other_segment in direct_segments[index + 1 :]:
            if straight_segments_conflict(segment, other_segment):
                conflicts.append(f"{edge_id} intersects {other_edge_id}")
    return conflicts


def edge_priority_score(relationship: dict[str, Any]) -> tuple[int, int, int]:
    inferred_penalty = 0 if relationship.get("inferred") else 1
    labeled_penalty = 1 if str(relationship.get("label") or "").strip() else 0
    evidence_penalty = 1 if relationship.get("evidence_ids") else 0
    return (inferred_penalty, labeled_penalty, evidence_penalty)


def relationship_key(relationship: dict[str, Any]) -> str:
    source = str(relationship.get("source") or "")
    target = str(relationship.get("target") or "")
    label = str(relationship.get("label") or "").strip()
    return f"{source}->{target}" + (f" [{label}]" if label else "")


def minimal_suppression_suggestions(
    relationships: list[dict[str, Any]],
    conflicts: list[str],
) -> list[str]:
    by_edge_key: dict[str, dict[str, Any]] = {}
    edge_name_to_key: dict[str, str] = {}
    for relationship in relationships:
        if not isinstance(relationship, dict):
            continue
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        edge_name = f"edge-{sanitize_id(source)}-{sanitize_id(target)}"
        key = relationship_key(relationship)
        by_edge_key[key] = relationship
        edge_name_to_key[edge_name] = key

    unresolved = list(conflicts)
    suggestions: list[str] = []
    while unresolved:
        coverage: dict[str, list[str]] = {}
        for conflict in unresolved:
            mentioned = []
            for edge_name, rel_key in edge_name_to_key.items():
                if edge_name in conflict:
                    mentioned.append(rel_key)
            for rel_key in mentioned:
                coverage.setdefault(rel_key, []).append(conflict)
        if not coverage:
            break
        best_key = min(
            coverage,
            key=lambda rel_key: (
                edge_priority_score(by_edge_key.get(rel_key, {})),
                -len(coverage[rel_key]),
                rel_key,
            ),
        )
        best_relationship = by_edge_key.get(best_key, {})
        suggestions.append(
            f"{best_key} | conflicts={len(coverage[best_key])} | inferred={bool(best_relationship.get('inferred'))}"
        )
        unresolved = [
            conflict
            for conflict in unresolved
            if conflict not in coverage[best_key]
        ]
    return suggestions


def compute_stacked_positions(
    group_order: list[str],
    groups: list[dict[str, Any]],
    group_layouts: dict[str, dict[str, int]],
    elements_by_group: dict[str, list[dict[str, Any]]],
    relationships: list[dict[str, Any]],
    preview_element_groups: dict[str, str],
    preview_group_ranks: dict[str, int],
    gap_multiplier: float,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, tuple[int, int, int, int]]]:
    ordered_by_group: dict[str, list[dict[str, Any]]] = {}
    element_positions: dict[str, tuple[int, int, int, int]] = {}
    for group_id in group_order:
        layout_box = group_layouts.get(group_id)
        if not layout_box:
            continue
        group_elements = ordered_group_elements(
            group_id,
            elements_by_group,
            relationships,
            preview_element_groups,
            preview_group_ranks,
        )
        ordered_by_group[group_id] = group_elements
        group_width = layout_box["width"]
        group_x = layout_box["x"]
        group_y = layout_box["y"]
        content_y = GROUP_HEADER_HEIGHT + GROUP_PADDING_Y
        columns = compute_grid_columns(len(group_elements), group_width)
        base_gap_x = group_gap_x(
            group_id,
            group_width,
            len(group_elements),
            relationships,
            preview_element_groups,
            preview_group_ranks,
        )
        gap_x = int(base_gap_x * gap_multiplier)
        max_gap = max(ELEMENT_GAP_X, (group_width - (2 * GROUP_PADDING_X) - (len(group_elements) * ELEMENT_WIDTH)) // max(1, len(group_elements) - 1)) if len(group_elements) > 1 else base_gap_x
        gap_x = min(max_gap, gap_x)
        column_positions = compute_column_x_positions(group_width, columns, gap_x=gap_x)
        for index, element in enumerate(group_elements):
            element_id = str(element.get("id") or "")
            column = index % columns
            row = index // columns
            x = column_positions[column]
            y = content_y + row * (ELEMENT_HEIGHT + ELEMENT_GAP_Y)
            element_positions[element_id] = (group_x + x, group_y + y, ELEMENT_WIDTH, ELEMENT_HEIGHT)
    return ordered_by_group, element_positions


def direct_edge_style_for_relationship(
    source_group: str,
    target_group: str,
    source_box: tuple[int, int, int, int],
    target_box: tuple[int, int, int, int],
    group_ranks: dict[str, int],
    outgoing_index: int,
    outgoing_total: int,
    incoming_index: int,
    incoming_total: int,
    edge_style: dict[str, str],
) -> str:
    color_style = style_pairs(edge_style, ("strokeColor", "fontColor"))
    source_slot = slot_ratio(outgoing_index, outgoing_total)
    target_slot = slot_ratio(incoming_index, incoming_total)
    if incoming_total == 1 and outgoing_total > 1:
        target_slot = source_slot
    if source_group == target_group:
        source_center_x = source_box[0] + (source_box[2] / 2)
        target_center_x = target_box[0] + (target_box[2] / 2)
        if source_center_x <= target_center_x:
            exit_x, entry_x = "1", "0"
        else:
            exit_x, entry_x = "0", "1"
        return (
            f"edgeStyle=none;html=1;{color_style}endArrow=block;endFill=1;"
            f"exitX={exit_x};exitY=0.5;exitDx=0;exitDy=0;"
            f"entryX={entry_x};entryY=0.5;entryDx=0;entryDy=0;"
        )
    exit_x = f"{source_slot:.3f}"
    entry_x = f"{target_slot:.3f}"
    if group_ranks[target_group] > group_ranks[source_group]:
        return (
            f"edgeStyle=none;html=1;{color_style}endArrow=block;endFill=1;"
            f"exitX={exit_x};exitY=1;exitDx=0;exitDy=0;"
            f"entryX={entry_x};entryY=0;entryDx=0;entryDy=0;"
        )
    return (
        f"edgeStyle=none;html=1;{color_style}endArrow=block;endFill=1;"
        f"exitX={exit_x};exitY=0;exitDx=0;exitDy=0;"
        f"entryX={entry_x};entryY=1;entryDx=0;entryDy=0;"
    )




def layer_delta_for_relationship(
    relationship: dict[str, Any],
    source: str,
    target: str,
    element_groups: dict[str, str],
    group_ranks: dict[str, int],
) -> int:
    source_group = element_groups.get(source)
    target_group = element_groups.get(target)
    if not source_group or not target_group:
        return 0
    return group_ranks.get(target_group, 0) - group_ranks.get(source_group, 0)


def compute_group_layouts(
    groups: list[dict[str, Any]],
    elements_by_group: dict[str, list[dict[str, Any]]],
    strategy: str,
) -> dict[str, dict[str, int]]:
    del strategy
    layouts: dict[str, dict[str, int]] = {}
    y_cursor = GROUP_MARGIN_Y
    for group_id in ordered_group_ids(groups):
        group_height = compute_group_height(len(elements_by_group.get(group_id, [])), GROUP_WIDTH)
        layouts[group_id] = {
            "x": GROUP_MARGIN_X,
            "y": y_cursor,
            "width": GROUP_WIDTH,
            "height": group_height,
        }
        y_cursor += group_height + GROUP_GAP_Y
    page_height = compute_page_height([box["height"] for box in layouts.values()])
    page_side = max(PAGE_MIN_SIDE, GROUP_MARGIN_X * 2 + GROUP_WIDTH, page_height)
    layouts["_page"] = {"width": page_side, "height": page_side}
    return layouts


def slot_ratio(index: int, total: int) -> float:
    if total <= 1:
        return 0.5
    return (index + 1) / (total + 1)


def center_of(box: tuple[int, int, int, int]) -> tuple[float, float]:
    x, y, w, h = box
    return x + (w / 2), y + (h / 2)


def edge_anchor_style(
    source_box: tuple[int, int, int, int],
    target_box: tuple[int, int, int, int],
    outgoing_index: int,
    outgoing_total: int,
    incoming_index: int,
    incoming_total: int,
    *,
    force_vertical: bool = False,
) -> str:
    source_center_x, source_center_y = center_of(source_box)
    target_center_x, target_center_y = center_of(target_box)
    dx = target_center_x - source_center_x
    dy = target_center_y - source_center_y

    if force_vertical or abs(dy) >= abs(dx):
        exit_x = slot_ratio(outgoing_index, outgoing_total)
        entry_x = slot_ratio(incoming_index, incoming_total)
        if dy >= 0:
            return (
                f"exitX={exit_x:.3f};exitY=1;exitDx=0;exitDy=0;"
                f"entryX={entry_x:.3f};entryY=0;entryDx=0;entryDy=0;"
            )
        return (
            f"exitX={exit_x:.3f};exitY=0;exitDx=0;exitDy=0;"
            f"entryX={entry_x:.3f};entryY=1;entryDx=0;entryDy=0;"
        )

    exit_y = slot_ratio(outgoing_index, outgoing_total)
    entry_y = slot_ratio(incoming_index, incoming_total)
    if dx >= 0:
        return (
            f"exitX=1;exitY={exit_y:.3f};exitDx=0;exitDy=0;"
            f"entryX=0;entryY={entry_y:.3f};entryDx=0;entryDy=0;"
        )
    return (
        f"exitX=0;exitY={exit_y:.3f};exitDx=0;exitDy=0;"
        f"entryX=1;entryY={entry_y:.3f};entryDx=0;entryDy=0;"
    )


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def build_cross_group_waypoints(
    source_box: tuple[int, int, int, int],
    target_box: tuple[int, int, int, int],
    outgoing_index: int,
    outgoing_total: int,
    incoming_index: int,
    incoming_total: int,
) -> list[tuple[float, float]]:
    source_center_x, source_center_y = center_of(source_box)
    target_center_x, target_center_y = center_of(target_box)
    source_x, source_y, source_w, source_h = source_box
    target_x, target_y, target_w, target_h = target_box

    downward = target_center_y >= source_center_y
    source_stub_y = source_y + source_h + EDGE_STUB if downward else source_y - EDGE_STUB
    target_stub_y = target_y - EDGE_STUB if downward else target_y + target_h + EDGE_STUB

    start_x = source_x + source_w * slot_ratio(outgoing_index, outgoing_total)
    end_x = target_x + target_w * slot_ratio(incoming_index, incoming_total)

    left_bound = min(source_x, target_x)
    right_bound = max(source_x + source_w, target_x + target_w)
    route_on_left = target_center_x < source_center_x
    if route_on_left:
        outer_x = left_bound - 36 - ((outgoing_index + incoming_index) * EDGE_LANE_STEP)
        outer_x = clamp(outer_x, 24, PAGE_MIN_SIDE - 24)
    else:
        outer_x = right_bound + 36 + ((outgoing_index + incoming_index) * EDGE_LANE_STEP)

    if abs(target_center_x - source_center_x) < 220:
        lane_base_x = (source_center_x + target_center_x) / 2
        spread = ((outgoing_index - (outgoing_total - 1) / 2) + (incoming_index - (incoming_total - 1) / 2)) * EDGE_LANE_STEP
        outer_x = lane_base_x + spread

    return [
        (start_x, source_stub_y),
        (outer_x, source_stub_y),
        (outer_x, target_stub_y),
        (end_x, target_stub_y),
    ]


def solve_logic_view_layout(model: dict[str, Any]) -> dict[str, Any]:
    solved = copy.deepcopy(model)
    solved.setdefault("layout_suggestion", {"strategy": "stacked-groups"})
    return solved
