from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from render_drawio import render_use_case_pair_from_catalog, render_view_model
from tools.validate_drawio import validate_file


FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures"
TEST_OUTPUT_DIR = REPO_ROOT / "tmp-artifacts" / "test-rendered" / "test_other_views_rendering"


def without_soft_breaks(value: str) -> str:
    return value.replace("&amp;#8203;", "").replace("&#8203;", "").replace("\u200b", "")


def assert_renders_without_drawio_errors(fixture_path: Path, output_subdir: str) -> str:
    output_dir = TEST_OUTPUT_DIR / output_subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = render_view_model(fixture_path, output_dir)
    _, errors = validate_file(output_path)
    assert not errors
    return without_soft_breaks(output_path.read_text(encoding="utf-8"))


def assert_renders_with_drawio_errors(fixture_path: Path, output_subdir: str) -> list[str]:
    output_dir = TEST_OUTPUT_DIR / output_subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = render_view_model(fixture_path, output_dir)
    _, errors = validate_file(output_path)
    assert errors
    return errors


def test_logic_view_fixture_renders_layered_groups_and_edges() -> None:
    xml = assert_renders_without_drawio_errors(
        FIXTURE_ROOT / "logic_view" / "valid-layered.json",
        "logic",
    )

    assert "Logic View Fixture" in xml
    assert "Entry Layer" in xml
    assert "Case Service" in xml
    assert "submits" in xml
    assert "persists" in xml


def test_runtime_view_fixture_renders_primary_path_steps() -> None:
    xml = assert_renders_without_drawio_errors(
        FIXTURE_ROOT / "runtime_view" / "valid-primary-path.json",
        "runtime",
    )

    assert "Runtime View Fixture" in xml
    assert "Happy Path" in xml
    assert "Browser" in xml
    assert "submit request" in xml
    assert "return result" in xml


def test_use_case_view_fixture_renders_boundary_panels_and_include() -> None:
    xml = assert_renders_without_drawio_errors(
        FIXTURE_ROOT / "use_case_view" / "valid-grouped.json",
        "use-case",
    )

    assert "Use Case View Fixture" in xml
    assert "Planning System" in xml
    assert "Create Plan" in xml
    assert "Approve Plan" in xml
    assert "&lt;&lt;include&gt;&gt;" in xml


def test_use_case_catalog_fixture_renders_table_columns_and_rows() -> None:
    xml = assert_renders_without_drawio_errors(
        FIXTURE_ROOT / "use_case_catalog" / "valid-catalog.json",
        "use-case-catalog",
    )

    assert "Planning Use Case Catalog" in xml
    assert "UC-01" in xml
    assert "Create Plan" in xml
    assert "Web Console" in xml
    assert "Planner creates a new delivery plan." in xml


def test_use_case_catalog_fixture_renders_catalog_and_derived_view_pair() -> None:
    output_dir = TEST_OUTPUT_DIR / "use-case-pair"
    output_dir.mkdir(parents=True, exist_ok=True)

    rendered_paths = render_use_case_pair_from_catalog(
        FIXTURE_ROOT / "use_case_catalog" / "valid-catalog.json",
        output_dir,
    )

    assert [path.name for path in rendered_paths] == ["use-case-catalog-view.drawio", "use-case-view.drawio"]
    for rendered_path in rendered_paths:
        _, errors = validate_file(rendered_path)
        assert not errors

    derived_xml = without_soft_breaks((output_dir / "use-case-view.drawio").read_text(encoding="utf-8"))
    assert "Planning Use Case View" in derived_xml
    assert "Planning System" in derived_xml
    assert "Create Plan" in derived_xml


def test_logic_view_empty_fixture_is_rejected() -> None:
    with pytest.raises(ValueError, match="Logic view must include at least one group"):
        render_view_model(
            FIXTURE_ROOT / "logic_view" / "invalid-empty.json",
            TEST_OUTPUT_DIR / "logic-invalid-empty",
        )


def test_runtime_view_missing_primary_paths_fixture_is_rejected() -> None:
    with pytest.raises(ValueError, match="primary_paths"):
        render_view_model(
            FIXTURE_ROOT / "runtime_view" / "invalid-missing-primary-paths.json",
            TEST_OUTPUT_DIR / "runtime-invalid-missing-primary-paths",
        )


def test_runtime_view_unrenderable_primary_path_fixture_is_rejected() -> None:
    with pytest.raises(ValueError, match="references unknown relationship missing-step"):
        render_view_model(
            FIXTURE_ROOT / "runtime_view" / "invalid-unrenderable-primary-path.json",
            TEST_OUTPUT_DIR / "runtime-invalid-unrenderable-primary-path",
        )


def test_use_case_view_empty_fixture_is_rejected() -> None:
    with pytest.raises(ValueError, match="Use-case view must include at least one element"):
        render_view_model(
            FIXTURE_ROOT / "use_case_view" / "invalid-empty.json",
            TEST_OUTPUT_DIR / "use-case-invalid-empty",
        )


def test_use_case_catalog_empty_fixture_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty top-level use_cases"):
        render_view_model(
            FIXTURE_ROOT / "use_case_catalog" / "invalid-empty-use-cases.json",
            TEST_OUTPUT_DIR / "use-case-catalog-invalid-empty",
        )


def test_use_case_catalog_invalid_columns_fixture_is_rejected() -> None:
    with pytest.raises(ValueError, match="catalog_columns must be exactly"):
        render_view_model(
            FIXTURE_ROOT / "use_case_catalog" / "invalid-columns.json",
            TEST_OUTPUT_DIR / "use-case-catalog-invalid-columns",
        )


def test_unsupported_view_fixture_is_rejected() -> None:
    with pytest.raises(ValueError, match="Only development, logic, runtime, use-case, and use-case-catalog"):
        render_view_model(
            FIXTURE_ROOT / "unsupported_view" / "invalid-view.json",
            TEST_OUTPUT_DIR / "unsupported-view",
        )
