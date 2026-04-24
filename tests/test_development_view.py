from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from render_drawio import render_view_model
from validate_development_view import validate_development_view
from validate_drawio import validate_file


FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "development_view"
TEST_OUTPUT_DIR = REPO_ROOT / "tmp-artifacts" / "test-rendered" / "test_development_view"


def rule_ids(messages) -> set[str]:
    return {message.rule_id for message in messages}


def without_soft_breaks(value: str) -> str:
    return value.replace("&amp;#8203;", "").replace("&#8203;", "").replace("\u200b", "")


def test_valid_balanced_fixture_passes_structure_validation() -> None:
    report = validate_development_view(FIXTURE_DIR / "valid-balanced.json")
    assert not report.errors
    assert not report.warnings


def test_duplicate_edge_fixture_reports_duplicate_edge() -> None:
    report = validate_development_view(FIXTURE_DIR / "invalid-duplicate-edge.json")
    assert "duplicate-edge" in rule_ids(report.errors)


def test_edge_node_overlap_fixture_reports_overlap() -> None:
    report = validate_development_view(FIXTURE_DIR / "invalid-edge-node-overlap.json")
    assert "edge-node-overlap" in rule_ids(report.errors)


def test_edge_edge_intersection_fixture_reports_intersection() -> None:
    report = validate_development_view(FIXTURE_DIR / "invalid-edge-edge-intersection.json")
    assert "edge-edge-intersection" in rule_ids(report.errors)


def test_edge_label_overlap_fixture_is_allowed() -> None:
    report = validate_development_view(FIXTURE_DIR / "invalid-label-overlap.json")
    assert "label-label-overlap" not in rule_ids(report.errors)


def test_annotation_overlap_fixture_reports_overlap() -> None:
    report = validate_development_view(FIXTURE_DIR / "invalid-annotation-overlap.json")
    assert "annotation-annotation-overlap" in rule_ids(report.errors)


def test_missing_content_fixture_reports_missing_fields() -> None:
    report = validate_development_view(FIXTURE_DIR / "invalid-missing-content.json")
    assert {"missing-responsibility", "missing-exposes"} <= rule_ids(report.errors)


def test_sparse_layout_fixture_warns_without_errors() -> None:
    report = validate_development_view(FIXTURE_DIR / "invalid-sparse-layout.json")
    assert not report.errors
    assert "compactness-warning" in rule_ids(report.warnings)


def test_valid_balanced_fixture_renders_and_passes_drawio_validation() -> None:
    output_dir = TEST_OUTPUT_DIR / "valid-balanced"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = render_view_model(FIXTURE_DIR / "valid-balanced.json", output_dir)
    assert output_path.name == "valid-balanced.drawio"

    warnings, errors = validate_file(output_path)
    assert not errors

    xml = without_soft_breaks(output_path.read_text(encoding="utf-8"))
    assert "Coordinates multi-generation development-view export runs" in xml
    assert "+ choose_selfimproves()" in xml
    assert "+ export_with_real_drawio()" in xml
    assert "dispatch structured export" in xml
    assert "publish drawio result" in xml
