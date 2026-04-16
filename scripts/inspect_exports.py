from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image
from PIL import ImageFile


ImageFile.LOAD_TRUNCATED_IMAGES = True


REF_MAP = {
    "logic-view": "\u903b\u8f91\u89c6\u56fe.jpg",
    "development-view": "\u5f00\u53d1\u89c6\u56fe.jpg",
    "runtime-view": "\u8fd0\u884c\u89c6\u56fe.jpg",
    "physical-view": "\u7269\u7406\u89c6\u56fe.jpg",
    "scenario-view": "\u573a\u666f\u89c6\u56fe.jpg",
}


def iter_images(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(path for path in target.glob("*.png") if path.is_file())
    raise FileNotFoundError(f"Target not found: {target}")


def inspect_image(image_path: Path) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    with Image.open(image_path) as img:
        rgb = img.convert("RGB")
        width, height = rgb.size
        if width < 400 or height < 300:
            warnings.append(f"{image_path}: unusually small export ({width}x{height})")
        pixels = list(rgb.getdata())
        non_white = sum(1 for pixel in pixels if pixel != (255, 255, 255))
        ratio = non_white / max(1, len(pixels))
        if ratio < 0.01:
            errors.append(f"{image_path}: image is nearly blank (non-white pixel ratio {ratio:.4f})")
        elif ratio < 0.05:
            warnings.append(f"{image_path}: image content is sparse (non-white pixel ratio {ratio:.4f})")
    return warnings, errors


def inspect_metrics(image_path: Path) -> tuple[int, int, float]:
    with Image.open(image_path) as img:
        rgb = img.convert("RGB")
        width, height = rgb.size
        pixels = list(rgb.getdata())
        non_white = sum(1 for pixel in pixels if pixel != (255, 255, 255))
        ratio = non_white / max(1, len(pixels))
        return width, height, ratio


def ref_metrics_for(image_path: Path, repo_root: Path) -> tuple[Path | None, tuple[int, int, float] | None]:
    stem = image_path.stem
    ref_name = REF_MAP.get(stem)
    ref_path = repo_root / "ref" / ref_name if ref_name else None
    if not ref_path or not ref_path.exists():
        return ref_path, None
    return ref_path, inspect_metrics(ref_path)


def review_prompt_for(image_path: Path, repo_root: Path) -> str:
    width, height, ratio = inspect_metrics(image_path)
    ref_path, ref_metrics = ref_metrics_for(image_path, repo_root)
    lines = [
        "AI visual review task:",
        f"1. You must load the exported preview image: {image_path}",
    ]
    if ref_path and ref_metrics:
        ref_width, ref_height, ref_ratio = ref_metrics
        lines.append(f"2. You must load the matching reference image: {ref_path}")
        lines.append(
            f"3. Current preview metrics: size {width}x{height}, non-white pixel ratio {ratio:.4f}. Reference metrics: size {ref_width}x{ref_height}, non-white pixel ratio {ref_ratio:.4f}."
        )
    else:
        lines.append("2. No matching reference image was found; compare against references/style-profiles.md and references/ref-usage.md instead.")
        lines.append(f"3. Current preview metrics: size {width}x{height}, non-white pixel ratio {ratio:.4f}.")
    lines.extend(
        [
            "4. State explicitly that you reviewed both the export and the reference before judging quality.",
            "5. Compare structure layering, grouping semantics, visual density, label language and readability, edge routing, color discipline, and overall visual order.",
            "6. Call out concrete issues such as large blank areas, unbalanced layout, weak grouping semantics, oversized labels, inconsistent colors, missing relationships, or unreadable labels.",
            "7. Prefer suggesting changes to intermediate-model fields or renderer layout rules; if suggesting edge removal, keep it minimal rather than deleting all cross-group edges.",
            "8. After changes, export again and review again; do not stop at one round of commentary.",
        ]
    )
    return "\n".join(lines)


def write_visual_review_report(target: Path, repo_root: Path, images: list[Path]) -> Path:
    report_path = target / "visual-review.md"
    lines = ["# Visual Review Checklist", ""]
    for image_path in images:
        stem = image_path.stem
        width, height, ratio = inspect_metrics(image_path)
        ref_path, ref_metrics = ref_metrics_for(image_path, repo_root)
        lines.append(f"## {stem}")
        lines.append("")
        lines.append(f"- Export: `{image_path}`")
        lines.append(f"- Reference: `{ref_path}`" if ref_path and ref_path.exists() else "- Reference: not found")
        lines.append(f"- Metrics: `{width}x{height}`, non-white pixel ratio `{ratio:.4f}`")
        if ref_metrics:
            ref_width, ref_height, ref_ratio = ref_metrics
            lines.append(f"- Reference metrics: `{ref_width}x{ref_height}`, non-white pixel ratio `{ref_ratio:.4f}`")
            lines.append(f"- Density delta: `{abs(ratio - ref_ratio):.4f}`")
        lines.append("")
        lines.append("```text")
        lines.append(review_prompt_for(image_path, repo_root))
        lines.append("```")
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect exported diagram previews for obvious failures."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="docs/architecture",
        help="Directory containing exported previews",
    )
    args = parser.parse_args()

    target = Path(args.target)
    repo_root = Path(__file__).resolve().parents[1]
    try:
        images = iter_images(target)
    except Exception as exc:
        print(f"inspect_exports.py failed: {exc}")
        return 1

    if not images:
        print(f"inspect_exports.py failed: no .png exports found in {target}")
        return 1

    all_warnings: list[str] = []
    all_errors: list[str] = []
    for image_path in images:
        warnings, errors = inspect_image(image_path)
        all_warnings.extend(warnings)
        all_errors.extend(errors)

    for warning in all_warnings:
        print(f"WARNING: {warning}")
    for error in all_errors:
        print(f"ERROR: {error}")

    report_path = write_visual_review_report(target, repo_root, images)

    print("\nSuggested AI visual review prompt:\n")
    for image_path in images:
        print(review_prompt_for(image_path, repo_root))
        print()
    print(f"Visual review report written to: {report_path}")

    if all_errors:
        print(f"Inspection failed with {len(all_errors)} error(s) and {len(all_warnings)} warning(s).")
        return 1

    print(f"Inspection passed for {len(images)} image(s) with {len(all_warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
