from __future__ import annotations

from ..drawio_common import *  # noqa: F401,F403

RUNTIME_ROOT_MARGIN = 24
RUNTIME_HEADER_HEIGHT = 44
RUNTIME_PARTICIPANT_WIDTH = 190
RUNTIME_PARTICIPANT_GAP = 36
RUNTIME_SECTION_GAP = 28
RUNTIME_SECTION_PADDING_X = 36
RUNTIME_SECTION_PADDING_Y = 18
RUNTIME_SECTION_HEADER = 36
RUNTIME_STEP_GAP_Y = 52
RUNTIME_BRANCH_GAP_Y = 36
RUNTIME_ACTIVATION_WIDTH = 16
RUNTIME_ACTIVATION_HEIGHT = 34
RUNTIME_MIN_PAGE_WIDTH = 1800
RUNTIME_MIN_SECTION_HEIGHT = 140
RUNTIME_NESTED_SIDE_GAP = 32
RUNTIME_NESTED_TOP_GAP = 28
RUNTIME_NESTED_BOTTOM_GAP = 32
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
USE_CASE_CATALOG_ROOT_MARGIN = 24
USE_CASE_CATALOG_HEADER_HEIGHT = 44
USE_CASE_CATALOG_SECTION_GAP = 28
USE_CASE_CATALOG_ROW_HEIGHT = 52
USE_CASE_CATALOG_HEADER_ROW_HEIGHT = 58
USE_CASE_CATALOG_MIN_PAGE_WIDTH = 1600
USE_CASE_CATALOG_MIN_PAGE_HEIGHT = 960
CATALOG_ALLOWED_COLUMNS = ["编号", "用例", "主参与者", "入口面", "优先级", "说明"]
CATALOG_FULL_TEXT_COLUMNS = {"入口面", "说明"}
USE_CASE_CATALOG_LINE_HEIGHT = 18
USE_CASE_CATALOG_ROW_PADDING_Y = 16
CATALOG_CELL_MAX_CHARS = {
    "编号": 12,
    "用例": 40,
    "主参与者": 24,
    "入口面": 72,
    "优先级": 6,
    "说明": 120,
}
CATALOG_CELL_MAX_LINES = {
    "编号": 1,
    "用例": 2,
    "主参与者": 2,
    "入口面": 3,
    "优先级": 1,
    "说明": 3,
}
CATALOG_COLUMN_MIN_WIDTHS = {
    "编号": 110,
    "用例": 220,
    "主参与者": 150,
    "入口面": 280,
    "优先级": 110,
    "说明": 360,
}
CATALOG_COLUMN_MAX_WIDTHS = {
    "编号": 140,
    "用例": 340,
    "主参与者": 220,
    "入口面": 520,
    "优先级": 120,
    "说明": 720,
}


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
    current_y = RUNTIME_NESTED_TOP_GAP
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
    root_width = max(
        RUNTIME_MIN_PAGE_WIDTH - (2 * RUNTIME_ROOT_MARGIN),
        max_section_width + (2 * RUNTIME_NESTED_SIDE_GAP),
    )
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
        section_x = max(RUNTIME_NESTED_SIDE_GAP, (root_width - section_width) // 2)
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
            column_y = RUNTIME_SECTION_HEADER + RUNTIME_NESTED_TOP_GAP
            column_height = max(
                80,
                section["height"] - RUNTIME_SECTION_HEADER - RUNTIME_NESTED_TOP_GAP - RUNTIME_NESTED_BOTTOM_GAP,
            )
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
                y=str(column_y),
                width=str(RUNTIME_PARTICIPANT_WIDTH),
                height=str(column_height),
                attrib={"as": "geometry"},
            )
            participant_positions[str(element.get("id") or "")] = (
                column_x,
                section_inner_y + column_y,
                RUNTIME_PARTICIPANT_WIDTH,
                column_height,
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


