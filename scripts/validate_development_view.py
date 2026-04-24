from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from development_view_model import (
    LabelBox,
    Point,
    Segment,
    ValidationMessage,
    ValidationReport,
    element_port_map,
    iter_annotation_boxes,
    iter_edge_segments,
    iter_element_boxes,
    iter_group_boxes,
    load_development_view_model,
)
from orthogonal_router import Box


GEOMETRY_EPSILON = 1e-6
MIN_COMPACTNESS = 0.15
MAX_EDGE_LENGTH_FACTOR = 0.75


def is_close(value: float, target: float = 0.0) -> bool:
    return abs(value - target) <= GEOMETRY_EPSILON


def points_equal(first: tuple[float, float], second: tuple[float, float]) -> bool:
    return is_close(first[0], second[0]) and is_close(first[1], second[1])


def orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return ((b[0] - a[0]) * (c[1] - a[1])) - ((b[1] - a[1]) * (c[0] - a[0]))


def on_segment(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    return (
        min(a[0], c[0]) - GEOMETRY_EPSILON <= b[0] <= max(a[0], c[0]) + GEOMETRY_EPSILON
        and min(a[1], c[1]) - GEOMETRY_EPSILON <= b[1] <= max(a[1], c[1]) + GEOMETRY_EPSILON
    )


def segment_overlap_length(
    first: tuple[tuple[float, float], tuple[float, float]],
    second: tuple[tuple[float, float], tuple[float, float]],
) -> float:
    (ax1, ay1), (ax2, ay2) = first
    (bx1, by1), (bx2, by2) = second
    if abs(ax1 - ax2) >= abs(ay1 - ay2):
        start = max(min(ax1, ax2), min(bx1, bx2))
        end = min(max(ax1, ax2), max(bx1, bx2))
    else:
        start = max(min(ay1, ay2), min(by1, by2))
        end = min(max(ay1, ay2), max(by1, by2))
    return end - start


def segments_conflict(
    first: tuple[tuple[float, float], tuple[float, float]],
    second: tuple[tuple[float, float], tuple[float, float]],
) -> bool:
    p1, q1 = first
    p2, q2 = second

    shared_points = [
        candidate
        for candidate in (p1, q1)
        if points_equal(candidate, p2) or points_equal(candidate, q2)
    ]
    if len(shared_points) == 2:
        return False

    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    if (
        ((o1 > GEOMETRY_EPSILON and o2 < -GEOMETRY_EPSILON) or (o1 < -GEOMETRY_EPSILON and o2 > GEOMETRY_EPSILON))
        and ((o3 > GEOMETRY_EPSILON and o4 < -GEOMETRY_EPSILON) or (o3 < -GEOMETRY_EPSILON and o4 > GEOMETRY_EPSILON))
    ):
        return True

    collinear = is_close(o1) and is_close(o2) and is_close(o3) and is_close(o4)
    if collinear:
        return segment_overlap_length(first, second) > GEOMETRY_EPSILON

    for point, start, end in ((p2, p1, q1), (q2, p1, q1), (p1, p2, q2), (q1, p2, q2)):
        if is_close(orientation(start, end, point)) and on_segment(start, point, end):
            if any(points_equal(point, shared) for shared in shared_points):
                continue
            return True
    return False


def point_in_box(point: tuple[float, float], box: Box) -> bool:
    x, y = point
    return box.left <= x <= box.right and box.top <= y <= box.bottom


def segment_intersects_box(
    start: tuple[float, float],
    end: tuple[float, float],
    box: Box,
) -> bool:
    if point_in_box(start, box) or point_in_box(end, box):
        return True
    corners = [
        (box.left, box.top),
        (box.right, box.top),
        (box.right, box.bottom),
        (box.left, box.bottom),
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
    return point_in_box(midpoint, box)


def box_overlap_area(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> float:
    fx, fy, fw, fh = first
    sx, sy, sw, sh = second
    overlap_x = min(fx + fw, sx + sw) - max(fx, sx)
    overlap_y = min(fy + fh, sy + sh) - max(fy, sy)
    if overlap_x <= GEOMETRY_EPSILON or overlap_y <= GEOMETRY_EPSILON:
        return 0.0
    return overlap_x * overlap_y


def box_to_tuple(box: Box | LabelBox) -> tuple[float, float, float, float]:
    if isinstance(box, LabelBox):
        return box.x, box.y, box.width, box.height
    return box.x, box.y, box.width, box.height


def segment_length(segment: Segment) -> float:
    return ((segment.end.x - segment.start.x) ** 2 + (segment.end.y - segment.start.y) ** 2) ** 0.5


def validate_development_view(path_or_model: Path | str | dict[str, Any]) -> ValidationReport:
    model = load_development_view_model(path_or_model)
    report = ValidationReport()

    if str(model.get("view") or "").strip().lower() != "development":
        report.add_error("invalid-view", "Development validator only accepts view='development'.")
        return report

    canvas = model.get("canvas")
    if not isinstance(canvas, dict):
        report.add_error("missing-canvas", "Development view model must include a canvas object.")
        return report

    canvas_width = float(canvas.get("width") or 0)
    canvas_height = float(canvas.get("height") or 0)
    if canvas_width <= 0 or canvas_height <= 0:
        report.add_error("invalid-canvas", "Canvas width/height must be positive numbers.")
        return report

    group_ids: set[str] = set()
    for group, _ in iter_group_boxes(model):
        group_id = str(group.get("id") or "")
        if group_id:
            group_ids.add(group_id)

    element_boxes: dict[str, Box] = {}
    elements_by_id: dict[str, dict[str, Any]] = {}
    for element, box in iter_element_boxes(model):
        element_id = str(element.get("id") or "")
        elements_by_id[element_id] = element
        element_boxes[element_id] = box
        if str(element.get("group") or "") not in group_ids:
            report.add_error(
                "unknown-group",
                f"Element {element_id} references unknown group {element.get('group')!r}.",
                element_id,
                str(element.get("group") or ""),
            )
        if not str(element.get("responsibility") or "").strip():
            report.add_error("missing-responsibility", f"Element {element_id} is missing responsibility text.", element_id)
        exposes = element.get("exposes")
        if not isinstance(exposes, list) or not any(str(item).strip() for item in exposes):
            report.add_error("missing-exposes", f"Element {element_id} must expose at least one interface line.", element_id)

    port_map = element_port_map(model)
    annotation_boxes = list(iter_annotation_boxes(model))
    relationship_segments = list(iter_edge_segments(model))

    signature_counts: dict[tuple[str, str, str, str], list[str]] = {}
    seen_core_signatures: set[tuple[str, str, str, str]] = set()
    for relationship in model.get("relationships") or []:
        if not isinstance(relationship, dict):
            continue
        relationship_id = str(relationship.get("id") or "")
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        kind = str(relationship.get("kind") or "dependency")
        label = str(relationship.get("label") or "")
        signature = (source, target, kind, label)
        signature_counts.setdefault(signature, []).append(relationship_id)
        if source not in element_boxes:
            report.add_error("unknown-element", f"Relationship {relationship_id} references missing source {source!r}.", relationship_id, source)
        if target not in element_boxes:
            report.add_error("unknown-element", f"Relationship {relationship_id} references missing target {target!r}.", relationship_id, target)
        source_port = str(relationship.get("source_port") or "")
        target_port = str(relationship.get("target_port") or "")
        if source and source_port and source_port not in port_map.get(source, {}):
            report.add_error("unknown-port", f"Relationship {relationship_id} references missing source port {source_port!r}.", relationship_id, source, source_port)
        if target and target_port and target_port not in port_map.get(target, {}):
            report.add_error("unknown-port", f"Relationship {relationship_id} references missing target port {target_port!r}.", relationship_id, target, target_port)
        if relationship.get("core") is True and relationship.get("render", True) is False:
            report.add_error("core-edge-missing", f"Core relationship {relationship_id} is marked render=false.", relationship_id)
        if relationship.get("core") is True:
            seen_core_signatures.add(signature)

    for signature, relationship_ids in signature_counts.items():
        if len(relationship_ids) > 1:
            report.add_error(
                "duplicate-edge",
                f"Duplicate relationships detected for {signature[0]} -> {signature[1]} ({signature[2]} / {signature[3]}).",
                *relationship_ids,
            )

    for relationship in model.get("relationships") or []:
        if not isinstance(relationship, dict):
            continue
        relationship_id = str(relationship.get("id") or "")
        raw_segments = relationship.get("segments")
        if relationship.get("core") is True and (not isinstance(raw_segments, list) or not raw_segments):
            report.add_error(
                "core-edge-missing",
                f"Core relationship {relationship_id} is missing geometry segments.",
                relationship_id,
            )

    for relationship, segments in relationship_segments:
        relationship_id = str(relationship.get("id") or "")
        if len(segments) != 1:
            report.add_error("non-straight-edge", f"Relationship {relationship_id} must contain exactly one straight segment.", relationship_id)
        if len(segments) == 1:
            source = str(relationship.get("source") or "")
            target = str(relationship.get("target") or "")
            source_port = str(relationship.get("source_port") or "")
            target_port = str(relationship.get("target_port") or "")
            expected_start = port_map.get(source, {}).get(source_port)
            expected_end = port_map.get(target, {}).get(target_port)
            if expected_start is not None:
                actual_start = segments[0].start
                if not (is_close(actual_start.x, expected_start.x) and is_close(actual_start.y, expected_start.y)):
                    report.add_error(
                        "port-segment-mismatch",
                        f"Relationship {relationship_id} segment start does not match source port {source_port!r}.",
                        relationship_id,
                        source,
                        source_port,
                    )
            if expected_end is not None:
                actual_end = segments[0].end
                if not (is_close(actual_end.x, expected_end.x) and is_close(actual_end.y, expected_end.y)):
                    report.add_error(
                        "port-segment-mismatch",
                        f"Relationship {relationship_id} segment end does not match target port {target_port!r}.",
                        relationship_id,
                        target,
                        target_port,
                    )

    box_items = list(element_boxes.items())
    for index, (first_id, first_box) in enumerate(box_items):
        for second_id, second_box in box_items[index + 1 :]:
            if box_overlap_area(box_to_tuple(first_box), box_to_tuple(second_box)) > GEOMETRY_EPSILON:
                report.add_error("node-node-overlap", f"Elements {first_id} and {second_id} overlap.", first_id, second_id)

    all_segments: list[tuple[str, str, str, tuple[tuple[float, float], tuple[float, float]]]] = []
    for relationship, segments in relationship_segments:
        relationship_id = str(relationship.get("id") or "")
        source = str(relationship.get("source") or "")
        target = str(relationship.get("target") or "")
        for segment in segments:
            start = (segment.start.x, segment.start.y)
            end = (segment.end.x, segment.end.y)
            for obstacle_id, obstacle in element_boxes.items():
                if obstacle_id in {source, target}:
                    continue
                if segment_intersects_box(start, end, obstacle):
                    report.add_error(
                        "edge-node-overlap",
                        f"Relationship {relationship_id} intersects element {obstacle_id}.",
                        relationship_id,
                        obstacle_id,
                    )
            all_segments.append((relationship_id, source, target, (start, end)))

        edge_total_length = sum(segment_length(segment) for segment in segments)
        if edge_total_length > max(canvas_width, canvas_height) * MAX_EDGE_LENGTH_FACTOR:
            report.add_warning(
                "overlong-edge-warning",
                f"Relationship {relationship_id} spans a long distance ({edge_total_length:.1f}px).",
                relationship_id,
            )

    for index, (edge_id, source, target, segment) in enumerate(all_segments):
        for other_edge_id, other_source, other_target, other_segment in all_segments[index + 1 :]:
            if edge_id == other_edge_id:
                continue
            if {source, target} == {other_source, other_target}:
                continue
            if segments_conflict(segment, other_segment):
                report.add_error(
                    "edge-edge-intersection",
                    f"Relationships {edge_id} and {other_edge_id} intersect or overlap.",
                    edge_id,
                    other_edge_id,
                )

    for annotation_id, annotation_box in annotation_boxes:
        annotation_tuple = box_to_tuple(annotation_box)
        for element_id, element_box in element_boxes.items():
            if box_overlap_area(annotation_tuple, box_to_tuple(element_box)) > GEOMETRY_EPSILON:
                report.add_error(
                    "annotation-node-overlap",
                    f"Annotation {annotation_id} overlaps element {element_id}.",
                    annotation_id,
                    element_id,
                )

    for index, (first_id, first_box) in enumerate(annotation_boxes):
        for second_id, second_box in annotation_boxes[index + 1 :]:
            if box_overlap_area(box_to_tuple(first_box), box_to_tuple(second_box)) > GEOMETRY_EPSILON:
                report.add_error(
                    "annotation-annotation-overlap",
                    f"Annotations {first_id} and {second_id} overlap.",
                    first_id,
                    second_id,
                )

    if element_boxes:
        min_left = min(box.left for box in element_boxes.values())
        min_top = min(box.top for box in element_boxes.values())
        max_right = max(box.right for box in element_boxes.values())
        max_bottom = max(box.bottom for box in element_boxes.values())
        occupied_area = (max_right - min_left) * (max_bottom - min_top)
        compactness = occupied_area / max(1.0, canvas_width * canvas_height)
        if compactness < MIN_COMPACTNESS:
            report.add_warning(
                "compactness-warning",
                f"Layout is sparse (occupied area ratio {compactness:.3f} < {MIN_COMPACTNESS:.3f}).",
            )

    return report


def iter_targets(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(target.glob("*.json"))
    raise FileNotFoundError(f"Target not found: {target}")


def _render_message(level: str, message: ValidationMessage, source: Path) -> str:
    objects = f" [{', '.join(message.object_ids)}]" if message.object_ids else ""
    return f"{level}: {source}: {message.rule_id}{objects}: {message.message}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate development-view unified layout models.")
    parser.add_argument("target", nargs="?", default="tests/fixtures/development_view", help="File or directory to validate")
    args = parser.parse_args()

    target = Path(args.target)
    try:
        files = iter_targets(target)
    except Exception as exc:
        print(f"validate_development_view.py failed: {exc}")
        return 1

    if not files:
        print(f"validate_development_view.py failed: no .json files found in {target}")
        return 1

    all_errors = 0
    all_warnings = 0
    for source in files:
        report = validate_development_view(source)
        for warning in report.warnings:
            print(_render_message("WARNING", warning, source))
        for error in report.errors:
            print(_render_message("ERROR", error, source))
        all_errors += len(report.errors)
        all_warnings += len(report.warnings)

    if all_errors:
        print(f"Validation failed with {all_errors} error(s) and {all_warnings} warning(s).")
        return 1
    print(f"Validation passed for {len(files)} file(s) with {all_warnings} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
