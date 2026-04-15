from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image
from PIL import ImageFile


ImageFile.LOAD_TRUNCATED_IMAGES = True


REF_MAP = {
    "logic-view": "逻辑视图.jpg",
    "development-view": "开发视图.jpg",
    "process-view": "运行视图.jpg",
    "physical-view": "物理视图.jpg",
    "scenario-view": "场景视图.jpg",
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
            errors.append(f"{image_path}: 图像几乎空白（非白像素占比 {ratio:.4f}）")
        elif ratio < 0.05:
            warnings.append(f"{image_path}: 图像内容过稀（非白像素占比 {ratio:.4f}）")
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
        "AI 视觉复核任务：",
        f"1. 必须加载导出的预览图：{image_path}",
    ]
    if ref_path and ref_metrics:
        ref_width, ref_height, ref_ratio = ref_metrics
        lines.append(f"2. 必须加载参考图：{ref_path}")
        lines.append(
            f"3. 当前预览指标：尺寸 {width}x{height}，非白像素占比 {ratio:.4f}。参考图指标：尺寸 {ref_width}x{ref_height}，非白像素占比 {ref_ratio:.4f}。"
        )
    else:
        lines.append("2. 未找到同名参考图，请改为对照 references/style-profiles.md 与 references/ref-usage.md。")
        lines.append(f"3. 当前预览指标：尺寸 {width}x{height}，非白像素占比 {ratio:.4f}。")
    lines.extend(
        [
            "4. 先明确说明你已经同时看过导出图和参考图，再开始判断。",
            "5. 必须逐项对比：结构分层、分组表达、画面密度、标签语言与可读性、连线走向、颜色纪律、整体视觉秩序。",
            "6. 明确指出具体问题，例如大面积空白、布局失衡、分组语义弱、标签过长、颜色不一致、缺失关系、英文泄漏或中文不可读。",
            "7. 优先给出应修改的中间模型字段或渲染器布局规则；如果建议删边，只能给出最小化删边建议，不得把所有跨组连线全部去掉。",
            "8. 修改后重新导出并再次复核，不要停在一次性评论。",
        ]
    )
    return "\n".join(lines)


def write_visual_review_report(target: Path, repo_root: Path, images: list[Path]) -> Path:
    report_path = target / "visual-review.md"
    lines = ["# 视觉复核清单", ""]
    for image_path in images:
        stem = image_path.stem
        width, height, ratio = inspect_metrics(image_path)
        ref_path, ref_metrics = ref_metrics_for(image_path, repo_root)
        lines.append(f"## {stem}")
        lines.append("")
        lines.append(f"- 导出图：`{image_path}`")
        lines.append(f"- 参考图：`{ref_path}`" if ref_path and ref_path.exists() else "- 参考图：未找到")
        lines.append(f"- 指标：`{width}x{height}`，非白像素占比 `{ratio:.4f}`")
        if ref_metrics:
            ref_width, ref_height, ref_ratio = ref_metrics
            lines.append(f"- 参考指标：`{ref_width}x{ref_height}`，非白像素占比 `{ref_ratio:.4f}`")
            lines.append(f"- 密度差值：`{abs(ratio - ref_ratio):.4f}`")
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

    print("\n建议使用的 AI 视觉复核提示词：\n")
    for image_path in images:
        print(review_prompt_for(image_path, repo_root))
        print()
    print(f"视觉复核报告已写入：{report_path}")

    if all_errors:
        print(f"Inspection failed with {len(all_errors)} error(s) and {len(all_warnings)} warning(s).")
        return 1

    print(f"Inspection passed for {len(images)} image(s) with {len(all_warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
