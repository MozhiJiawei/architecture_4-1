from __future__ import annotations

from ..drawio_common import *  # noqa: F401,F403
from .layout import *  # noqa: F401,F403

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


