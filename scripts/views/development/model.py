from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    from drawio_core.orthogonal_router import Box
except ModuleNotFoundError:
    from scripts.drawio_core.orthogonal_router import Box


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Segment:
    start: Point
    end: Point


@dataclass(frozen=True)
class LabelBox:
    id: str
    x: float
    y: float
    width: float
    height: float
    relationship_id: str


@dataclass(frozen=True)
class ValidationMessage:
    rule_id: str
    message: str
    object_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class ValidationReport:
    errors: list[ValidationMessage] = field(default_factory=list)
    warnings: list[ValidationMessage] = field(default_factory=list)

    def add_error(self, rule_id: str, message: str, *object_ids: str) -> None:
        self.errors.append(ValidationMessage(rule_id=rule_id, message=message, object_ids=tuple(object_ids)))

    def add_warning(self, rule_id: str, message: str, *object_ids: str) -> None:
        self.warnings.append(ValidationMessage(rule_id=rule_id, message=message, object_ids=tuple(object_ids)))

    @property
    def ok(self) -> bool:
        return not self.errors


def load_development_view_model(path_or_model: Path | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(path_or_model, dict):
        model = path_or_model
    else:
        path = Path(path_or_model)
        with path.open(encoding="utf-8") as handle:
            model = json.load(handle)
    if not isinstance(model, dict):
        raise ValueError("Development view model must be a JSON object.")
    return model


def _numeric(mapping: dict[str, Any], key: str) -> float:
    value = mapping.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"Expected numeric field {key!r}, got {value!r}.")
    return float(value)


def frame_to_box(frame: dict[str, Any], *, box_id: str, kind: str) -> Box:
    return Box(
        id=box_id,
        x=_numeric(frame, "x"),
        y=_numeric(frame, "y"),
        width=_numeric(frame, "width"),
        height=_numeric(frame, "height"),
        kind=kind,
    )


def label_frame_to_box(frame: dict[str, Any], *, label_id: str, relationship_id: str) -> LabelBox:
    return LabelBox(
        id=label_id,
        x=_numeric(frame, "x"),
        y=_numeric(frame, "y"),
        width=_numeric(frame, "width"),
        height=_numeric(frame, "height"),
        relationship_id=relationship_id,
    )


def point_from_mapping(raw: dict[str, Any]) -> Point:
    return Point(x=_numeric(raw, "x"), y=_numeric(raw, "y"))


def segment_from_mapping(raw: dict[str, Any]) -> Segment:
    start = raw.get("start")
    end = raw.get("end")
    if not isinstance(start, dict) or not isinstance(end, dict):
        raise ValueError(f"Segment must include object start/end points, got {raw!r}.")
    return Segment(start=point_from_mapping(start), end=point_from_mapping(end))


def iter_element_boxes(model: dict[str, Any]) -> Iterable[tuple[dict[str, Any], Box]]:
    for element in model.get("elements") or []:
        if not isinstance(element, dict):
            continue
        frame = element.get("frame")
        element_id = str(element.get("id") or "")
        if not isinstance(frame, dict) or not element_id:
            continue
        yield element, frame_to_box(frame, box_id=element_id, kind="node")


def iter_group_boxes(model: dict[str, Any]) -> Iterable[tuple[dict[str, Any], Box]]:
    for group in model.get("groups") or []:
        if not isinstance(group, dict):
            continue
        frame = group.get("frame")
        group_id = str(group.get("id") or "")
        if not isinstance(frame, dict) or not group_id:
            continue
        yield group, frame_to_box(frame, box_id=group_id, kind="group")


def iter_edge_segments(model: dict[str, Any]) -> Iterable[tuple[dict[str, Any], list[Segment]]]:
    for relationship in model.get("relationships") or []:
        if not isinstance(relationship, dict):
            continue
        raw_segments = relationship.get("segments")
        if not isinstance(raw_segments, list):
            continue
        segments: list[Segment] = []
        for raw_segment in raw_segments:
            if not isinstance(raw_segment, dict):
                continue
            segments.append(segment_from_mapping(raw_segment))
        if segments:
            yield relationship, segments


def iter_label_boxes(model: dict[str, Any]) -> Iterable[tuple[dict[str, Any], LabelBox]]:
    for relationship in model.get("relationships") or []:
        if not isinstance(relationship, dict):
            continue
        label_box = relationship.get("label_box")
        relationship_id = str(relationship.get("id") or "")
        if not isinstance(label_box, dict) or not relationship_id:
            continue
        yield relationship, label_frame_to_box(
            label_box,
            label_id=f"label-{relationship_id}",
            relationship_id=relationship_id,
        )


def iter_annotation_boxes(model: dict[str, Any]) -> Iterable[tuple[str, Box]]:
    for key, box_id in (
        ("legend", "development-legend"),
        ("relationship_legend", "development-relationship-legend"),
    ):
        raw = model.get(key)
        frame = raw.get("frame") if isinstance(raw, dict) else None
        if isinstance(frame, dict):
            yield box_id, frame_to_box(frame, box_id=box_id, kind="annotation")


def element_port_map(model: dict[str, Any]) -> dict[str, dict[str, Point]]:
    result: dict[str, dict[str, Point]] = {}
    for element in model.get("elements") or []:
        if not isinstance(element, dict):
            continue
        element_id = str(element.get("id") or "")
        raw_ports = element.get("ports")
        if not element_id or not isinstance(raw_ports, dict):
            continue
        ports: dict[str, Point] = {}
        for port_name, raw_point in raw_ports.items():
            if isinstance(port_name, str) and isinstance(raw_point, dict):
                ports[port_name] = point_from_mapping(raw_point)
        result[element_id] = ports
    return result


def geometry_digest(model: dict[str, Any]) -> str:
    relevant = {
        "canvas": model.get("canvas"),
        "groups": [
            {
                "id": group.get("id"),
                "frame": group.get("frame"),
            }
            for group in (model.get("groups") or [])
            if isinstance(group, dict)
        ],
        "elements": [
            {
                "id": element.get("id"),
                "frame": element.get("frame"),
                "ports": element.get("ports"),
            }
            for element in (model.get("elements") or [])
            if isinstance(element, dict)
        ],
        "relationships": [
            {
                "id": relationship.get("id"),
                "segments": relationship.get("segments"),
                "label_box": relationship.get("label_box"),
                "code": relationship.get("code"),
                "summary_label": relationship.get("summary_label"),
            }
            for relationship in (model.get("relationships") or [])
            if isinstance(relationship, dict)
        ],
        "legend": model.get("legend"),
        "relationship_legend": model.get("relationship_legend"),
    }
    payload = json.dumps(relevant, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
