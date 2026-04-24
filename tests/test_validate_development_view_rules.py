from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_development_view import validate_development_view


FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "development_view"


def error_ids(report) -> set[str]:
    return {message.rule_id for message in report.errors}


def warning_ids(report) -> set[str]:
    return {message.rule_id for message in report.warnings}


@pytest.mark.parametrize(
    ("fixture_name", "expected_errors", "expected_warnings"),
    [
        ("invalid-view.json", {"invalid-view"}, set()),
        ("missing-canvas.json", {"missing-canvas"}, set()),
        ("invalid-canvas.json", {"invalid-canvas"}, set()),
        ("unknown-group.json", {"unknown-group"}, {"compactness-warning"}),
        ("invalid-missing-content.json", {"missing-responsibility", "missing-exposes"}, set()),
        ("unknown-element.json", {"unknown-element", "unknown-port"}, {"compactness-warning"}),
        ("unknown-port.json", {"unknown-port"}, {"compactness-warning"}),
        ("core-edge-missing.json", {"core-edge-missing"}, {"compactness-warning"}),
        ("invalid-duplicate-edge.json", {"duplicate-edge"}, set()),
        ("invalid-non-straight-edge.json", {"non-straight-edge"}, set()),
        ("invalid-port-segment-mismatch.json", {"port-segment-mismatch"}, {"compactness-warning"}),
        ("invalid-node-node-overlap.json", {"node-node-overlap"}, {"compactness-warning"}),
        ("invalid-edge-node-overlap.json", {"edge-node-overlap"}, set()),
        ("invalid-edge-edge-intersection.json", {"edge-edge-intersection"}, set()),
        ("invalid-label-node-overlap.json", set(), {"compactness-warning"}),
        ("invalid-label-overlap.json", set(), set()),
        ("invalid-annotation-node-overlap.json", {"annotation-node-overlap"}, {"compactness-warning"}),
        ("invalid-annotation-overlap.json", {"annotation-annotation-overlap"}, {"compactness-warning"}),
        ("overlong-edge-warning.json", set(), {"overlong-edge-warning"}),
        ("invalid-sparse-layout.json", set(), {"compactness-warning"}),
        ("valid-balanced.json", set(), set()),
    ],
)
def test_structure_rule_fixture_matrix(
    fixture_name: str,
    expected_errors: set[str],
    expected_warnings: set[str],
) -> None:
    report = validate_development_view(FIXTURE_DIR / fixture_name)
    assert expected_errors == error_ids(report)
    assert expected_warnings == warning_ids(report)
