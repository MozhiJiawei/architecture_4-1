from __future__ import annotations

from ..drawio_common import *  # noqa: F401,F403

USE_CASE_PAGE_WIDTH = 1680
USE_CASE_PAGE_HEIGHT = 1080
USE_CASE_ROOT_MARGIN = 24
USE_CASE_HEADER_HEIGHT = 44
USE_CASE_BOUNDARY_GAP = 32
USE_CASE_BOUNDARY_HEADER = 36
USE_CASE_BOUNDARY_MIN_WIDTH = 760
USE_CASE_NESTED_BOUNDARY_SIDE_GAP = 32
USE_CASE_NESTED_BOUNDARY_BOTTOM_GAP = 32
USE_CASE_BOUNDARY_TOP = 180
USE_CASE_BOUNDARY_HEIGHT = 700
USE_CASE_ACTOR_WIDTH = 110
USE_CASE_ACTOR_HEIGHT = 96
USE_CASE_ELLIPSE_WIDTH = 220
USE_CASE_ELLIPSE_HEIGHT = 92
USE_CASE_ELLIPSE_MIN_WIDTH = 220
USE_CASE_ELLIPSE_MAX_WIDTH = 360
USE_CASE_NOTE_WIDTH = 220
USE_CASE_NOTE_HEIGHT = 110
USE_CASE_NOTE_MIN_WIDTH = 220
USE_CASE_NOTE_MAX_WIDTH = 360
USE_CASE_LEFT_ACTOR_X = 84
USE_CASE_ACTOR_RIGHT_GAP = 96
USE_CASE_NOTE_GAP = 22
USE_CASE_LABEL_MAX_CHARS = 18
USE_CASE_LABEL_MAX_LINES = 2
USE_CASE_NOTE_MAX_CHARS = 90
USE_CASE_NOTE_MAX_LINES = 4
def normalized_element_type(raw_type: Any) -> str:
    normalized = str(raw_type or "component").strip().lower()
    alias_map = {
        "usecase": "use_case",
        "boundary": "system_boundary",
        "db": "database",
    }
    return alias_map.get(normalized, normalized)


def use_case_view_title(view_model: dict[str, Any], language: str) -> str:
    default_title = "\u7528\u4f8b\u89c6\u56fe" if language == "zh" else "Use Case View"
    return str(view_model.get("title") or default_title)


def use_case_boundary_specs(view_model: dict[str, Any], use_cases: list[dict[str, Any]], title: str) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    groups = view_model.get("groups") or []

    top_level_boundary = view_model.get("system_boundary")
    if isinstance(top_level_boundary, dict):
        boundary_id = str(top_level_boundary.get("id") or "system-boundary").strip() or "system-boundary"
        specs.append({
            "id": boundary_id,
            "label": str(top_level_boundary.get("label") or title).strip() or title,
            "subject": top_level_boundary,
        })

    for group in groups if not isinstance(top_level_boundary, dict) else []:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("id") or "").strip()
        if not group_id or any(spec["id"] == group_id for spec in specs):
            continue
        specs.append({
            "id": group_id,
            "label": str(group.get("label") or group_id).strip() or group_id,
            "subject": group,
        })

    for element in view_model.get("elements") or []:
        if not isinstance(element, dict):
            continue
        if normalized_element_type(element.get("type")) != "system_boundary":
            continue
        boundary_id = str(element.get("id") or "").strip()
        if not boundary_id or any(spec["id"] == boundary_id for spec in specs):
            continue
        specs.append({
            "id": boundary_id,
            "label": str(element.get("label") or boundary_id).strip() or boundary_id,
            "subject": element,
        })

    if not specs:
        inferred_boundary_id = str(view_model.get("id") or "system-boundary").strip() or "system-boundary"
        inferred_label = title
        if use_cases:
            boundary_ids = {
                str(use_case.get("boundary") or use_case.get("group") or "").strip()
                for use_case in use_cases
                if isinstance(use_case, dict)
            }
            boundary_ids.discard("")
            if len(boundary_ids) == 1:
                inferred_boundary_id = next(iter(boundary_ids))
        specs.append({
            "id": inferred_boundary_id,
            "label": inferred_label,
            "subject": {"id": inferred_boundary_id, "label": inferred_label, "type": "system_boundary"},
        })
    return specs


def use_case_relationships(view_model: dict[str, Any]) -> list[dict[str, Any]]:
    relationships: list[dict[str, Any]] = []
    for item in view_model.get("relationships") or []:
        if isinstance(item, dict):
            relationships.append(item)
    for index, item in enumerate(view_model.get("associations") or [], start=1):
        if not isinstance(item, dict):
            continue
        association = dict(item)
        association.setdefault("id", f"association-{index}")
        association.setdefault("kind", "association")
        association.setdefault("render", False)
        relationships.append(association)
    return relationships


def use_case_primary_ids(view_model: dict[str, Any]) -> tuple[str | None, str | None]:
    layout = view_model.get("layout_suggestion")
    if not isinstance(layout, dict):
        return None, None
    actor_id = str(layout.get("primary_actor") or "").strip() or None
    use_case_id = str(layout.get("primary_use_case") or "").strip() or None
    return actor_id, use_case_id


def use_case_boundary_for(use_case: dict[str, Any], boundary_specs: list[dict[str, Any]]) -> str:
    preferred = str(use_case.get("boundary") or use_case.get("group") or "").strip()
    if preferred and any(spec["id"] == preferred for spec in boundary_specs):
        return preferred
    grouped = str(use_case.get("group") or "").strip()
    if grouped and any(spec["id"] == grouped for spec in boundary_specs):
        return grouped
    return boundary_specs[0]["id"]


def use_case_counting(items: list[dict[str, Any]], cell_width: int, gap: int, min_rows: int = 1) -> tuple[int, int]:
    count = max(1, len(items))
    columns = 1 if count <= 3 else 2
    rows = max(min_rows, (count + columns - 1) // columns)
    width = columns * cell_width + max(0, columns - 1) * gap
    return columns, rows if rows > 0 else 1


def distribute_centers(desired: list[float], minimum_gap: int, minimum: int, maximum: int) -> list[int]:
    if not desired:
        return []
    ordered = sorted(enumerate(desired), key=lambda item: item[1])
    placed: list[tuple[int, float]] = []
    current = float(minimum)
    for original_index, target in ordered:
        position = max(target, current)
        placed.append((original_index, position))
        current = position + minimum_gap
    overflow = placed[-1][1] - maximum
    if overflow > 0:
        placed = [(index, position - overflow) for index, position in placed]
        for idx in range(len(placed) - 2, -1, -1):
            index, position = placed[idx]
            next_position = placed[idx + 1][1]
            placed[idx] = (index, min(position, next_position - minimum_gap))
        if placed[0][1] < minimum:
            shift = minimum - placed[0][1]
            placed = [(index, position + shift) for index, position in placed]
    result = [0] * len(desired)
    for original_index, position in placed:
        result[original_index] = int(position)
    return result


def use_case_node_dimensions(label: str, element_type: str) -> tuple[int, int]:
    if element_type == "note":
        display = capped_display_text(label, USE_CASE_NOTE_MAX_CHARS, USE_CASE_NOTE_MAX_LINES, 24)
        widest_units = max((weighted_text_units(line) for line in display.splitlines()), default=18)
        width = clamp(80 + widest_units * 8, USE_CASE_NOTE_MIN_WIDTH, USE_CASE_NOTE_MAX_WIDTH)
        line_count = max(1, len(display.splitlines()))
        height = max(USE_CASE_NOTE_HEIGHT, 32 + line_count * 22)
        return width, height

    display = capped_display_text(label, USE_CASE_LABEL_MAX_CHARS, USE_CASE_LABEL_MAX_LINES, 12)
    widest_units = max((weighted_text_units(line) for line in display.splitlines()), default=12)
    width = clamp(80 + widest_units * 10, USE_CASE_ELLIPSE_MIN_WIDTH, USE_CASE_ELLIPSE_MAX_WIDTH)
    line_count = max(1, len(display.splitlines()))
    height = max(USE_CASE_ELLIPSE_HEIGHT, 48 + line_count * 18)
    return width, height


def use_case_priority_style(profile: dict[str, Any], subject: dict[str, Any]) -> dict[str, str]:
    priority = str(subject.get("priority") or "").strip().upper()
    if priority == "P0":
        styled = dict(subject)
        styled.setdefault("style", {})
        if isinstance(styled["style"], dict):
            styled["style"] = {
                **styled["style"],
                "fillColor": "#f8d7da",
                "strokeColor": "#b85450",
                "fontColor": "#1f2937",
            }
        return effective_subject_style(profile, "node", styled)
    if priority == "P1":
        styled = dict(subject)
        styled.setdefault("style", {})
        if isinstance(styled["style"], dict):
            styled["style"] = {
                **styled["style"],
                "fillColor": "#fff2cc",
                "strokeColor": "#d6b656",
                "fontColor": "#1f2937",
            }
        return effective_subject_style(profile, "node", styled)
    return effective_subject_style(profile, "node", subject)


def use_case_group_ids(view_model: dict[str, Any], use_cases: list[dict[str, Any]]) -> list[str]:
    configured = [group for group in (view_model.get("groups") or []) if isinstance(group, dict) and str(group.get("id") or "").strip()]
    ordered = ordered_group_ids(configured)
    present = {str(use_case.get("group") or "").strip() for use_case in use_cases if isinstance(use_case, dict)}
    present.discard("")
    result = [group_id for group_id in ordered if group_id in present]
    for group_id in sorted(present):
        if group_id not in result:
            result.append(group_id)
    if any(not str(use_case.get("group") or "").strip() for use_case in use_cases):
        result.append("__ungrouped__")
    return result


def use_case_group_labels(view_model: dict[str, Any]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for group in view_model.get("groups") or []:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("id") or "").strip()
        if group_id:
            labels[group_id] = str(group.get("label") or group_id).strip() or group_id
    labels["__ungrouped__"] = localized_default_label("ungrouped", infer_language(view_model))
    return labels


def use_case_grouped_positions(
    boundary_box: tuple[int, int, int, int],
    use_cases: list[dict[str, Any]],
    view_model: dict[str, Any],
) -> tuple[dict[str, tuple[int, int, int, int]], list[dict[str, int | str]]]:
    bx, by, bw, bh = boundary_box
    positions: dict[str, tuple[int, int, int, int]] = {}
    zones: list[dict[str, int | str]] = []
    if not use_cases:
        return positions, zones

    use_case_map = {str(item.get("id") or ""): item for item in use_cases}
    dimensions = {
        item_id: use_case_node_dimensions(str(item.get("label") or item_id), "use_case")
        for item_id, item in use_case_map.items()
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for use_case in use_cases:
        group_id = str(use_case.get("group") or "").strip() or "__ungrouped__"
        grouped.setdefault(group_id, []).append(use_case)

    group_ids = use_case_group_ids(view_model, use_cases)
    group_labels = use_case_group_labels(view_model)
    inner_x = bx + 32
    inner_y = by + USE_CASE_BOUNDARY_HEADER + 24
    inner_width = bw - 64
    zone_gap_y = 18
    zone_header_height = 24
    current_y = inner_y

    for group_id in group_ids:
        items = grouped.get(group_id, [])
        if not items:
            continue
        widest = max(dimensions[str(item.get("id") or "")][0] for item in items)
        tallest = max(dimensions[str(item.get("id") or "")][1] for item in items)
        columns = min(3, max(1, inner_width // max(widest + 44, USE_CASE_ELLIPSE_MIN_WIDTH + 44)))
        columns = min(columns, max(1, len(items)))
        row_gap = 34
        col_gap = 40
        rows = max(1, (len(items) + columns - 1) // columns)
        zone_height = zone_header_height + rows * tallest + max(0, rows - 1) * row_gap
        zones.append({
            "id": group_id,
            "label": group_labels.get(group_id, group_id),
            "x": inner_x,
            "y": current_y,
            "width": inner_width,
            "height": zone_height,
        })
        grid_y = current_y + zone_header_height
        grid_width = columns * widest + max(0, columns - 1) * col_gap
        start_x = inner_x + max(0, (inner_width - grid_width) // 2)
        for index, item in enumerate(items):
            item_id = str(item.get("id") or "")
            item_width, item_height = dimensions[item_id]
            row = index // columns
            column = index % columns
            cell_x = start_x + column * (widest + col_gap) + max(0, (widest - item_width) // 2)
            cell_y = grid_y + row * (tallest + row_gap) + max(0, (tallest - item_height) // 2)
            positions[item_id] = (cell_x, cell_y, item_width, item_height)
        current_y += zone_height + zone_gap_y
    return positions, zones


def use_case_actor_map(actors: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for actor in actors:
        actor_id = str(actor.get("id") or "").strip()
        if actor_id:
            mapping[actor_id] = actor
    return mapping


def use_case_panel_layout(
    boundary_box: tuple[int, int, int, int],
    view_model: dict[str, Any],
    actors: list[dict[str, Any]],
    use_cases: list[dict[str, Any]],
) -> tuple[dict[str, tuple[int, int, int, int]], list[dict[str, int | str]], set[str]]:
    bx, by, bw, _ = boundary_box
    positions: dict[str, tuple[int, int, int, int]] = {}
    panels: list[dict[str, int | str]] = []
    grouped_actor_ids: set[str] = set()
    if not use_cases:
        return positions, panels, grouped_actor_ids

    actor_map = use_case_actor_map(actors)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for use_case in use_cases:
        group_id = str(use_case.get("group") or "").strip() or "__ungrouped__"
        grouped.setdefault(group_id, []).append(use_case)

    group_ids = use_case_group_ids(view_model, use_cases)
    group_labels = use_case_group_labels(view_model)
    dimensions = {
        str(item.get("id") or ""): use_case_node_dimensions(str(item.get("label") or item.get("id") or ""), "use_case")
        for item in use_cases
    }

    inner_x = bx + 32
    inner_y = by + USE_CASE_BOUNDARY_HEADER + 28
    inner_width = bw - 64
    panel_gap_x = 32
    panel_gap_y = 32
    max_group_size = max((len(grouped.get(group_id, [])) for group_id in group_ids), default=1)
    preferred_columns = 2 if max_group_size > 4 else 3
    columns = min(preferred_columns, max(1, len(group_ids)))
    panel_width = max(420, (inner_width - (panel_gap_x * max(0, columns - 1))) // columns)
    actor_box_width = 132

    def use_case_columns_for_panel(items: list[dict[str, Any]]) -> int:
        if len(items) <= 1:
            return 1
        area_width = panel_width - actor_box_width - 20
        widest = max((dimensions[str(item.get("id") or "")][0] for item in items), default=USE_CASE_ELLIPSE_WIDTH)
        if len(items) >= 4 and (widest * 2) + 26 <= area_width:
            return 2
        return 1

    row_heights: list[int] = []
    grouped_by_row: list[list[str]] = []
    for row_start in range(0, len(group_ids), columns):
        row_group_ids = group_ids[row_start : row_start + columns]
        grouped_by_row.append(row_group_ids)
        row_height = 0
        for group_id in row_group_ids:
            items = grouped.get(group_id, [])
            cols = use_case_columns_for_panel(items)
            rows = max(1, (len(items) + cols - 1) // cols)
            tallest = max((dimensions[str(item.get("id") or "")][1] for item in items), default=USE_CASE_ELLIPSE_HEIGHT)
            panel_height = max(300, 70 + rows * tallest + max(0, rows - 1) * 24)
            row_height = max(row_height, panel_height)
        row_heights.append(row_height)

    current_y = inner_y
    for row_index, row_group_ids in enumerate(grouped_by_row):
        row_height = row_heights[row_index]
        total_width = len(row_group_ids) * panel_width + max(0, len(row_group_ids) - 1) * panel_gap_x
        start_x = inner_x + max(0, (inner_width - total_width) // 2)
        for column_index, group_id in enumerate(row_group_ids):
            panel_x = start_x + column_index * (panel_width + panel_gap_x)
            panel_y = current_y
            panel = {
                "id": group_id,
                "label": group_labels.get(group_id, group_id),
                "x": panel_x,
                "y": panel_y,
                "width": panel_width,
                "height": row_height,
            }
            panels.append(panel)
            actor = actor_map.get(group_id)
            if actor:
                grouped_actor_ids.add(group_id)
                positions[group_id] = (panel_x + 18, panel_y + 74, USE_CASE_ACTOR_WIDTH, USE_CASE_ACTOR_HEIGHT)

            items = grouped.get(group_id, [])
            area_x = panel_x + actor_box_width
            area_y = panel_y + 48
            area_width = panel_width - actor_box_width - 20
            cols = use_case_columns_for_panel(items)
            widest = max((dimensions[str(item.get("id") or "")][0] for item in items), default=USE_CASE_ELLIPSE_WIDTH)
            tallest = max((dimensions[str(item.get("id") or "")][1] for item in items), default=USE_CASE_ELLIPSE_HEIGHT)
            col_gap = 26
            row_gap = 24
            grid_width = cols * widest + max(0, cols - 1) * col_gap
            start_use_case_x = area_x + max(0, (area_width - grid_width) // 2)
            for item_index, item in enumerate(items):
                item_id = str(item.get("id") or "")
                item_width, item_height = dimensions[item_id]
                row = item_index // cols
                col = item_index % cols
                x = start_use_case_x + col * (widest + col_gap) + max(0, (widest - item_width) // 2)
                y = area_y + row * (tallest + row_gap) + max(0, (tallest - item_height) // 2)
                positions[item_id] = (x, y, item_width, item_height)
        current_y += row_height + panel_gap_y

    return positions, panels, grouped_actor_ids


def use_case_panel_boundary_height(
    boundary_width: int,
    view_model: dict[str, Any],
    actors: list[dict[str, Any]],
    use_cases: list[dict[str, Any]],
) -> int:
    if not use_cases:
        return USE_CASE_BOUNDARY_HEIGHT
    fake_boundary = (0, 0, boundary_width, 10000)
    _, panels, _ = use_case_panel_layout(fake_boundary, view_model, actors, use_cases)
    if not panels:
        return USE_CASE_BOUNDARY_HEIGHT
    last_panel = panels[-1]
    content_bottom = int(last_panel["y"]) + int(last_panel["height"])
    return max(USE_CASE_BOUNDARY_HEIGHT, content_bottom + 32)


def use_case_ellipse_positions(
    boundary_box: tuple[int, int, int, int],
    use_cases: list[dict[str, Any]],
    primary_use_case_id: str | None,
    relationships: list[dict[str, Any]],
) -> dict[str, tuple[int, int, int, int]]:
    bx, by, bw, bh = boundary_box
    available_top = by + USE_CASE_BOUNDARY_HEADER + 42
    available_height = bh - USE_CASE_BOUNDARY_HEADER - 84
    positions: dict[str, tuple[int, int, int, int]] = {}
    if not use_cases:
        return positions

    use_case_map = {str(item.get("id") or ""): item for item in use_cases}
    dimensions = {
        item_id: use_case_node_dimensions(str(item.get("label") or item_id), "use_case")
        for item_id, item in use_case_map.items()
    }
    main_id = primary_use_case_id if primary_use_case_id in use_case_map else str(use_cases[0].get("id") or "")
    related_ids: list[str] = []
    for relationship in relationships:
        if not isinstance(relationship, dict):
            continue
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        if source == main_id and target in use_case_map and target != main_id:
            related_ids.append(target)
        elif target == main_id and source in use_case_map and source != main_id:
            related_ids.append(source)
    orbit_ids: list[str] = []
    for related_id in related_ids:
        if related_id not in orbit_ids:
            orbit_ids.append(related_id)
    remaining_ids = [
        str(item.get("id") or "")
        for item in use_cases
        if str(item.get("id") or "") not in {main_id, *orbit_ids}
    ]

    main_width, main_height = dimensions[main_id]
    main_x = bx + max(48, min((bw // 2) - (main_width // 2) - 120, bw - main_width - 320))
    main_y = available_top + max(0, (available_height - main_height) // 2)
    positions[main_id] = (main_x, main_y, main_width, main_height)

    orbit_slots = [
        (main_x + 280, main_y - 160),
        (main_x + 360, main_y),
        (main_x + 280, main_y + 160),
        (main_x - 40, main_y - 180),
        (main_x - 40, main_y + 180),
    ]
    for index, use_case_id in enumerate(orbit_ids):
        use_case_width, use_case_height = dimensions[use_case_id]
        slot_x, slot_y = orbit_slots[index] if index < len(orbit_slots) else (
            bx + 60 + ((index % 2) * 320),
            available_top + ((index // 2) * 150),
        )
        clamped_x = max(bx + 30, min(slot_x, bx + bw - use_case_width - 30))
        clamped_y = max(available_top, min(slot_y, by + bh - use_case_height - 30))
        positions[use_case_id] = (clamped_x, clamped_y, use_case_width, use_case_height)

    if remaining_ids:
        start_y = available_top + 24
        widest = max(dimensions[item_id][0] for item_id in remaining_ids)
        tallest = max(dimensions[item_id][1] for item_id in remaining_ids)
        columns, rows = use_case_counting([use_case_map[item_id] for item_id in remaining_ids], widest, 56)
        grid_width = columns * widest + max(0, columns - 1) * 56
        start_x = bx + bw - grid_width - 48
        for index, use_case_id in enumerate(remaining_ids):
            use_case_width, use_case_height = dimensions[use_case_id]
            row = index // columns
            column = index % columns
            x = start_x + column * (widest + 56)
            y = start_y + row * (tallest + 52)
            clamped_x = max(bx + 30, min(x, bx + bw - use_case_width - 30))
            clamped_y = max(available_top, min(y, by + bh - use_case_height - 30))
            positions[use_case_id] = (clamped_x, clamped_y, use_case_width, use_case_height)

    return positions


def use_case_actor_positions(
    actors: list[dict[str, Any]],
    actor_associations: dict[str, list[str]],
    node_positions: dict[str, tuple[int, int, int, int]],
    page_width: int,
) -> dict[str, tuple[int, int, int, int]]:
    positions: dict[str, tuple[int, int, int, int]] = {}
    left_actors = [actor for actor in actors if str(actor.get("placement") or "").strip().lower() == "left"]
    right_actors = [actor for actor in actors if str(actor.get("placement") or "").strip().lower() == "right"]
    top_actors = [actor for actor in actors if str(actor.get("placement") or "").strip().lower() == "top"]
    bottom_actors = [actor for actor in actors if str(actor.get("placement") or "").strip().lower() == "bottom"]
    default_actors = [
        actor for actor in actors
        if str(actor.get("placement") or "").strip().lower() not in {"left", "right", "top", "bottom"}
    ]
    left_actors = left_actors + default_actors

    def place(side_actors: list[dict[str, Any]], side: str) -> None:
        fallback_top = USE_CASE_BOUNDARY_TOP + 100
        desired: list[float] = []
        actor_ids: list[str] = []
        for index, actor in enumerate(side_actors):
            actor_id = str(actor.get("id") or "")
            associated_ids = [
                target_id for target_id in actor_associations.get(actor_id, [])
                if target_id in node_positions
            ]
            if associated_ids:
                center_y = sum(node_positions[target_id][1] + (node_positions[target_id][3] / 2) for target_id in associated_ids) / len(associated_ids)
                desired.append(center_y - (USE_CASE_ACTOR_HEIGHT / 2))
            else:
                desired.append(fallback_top + index * 180)
            actor_ids.append(actor_id)
        min_y = 72
        max_y = USE_CASE_PAGE_HEIGHT - USE_CASE_ACTOR_HEIGHT - 96
        placed_y = distribute_centers(desired, USE_CASE_ACTOR_HEIGHT + 18, min_y, max_y)
        for actor_id, y in zip(actor_ids, placed_y):
            x = USE_CASE_LEFT_ACTOR_X if side == "left" else page_width - USE_CASE_ACTOR_WIDTH - USE_CASE_ACTOR_RIGHT_GAP
            positions[actor_id] = (x, y, USE_CASE_ACTOR_WIDTH, USE_CASE_ACTOR_HEIGHT)

    def place_vertical(vertical_actors: list[dict[str, Any]], side: str) -> None:
        fallback_left = 360
        desired: list[float] = []
        actor_ids: list[str] = []
        for index, actor in enumerate(vertical_actors):
            actor_id = str(actor.get("id") or "")
            associated_ids = [
                target_id for target_id in actor_associations.get(actor_id, [])
                if target_id in node_positions
            ]
            if associated_ids:
                center_x = sum(node_positions[target_id][0] + (node_positions[target_id][2] / 2) for target_id in associated_ids) / len(associated_ids)
                desired.append(center_x - (USE_CASE_ACTOR_WIDTH / 2))
            else:
                desired.append(fallback_left + index * 180)
            actor_ids.append(actor_id)
        min_x = 180
        max_x = page_width - USE_CASE_ACTOR_WIDTH - 180
        placed_x = distribute_centers(desired, USE_CASE_ACTOR_WIDTH + 36, min_x, max_x)
        for actor_id, x in zip(actor_ids, placed_x):
            y = 74 if side == "top" else USE_CASE_BOUNDARY_TOP + USE_CASE_BOUNDARY_HEIGHT + 70
            positions[actor_id] = (x, y, USE_CASE_ACTOR_WIDTH, USE_CASE_ACTOR_HEIGHT)

    place(left_actors, "left")
    place(right_actors, "right")
    place_vertical(top_actors, "top")
    place_vertical(bottom_actors, "bottom")
    return positions


def use_case_note_positions(
    notes: list[dict[str, Any]],
    boundary_boxes: list[tuple[int, int, int, int]],
    page_width: int,
) -> dict[str, tuple[int, int, int, int]]:
    positions: dict[str, tuple[int, int, int, int]] = {}
    base_y = USE_CASE_BOUNDARY_TOP + USE_CASE_BOUNDARY_HEIGHT + 32
    for index, note in enumerate(notes):
        note_id = str(note.get("id") or "")
        note_width, note_height = use_case_node_dimensions(
            str(note.get("label") or note.get("description") or note_id),
            "note",
        )
        if boundary_boxes:
            boundary_x, _, boundary_width, _ = boundary_boxes[min(index, len(boundary_boxes) - 1)]
            x = boundary_x + boundary_width - note_width
        else:
            x = page_width - note_width - 120
        positions[note_id] = (
            min(x, page_width - note_width - 80),
            base_y + index * (note_height + USE_CASE_NOTE_GAP),
            note_width,
            note_height,
        )
    return positions


def use_case_edge_style(kind: str, style: dict[str, str], inferred: bool) -> tuple[str, str]:
    normalized_kind = str(kind or "dependency").strip().lower()
    label = ""
    base = f"edgeStyle=none;html=1;rounded=0;orthogonalLoop=1;jettySize=auto;{style_pairs(style, ('strokeColor', 'fontColor'))}"
    if normalized_kind == "association":
        return "curved=0;endArrow=none;startArrow=none;" + base, label
    if normalized_kind == "include":
        label = "<<include>>"
        dashed = "dashed=1;"
        return "curved=0;endArrow=open;endFill=0;" + dashed + base, label
    if normalized_kind == "extend":
        label = "<<extend>>"
        dashed = "dashed=1;"
        return "curved=0;endArrow=open;endFill=0;" + dashed + base, label
    if normalized_kind == "generalization":
        return "curved=0;endArrow=block;endFill=0;" + base, label
    edge_style = "curved=0;endArrow=open;endFill=0;" + base
    if inferred:
        edge_style += "dashed=1;"
    return edge_style, label


def build_use_case_diagram_xml(view_model: dict[str, Any]) -> str:
    language = infer_language(view_model)
    title = use_case_view_title(view_model, language)
    profile = resolve_style_profile(view_model)
    boundary_top = USE_CASE_HEADER_HEIGHT + 28
    elements = [
        item
        for item in (view_model.get("elements") or [])
        if isinstance(item, dict) and item.get("render") is not False
    ]
    relationships = use_case_relationships(view_model)
    rendered_relationships = [
        relationship
        for relationship in relationships
        if isinstance(relationship, dict) and relationship.get("render") is not False
    ]

    actors = [item for item in elements if normalized_element_type(item.get("type")) == "actor"]
    use_cases = [item for item in elements if normalized_element_type(item.get("type")) == "use_case"]
    notes = [item for item in elements if normalized_element_type(item.get("type")) == "note"]

    boundary_specs = use_case_boundary_specs(view_model, use_cases, title)
    configured_groups = [group for group in (view_model.get("groups") or []) if isinstance(group, dict)]
    boundary_count = len(boundary_specs)
    root_width = USE_CASE_PAGE_WIDTH - (2 * USE_CASE_ROOT_MARGIN)
    boundary_container_width = root_width - (2 * USE_CASE_NESTED_BOUNDARY_SIDE_GAP)
    usable_width = boundary_container_width - ((boundary_count - 1) * USE_CASE_BOUNDARY_GAP)
    boundary_width = max(USE_CASE_BOUNDARY_MIN_WIDTH, usable_width // max(1, boundary_count))
    boundary_span = boundary_count * boundary_width + max(0, boundary_count - 1) * USE_CASE_BOUNDARY_GAP
    boundary_origin_x = max(
        0,
        USE_CASE_NESTED_BOUNDARY_SIDE_GAP + ((boundary_container_width - boundary_span) // 2),
    )
    grouped_mode = len(boundary_specs) == 1 and bool(configured_groups)
    dynamic_boundary_height = USE_CASE_BOUNDARY_HEIGHT
    if grouped_mode:
        dynamic_boundary_height = use_case_panel_boundary_height(boundary_width, view_model, actors, use_cases)
    note_space = max(0, len(notes) * (USE_CASE_NOTE_HEIGHT + USE_CASE_NOTE_GAP))
    page_height = max(
        USE_CASE_PAGE_HEIGHT,
        boundary_top + dynamic_boundary_height + USE_CASE_ROOT_MARGIN + 24 + USE_CASE_NESTED_BOUNDARY_BOTTOM_GAP + note_space,
    )

    root = ET.Element("mxfile", host="app.diagrams.net", version="24.7.17")
    diagram = ET.SubElement(root, "diagram", id="use-case-view", name=title)
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
        pageWidth=str(USE_CASE_PAGE_WIDTH),
        pageHeight=str(page_height),
        math="0",
        shadow="0",
    )
    mx_root = ET.SubElement(model, "root")
    ET.SubElement(mx_root, "mxCell", id="0")
    ET.SubElement(mx_root, "mxCell", id="1", parent="0")

    root_style = effective_subject_style(profile, "group", {"color_role": "neutral"})
    root_group = ET.SubElement(
        mx_root,
        "mxCell",
        id="group-use-case-root",
        value=title,
        style=(
            "swimlane;fontStyle=1;horizontal=1;rounded=1;html=1;"
            f"whiteSpace=wrap;startSize={USE_CASE_HEADER_HEIGHT};{style_pairs(root_style, ('fillColor', 'strokeColor', 'fontColor'))}"
        ),
        vertex="1",
        parent="1",
    )
    ET.SubElement(
        root_group,
        "mxGeometry",
        x=str(USE_CASE_ROOT_MARGIN),
        y=str(USE_CASE_ROOT_MARGIN),
        width=str(USE_CASE_PAGE_WIDTH - (2 * USE_CASE_ROOT_MARGIN)),
        height=str(page_height - (2 * USE_CASE_ROOT_MARGIN)),
        attrib={"as": "geometry"},
    )

    boundary_boxes: dict[str, tuple[int, int, int, int]] = {}
    boundary_members: dict[str, list[dict[str, Any]]] = {spec["id"]: [] for spec in boundary_specs}
    for use_case in use_cases:
        boundary_members.setdefault(use_case_boundary_for(use_case, boundary_specs), []).append(use_case)

    for index, spec in enumerate(boundary_specs):
        boundary_x = boundary_origin_x + index * (boundary_width + USE_CASE_BOUNDARY_GAP)
        boundary_y = boundary_top
        boundary_style = effective_subject_style(profile, "group", spec["subject"])
        boundary_cell = ET.SubElement(
            mx_root,
            "mxCell",
            id=f"boundary-{sanitize_id(spec['id'])}",
            value=str(spec["label"]),
            style=(
                "swimlane;fontStyle=1;horizontal=1;rounded=0;html=1;"
                f"whiteSpace=wrap;startSize={USE_CASE_BOUNDARY_HEADER};{style_pairs(boundary_style, ('fillColor', 'strokeColor', 'fontColor'))}"
            ),
            vertex="1",
            parent="group-use-case-root",
        )
        ET.SubElement(
            boundary_cell,
            "mxGeometry",
            x=str(boundary_x),
            y=str(boundary_y),
            width=str(boundary_width),
            height=str(dynamic_boundary_height),
            attrib={"as": "geometry"},
        )
        boundary_boxes[spec["id"]] = (boundary_x, boundary_y, boundary_width, dynamic_boundary_height)

    primary_actor_id, primary_use_case_id = use_case_primary_ids(view_model)
    node_positions: dict[str, tuple[int, int, int, int]] = {}
    panel_specs: list[dict[str, int | str]] = []
    grouped_actor_ids: set[str] = set()
    for spec in boundary_specs:
        spec_use_cases = boundary_members.get(spec["id"], [])
        if grouped_mode:
            grouped_positions, grouped_panels, actor_ids = use_case_panel_layout(
                boundary_boxes[spec["id"]],
                view_model,
                actors,
                spec_use_cases,
            )
            node_positions.update(grouped_positions)
            panel_specs.extend(grouped_panels)
            grouped_actor_ids.update(actor_ids)
        else:
            node_positions.update(
                use_case_ellipse_positions(
                    boundary_boxes[spec["id"]],
                    spec_use_cases,
                    primary_use_case_id,
                    rendered_relationships,
                )
            )

    actor_associations: dict[str, list[str]] = {}
    for relationship in rendered_relationships:
        if not isinstance(relationship, dict):
            continue
        if str(relationship.get("kind") or "").strip().lower() != "association":
            continue
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        actor_associations.setdefault(source, []).append(target)
        actor_associations.setdefault(target, []).append(source)
    visible_actor_ids = set(actor_associations.keys())
    external_actors = [
        actor
        for actor in actors
        if str(actor.get("id") or "") not in grouped_actor_ids
        and str(actor.get("id") or "") in visible_actor_ids
    ]
    node_positions.update(
        use_case_actor_positions(external_actors, actor_associations, node_positions, USE_CASE_PAGE_WIDTH)
    )
    node_positions.update(
        use_case_note_positions(notes, list(boundary_boxes.values()), USE_CASE_PAGE_WIDTH)
    )

    if grouped_mode:
        boundary_id = boundary_specs[0]["id"]
        for panel in panel_specs:
            panel_subject = {"color_role": "neutral"}
            panel_style = effective_subject_style(profile, "group", panel_subject)
            panel_cell = ET.SubElement(
                mx_root,
                "mxCell",
                id=f"use-case-panel-{sanitize_id(str(panel['id']))}",
                value=str(panel["label"]),
                style=(
                    "swimlane;fontStyle=1;horizontal=1;rounded=0;html=1;"
                    f"whiteSpace=wrap;startSize={USE_CASE_BOUNDARY_HEADER};"
                    f"{style_pairs(panel_style, ('fillColor', 'strokeColor', 'fontColor'))}"
                ),
                vertex="1",
                parent=f"boundary-{sanitize_id(boundary_id)}",
            )
            ET.SubElement(
                panel_cell,
                "mxGeometry",
                x=str(int(panel["x"]) - boundary_boxes[boundary_id][0]),
                y=str(int(panel["y"]) - boundary_boxes[boundary_id][1]),
                width=str(int(panel["width"])),
                height=str(int(panel["height"])),
                attrib={"as": "geometry"},
            )

    routing_obstacles: list[Box] = []
    rendered_element_ids = {str(element.get("id") or "") for element in elements}
    for element in actors + use_cases + notes:
        element_id = str(element.get("id") or "")
        if not element_id or element_id not in rendered_element_ids or element_id not in node_positions:
            continue
        x, y, width, height = node_positions[element_id]
        element_type = normalized_element_type(element.get("type"))
        subject = dict(element)
        if not subject.get("color_role"):
            if element_type == "actor":
                subject["color_role"] = "entry-surface"
            elif element_type == "use_case":
                subject["color_role"] = "agent-core"
            elif element_type == "note":
                subject["color_role"] = "yellow"
        node_style = (
            use_case_priority_style(profile, subject)
            if element_type == "use_case"
            else effective_subject_style(profile, "node", subject)
        )
        parent_id = "group-use-case-root"
        if grouped_mode and element_type in {"actor", "use_case"}:
            group_id = str(element.get("group") or element.get("id") or "").strip()
            if element_type == "actor":
                group_id = str(element.get("id") or "").strip()
            if group_id in {str(panel["id"]) for panel in panel_specs}:
                parent_id = f"use-case-panel-{sanitize_id(group_id)}"
                panel = next(panel for panel in panel_specs if str(panel["id"]) == group_id)
                x = x - int(panel["x"])
                y = y - int(panel["y"])
        elif element_type == "use_case":
            parent_id = f"boundary-{sanitize_id(use_case_boundary_for(element, boundary_specs))}"
            x = x - boundary_boxes[use_case_boundary_for(element, boundary_specs)][0]
            y = y - boundary_boxes[use_case_boundary_for(element, boundary_specs)][1]

        if element_type == "actor":
            style = (
                "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;"
                "outlineConnect=0;whiteSpace=wrap;"
                f"{style_pairs(node_style, ('fillColor', 'strokeColor', 'fontColor'))}"
            )
        elif element_type == "note":
            style = (
                "shape=note;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=8;"
                f"{style_pairs(node_style, ('fillColor', 'strokeColor', 'fontColor'))}"
            )
        else:
            style = (
                "shape=ellipse;whiteSpace=wrap;html=1;"
                f"{style_pairs(node_style, ('fillColor', 'strokeColor', 'fontColor'))}"
            )

        cell = ET.SubElement(
            mx_root,
            "mxCell",
            id=f"element-{sanitize_id(element_id)}",
            value=(
                capped_display_text(str(element.get("label") or element_id), USE_CASE_LABEL_MAX_CHARS, USE_CASE_LABEL_MAX_LINES, max(10, (width - 36) // 10))
                if element_type in {"actor", "use_case"}
                else capped_display_text(
                    str(element.get("label") or element.get("description") or element_id),
                    USE_CASE_NOTE_MAX_CHARS,
                    USE_CASE_NOTE_MAX_LINES,
                    max(16, (width - 32) // 8),
                )
            ),
            style=style,
            vertex="1",
            parent=parent_id,
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            x=str(int(x)),
            y=str(int(y)),
            width=str(int(width)),
            height=str(int(height)),
            attrib={"as": "geometry"},
        )
        routing_obstacles.append(
            Box(
                id=element_id,
                x=node_positions[element_id][0],
                y=node_positions[element_id][1],
                width=node_positions[element_id][2],
                height=node_positions[element_id][3],
                kind="node",
            )
        )

    reserved_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for index, relationship in enumerate(rendered_relationships, start=1):
        if not isinstance(relationship, dict):
            continue
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        if source not in node_positions or target not in node_positions:
            continue
        subject = dict(relationship)
        if not subject.get("color_role"):
            relationship_kind = str(subject.get("kind") or "dependency").strip().lower()
            if relationship_kind == "association":
                subject["color_role"] = "neutral"
            elif relationship_kind in {"include", "extend", "generalization"}:
                subject["color_role"] = "external-system"
        edge_subject_style = effective_subject_style(profile, "edge", subject)
        edge_style, default_label = use_case_edge_style(
            str(relationship.get("kind") or "dependency"),
            edge_subject_style,
            bool(relationship.get("inferred")),
        )
        label = str(relationship.get("label") or "").strip() or default_label
        source_box = Box(id=source, x=node_positions[source][0], y=node_positions[source][1], width=node_positions[source][2], height=node_positions[source][3])
        target_box = Box(id=target, x=node_positions[target][0], y=node_positions[target][1], width=node_positions[target][2], height=node_positions[target][3])
        routed = None
        try:
            routed = route_edge(
                source_box,
                target_box,
                page_width=USE_CASE_PAGE_WIDTH,
                page_height=page_height,
                obstacles=routing_obstacles,
                reserved_segments=reserved_segments,
            )
        except ValueError:
            routed = None
        if routed is not None:
            edge_style += style_for_ports(routed.source_port, routed.target_port)
        edge = ET.SubElement(
            mx_root,
            "mxCell",
            id=f"edge-use-case-{index}-{sanitize_id(source)}-{sanitize_id(target)}",
            value=label,
            style=edge_style,
            edge="1",
            parent="group-use-case-root",
            source=f"element-{sanitize_id(source)}",
            target=f"element-{sanitize_id(target)}",
        )
        geometry = ET.SubElement(edge, "mxGeometry", relative="1", attrib={"as": "geometry"})
        if routed is not None:
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


