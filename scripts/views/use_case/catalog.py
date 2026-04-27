from __future__ import annotations

from ..drawio_common import *  # noqa: F401,F403
from .render import use_case_priority_style

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




def catalog_actor_ids(view_model: dict[str, Any]) -> list[str]:
    ordered: list[str] = []
    for actor in view_model.get("actors") or []:
        if not isinstance(actor, dict):
            continue
        actor_id = str(actor.get("id") or "").strip()
        if actor_id and actor_id not in ordered:
            ordered.append(actor_id)
    for use_case in view_model.get("use_cases") or []:
        if not isinstance(use_case, dict):
            continue
        actor_id = str(use_case.get("primary_actor") or "").strip()
        if actor_id and actor_id not in ordered:
            ordered.append(actor_id)
    return ordered


def catalog_actor_map(view_model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for actor in view_model.get("actors") or []:
        if not isinstance(actor, dict):
            continue
        actor_id = str(actor.get("id") or "").strip()
        if actor_id:
            mapping[actor_id] = actor
    return mapping


def derive_use_case_view_title(catalog_model: dict[str, Any], language: str) -> str:
    explicit = str(catalog_model.get("derived_view_title") or "").strip()
    if explicit:
        return explicit
    title = str(catalog_model.get("title") or "").strip()
    if title:
        replacements = [
            ("用例目录", "用例视图"),
            ("Use Case Catalog", "Use Case View"),
        ]
        for old, new in replacements:
            if old in title:
                return title.replace(old, new)
        return title
    return "用例视图" if language == "zh" else "Use Case View"


def derive_use_case_boundary_label(catalog_model: dict[str, Any], language: str) -> str:
    explicit = str(catalog_model.get("system_name") or catalog_model.get("subject_system") or "").strip()
    if explicit:
        return explicit
    title = str(catalog_model.get("title") or "").strip()
    if title:
        for suffix in (" 用例目录", "用例目录", " Use Case Catalog"):
            if title.endswith(suffix):
                return title[: -len(suffix)].strip() or title
    return "System" if language != "zh" else "系统"


def derive_use_case_view_model_from_catalog(catalog_model: dict[str, Any]) -> dict[str, Any]:
    language = infer_language(catalog_model)
    actor_ids = catalog_actor_ids(catalog_model)
    actor_map = catalog_actor_map(catalog_model)

    groups: list[dict[str, Any]] = []
    elements: list[dict[str, Any]] = []
    for index, actor_id in enumerate(actor_ids, start=1):
        actor = actor_map.get(actor_id, {})
        actor_label = str(actor.get("label") or actor_id).strip() or actor_id
        groups.append(
            {
                "id": actor_id,
                "label": actor_label,
                "layout_hint": {"order": index},
            }
        )
        elements.append(
            {
                "id": actor_id,
                "label": actor_label,
                "type": "actor",
                "group": actor_id,
            }
        )

    for use_case in catalog_model.get("use_cases") or []:
        if not isinstance(use_case, dict):
            continue
        use_case_id = str(use_case.get("id") or "").strip()
        if not use_case_id:
            continue
        group_id = str(use_case.get("primary_actor") or "").strip()
        if not group_id:
            group_id = actor_ids[0] if actor_ids else "default-actor"
        label = str(use_case.get("label") or use_case.get("code") or use_case_id).strip() or use_case_id
        element: dict[str, Any] = {
            "id": use_case_id,
            "label": label,
            "type": "use_case",
            "group": group_id,
            "boundary": "system-boundary",
        }
        priority = str(use_case.get("priority") or "").strip()
        if priority:
            element["priority"] = priority
        summary = str(use_case.get("summary") or "").strip()
        if summary:
            element["summary"] = summary
        elements.append(element)

    derived: dict[str, Any] = {
        "view": "use-case",
        "title": derive_use_case_view_title(catalog_model, language),
        "description": str(catalog_model.get("description") or "").strip(),
        "scope": catalog_model.get("scope"),
        "style_profile": catalog_model.get("style_profile") or "ref-default",
        "layout_suggestion": {
            "strategy": "use-case-diagram",
            "orientation": "left-to-right",
        },
        "system_boundary": {
            "id": "system-boundary",
            "label": derive_use_case_boundary_label(catalog_model, language),
        },
        "groups": groups,
        "elements": elements,
        "relationships": [],
        "omissions": list(catalog_model.get("omissions") or []),
        "uncertainties": list(catalog_model.get("uncertainties") or []),
    }
    return derived


def split_use_case_catalog_view_models(catalog_model: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [
        ("use-case-catalog-view.drawio", catalog_model),
        ("use-case-view.drawio", derive_use_case_view_model_from_catalog(catalog_model)),
    ]


def use_case_catalog_title(view_model: dict[str, Any], language: str) -> str:
    default_title = "\u7528\u4f8b\u76ee\u5f55" if language == "zh" else "Use Case Catalog"
    return str(view_model.get("title") or default_title)


def catalog_columns(view_model: dict[str, Any]) -> list[str]:
    raw = view_model.get("catalog_columns")
    if raw is None:
        return list(CATALOG_ALLOWED_COLUMNS)
    if not isinstance(raw, list):
        raise ValueError("use-case-catalog.catalog_columns must be a list of fixed business columns.")
    columns = [str(item).strip() for item in raw if isinstance(item, str) and str(item).strip()]
    if columns != CATALOG_ALLOWED_COLUMNS:
        raise ValueError(
            "use-case-catalog.catalog_columns must be exactly: 编号, 用例, 主参与者, 入口面, 优先级, 说明"
        )
    return list(CATALOG_ALLOWED_COLUMNS)


def catalog_column_width(column: str, cell_values: list[str]) -> int:
    minimum = CATALOG_COLUMN_MIN_WIDTHS.get(column, 180)
    maximum = CATALOG_COLUMN_MAX_WIDTHS.get(column, minimum)
    widest_units = weighted_text_units(column)
    for value in cell_values:
        widest_units = max(
            widest_units,
            max((weighted_text_units(line) for line in str(value or "").splitlines()), default=0),
        )
    estimated = 40 + widest_units * 9
    return clamp(estimated, minimum, maximum)


def catalog_display_text(column: str, raw_value: str, max_units_per_line: int) -> str:
    normalized = column.strip()
    if normalized in CATALOG_FULL_TEXT_COLUMNS:
        return wrap_text(raw_value, max_units_per_line)
    max_chars = CATALOG_CELL_MAX_CHARS.get(normalized, 80)
    max_lines = CATALOG_CELL_MAX_LINES.get(normalized, 3)
    return capped_display_text(raw_value, max_chars, max_lines, max_units_per_line)


def catalog_row_height(row_display_values: dict[str, str]) -> int:
    max_line_count = 1
    for value in row_display_values.values():
        line_count = max(1, len(str(value or "").splitlines()))
        max_line_count = max(max_line_count, line_count)
    dynamic_height = (max_line_count * USE_CASE_CATALOG_LINE_HEIGHT) + USE_CASE_CATALOG_ROW_PADDING_Y
    return max(USE_CASE_CATALOG_ROW_HEIGHT, dynamic_height)


def use_case_catalog_sections(view_model: dict[str, Any]) -> list[dict[str, Any]]:
    language = infer_language(view_model)
    use_cases = [item for item in (view_model.get("use_cases") or []) if isinstance(item, dict)]
    if not use_cases:
        return []

    grouped: dict[str, list[dict[str, Any]]] = {}
    ungrouped: list[dict[str, Any]] = []
    for use_case in use_cases:
        section = str(use_case.get("section") or "").strip()
        if section:
            grouped.setdefault(section, []).append(use_case)
        else:
            ungrouped.append(use_case)

    sections: list[dict[str, Any]] = []
    p0 = [item for item in ungrouped if str(item.get("priority") or "").strip().upper() == "P0"]
    if p0:
        sections.append({"label": None, "rows": p0})

    remaining = [item for item in ungrouped if item not in p0]
    buckets: dict[str, list[dict[str, Any]]] = {}
    for item in remaining:
        priority = str(item.get("priority") or "Other").strip().upper() or "Other"
        buckets.setdefault(priority, []).append(item)
    for priority in sorted(buckets):
        label = f"{priority} 用例" if language == "zh" else f"{priority} Use Cases"
        sections.append({"label": label, "rows": buckets[priority]})

    for section_label in sorted(grouped):
        sections.append({"label": section_label, "rows": grouped[section_label]})
    return sections


def catalog_use_case_label(use_case: dict[str, Any]) -> str:
    code = str(use_case.get("code") or "").strip()
    label = str(use_case.get("label") or use_case.get("id") or "").strip()
    return f"{code} {label}".strip() or label or code


def catalog_actor_labels(view_model: dict[str, Any]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for actor in view_model.get("actors") or []:
        if not isinstance(actor, dict):
            continue
        actor_id = str(actor.get("id") or "").strip()
        actor_label = str(actor.get("label") or "").strip()
        if actor_id and actor_label:
            labels[actor_id] = actor_label
    return labels


def catalog_cell_value(column: str, use_case: dict[str, Any], actor_labels: dict[str, str]) -> str:
    normalized = column.strip()
    if normalized == "编号":
        return str(use_case.get("code") or "")
    if normalized == "用例":
        return catalog_use_case_label(use_case)
    if normalized == "主参与者":
        actor_id = str(use_case.get("primary_actor") or "").strip()
        return actor_labels.get(actor_id, actor_id)
    if normalized == "入口面":
        entry_surfaces = use_case.get("entry_surfaces")
        if isinstance(entry_surfaces, list):
            return "\n".join(str(item).strip() for item in entry_surfaces if str(item).strip())
        return ""
    if normalized == "优先级":
        return str(use_case.get("priority") or "")
    if normalized == "说明":
        return str(use_case.get("summary") or use_case.get("description") or "")
    raise ValueError(f"Unsupported use-case catalog column: {column}")


def build_use_case_catalog_diagram_xml(view_model: dict[str, Any]) -> str:
    language = infer_language(view_model)
    title = use_case_catalog_title(view_model, language)
    profile = resolve_style_profile(view_model)
    columns = catalog_columns(view_model)
    sections = use_case_catalog_sections(view_model)
    if not sections:
        raise ValueError("Use-case catalog view requires a non-empty top-level use_cases array.")
    actor_labels = catalog_actor_labels(view_model)

    column_display_values: dict[str, list[str]] = {column: [] for column in columns}
    for section in sections:
        for use_case in section.get("rows") or []:
            for column in columns:
                raw_value = catalog_cell_value(column, use_case, actor_labels)
                column_display_values[column].append(raw_value)

    column_widths = {
        column: catalog_column_width(column, column_display_values.get(column, []))
        for column in columns
    }
    table_width = sum(column_widths[column] for column in columns)
    page_width = max(USE_CASE_CATALOG_MIN_PAGE_WIDTH, table_width + (2 * USE_CASE_CATALOG_ROOT_MARGIN) + 80)

    section_row_layouts: list[dict[str, Any]] = []
    for section in sections:
        row_layouts: list[dict[str, Any]] = []
        for use_case in section.get("rows") or []:
            row_display_values: dict[str, str] = {}
            for column in columns:
                width = column_widths[column]
                max_units_per_line = max(10, (width - 32) // 9)
                row_display_values[column] = catalog_display_text(
                    column,
                    catalog_cell_value(column, use_case, actor_labels),
                    max_units_per_line,
                )
            row_layouts.append({
                "use_case": use_case,
                "display_values": row_display_values,
                "height": catalog_row_height(row_display_values),
            })
        section_row_layouts.append({
            "label": section.get("label"),
            "rows": row_layouts,
        })

    content_height = USE_CASE_CATALOG_HEADER_HEIGHT + 32
    for section in section_row_layouts:
        if section.get("label"):
            content_height += 38
        content_height += USE_CASE_CATALOG_HEADER_ROW_HEIGHT
        content_height += sum(int(row.get("height") or USE_CASE_CATALOG_ROW_HEIGHT) for row in (section.get("rows") or []))
        content_height += USE_CASE_CATALOG_SECTION_GAP
    page_height = max(USE_CASE_CATALOG_MIN_PAGE_HEIGHT, content_height + (2 * USE_CASE_CATALOG_ROOT_MARGIN))

    root = ET.Element("mxfile", host="app.diagrams.net", version="24.7.17")
    diagram = ET.SubElement(root, "diagram", id="use-case-catalog-view", name=title)
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

    root_style = effective_subject_style(profile, "group", {"color_role": "neutral"})
    root_group = ET.SubElement(
        mx_root,
        "mxCell",
        id="group-use-case-catalog-root",
        value=title,
        style=(
            "swimlane;fontStyle=1;horizontal=1;rounded=1;html=1;"
            f"whiteSpace=wrap;startSize={USE_CASE_CATALOG_HEADER_HEIGHT};{style_pairs(root_style, ('fillColor', 'strokeColor', 'fontColor'))}"
        ),
        vertex="1",
        parent="1",
    )
    ET.SubElement(
        root_group,
        "mxGeometry",
        x=str(USE_CASE_CATALOG_ROOT_MARGIN),
        y=str(USE_CASE_CATALOG_ROOT_MARGIN),
        width=str(page_width - (2 * USE_CASE_CATALOG_ROOT_MARGIN)),
        height=str(page_height - (2 * USE_CASE_CATALOG_ROOT_MARGIN)),
        attrib={"as": "geometry"},
    )

    current_y = 30
    left_x = 28
    table_style = effective_subject_style(profile, "group", {"color_role": "neutral"})
    header_subject = {"color_role": "entry-surface"}
    header_style = effective_subject_style(profile, "node", header_subject)
    body_style = effective_subject_style(profile, "node", {"color_role": "neutral"})
    for section_index, section in enumerate(section_row_layouts, start=1):
        section_label = str(section.get("label") or "").strip()
        if section_label:
            label_cell = ET.SubElement(
                mx_root,
                "mxCell",
                id=f"use-case-catalog-section-label-{section_index}",
                value=section_label,
                style=(
                    "text;html=1;whiteSpace=wrap;rounded=0;strokeColor=none;fillColor=none;"
                    "fontStyle=1;fontSize=12;align=center;verticalAlign=middle;fontColor=#111827;"
                ),
                vertex="1",
                parent="group-use-case-catalog-root",
            )
            ET.SubElement(
                label_cell,
                "mxGeometry",
                x=str(left_x),
                y=str(current_y),
                width=str(table_width),
                height="28",
                attrib={"as": "geometry"},
            )
            current_y += 34

        x = left_x
        for column in columns:
            width = column_widths[column]
            cell = ET.SubElement(
                mx_root,
                "mxCell",
                id=f"use-case-catalog-header-{section_index}-{sanitize_id(column)}",
                value=column,
                style=(
                    "rounded=0;whiteSpace=wrap;html=1;fontStyle=1;align=center;verticalAlign=middle;"
                    f"{style_pairs(header_style, ('fillColor', 'strokeColor', 'fontColor'))}"
                ),
                vertex="1",
                parent="group-use-case-catalog-root",
            )
            ET.SubElement(
                cell,
                "mxGeometry",
                x=str(x),
                y=str(current_y),
                width=str(width),
                height=str(USE_CASE_CATALOG_HEADER_ROW_HEIGHT),
                attrib={"as": "geometry"},
            )
            x += width
        current_y += USE_CASE_CATALOG_HEADER_ROW_HEIGHT

        for row_index, row_layout in enumerate(section.get("rows") or [], start=1):
            use_case = row_layout["use_case"]
            row_height = int(row_layout.get("height") or USE_CASE_CATALOG_ROW_HEIGHT)
            display_values = row_layout.get("display_values") or {}
            x = left_x
            for column in columns:
                width = column_widths[column]
                value = str(display_values.get(column) or "")
                normalized = column.strip()
                subject_style = (
                    use_case_priority_style(profile, use_case)
                    if normalized == "优先级"
                    else body_style
                )
                align = "left" if normalized in {"用例", "入口面", "说明"} else "center"
                font_style = "fontStyle=1;" if normalized == "优先级" else ""
                vertical_align = "top" if normalized in CATALOG_FULL_TEXT_COLUMNS else "middle"
                cell = ET.SubElement(
                    mx_root,
                    "mxCell",
                    id=f"use-case-catalog-row-{section_index}-{row_index}-{sanitize_id(column)}",
                    value=value,
                    style=(
                        "rounded=0;whiteSpace=wrap;html=1;"
                        f"{font_style}align={align};verticalAlign={vertical_align};spacingLeft=8;spacingTop=6;"
                        f"{style_pairs(subject_style, ('fillColor', 'strokeColor', 'fontColor'))}"
                    ),
                    vertex="1",
                    parent="group-use-case-catalog-root",
                )
                ET.SubElement(
                    cell,
                    "mxGeometry",
                    x=str(x),
                    y=str(current_y),
                    width=str(width),
                    height=str(row_height),
                    attrib={"as": "geometry"},
                )
                x += width
            current_y += row_height
        current_y += USE_CASE_CATALOG_SECTION_GAP

    return ET.tostring(root, encoding="unicode")


