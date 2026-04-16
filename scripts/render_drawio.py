from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from orthogonal_router import Box, route_edge, style_for_ports
from style_profiles import effective_subject_style, resolve_style_profile


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
CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")
TYPE_LABELS_ZH = {
    "service": "\u670d\u52a1",
    "interface": "\u754c\u9762",
    "external": "\u5916\u90e8\u7cfb\u7edf",
    "orchestrator": "\u7f16\u6392\u6838\u5fc3",
    "subsystem": "\u5b50\u7cfb\u7edf",
    "component": "\u7ec4\u4ef6",
}
TYPE_LABELS_EN = {
    "service": "Service",
    "interface": "Interface",
    "external": "External System",
    "orchestrator": "Orchestrator",
    "subsystem": "Subsystem",
    "component": "Component",
}


def style_pairs(style: dict[str, str], keys: tuple[str, ...]) -> str:
    return "".join(
        f"{key}={style[key]};"
        for key in keys
        if key in style
    )


def load_view_model(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def contains_cjk(value: str) -> bool:
    return bool(CJK_PATTERN.search(value or ""))


def infer_language(view_model: dict[str, Any]) -> str:
    explicit = str(view_model.get("language") or view_model.get("locale") or "").strip().lower()
    if explicit:
        if explicit.startswith("zh"):
            return "zh"
        if explicit.startswith("en"):
            return "en"
    samples: list[str] = []
    for key in ("title", "summary", "scope"):
        raw = view_model.get(key)
        if isinstance(raw, str):
            samples.append(raw)
    for collection_key in ("groups", "elements", "relationships", "uncertainties"):
        raw = view_model.get(collection_key)
        if isinstance(raw, list):
            for item in raw[:12]:
                if isinstance(item, dict):
                    for key in ("label", "description", "summary", "reason"):
                        value = item.get(key)
                        if isinstance(value, str):
                            samples.append(value)
                elif isinstance(item, str):
                    samples.append(item)
    joined = " ".join(samples)
    return "zh" if contains_cjk(joined) else "en"


def localized_default_label(kind: str, language: str) -> str:
    if language == "zh":
        defaults = {
            "ungrouped": "\u5176\u4ed6",
            "logic-view": "\u903b\u8f91\u89c6\u56fe",
        }
    else:
        defaults = {
            "ungrouped": "Other",
            "logic-view": "Logic View",
        }
    return defaults.get(kind, kind)


def show_element_type(view_model: dict[str, Any]) -> bool:
    render_hints = view_model.get("render_hints")
    if isinstance(render_hints, dict):
        logic_hints = render_hints.get("logic")
        if isinstance(logic_hints, dict) and "show_element_type" in logic_hints:
            return bool(logic_hints["show_element_type"])
    return False


def localized_type_label(element_type: str, language: str) -> str:
    normalized = (element_type or "component").strip().lower()
    labels = TYPE_LABELS_ZH if language == "zh" else TYPE_LABELS_EN
    return labels.get(normalized, element_type or labels["component"])


def show_cross_group_edges(view_model: dict[str, Any]) -> bool:
    render_hints = view_model.get("render_hints")
    if isinstance(render_hints, dict):
        logic_hints = render_hints.get("logic")
        if isinstance(logic_hints, dict) and "show_cross_group_edges" in logic_hints:
            return bool(logic_hints["show_cross_group_edges"])
    return True


def sanitize_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value)
    return cleaned or "item"


def drawio_filename_for_view(view_model: dict[str, Any], source_path: Path) -> str:
    view = str(view_model.get("view") or source_path.stem).strip().lower()
    if not view:
        view = "diagram"
    suffix = "-view" if not view.endswith("-view") else ""
    return f"{view}{suffix}.drawio"


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


def build_logic_diagram_xml(view_model: dict[str, Any]) -> str:
    groups = view_model.get("groups") or []
    elements = view_model.get("elements") or []
    relationships = view_model.get("relationships") or []
    language = infer_language(view_model)
    title = str(view_model.get("title") or localized_default_label("logic-view", language))
    include_cross_group_edges = show_cross_group_edges(view_model)
    layout_strategy = get_layout_strategy(view_model)
    include_element_type = show_element_type(view_model)
    profile = resolve_style_profile(view_model)

    group_order = ordered_group_ids(groups)
    elements_by_group: dict[str, list[dict[str, Any]]] = {group_id: [] for group_id in group_order}
    ungrouped: list[dict[str, Any]] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        group_id = str(element.get("group") or "")
        if group_id in elements_by_group:
            elements_by_group[group_id].append(element)
        else:
            ungrouped.append(element)
    if ungrouped:
        group_order.append("__ungrouped__")
        groups = list(groups) + [{
            "id": "__ungrouped__",
            "label": localized_default_label("ungrouped", language),
            "description": "",
        }]
        elements_by_group["__ungrouped__"] = ungrouped
    preview_group_ranks = {group_id: index for index, group_id in enumerate(group_order)}
    preview_element_groups: dict[str, str] = {}
    for group_id, grouped_elements in elements_by_group.items():
        for element in grouped_elements:
            if isinstance(element, dict) and element.get("id"):
                preview_element_groups[str(element["id"])] = group_id

    root = ET.Element("mxfile", host="app.diagrams.net", version="24.7.17")
    diagram = ET.SubElement(root, "diagram", id="logic-view", name=title)
    group_layouts = compute_group_layouts(
        [group for group in groups if isinstance(group, dict)],
        elements_by_group,
        layout_strategy,
    )
    page_meta = group_layouts.get("_page", {})
    page_width = page_meta.get("width")
    page_height = page_meta.get("height")
    if not isinstance(page_width, int) or not isinstance(page_height, int):
        group_heights = [
            compute_group_height(len(elements_by_group.get(group["id"], [])), GROUP_WIDTH)
            for group in groups
            if isinstance(group, dict) and group.get("id")
        ]
        page_height = compute_page_height(group_heights)
        page_width = max(PAGE_MIN_SIDE, GROUP_MARGIN_X * 2 + GROUP_WIDTH, page_height)
        page_height = max(page_width, page_height)
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        dx="1600",
        dy="1200",
        grid="1",
        gridSize="10",
        guides="1",
        tooltips="1",
        connect="1",
        arrows="1",
        fold="1",
        page="1",
        pageScale="1",
        pageWidth=str(page_width),
        pageHeight=str(page_height),
        math="0",
        shadow="0",
    )
    mx_root = ET.SubElement(model, "root")
    ET.SubElement(mx_root, "mxCell", id="0")
    ET.SubElement(mx_root, "mxCell", id="1", parent="0")

    ordered_elements_by_group: dict[str, list[dict[str, Any]]] = {}
    element_positions: dict[str, tuple[int, int, int, int]] = {}
    element_groups: dict[str, str] = {}
    outgoing_edges: dict[str, list[dict[str, Any]]] = {}
    incoming_edges: dict[str, list[dict[str, Any]]] = {}
    routing_obstacles: list[Box] = []
    cell_id = 2
    if layout_strategy == "stacked-groups":
        for gap_multiplier in DIRECT_LAYOUT_GAP_MULTIPLIERS:
            candidate_groups, candidate_positions = compute_stacked_positions(
                group_order,
                groups,
                group_layouts,
                elements_by_group,
                relationships,
                preview_element_groups,
                preview_group_ranks,
                gap_multiplier,
            )
            direct_conflicts = compute_direct_conflicts(
                relationships,
                preview_element_groups,
                preview_group_ranks,
                candidate_positions,
            )
            if not direct_conflicts:
                ordered_elements_by_group = candidate_groups
                element_positions = candidate_positions
                break
        if not ordered_elements_by_group:
            conflict_text = "; ".join(direct_conflicts[:6]) if direct_conflicts else "unknown direct-line conflict"
            suggestions = minimal_suppression_suggestions(relationships, direct_conflicts)
            suggestion_text = "; ".join(suggestions[:4]) if suggestions else "no minimal suppression suggestion available"
            raise ValueError(
                "stacked-groups layout could not satisfy straight-line constraint: "
                f"{conflict_text}. Minimal suppression suggestions: {suggestion_text}. "
                "Prefer setting render=false only on the suggested relationships instead of removing all cross-group edges."
            )

    for group in groups:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("id") or f"group-{cell_id}")
        group_label = str(group.get("label") or group_id)
        group_elements = ordered_elements_by_group.get(group_id)
        if group_elements is None:
            group_elements = ordered_group_elements(
                group_id,
                elements_by_group,
                relationships,
                preview_element_groups,
                preview_group_ranks,
            )
        layout_box = group_layouts.get(group_id)
        if not layout_box:
            continue
        group_height = layout_box["height"]
        group_width = layout_box["width"]
        group_x = layout_box["x"]
        group_y = layout_box["y"]

        group_cell_id = f"group-{sanitize_id(group_id)}"
        group_value = group_label
        if group.get("description"):
            group_value = f"{group_label}\n{group['description']}"
        group_style = effective_subject_style(profile, "group", group)

        group_cell = ET.SubElement(
            mx_root,
            "mxCell",
            id=group_cell_id,
            value=group_value,
            style=(
                "swimlane;fontStyle=1;horizontal=1;rounded=1;html=1;"
                f"whiteSpace=wrap;startSize=44;{style_pairs(group_style, ('fillColor', 'strokeColor', 'fontColor'))}"
            ),
            vertex="1",
            parent="1",
        )
        ET.SubElement(
            group_cell,
            "mxGeometry",
            x=str(group_x),
            y=str(group_y),
            width=str(group_width),
            height=str(group_height),
            attrib={"as": "geometry"},
        )
        routing_obstacles.append(
            Box(
                id=f"{group_id}-header",
                x=group_x,
                y=group_y,
                width=group_width,
                height=GROUP_HEADER_HEIGHT,
                kind="group-header",
            )
        )

        content_y = GROUP_HEADER_HEIGHT + GROUP_PADDING_Y
        columns = compute_grid_columns(len(group_elements), group_width)
        gap_x = group_gap_x(
            group_id,
            group_width,
            len(group_elements),
            relationships,
            preview_element_groups,
            preview_group_ranks,
        )
        column_positions = compute_column_x_positions(group_width, columns, gap_x=gap_x)

        for index, element in enumerate(group_elements):
            element_id = str(element.get("id") or f"element-{cell_id}")
            label = str(element.get("label") or element_id)
            description = str(element.get("description") or "")
            value = label
            if include_element_type:
                element_type = localized_type_label(str(element.get("type") or "component"), language)
                value = f"{value}\n{element_type}"
            if description:
                value = f"{value}\n{description}"
            element_style = effective_subject_style(profile, "node", element)

            column = index % columns
            row = index // columns
            x = column_positions[column]
            y = content_y + row * (ELEMENT_HEIGHT + ELEMENT_GAP_Y)
            element_cell_id = f"element-{sanitize_id(element_id)}"
            element_cell = ET.SubElement(
                mx_root,
                "mxCell",
                id=element_cell_id,
                value=value,
                style=(
                    "rounded=1;whiteSpace=wrap;html=1;arcSize=6;spacing=8;"
                    f"fontSize=12;{style_pairs(element_style, ('fillColor', 'strokeColor', 'fontColor'))}"
                ),
                vertex="1",
                parent=group_cell_id,
            )
            ET.SubElement(
                element_cell,
                "mxGeometry",
                x=str(x),
                y=str(y),
                width=str(ELEMENT_WIDTH),
                height=str(ELEMENT_HEIGHT),
                attrib={"as": "geometry"},
            )
            element_box = element_positions.get(element_id)
            if element_box is not None and layout_strategy == "stacked-groups":
                absolute_x, absolute_y, _, _ = element_box
                x = absolute_x - group_x
                y = absolute_y - group_y
            else:
                absolute_x = group_x + x
                absolute_y = group_y + y
                element_positions[element_id] = (
                    absolute_x,
                    absolute_y,
                    ELEMENT_WIDTH,
                    ELEMENT_HEIGHT,
                )
            element_groups[element_id] = group_id
            routing_obstacles.append(
                Box(
                    id=element_id,
                    x=absolute_x,
                    y=absolute_y,
                    width=ELEMENT_WIDTH,
                    height=ELEMENT_HEIGHT,
                    kind="node",
                )
            )
            cell_id += 1

    group_ranks = {group_id: index for index, group_id in enumerate(group_order)}
    reserved_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []

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
        if not include_cross_group_edges and element_groups.get(source) != element_groups.get(target):
            continue
        outgoing_edges.setdefault(source, []).append(relationship)
        incoming_edges.setdefault(target, []).append(relationship)

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
        if not include_cross_group_edges and element_groups.get(source) != element_groups.get(target):
            continue

        source_siblings = outgoing_edges.get(source, [])
        target_siblings = incoming_edges.get(target, [])
        relationship_style = effective_subject_style(profile, "edge", relationship)
        outgoing_index = source_siblings.index(relationship)
        incoming_index = target_siblings.index(relationship)
        source_box = Box(id=source, x=element_positions[source][0], y=element_positions[source][1], width=element_positions[source][2], height=element_positions[source][3])
        target_box = Box(id=target, x=element_positions[target][0], y=element_positions[target][1], width=element_positions[target][2], height=element_positions[target][3])
        use_direct_style = layout_strategy == "stacked-groups"
        routed = None
        if not use_direct_style:
            routed = route_edge(
                source_box,
                target_box,
                page_width=page_width,
                page_height=page_height,
                obstacles=routing_obstacles,
                reserved_segments=reserved_segments,
            )
        if use_direct_style:
            delta = layer_delta_for_relationship(
                relationship,
                source,
                target,
                element_groups,
                group_ranks,
            )
            directional_source_siblings = [
                sibling
                for sibling in source_siblings
                if layer_delta_for_relationship(sibling, source, str(sibling.get("target") or ""), element_groups, group_ranks) == delta
            ]
            directional_target_siblings = [
                sibling
                for sibling in target_siblings
                if layer_delta_for_relationship(
                    sibling,
                    str(sibling.get("source") or ""),
                    target,
                    element_groups,
                    group_ranks,
                ) == delta
            ]
            direct_outgoing_index = directional_source_siblings.index(relationship)
            direct_incoming_index = directional_target_siblings.index(relationship)
            edge_style = direct_edge_style_for_relationship(
                element_groups[source],
                element_groups[target],
                element_positions[source],
                element_positions[target],
                group_ranks,
                direct_outgoing_index,
                len(directional_source_siblings),
                direct_incoming_index,
                len(directional_target_siblings),
                relationship_style,
            )
            if relationship.get("inferred"):
                edge_style += "dashed=1;"
        else:
            edge_style = (
                "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
                f"html=1;{style_pairs(relationship_style, ('strokeColor', 'fontColor'))}endArrow=block;endFill=1;"
            )
            edge_style += style_for_ports(routed.source_port, routed.target_port)
            if relationship.get("inferred"):
                edge_style += "dashed=1;"

        edge = ET.SubElement(
            mx_root,
            "mxCell",
            id=f"edge-{sanitize_id(source)}-{sanitize_id(target)}",
            value=str(relationship.get("label") or ""),
            style=edge_style,
            edge="1",
            parent="1",
            source=f"element-{sanitize_id(source)}",
            target=f"element-{sanitize_id(target)}",
        )
        geometry = ET.SubElement(edge, "mxGeometry", relative="1", attrib={"as": "geometry"})
        if not use_direct_style:
            points = ET.SubElement(geometry, "Array", attrib={"as": "points"})
            for point_x, point_y in routed.points:
                ET.SubElement(
                    points,
                    "mxPoint",
                    x=f"{point_x:.1f}",
                    y=f"{point_y:.1f}",
                )
            reserved_segments.append((routed.source_port.anchor, routed.points[0]))
            for start_point, end_point in zip(routed.points, routed.points[1:]):
                reserved_segments.append((start_point, end_point))
            reserved_segments.append((routed.points[-1], routed.target_port.anchor))

    return ET.tostring(root, encoding="unicode")


RUNTIME_ROOT_MARGIN = 24
RUNTIME_HEADER_HEIGHT = 44
RUNTIME_PARTICIPANT_WIDTH = 190
RUNTIME_PARTICIPANT_GAP = 36
RUNTIME_SECTION_GAP = 28
RUNTIME_SECTION_PADDING_X = 26
RUNTIME_SECTION_PADDING_Y = 18
RUNTIME_SECTION_HEADER = 36
RUNTIME_STEP_GAP_Y = 52
RUNTIME_BRANCH_GAP_Y = 36
RUNTIME_ACTIVATION_WIDTH = 16
RUNTIME_ACTIVATION_HEIGHT = 34
RUNTIME_MIN_PAGE_WIDTH = 1800
RUNTIME_MIN_SECTION_HEIGHT = 140


def runtime_primary_paths(view_model: dict[str, Any]) -> list[dict[str, Any]]:
    raw = view_model.get("primary_paths")
    if isinstance(raw, list):
        return [path for path in raw if isinstance(path, dict) and path.get("id")]
    return []


def runtime_relationship_map(view_model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for relationship in view_model.get("relationships") or []:
        if isinstance(relationship, dict):
            relationship_id = str(relationship.get("id") or "").strip()
            if relationship_id:
                mapping[relationship_id] = relationship
    return mapping


def runtime_group_order(view_model: dict[str, Any]) -> dict[str, int]:
    ordered = ordered_group_ids(view_model.get("groups") or [])
    return {group_id: index for index, group_id in enumerate(ordered)}


def runtime_used_element_ids(primary_paths: list[dict[str, Any]], relationship_map: dict[str, dict[str, Any]]) -> set[str]:
    used: set[str] = set()
    for path in primary_paths:
        for relationship_id in path.get("main_step_ids") or []:
            relationship = relationship_map.get(str(relationship_id))
            if not relationship:
                continue
            used.add(str(relationship.get("source") or ""))
            used.add(str(relationship.get("target") or ""))
        for branch in path.get("branches") or []:
            if not isinstance(branch, dict):
                continue
            for relationship_id in branch.get("step_ids") or []:
                relationship = relationship_map.get(str(relationship_id))
                if not relationship:
                    continue
                used.add(str(relationship.get("source") or ""))
                used.add(str(relationship.get("target") or ""))
    return {item for item in used if item}


def ordered_runtime_elements(view_model: dict[str, Any]) -> list[dict[str, Any]]:
    primary_paths = runtime_primary_paths(view_model)
    relationship_map = runtime_relationship_map(view_model)
    used_element_ids = runtime_used_element_ids(primary_paths, relationship_map)
    group_rank = runtime_group_order(view_model)
    indexed: list[tuple[int, int, dict[str, Any]]] = []
    for original_index, element in enumerate(view_model.get("elements") or []):
        if not isinstance(element, dict):
            continue
        element_id = str(element.get("id") or "")
        if used_element_ids and element_id not in used_element_ids:
            continue
        indexed.append((group_rank.get(str(element.get("group") or ""), 999), original_index, element))
    indexed.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in indexed]


def runtime_element_lookup(view_model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for element in view_model.get("elements") or []:
        if isinstance(element, dict):
            element_id = str(element.get("id") or "").strip()
            if element_id:
                mapping[element_id] = element
    return mapping


def runtime_rows_for_path(path: dict[str, Any], relationship_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for step_index, relationship_id in enumerate(path.get("main_step_ids") or [], start=1):
        relationship = relationship_map.get(str(relationship_id))
        if relationship:
            rows.append({
                "type": "edge",
                "relationship": relationship,
                "prefix": str(step_index),
                "branch": False,
            })
    for branch_index, branch in enumerate(path.get("branches") or [], start=1):
        if not isinstance(branch, dict):
            continue
        label = str(branch.get("label") or f"\u5206\u652f {branch_index}")
        when = str(branch.get("when") or "").strip()
        rows.append({
            "type": "branch_label",
            "label": label,
            "when": when,
        })
        for step_index, relationship_id in enumerate(branch.get("step_ids") or [], start=1):
            relationship = relationship_map.get(str(relationship_id))
            if relationship:
                rows.append({
                    "type": "edge",
                    "relationship": relationship,
                    "prefix": f"B{branch_index}.{step_index}",
                    "branch": True,
                })
    return rows


def runtime_section_height(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return RUNTIME_MIN_SECTION_HEIGHT
    content_height = RUNTIME_SECTION_PADDING_Y * 2
    first = True
    for row in rows:
        if not first:
            content_height += RUNTIME_BRANCH_GAP_Y if row.get("type") == "branch_label" else RUNTIME_STEP_GAP_Y
        first = False
    content_height += RUNTIME_ACTIVATION_HEIGHT
    return max(RUNTIME_MIN_SECTION_HEIGHT, RUNTIME_SECTION_HEADER + content_height)


def runtime_scope_lines(view_model: dict[str, Any]) -> list[str]:
    scope = view_model.get("scope")
    if isinstance(scope, str) and scope.strip():
        return [scope.strip()]
    if isinstance(scope, dict):
        lines: list[str] = []
        focus = str(scope.get("focus") or "").strip()
        if focus:
            lines.append(focus)
        included = scope.get("included_surfaces")
        if isinstance(included, list) and included:
            lines.append(
                f"\u8303\u56f4\uff1a{len([item for item in included if isinstance(item, str) and item.strip()])} \u4e2a\u8fd0\u884c\u9762"
            )
        strategy = str(scope.get("reading_strategy") or "").strip()
        if strategy:
            lines.append(strategy)
        return lines[:3]
    return []


def runtime_note_text(*parts: str) -> str:
    cleaned = [part.strip() for part in parts if isinstance(part, str) and part.strip()]
    return "\n".join(cleaned[:2])


def runtime_participants_for_rows(
    rows: list[dict[str, Any]],
    element_lookup: dict[str, dict[str, Any]],
    group_rank: dict[str, int],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    indexed: list[tuple[int, str, dict[str, Any]]] = []
    for row in rows:
        if row.get("type") != "edge":
            continue
        relationship = row.get("relationship")
        if not isinstance(relationship, dict):
            continue
        for endpoint in (str(relationship.get("source") or ""), str(relationship.get("target") or "")):
            if not endpoint or endpoint in seen or endpoint not in element_lookup:
                continue
            seen.add(endpoint)
            element = element_lookup[endpoint]
            indexed.append((group_rank.get(str(element.get("group") or ""), 999), endpoint, element))
    indexed.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in indexed]


def build_runtime_diagram_xml(view_model: dict[str, Any]) -> str:
    primary_paths = runtime_primary_paths(view_model)
    if not primary_paths:
        raise ValueError("Runtime view requires a non-empty top-level primary_paths array.")

    relationship_map = runtime_relationship_map(view_model)
    element_lookup = runtime_element_lookup(view_model)
    group_rank = runtime_group_order(view_model)

    language = infer_language(view_model)
    title = str(view_model.get("title") or ("\u8fd0\u884c\u89c6\u56fe" if language == "zh" else "Runtime View"))
    profile = resolve_style_profile(view_model)

    section_layouts: list[dict[str, Any]] = []
    max_section_width = 0
    current_y = 24
    for path in primary_paths:
        rows = runtime_rows_for_path(path, relationship_map)
        participants = runtime_participants_for_rows(rows, element_lookup, group_rank)
        if not participants:
            continue
        participant_count = len(participants)
        section_inner_width = (
            (participant_count * RUNTIME_PARTICIPANT_WIDTH)
            + (max(0, participant_count - 1) * RUNTIME_PARTICIPANT_GAP)
        )
        section_width = max(960, section_inner_width + (2 * RUNTIME_SECTION_PADDING_X))
        participant_band_height = 120
        height = runtime_section_height(rows) + participant_band_height
        section_layouts.append({
            "path": path,
            "rows": rows,
            "participants": participants,
            "width": section_width,
            "participant_band_height": participant_band_height,
            "y": current_y,
            "height": height,
        })
        max_section_width = max(max_section_width, section_width)
        current_y += height + RUNTIME_SECTION_GAP
    if not section_layouts:
        raise ValueError("Runtime view has no primary path with renderable participants.")

    content_height = RUNTIME_HEADER_HEIGHT + current_y + 24
    root_width = max(RUNTIME_MIN_PAGE_WIDTH - (2 * RUNTIME_ROOT_MARGIN), max_section_width)
    root_height = max(1200, content_height)
    page_width = root_width + (2 * RUNTIME_ROOT_MARGIN)
    page_height = root_height + (2 * RUNTIME_ROOT_MARGIN)

    root = ET.Element("mxfile", host="app.diagrams.net", version="24.7.17")
    diagram = ET.SubElement(root, "diagram", id="runtime-view", name=title)
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        dx="1600",
        dy="1200",
        grid="1",
        gridSize="10",
        guides="1",
        tooltips="1",
        connect="1",
        arrows="1",
        fold="1",
        page="1",
        pageScale="1",
        pageWidth=str(page_width),
        pageHeight=str(page_height),
        math="0",
        shadow="0",
    )
    mx_root = ET.SubElement(model, "root")
    ET.SubElement(mx_root, "mxCell", id="0")
    ET.SubElement(mx_root, "mxCell", id="1", parent="0")

    root_group_style = effective_subject_style(profile, "group", {"color_role": "neutral"})
    root_group = ET.SubElement(
        mx_root,
        "mxCell",
        id="group-runtime-root",
        value=title,
        style=(
            "swimlane;fontStyle=1;horizontal=1;rounded=1;html=1;"
            f"whiteSpace=wrap;startSize={RUNTIME_HEADER_HEIGHT};{style_pairs(root_group_style, ('fillColor', 'strokeColor', 'fontColor'))}"
        ),
        vertex="1",
        parent="1",
    )
    ET.SubElement(
        root_group,
        "mxGeometry",
        x=str(RUNTIME_ROOT_MARGIN),
        y=str(RUNTIME_ROOT_MARGIN),
        width=str(root_width),
        height=str(root_height),
        attrib={"as": "geometry"},
    )

    activation_cells: dict[str, str] = {}
    for section_index, section in enumerate(section_layouts, start=1):
        path = section["path"]
        participants = section["participants"]
        section_width = section["width"]
        section_x = max(0, (root_width - section_width) // 2)
        section_id = f"runtime-section-{sanitize_id(str(path.get('id') or section_index))}"
        section_style = effective_subject_style(profile, "group", {"color_role": "neutral"})
        section_label = str(path.get("label") or path.get("id") or f"\u8def\u5f84 {section_index}")
        section_cell = ET.SubElement(
            mx_root,
            "mxCell",
            id=section_id,
            value=section_label,
            style=(
                "swimlane;fontStyle=1;horizontal=1;rounded=0;html=1;"
                "whiteSpace=wrap;startSize=36;fillColor=#ffffff;"
                f"{style_pairs(section_style, ('strokeColor', 'fontColor'))}"
            ),
            vertex="1",
            parent="group-runtime-root",
        )
        ET.SubElement(
            section_cell,
            "mxGeometry",
            x=str(section_x),
            y=str(section["y"] + RUNTIME_HEADER_HEIGHT),
            width=str(section_width),
            height=str(section["height"]),
            attrib={"as": "geometry"},
        )

        section_inner_y = section["y"] + RUNTIME_HEADER_HEIGHT
        participant_positions: dict[str, tuple[int, int, int, int]] = {}
        for participant_index, element in enumerate(participants):
            column_x = RUNTIME_SECTION_PADDING_X + participant_index * (RUNTIME_PARTICIPANT_WIDTH + RUNTIME_PARTICIPANT_GAP)
            column_style = effective_subject_style(profile, "group", element)
            column_id = f"participant-{sanitize_id(str(path.get('id') or section_index))}-{sanitize_id(str(element.get('id') or participant_index))}"
            column_cell = ET.SubElement(
                mx_root,
                "mxCell",
                id=column_id,
                value=str(element.get("label") or element.get("id") or ""),
                style=(
                    "swimlane;fontStyle=1;horizontal=1;rounded=0;html=1;"
                    "whiteSpace=wrap;startSize=44;dashed=1;"
                    f"{style_pairs(column_style, ('strokeColor', 'fontColor'))}"
                ),
                vertex="1",
                parent=section_id,
            )
            ET.SubElement(
                column_cell,
                "mxGeometry",
                x=str(column_x),
                y=str(RUNTIME_SECTION_HEADER),
                width=str(RUNTIME_PARTICIPANT_WIDTH),
                height=str(section["height"] - RUNTIME_SECTION_HEADER),
                attrib={"as": "geometry"},
            )
            participant_positions[str(element.get("id") or "")] = (
                column_x,
                section_inner_y + RUNTIME_SECTION_HEADER,
                RUNTIME_PARTICIPANT_WIDTH,
                section["height"] - RUNTIME_SECTION_HEADER,
            )

        current_row_y = (
            RUNTIME_SECTION_HEADER
            + section["participant_band_height"]
            + RUNTIME_SECTION_PADDING_Y
        )
        for row_index, row in enumerate(section["rows"], start=1):
            if row_index > 1:
                current_row_y += RUNTIME_BRANCH_GAP_Y if row.get("type") == "branch_label" else RUNTIME_STEP_GAP_Y
            if row.get("type") == "branch_label":
                note_cell = ET.SubElement(
                    mx_root,
                    "mxCell",
                    id=f"{section_id}-branch-{row_index}",
                    value=runtime_note_text(f"\u5206\u652f\uff1a{row.get('label')}", str(row.get("when") or "")),
                    style=(
                        "text;html=1;whiteSpace=wrap;rounded=0;strokeColor=none;fillColor=none;"
                        "fontSize=12;fontStyle=1;align=left;verticalAlign=middle;spacingLeft=0;fontColor=#374151;"
                    ),
                    vertex="1",
                    parent=section_id,
                )
                ET.SubElement(
                    note_cell,
                    "mxGeometry",
                    x="18",
                    y=str(current_row_y),
                    width=str(max(240, section_width - 36)),
                    height="22",
                    attrib={"as": "geometry"},
                )
                continue

            relationship = row["relationship"]
            source = str(relationship.get("source") or "")
            target = str(relationship.get("target") or "")
            if source not in participant_positions or target not in participant_positions:
                continue
            for participant_id in {source, target}:
                activation_id = f"activation-{sanitize_id(str(path.get('id') or section_index))}-{sanitize_id(participant_id)}-{row_index}"
                if activation_id in activation_cells:
                    continue
                participant_x, _, participant_w, _ = participant_positions[participant_id]
                activation_x = participant_x + (participant_w - RUNTIME_ACTIVATION_WIDTH) // 2
                activation_style = effective_subject_style(profile, "node", {"color_role": "neutral"})
                activation_cell = ET.SubElement(
                    mx_root,
                    "mxCell",
                    id=activation_id,
                    value="",
                    style=(
                        "rounded=0;whiteSpace=wrap;html=1;arcSize=2;"
                        f"fontSize=12;{style_pairs(activation_style, ('fillColor', 'strokeColor', 'fontColor'))}"
                    ),
                    vertex="1",
                    parent=section_id,
                )
                ET.SubElement(
                    activation_cell,
                    "mxGeometry",
                    x=str(activation_x),
                    y=str(current_row_y),
                    width=str(RUNTIME_ACTIVATION_WIDTH),
                    height=str(RUNTIME_ACTIVATION_HEIGHT),
                    attrib={"as": "geometry"},
                )
                activation_cells[activation_id] = activation_id

            source_cell_id = f"activation-{sanitize_id(str(path.get('id') or section_index))}-{sanitize_id(source)}-{row_index}"
            target_cell_id = f"activation-{sanitize_id(str(path.get('id') or section_index))}-{sanitize_id(target)}-{row_index}"
            edge_style_subject = dict(relationship)
            edge_style = effective_subject_style(profile, "edge", edge_style_subject)
            dashed = bool(relationship.get("inferred")) or bool(row.get("branch"))
            edge_style_value = (
                "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
                f"html=1;{style_pairs(edge_style, ('strokeColor', 'fontColor'))}endArrow=block;endFill=1;"
            )
            if dashed:
                edge_style_value += "dashed=1;"

            label_prefix = str(row.get("prefix") or "").strip()
            label_text = str(relationship.get("label") or "").strip()
            edge_value = f"{label_prefix} {label_text}".strip()

            edge_cell = ET.SubElement(
                mx_root,
                "mxCell",
                id=f"edge-{sanitize_id(str(path.get('id') or section_index))}-{sanitize_id(str(relationship.get('id') or row_index))}-{row_index}",
                value=edge_value,
                style=edge_style_value,
                edge="1",
                parent=section_id,
                source=source_cell_id,
                target=target_cell_id,
            )
            geometry = ET.SubElement(edge_cell, "mxGeometry", relative="1", attrib={"as": "geometry"})
            if source == target:
                points = ET.SubElement(geometry, "Array", attrib={"as": "points"})
                participant_x, _, participant_w, _ = participant_positions[source]
                loop_x = participant_x + participant_w + 28
                step_mid_y = current_row_y + (RUNTIME_ACTIVATION_HEIGHT / 2)
                ET.SubElement(points, "mxPoint", x=f"{loop_x:.1f}", y=f"{step_mid_y - 20:.1f}")
                ET.SubElement(points, "mxPoint", x=f"{loop_x:.1f}", y=f"{step_mid_y + 20:.1f}")

    return ET.tostring(root, encoding="unicode")


def render_view_model(input_path: Path, output_dir: Path) -> Path:
    view_model = load_view_model(input_path)
    view = str(view_model.get("view") or "").strip().lower()
    if view not in {"logic", "runtime"}:
        raise ValueError(
            f"Only logic and runtime view rendering are supported right now; got view={view!r} in {input_path}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / drawio_filename_for_view(view_model, input_path)
    if view == "logic":
        xml = build_logic_diagram_xml(view_model)
    else:
        xml = build_runtime_diagram_xml(view_model)
    output_path.write_text(xml, encoding="utf-8")
    return output_path


def export_rendered_preview(
    rendered_path: Path,
    preview_dir: Path,
    *,
    preview_format: str,
    preserve_alpha: bool,
) -> Path:
    from export_diagrams import export_with_real_drawio

    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_path = preview_dir / f"{rendered_path.stem}.{preview_format}"
    asyncio.run(
        export_with_real_drawio(
            rendered_path,
            preview_path,
            flatten_png=not preserve_alpha,
        )
    )
    return preview_path


def collect_input_models(input_arg: str | None) -> list[Path]:
    if not input_arg:
        raise ValueError("Provide a path to a view model JSON file or a directory containing view model JSON files.")
    input_path = Path(input_arg)
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted(path for path in input_path.glob("*.json") if path.is_file())
    raise ValueError(f"Input path not found: {input_path}")


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
    parser.add_argument(
        "--export-previews",
        action="store_true",
        help="Also export rendered draw.io files through the real draw.io renderer.",
    )
    parser.add_argument(
        "--preview-dir",
        help="Directory for exported previews (defaults to <output-dir>/exports).",
    )
    parser.add_argument(
        "--preview-format",
        default="png",
        choices=["png", "svg"],
        help="Format for exported previews.",
    )
    parser.add_argument(
        "--preserve-preview-alpha",
        action="store_true",
        help="Keep PNG alpha instead of flattening previews onto white.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    preview_dir = Path(args.preview_dir) if args.preview_dir else output_dir / "exports"
    try:
        inputs = collect_input_models(args.input)
        if not inputs:
            raise ValueError(f"No JSON view models found in {args.input}")
        for input_path in inputs:
            rendered = render_view_model(input_path, output_dir)
            print(f"Rendered {input_path} -> {rendered}")
            if args.export_previews:
                preview_path = export_rendered_preview(
                    rendered,
                    preview_dir,
                    preview_format=args.preview_format,
                    preserve_alpha=args.preserve_preview_alpha,
                )
                print(f"Previewed {rendered} -> {preview_path}")
    except Exception as exc:
        print(f"render_drawio.py failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
