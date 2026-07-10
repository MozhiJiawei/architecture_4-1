# 使用方式

## 适用场景

当用户希望从一个源码仓库生成架构图时使用本 Skill。可以生成逻辑视图、开发视图、运行视图或用例视图，也可以从已有中间 JSON 重新渲染 `.drawio` 和 PNG 预览。

## 可复制 Prompt

完整多视图任务必须为每个请求的视图启动一个专属视图 owner 子 Agent。请在任务中明确授权启动子 Agent；主 Agent 仍负责监督、渲染、验证和最终交付。可直接复制下面的中文 prompt，并替换尖括号占位符：

```text
请使用 generate-3plus1-diagrams 分析仓库 <workspace 根目录下的目标仓库路径>，围绕 <核心用例或业务问题> 生成逻辑视图、开发视图、运行视图和用例视图，图中文字与证据说明使用中文。

我允许你按 Skill 规范启动子 Agent：每个请求的视图启动且只启动一个专属视图 owner 子 Agent。子 Agent 只负责分析自己拥有的视图，并把 <view>-view.json 和 evidence-assumptions.md 写入 workspace 根目录下的 .tmp/generate-3plus1-diagrams/<repo-name>/<view>/；主 Agent 负责监督、跨视图复核、渲染、导出、验证和最终交付。

请忽略 generated、vendor、cache 和实验输出。最终交付每个视图的中间 JSON、证据/假设说明、可编辑 .drawio、PNG 预览和验证结果；明确事实、推断、刻意省略与仍未解决的不确定性。
```

只请求单个视图时，可把第一段改为“只生成 `<逻辑/开发/运行/用例>` 视图”。即使只请求一个视图，也需要允许为该视图启动一个专属 owner 子 Agent。

## 输入材料

最小输入是目标仓库路径和需要生成的视图。若用户没有指定视图，应先确认是否需要完整 3+1 / 4+1 交付。建议同时说明：

- 用户关心的核心用例或业务问题。
- 需要忽略的目录，例如 generated、vendor、cache、实验输出。
- 目标语言；中文任务默认使用中文标签和说明。
- 是否同时需要 PNG 预览和打包交付。

## 输出与临时目录

所有中间稿和交付物默认放在 **workspace 根目录**下，而不是 Skill 子仓或目标仓库源码目录：

```text
.tmp/generate-3plus1-diagrams/<repo-name>/<view>/
```

每个视图目录通常包含：

- `<view>-view.json`：中间模型。
- `evidence-assumptions.md`：证据、假设、遗漏和剪枝说明。
- `<view>-view.drawio`：可编辑 draw.io 文件。
- `exports/*.png`：导出预览。
- `exports/visual-review.md`：视觉审阅辅助信息。

用例视图会额外产出 `use-case-catalog-view.drawio` 及其 PNG；运行视图可能按 primary path 产出多张 `.drawio` 和 PNG。

## 推荐流程

1. 主 Agent 读取 `skills/architecture_4-1/SKILL.md`、相关规则和参考图。
2. 每个请求视图由唯一的 owner 子 Agent 分析目标仓库，产出 JSON 和 `evidence-assumptions.md`。
3. 主 Agent 检查证据、假设、遗漏和跨视图一致性；有缺口时让对应 owner 定向补查。
4. 主 Agent 使用统一脚本渲染 `.drawio`、导出 PNG，并运行结构与视觉管线检查。
5. 主 Agent 对照 `skills/architecture_4-1/ref/` 完成视觉复核后交付。

## 常用命令

以下命令都从 **workspace 根目录**运行。示例假定模型位于 workspace 根目录的 `.tmp/`；请替换 `<repo>`、`<view>` 占位符。

渲染单个中间模型并导出 PNG：

```powershell
python skills/architecture_4-1/scripts/render_drawio.py .tmp/generate-3plus1-diagrams/<repo>/<view>/<view>-view.json --output-dir .tmp/generate-3plus1-diagrams/<repo>/<view> --export-previews --preview-dir .tmp/generate-3plus1-diagrams/<repo>/<view>/exports --preview-format png
```

验证单个 `.drawio`：

```powershell
python skills/architecture_4-1/scripts/tools/validate_drawio.py .tmp/generate-3plus1-diagrams/<repo>/<view>/<view>-view.drawio
```

运行完整视觉管线（校验、重新导出、检查预览）：

```powershell
python skills/architecture_4-1/scripts/tools/validate_visual_pipeline.py .tmp/generate-3plus1-diagrams/<repo>/<view>/<view>-view.drawio --exports-dir .tmp/generate-3plus1-diagrams/<repo>/<view>/exports
```

单独导出已有图：

```powershell
python skills/architecture_4-1/scripts/tools/export_diagrams.py .tmp/generate-3plus1-diagrams/<repo>/<view>/<view>-view.drawio --output-dir .tmp/generate-3plus1-diagrams/<repo>/<view>/exports --format png
```

## 完成标准

- 每个请求视图都有 JSON、证据说明、所有应有的 `.drawio` 和 PNG。
- 用例视图同时具备用例目录表和全量用例图；运行视图的每条主要路径均已交付。
- `evidence-assumptions.md` 明确区分事实、推断、刻意省略和未解决的不确定性。
- 每个 `.drawio` 都通过验证与视觉管线；PNG 非空、标签可读、布局不过密。
- 逻辑视图讲职责，开发视图讲维护边界，运行视图讲运行协作，用例视图讲 actor 与用户目标。
- 主 Agent 已把导出图与对应 `skills/architecture_4-1/ref/` 视觉基线进行比较。
