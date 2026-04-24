from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from views.logic.validate import validate_logic_view
from views.runtime.validate import validate_runtime_view
from views.use_case.validate import validate_use_case_catalog, validate_use_case_view


FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    return data


def assert_error_contains(errors: list[str], needle: str) -> None:
    assert any(needle in error for error in errors), errors


@pytest.mark.parametrize(
    ("fixture_name", "expected"),
    [
        ("invalid-empty.json", "must include at least one group"),
        ("invalid-unknown-group.json", "references unknown group missing"),
        ("invalid-unknown-endpoint.json", "references unknown target db"),
        ("invalid-duplicate-relationship.json", "Duplicate logic relationship"),
        ("invalid-duplicate-element.json", "duplicate element ids"),
    ],
)
def test_logic_view_validator_rejects_invalid_models(fixture_name: str, expected: str) -> None:
    errors = validate_logic_view(load_json(FIXTURE_ROOT / "logic_view" / fixture_name))
    assert_error_contains(errors, expected)


def test_logic_view_validator_accepts_valid_model() -> None:
    errors = validate_logic_view(load_json(FIXTURE_ROOT / "logic_view" / "valid-layered.json"))
    assert not errors


@pytest.mark.parametrize(
    ("fixture_name", "expected"),
    [
        ("invalid-missing-primary-paths.json", "primary_paths"),
        ("invalid-unrenderable-primary-path.json", "unknown relationship missing-step"),
        ("invalid-unknown-endpoint.json", "unknown target db"),
        ("invalid-empty-path.json", "has no step ids"),
        ("invalid-duplicate-relationship-id.json", "duplicate relationship ids"),
    ],
)
def test_runtime_view_validator_rejects_invalid_models(fixture_name: str, expected: str) -> None:
    errors = validate_runtime_view(load_json(FIXTURE_ROOT / "runtime_view" / fixture_name))
    assert_error_contains(errors, expected)


def test_runtime_view_validator_accepts_valid_model() -> None:
    errors = validate_runtime_view(load_json(FIXTURE_ROOT / "runtime_view" / "valid-primary-path.json"))
    assert not errors


@pytest.mark.parametrize(
    ("fixture_name", "expected"),
    [
        ("invalid-empty.json", "must include at least one element"),
        ("invalid-unknown-group.json", "unknown group missing"),
        ("invalid-unknown-boundary.json", "unknown boundary missing-boundary"),
        ("invalid-unknown-endpoint.json", "unknown target missing"),
        ("invalid-duplicate-element.json", "duplicate element ids"),
    ],
)
def test_use_case_view_validator_rejects_invalid_models(fixture_name: str, expected: str) -> None:
    errors = validate_use_case_view(load_json(FIXTURE_ROOT / "use_case_view" / fixture_name))
    assert_error_contains(errors, expected)


def test_use_case_view_validator_accepts_valid_model() -> None:
    errors = validate_use_case_view(load_json(FIXTURE_ROOT / "use_case_view" / "valid-grouped.json"))
    assert not errors


@pytest.mark.parametrize(
    ("fixture_name", "expected"),
    [
        ("invalid-empty-use-cases.json", "non-empty top-level use_cases"),
        ("invalid-columns.json", "catalog_columns must be exactly"),
        ("invalid-unknown-actor.json", "unknown actor operator"),
        ("invalid-duplicate-id-code.json", "Duplicate use-case catalog id create-plan"),
        ("invalid-duplicate-id-code.json", "Duplicate use-case catalog code UC-01"),
        ("invalid-entry-surfaces-type.json", "entry_surfaces must be a list"),
        ("invalid-missing-id.json", "row is missing id"),
    ],
)
def test_use_case_catalog_validator_rejects_invalid_models(fixture_name: str, expected: str) -> None:
    errors = validate_use_case_catalog(load_json(FIXTURE_ROOT / "use_case_catalog" / fixture_name))
    assert_error_contains(errors, expected)


def test_use_case_catalog_validator_accepts_valid_model() -> None:
    errors = validate_use_case_catalog(load_json(FIXTURE_ROOT / "use_case_catalog" / "valid-catalog.json"))
    assert not errors
