from __future__ import annotations

from html import escape
from xml.etree import ElementTree as ET

try:
    from views.development.model import geometry_digest, load_development_view_model
    from drawio_core.style_profiles import effective_subject_style, resolve_style_profile
except ModuleNotFoundError:
    from scripts.views.development.model import geometry_digest, load_development_view_model
    from scripts.drawio_core.style_profiles import effective_subject_style, resolve_style_profile


ROOT_MARGIN = 16
LEGEND_DEFAULT_WIDTH = 240
LEGEND_DEFAULT_HEIGHT = 132
RELATIONSHIP_LEGEND_DEFAULT_WIDTH = 360
RELATIONSHIP_LEGEND_DEFAULT_HEIGHT = 420
SECTION_STROKE = "#6b7280"


def style_pairs(style: dict[str, str], keys: tuple[str, ...]) -> str:
    return "".join(
        f"{key}={style[key]};"
        for key in keys
        if key in style
    )


def sanitize_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value)
    return cleaned or "item"


def html_multiline(value: str) -> str:
    lines = [soft_wrap_text(line.strip()) for line in str(value or "").splitlines() if line.strip()]
    return "<br/>".join(lines) if lines else "&nbsp;"


def html_list(items: list[str], prefix: str = "") -> str:
    lines = [soft_wrap_text(f"{prefix}{item.strip()}") for item in items if item.strip()]
    return "<br/>".join(lines) if lines else "&nbsp;"


def soft_wrap_text(value: str) -> str:
    escaped = escape(str(value or ""))
    # Draw.io HTML labels do not reliably wrap long code-ish tokens such as
    # MODEL_EXPRESS_CACHE_PATH. Add explicit soft-break opportunities at common
    # code separators so table labels stay inside their cards.
    return "".join(f"{char}&#8203;" if char in "_/.-:" else char for char in escaped)


def lighten_hex(color: str, ratio: float) -> str:
    value = str(color or "").strip()
    if len(value) != 7 or not value.startswith("#"):
        return "#ffffff"
    try:
        red = int(value[1:3], 16)
        green = int(value[3:5], 16)
        blue = int(value[5:7], 16)
    except ValueError:
        return "#ffffff"
    ratio = max(0.0, min(1.0, ratio))
    blend = lambda channel: int(channel + ((255 - channel) * ratio))
    return f"#{blend(red):02x}{blend(green):02x}{blend(blue):02x}"


def node_value(element: dict[str, object], node_style: dict[str, str]) -> str:
    stroke = SECTION_STROKE
    card_fill = node_style.get("fillColor", "#f8f9fa")
    title_fill = lighten_hex(card_fill, 0.15)
    section_fill = lighten_hex(card_fill, 0.55)
    title_color = node_style.get("fontColor", "#111827")
    label = escape(str(element.get("label") or "").strip() or "Unnamed")
    responsibility = html_multiline(str(element.get("responsibility") or "").strip())
    exposes = html_list(
        [str(item).strip() for item in (element.get("exposes") or []) if str(item).strip()],
        prefix="+ ",
    )
    return (
        "<table style='width:100%;height:100%;border-collapse:collapse;table-layout:fixed;'>"
        f"<tr><td style='background:{title_fill};color:{title_color};"
        "font-size:13px;font-weight:700;"
        "text-align:center;padding:8px 10px;overflow-wrap:anywhere;word-break:break-word;'>"
        f"{label}</td></tr>"
        f"<tr><td style='background:{section_fill};padding:8px 10px;"
        "font-size:11px;line-height:1.35;text-align:left;vertical-align:top;overflow-wrap:anywhere;word-break:break-word;'>"
        "<div style='font-weight:700;margin-bottom:4px;'>简述</div>"
        f"<div style='overflow-wrap:anywhere;word-break:break-word;'>{responsibility}</div></td></tr>"
        f"<tr><td style='background:{section_fill};border-top:1px solid {stroke};padding:8px 10px;font-size:11px;line-height:1.35;"
        "text-align:left;vertical-align:top;overflow-wrap:anywhere;word-break:break-word;'>"
        "<div style='font-weight:700;margin-bottom:4px;'>接口</div>"
        f"<div style='overflow-wrap:anywhere;word-break:break-word;'>{exposes}</div></td></tr>"
        "</table>"
    )


def legend_value(model: dict[str, object], profile: dict[str, object]) -> str:
    legend = model.get("legend")
    if not isinstance(legend, dict):
        return "Legend"
    title = escape(str(legend.get("title") or "Legend").strip() or "Legend")
    rows = [f"<tr><td colspan='2' style='font-weight:700;padding:2px 0 8px 0;'>{title}</td></tr>"]
    for item in legend.get("items") or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        role = str(item.get("color_role") or "").strip()
        if label and role:
            style = effective_subject_style(profile, "node", {"color_role": role})
            fill = style.get("fillColor", "#ffffff")
            stroke = style.get("strokeColor", "#6b7280")
            rows.append(
                "<tr>"
                f"<td style='width:30px;padding:5px 8px 5px 0;'><span style='display:inline-block;width:20px;height:14px;background:{fill};border:1px solid {stroke};'></span></td>"
                f"<td style='padding:4px 0;'>{escape(label)}</td>"
                "</tr>"
            )
    return "<table style='width:100%;border-collapse:collapse;font-size:12px;line-height:1.3;'>" + "".join(rows) + "</table>"


def relationship_legend_value(model: dict[str, object]) -> str:
    legend = model.get("relationship_legend")
    title = "关系说明"
    items: list[dict[str, object]] = []
    if isinstance(legend, dict):
        title = str(legend.get("title") or title).strip() or title
        raw_items = legend.get("items")
        if isinstance(raw_items, list):
            items = [item for item in raw_items if isinstance(item, dict)]
    if not items:
        for relationship in model.get("relationships") or []:
            if not isinstance(relationship, dict):
                continue
            code = relationship_display_label(relationship)
            label = str(relationship.get("label") or "").strip()
            source = str(relationship.get("source") or "").strip()
            target = str(relationship.get("target") or "").strip()
            if code and label:
                items.append({"code": code, "label": f"{source} -> {target}: {label}".strip(": ")})
    rows = [f"<tr><td colspan='2' style='font-weight:700;padding:2px 0 8px 0;'>{escape(title)}</td></tr>"]
    for item in items:
        code = str(item.get("summary_label") or item.get("code") or "").strip()
        label = str(item.get("label") or "").strip()
        if code and label:
            rows.append(
                "<tr>"
                f"<td style='width:36px;font-weight:700;vertical-align:top;padding:3px 8px 3px 0;'>{escape(code)}</td>"
                f"<td style='vertical-align:top;padding:3px 0;'>{escape(label)}</td>"
                "</tr>"
            )
    return "<table style='width:100%;border-collapse:collapse;font-size:12px;line-height:1.25;'>" + "".join(rows) + "</table>"


def relationship_display_label(relationship: dict[str, object]) -> str:
    return str(
        relationship.get("summary_label")
        or relationship.get("line_label")
        or relationship.get("code")
        or relationship.get("label")
        or ""
    ).strip()


def build_development_diagram_xml(view_model: dict[str, object]) -> str:
    model = load_development_view_model(view_model)
    canvas = model.get("canvas") or {}
    page_width = int(float(canvas.get("width") or 1600) + (ROOT_MARGIN * 2))
    page_height = int(float(canvas.get("height") or 1000) + (ROOT_MARGIN * 2))
    title = str(model.get("title") or "Development View")
    digest = geometry_digest(model)
    profile = resolve_style_profile(model)

    root = ET.Element("mxfile", host="app.diagrams.net", version="24.7.17")
    diagram = ET.SubElement(root, "diagram", id="development-view", name=title)
    graph_model = ET.SubElement(
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
    xml_root = ET.SubElement(graph_model, "root")
    ET.SubElement(xml_root, "mxCell", id="0")
    ET.SubElement(xml_root, "mxCell", id="1", parent="0")

    root_style = effective_subject_style(profile, "group", {"color_role": "neutral"})
    root_group = ET.SubElement(
        xml_root,
        "mxCell",
        id="group-development-root",
        value=title,
        style=(
            "swimlane;fontStyle=1;horizontal=1;rounded=1;html=1;whiteSpace=wrap;"
            "startSize=44;"
            f"{style_pairs(root_style, ('fillColor', 'strokeColor', 'fontColor'))}"
        ),
        vertex="1",
        parent="1",
    )
    ET.SubElement(
        root_group,
        "mxGeometry",
        x=str(ROOT_MARGIN),
        y=str(ROOT_MARGIN),
        width=str(int(float(canvas.get("width") or 1600))),
        height=str(int(float(canvas.get("height") or 1000))),
        attrib={"as": "geometry"},
    )

    groups_by_id = {
        str(group.get("id") or ""): group
        for group in (model.get("groups") or [])
        if isinstance(group, dict)
    }
    for element in model.get("elements") or []:
        if not isinstance(element, dict):
            continue
        element_id = str(element.get("id") or "")
        frame = element.get("frame")
        if not element_id or not isinstance(frame, dict):
            continue
        group = groups_by_id.get(str(element.get("group") or ""), {})
        subject = {
            "color_role": element.get("color_role") or group.get("color_role") or "neutral",
            "style": element.get("style"),
        }
        node_style = effective_subject_style(profile, "node", subject)
        cell = ET.SubElement(
            xml_root,
            "mxCell",
            id=element_id,
            value=node_value(element, node_style),
            style=(
                "rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;"
                "spacing=0;fontSize=12;overflow=fill;"
                f"{style_pairs(node_style, ('fillColor', 'strokeColor', 'fontColor'))}"
            ),
            vertex="1",
            parent="group-development-root",
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            x=str(int(float(frame["x"]))),
            y=str(int(float(frame["y"]))),
            width=str(int(float(frame["width"]))),
            height=str(int(float(frame["height"]))),
            attrib={"as": "geometry"},
        )

    for relationship in model.get("relationships") or []:
        if not isinstance(relationship, dict):
            continue
        relationship_id = str(relationship.get("id") or "")
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        segments = relationship.get("segments")
        if not relationship_id or not source or not target or not isinstance(segments, list) or not segments:
            continue
        source_port = str(relationship.get("source_port") or "right")
        target_port = str(relationship.get("target_port") or "left")
        source_anchor = {
            "left": ("0", "0.500"),
            "right": ("1", "0.500"),
            "top": ("0.500", "0"),
            "bottom": ("0.500", "1"),
        }
        target_anchor = source_anchor
        exit_x, exit_y = source_anchor.get(source_port, ("0.500", "0.500"))
        entry_x, entry_y = target_anchor.get(target_port, ("0.500", "0.500"))
        edge_style = effective_subject_style(profile, "edge", {"color_role": relationship.get("color_role"), "style": relationship.get("style")})
        edge = ET.SubElement(
            xml_root,
            "mxCell",
            id=relationship_id,
            value="",
            style=(
                "edgeStyle=none;rounded=0;html=1;endArrow=block;endFill=1;strokeWidth=2;"
                f"exitX={exit_x};exitY={exit_y};exitDx=0;exitDy=0;"
                f"entryX={entry_x};entryY={entry_y};entryDx=0;entryDy=0;"
                f"{style_pairs(edge_style, ('strokeColor', 'fontColor'))}"
            ),
            edge="1",
            parent="group-development-root",
            source=source,
            target=target,
        )
        edge_geometry = ET.SubElement(edge, "mxGeometry", relative="1", attrib={"as": "geometry"})
        if len(segments) > 1:
            array = ET.SubElement(edge_geometry, "Array", attrib={"as": "points"})
            for raw_segment in segments[:-1]:
                end = raw_segment.get("end")
                if isinstance(end, dict):
                    ET.SubElement(array, "mxPoint", x=str(end.get("x")), y=str(end.get("y")))

        label_box = relationship.get("label_box")
        label = relationship_display_label(relationship)
        if label:
            label_geometry = {"x": 0, "y": 0, "width": 32, "height": 18}
            if isinstance(label_box, dict):
                label_geometry["width"] = int(float(label_box.get("width") or 32))
                label_geometry["height"] = int(float(label_box.get("height") or 18))
            label_cell = ET.SubElement(
                xml_root,
                "mxCell",
                id=f"edge-label-{sanitize_id(relationship_id)}",
                value=label.replace("\n", "&#10;"),
                style=(
                    "text;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;"
                    "fontSize=12;fontStyle=1;fillColor=none;strokeColor=none;"
                    f"{style_pairs(edge_style, ('fontColor',))}"
                ),
                vertex="1",
                connectable="0",
                parent=relationship_id,
            )
            ET.SubElement(
                label_cell,
                "mxGeometry",
                x="0",
                y="0",
                width=str(label_geometry["width"]),
                height=str(label_geometry["height"]),
                relative="1",
                attrib={"as": "geometry"},
            )

    legend = model.get("legend")
    legend_frame = legend.get("frame") if isinstance(legend, dict) else None
    if not isinstance(legend_frame, dict):
        legend_frame = {
            "x": float(canvas.get("width") or 1600) - LEGEND_DEFAULT_WIDTH - 24,
            "y": 28,
            "width": LEGEND_DEFAULT_WIDTH,
            "height": LEGEND_DEFAULT_HEIGHT,
        }
    legend_style = effective_subject_style(profile, "group", {"color_role": "neutral"})
    legend_cell = ET.SubElement(
        xml_root,
        "mxCell",
        id="development-legend",
        value=legend_value(model, profile),
        style=(
            "rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=10;fontSize=12;"
            f"{style_pairs(legend_style, ('fillColor', 'strokeColor', 'fontColor'))}"
        ),
        vertex="1",
        parent="group-development-root",
    )
    ET.SubElement(
        legend_cell,
        "mxGeometry",
        x=str(int(float(legend_frame["x"]))),
        y=str(int(float(legend_frame["y"]))),
        width=str(int(float(legend_frame["width"]))),
        height=str(int(float(legend_frame["height"]))),
        attrib={"as": "geometry"},
    )

    relationship_legend = model.get("relationship_legend")
    relationship_legend_frame = relationship_legend.get("frame") if isinstance(relationship_legend, dict) else None
    if isinstance(relationship_legend, dict):
        if not isinstance(relationship_legend_frame, dict):
            relationship_legend_frame = {
                "x": float(canvas.get("width") or 1600) - RELATIONSHIP_LEGEND_DEFAULT_WIDTH - 24,
                "y": float(legend_frame["y"]) + float(legend_frame["height"]) + 16,
                "width": RELATIONSHIP_LEGEND_DEFAULT_WIDTH,
                "height": RELATIONSHIP_LEGEND_DEFAULT_HEIGHT,
            }
        relationship_cell = ET.SubElement(
            xml_root,
            "mxCell",
            id="development-relationship-legend",
            value=relationship_legend_value(model),
            style=(
                "rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=10;fontSize=12;"
                f"{style_pairs(legend_style, ('fillColor', 'strokeColor', 'fontColor'))}"
            ),
            vertex="1",
            parent="group-development-root",
        )
        ET.SubElement(
            relationship_cell,
            "mxGeometry",
            x=str(int(float(relationship_legend_frame["x"]))),
            y=str(int(float(relationship_legend_frame["y"]))),
            width=str(int(float(relationship_legend_frame["width"]))),
            height=str(int(float(relationship_legend_frame["height"]))),
            attrib={"as": "geometry"},
        )

    hidden_hash = ET.SubElement(
        xml_root,
        "mxCell",
        id="development-geometry-hash",
        value=f"geometry_hash={digest}",
        style="text;html=1;strokeColor=none;fillColor=none;fontSize=12;",
        vertex="1",
        parent="group-development-root",
        visible="0",
    )
    ET.SubElement(
        hidden_hash,
        "mxGeometry",
        x="4",
        y="4",
        width="10",
        height="10",
        attrib={"as": "geometry"},
    )

    return ET.tostring(root, encoding="unicode")
