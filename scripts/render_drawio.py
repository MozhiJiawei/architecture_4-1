from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

try:
    from tools.validate_drawio import validate_file
    from views.development.layout import solve_development_view_layout
    from views.development.render import build_development_diagram_xml
    from views.development.validate import validate_development_view
    from views.drawio_common import drawio_filename_for_view
    from views.logic.layout import solve_logic_view_layout
    from views.logic.render import build_logic_diagram_xml
    from views.logic.validate import validate_logic_view
    from views.runtime.layout import solve_runtime_view_layout
    from views.runtime.render import build_runtime_diagram_xml
    from views.runtime.validate import validate_runtime_view
    from views.use_case.catalog import (
        build_use_case_catalog_diagram_xml,
        derive_use_case_view_model_from_catalog,
    )
    from views.use_case.layout import solve_use_case_catalog_layout, solve_use_case_view_layout
    from views.use_case.render import build_use_case_diagram_xml
    from views.use_case.validate import validate_use_case_catalog, validate_use_case_view
except ModuleNotFoundError:
    from scripts.tools.validate_drawio import validate_file
    from scripts.views.development.layout import solve_development_view_layout
    from scripts.views.development.render import build_development_diagram_xml
    from scripts.views.development.validate import validate_development_view
    from scripts.views.drawio_common import drawio_filename_for_view
    from scripts.views.logic.layout import solve_logic_view_layout
    from scripts.views.logic.render import build_logic_diagram_xml
    from scripts.views.logic.validate import validate_logic_view
    from scripts.views.runtime.layout import solve_runtime_view_layout
    from scripts.views.runtime.render import build_runtime_diagram_xml
    from scripts.views.runtime.validate import validate_runtime_view
    from scripts.views.use_case.catalog import (
        build_use_case_catalog_diagram_xml,
        derive_use_case_view_model_from_catalog,
    )
    from scripts.views.use_case.layout import solve_use_case_catalog_layout, solve_use_case_view_layout
    from scripts.views.use_case.render import build_use_case_diagram_xml
    from scripts.views.use_case.validate import validate_use_case_catalog, validate_use_case_view


def load_view_model(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _development_errors(model: dict[str, Any]) -> list[str]:
    report = validate_development_view(model)
    return [
        f"{message.rule_id}: {message.message}"
        for message in report.errors
    ]


def solve_view_layout(view_model: dict[str, Any]) -> dict[str, Any]:
    view = str(view_model.get("view") or "").strip().lower()
    if view == "development":
        return solve_development_view_layout(view_model)
    if view == "logic":
        return solve_logic_view_layout(view_model)
    if view == "runtime":
        return solve_runtime_view_layout(view_model)
    if view == "use-case":
        return solve_use_case_view_layout(view_model)
    if view == "use-case-catalog":
        return solve_use_case_catalog_layout(view_model)
    raise ValueError(
        f"Only development, logic, runtime, use-case, and use-case-catalog view rendering are supported right now; got view={view!r}"
    )


def validate_view_model(view_model: dict[str, Any]) -> None:
    view = str(view_model.get("view") or "").strip().lower()
    if view == "development":
        errors = _development_errors(view_model)
    elif view == "logic":
        errors = validate_logic_view(view_model)
    elif view == "runtime":
        errors = validate_runtime_view(view_model)
    elif view == "use-case":
        errors = validate_use_case_view(view_model)
    elif view == "use-case-catalog":
        errors = validate_use_case_catalog(view_model)
    else:
        raise ValueError(
            f"Only development, logic, runtime, use-case, and use-case-catalog view rendering are supported right now; got view={view!r}"
        )
    if errors:
        raise ValueError("Model validation failed: " + "; ".join(errors[:8]))


def render_view_xml(view_model: dict[str, Any]) -> str:
    view = str(view_model.get("view") or "").strip().lower()
    if view == "development":
        return build_development_diagram_xml(view_model)
    if view == "logic":
        return build_logic_diagram_xml(view_model)
    if view == "runtime":
        return build_runtime_diagram_xml(view_model)
    if view == "use-case-catalog":
        return build_use_case_catalog_diagram_xml(view_model)
    if view == "use-case":
        return build_use_case_diagram_xml(view_model)
    raise ValueError(
        f"Only development, logic, runtime, use-case, and use-case-catalog view rendering are supported right now; got view={view!r}"
    )


def validate_rendered_drawio(output_path: Path) -> None:
    _, errors = validate_file(output_path)
    if errors:
        raise ValueError("Draw.io validation failed: " + "; ".join(errors[:8]))


def render_view_model(input_path: Path, output_dir: Path) -> Path:
    view_model = load_view_model(input_path)
    view = str(view_model.get("view") or "").strip().lower()
    if view not in {"development", "logic", "runtime", "use-case", "use-case-catalog"}:
        raise ValueError(
            f"Only development, logic, runtime, use-case, and use-case-catalog view rendering are supported right now; got view={view!r} in {input_path}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    solved_model = solve_view_layout(view_model)
    validate_view_model(solved_model)
    output_path = output_dir / drawio_filename_for_view(solved_model, input_path)
    xml = render_view_xml(solved_model)
    output_path.write_text(xml, encoding="utf-8")
    validate_rendered_drawio(output_path)
    return output_path


def render_use_case_pair_from_catalog(input_path: Path, output_dir: Path) -> list[Path]:
    catalog_model = load_view_model(input_path)
    if str(catalog_model.get("view") or "").strip().lower() != "use-case-catalog":
        return [render_view_model(input_path, output_dir)]

    output_dir.mkdir(parents=True, exist_ok=True)
    rendered_paths: list[Path] = []

    solved_catalog_model = solve_view_layout(catalog_model)
    validate_view_model(solved_catalog_model)
    catalog_output_path = output_dir / drawio_filename_for_view(solved_catalog_model, input_path)
    catalog_xml = render_view_xml(solved_catalog_model)
    catalog_output_path.write_text(catalog_xml, encoding="utf-8")
    validate_rendered_drawio(catalog_output_path)
    rendered_paths.append(catalog_output_path)

    derived_view_model = derive_use_case_view_model_from_catalog(solved_catalog_model)
    solved_derived_model = solve_view_layout(derived_view_model)
    validate_view_model(solved_derived_model)
    derived_output_path = output_dir / "use-case-view.drawio"
    derived_xml = render_view_xml(solved_derived_model)
    derived_output_path.write_text(derived_xml, encoding="utf-8")
    validate_rendered_drawio(derived_output_path)
    rendered_paths.append(derived_output_path)

    return rendered_paths


def export_rendered_preview(
    rendered_path: Path,
    preview_dir: Path,
    *,
    preview_format: str,
    preserve_alpha: bool,
) -> Path:
    try:
        from tools.export_diagrams import export_with_real_drawio
    except ModuleNotFoundError:
        from scripts.tools.export_diagrams import export_with_real_drawio

    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_path = preview_dir / f"{rendered_path.stem}.{preview_format}"
    asyncio.run(
        export_with_real_drawio(
            rendered_path,
            preview_path,
            flatten_png=not preserve_alpha,
        )
    )
    return preview_path


def collect_input_models(input_arg: str | None) -> list[Path]:
    if not input_arg:
        raise ValueError("Provide a path to a view model JSON file or a directory containing view model JSON files.")
    input_path = Path(input_arg)
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted(path for path in input_path.glob("*.json") if path.is_file())
    raise ValueError(f"Input path not found: {input_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render draw.io files from intermediate 3+1 view models."
    )
    parser.add_argument("input", nargs="?", help="Path to a view model or model directory")
    parser.add_argument(
        "--output-dir",
        default="docs/architecture",
        help="Directory for rendered .drawio files",
    )
    parser.add_argument(
        "--export-previews",
        action="store_true",
        help="Also export rendered draw.io files through the real draw.io renderer.",
    )
    parser.add_argument(
        "--preview-dir",
        help="Directory for exported previews (defaults to <output-dir>/exports).",
    )
    parser.add_argument(
        "--preview-format",
        default="png",
        choices=["png", "svg"],
        help="Format for exported previews.",
    )
    parser.add_argument(
        "--preserve-preview-alpha",
        action="store_true",
        help="Keep PNG alpha instead of flattening previews onto white.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    preview_dir = Path(args.preview_dir) if args.preview_dir else output_dir / "exports"
    try:
        inputs = collect_input_models(args.input)
        if not inputs:
            raise ValueError(f"No JSON view models found in {args.input}")
        for input_path in inputs:
            rendered_paths = render_use_case_pair_from_catalog(input_path, output_dir)
            for rendered in rendered_paths:
                print(f"Rendered {input_path} -> {rendered}")
                if args.export_previews:
                    preview_path = export_rendered_preview(
                        rendered,
                        preview_dir,
                        preview_format=args.preview_format,
                        preserve_alpha=args.preserve_preview_alpha,
                    )
                    print(f"Previewed {rendered} -> {preview_path}")
    except Exception as exc:
        print(f"render_drawio.py failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
