from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from render_drawio import render_view_model
from solve_development_view_layout import solve_development_view_layout
from validate_development_view import validate_development_view
from validate_drawio import validate_file


DGM_DEVELOPMENT_MODEL = REPO_ROOT / "tmp-artifacts" / "dgm-main" / "development" / "development-view.json"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "development_view"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def strip_layout(model: dict) -> dict:
    stripped = copy.deepcopy(model)
    stripped.pop("canvas", None)
    stripped.pop("legend", None)
    stripped.pop("relationship_legend", None)
    for group in stripped.get("groups") or []:
        if isinstance(group, dict):
            group.pop("frame", None)
    for element in stripped.get("elements") or []:
        if isinstance(element, dict):
            element.pop("frame", None)
            element.pop("ports", None)
    for relationship in stripped.get("relationships") or []:
        if isinstance(relationship, dict):
            relationship.pop("id", None)
            relationship.pop("source_port", None)
            relationship.pop("target_port", None)
            relationship.pop("segments", None)
            relationship.pop("label_box", None)
    return stripped


def test_solver_completes_dgm_development_geometry_with_numbered_line_descriptions() -> None:
    solved = solve_development_view_layout(load_json(DGM_DEVELOPMENT_MODEL))

    report = validate_development_view(solved)
    assert not report.errors
    assert not report.warnings
    assert all(relationship.get("code", "").startswith("R") for relationship in solved["relationships"])
    assert all(relationship.get("label_box") for relationship in solved["relationships"])
    assert solved.get("relationship_legend", {}).get("items")


def test_solver_handles_generic_unlaid_development_fixture() -> None:
    source = strip_layout(load_json(FIXTURE_DIR / "valid-balanced.json"))
    solved = solve_development_view_layout(source)

    report = validate_development_view(solved)
    assert not report.errors
    assert not report.warnings
    assert all(element.get("frame") and element.get("ports") for element in solved["elements"])
    assert all(relationship.get("segments") for relationship in solved["relationships"])


def test_solver_output_renders_without_drawio_errors(tmp_path: Path) -> None:
    solved = solve_development_view_layout(load_json(DGM_DEVELOPMENT_MODEL))
    solved_path = tmp_path / "development-view-solved.json"
    solved_path.write_text(json.dumps(solved, ensure_ascii=False), encoding="utf-8")

    drawio_path = render_view_model(solved_path, tmp_path)
    _, errors = validate_file(drawio_path)

    assert not errors
    xml = drawio_path.read_text(encoding="utf-8")
    assert "edge-label-" in xml
    assert "development-relationship-legend" in xml
    root = ET.fromstring(xml)
    edge_ids = {
        cell.attrib["id"]
        for cell in root.findall(".//mxCell")
        if cell.attrib.get("edge") == "1"
    }
    label_cells = [
        cell
        for cell in root.findall(".//mxCell")
        if cell.attrib.get("id", "").startswith("edge-label-")
    ]
    assert label_cells
    assert all(cell.attrib.get("parent") in edge_ids for cell in label_cells)
