from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

try:
    from drawio_core.orthogonal_router import Box, route_edge, style_for_ports
    from drawio_core.style_profiles import effective_subject_style, resolve_style_profile
except ModuleNotFoundError:
    from scripts.drawio_core.orthogonal_router import Box, route_edge, style_for_ports
    from scripts.drawio_core.style_profiles import effective_subject_style, resolve_style_profile


CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")
TYPE_LABELS_ZH = {
    "service": "\u670d\u52a1",
    "interface": "\u754c\u9762",
    "external": "\u5916\u90e8\u7cfb\u7edf",
    "orchestrator": "\u7f16\u6392\u6838\u5fc3",
    "subsystem": "\u5b50\u7cfb\u7edf",
    "component": "\u7ec4\u4ef6",
    "actor": "\u89d2\u8272",
    "use_case": "\u7528\u4f8b",
    "system_boundary": "\u7cfb\u7edf\u8fb9\u754c",
    "database": "\u6570\u636e\u5e93",
    "queue": "\u961f\u5217",
    "cache": "\u7f13\u5b58",
    "broker": "\u6d88\u606f\u4e2d\u95f4\u4ef6",
    "scheduler": "\u8c03\u5ea6\u5668",
    "worker": "\u5de5\u4f5c\u8005",
    "job": "\u4efb\u52a1",
    "note": "\u8bf4\u660e",
}
TYPE_LABELS_EN = {
    "service": "Service",
    "interface": "Interface",
    "external": "External System",
    "orchestrator": "Orchestrator",
    "subsystem": "Subsystem",
    "component": "Component",
    "actor": "Actor",
    "use_case": "Use Case",
    "system_boundary": "System Boundary",
    "database": "Database",
    "queue": "Queue",
    "cache": "Cache",
    "broker": "Broker",
    "scheduler": "Scheduler",
    "worker": "Worker",
    "job": "Job",
    "note": "Note",
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


def weighted_text_units(value: str) -> int:
    total = 0
    for char in str(value or ""):
        total += 2 if contains_cjk(char) else 1
    return total


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def truncate_text(value: str, max_chars: int) -> str:
    text = str(value or "").strip()
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    if max_chars == 1:
        return text[:1]
    return text[: max_chars - 1].rstrip() + "…"


def wrap_text(value: str, max_units_per_line: int) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if max_units_per_line <= 0:
        return text

    wrapped_lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        current_units = 0
        for char in paragraph:
            char_units = 2 if contains_cjk(char) else 1
            if current and current_units + char_units > max_units_per_line:
                wrapped_lines.append(current.rstrip())
                current = char
                current_units = char_units
            else:
                current += char
                current_units += char_units
        wrapped_lines.append(current.rstrip())
    return "\n".join(line for line in wrapped_lines if line) or ""


def capped_display_text(value: str, max_chars: int, max_lines: int, max_units_per_line: int) -> str:
    truncated = truncate_text(value, max_chars)
    wrapped = wrap_text(truncated, max_units_per_line)
    lines = wrapped.splitlines() if wrapped else []
    if len(lines) <= max_lines:
        return wrapped
    kept = lines[:max_lines]
    last = kept[-1].rstrip()
    if not last.endswith("…"):
        last = truncate_text(last, max(1, len(last) - 1)) if len(last) > 1 else last
        if not last.endswith("…"):
            last = last.rstrip("…").rstrip() + "…"
    kept[-1] = last
    return "\n".join(kept)


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
    if view == "development":
        return f"{source_path.stem}.drawio"
    suffix = "-view" if not view.endswith("-view") else ""
    return f"{view}{suffix}.drawio"


def ordered_group_ids(groups: list[dict[str, Any]]) -> list[str]:
    ordered = sorted(
        [group for group in groups if isinstance(group, dict) and group.get("id")],
        key=lambda group: (
            int((group.get("layout_hint") or {}).get("order", 999))
            if isinstance(group.get("layout_hint"), dict)
            else 999,
            str(group.get("id")),
        ),
    )
    return [str(group["id"]) for group in ordered]


