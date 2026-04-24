from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xml.etree import ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from views.development.model import load_development_view_model
from views.development.render import build_development_diagram_xml
from tools.validate_drawio import validate_file


FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "development_view"
TEST_OUTPUT_DIR = REPO_ROOT / "tmp-artifacts" / "test-rendered" / "test_rendered_development_view_rules"


def assert_contains(messages: list[str], needle: str) -> None:
    assert any(needle in message for message in messages), messages


def render_development_xml_without_pipeline(fixture_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{fixture_path.stem}.drawio"
    model = load_development_view_model(fixture_path)
    output_path.write_text(build_development_diagram_xml(model), encoding="utf-8")
    return output_path


@pytest.mark.parametrize(
    ("fixture_name", "expected_errors", "expected_warnings"),
    [
        ("valid-balanced.json", [], []),
        ("xml-no-edges.json", [], ["diagram has no edges"]),
        ("xml-invalid-colors.json", ["invalid fillColor", "invalid strokeColor", "invalid fontColor"], []),
        ("xml-long-labels.json", [], ["group label on group-development-root is long", "group label on group-development-root has too many lines", "node label on node-a is long", "node label on node-a has too many lines", "node label on node-b has too many lines", "node label on edge-label-rel-a-b is long", "node label on edge-label-rel-a-b ends like prose"]),
        ("xml-semantic-budget.json", [], ["semantic fill palette uses", "semantic stroke palette uses"]),
        ("invalid-label-node-overlap.json", [], []),
        ("invalid-label-overlap.json", [], []),
    ],
)
def test_rendered_fixture_xml_validator_matrix(
    fixture_name: str,
    expected_errors: list[str],
    expected_warnings: list[str],
) -> None:
    output_dir = TEST_OUTPUT_DIR / Path(fixture_name).stem
    output_dir.mkdir(parents=True, exist_ok=True)
    output = render_development_xml_without_pipeline(FIXTURE_DIR / fixture_name, output_dir)
    warnings, errors = validate_file(output)
    for needle in expected_errors:
        assert_contains(errors, needle)
    for needle in expected_warnings:
        assert_contains(warnings, needle)
