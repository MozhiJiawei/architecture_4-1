# 架构概览

`generate-3plus1-diagrams` 是一个多 Agent 架构建模与制图 Skill。它的**输出图类型**是逻辑、开发、运行和用例视图；它自身的**工作架构**则由视图 owner 子 Agent、中间 JSON 契约、统一渲染/导出脚本和验证审阅环节组成。两者不能混为一谈。

## 输出图类型

| 输出视图 | 回答的问题 | 不应退化为 |
| --- | --- | --- |
| 逻辑视图 | 系统有哪些稳定职责、业务域、子系统、外部系统及依赖方向？ | 源码目录树或 helper 清单 |
| 开发视图 | 开发者维护哪些 package、module、shared library 和 ownership/layering 边界？ | 运行时调用时序 |
| 运行视图 | 请求、异步任务、队列、缓存、状态与外部系统如何在关键路径中协作？ | 静态 package 依赖图 |
| 用例视图 | actor 通过哪些入口实现哪些用户目标，哪些能力属于 P0/P1/P2？ | 内部组件图或逐步运行编排 |

用例视图是 4+1 中连接其他视图的“+1”。用户只请求部分视图时，Skill 只交付被请求的视图；完整多视图任务则为每个视图保留独立 owner 和独立中间模型。

## 逻辑视图：Skill 的核心概念与边界

Skill 接收目标仓库、请求的视图、核心用例、语言与忽略范围，输出中间 JSON、证据/假设说明、可编辑 `.drawio`、PNG/SVG 预览和验证结果。

核心模块分为四层：

1. **视图建模层**：各 view owner 子 Agent 阅读目标仓库，用证据建立本视图 JSON，并记录假设、推断、遗漏和剪枝。
2. **模型契约层**：`references/drawio-dsl.md` 定义共享 JSON schema，各 view pattern 定义视图专属约束。JSON 是子 Agent 到主 Agent 的正式交接物。
3. **生成层**：`scripts/render_drawio.py` 负责布局求解、模型校验、生成 `.drawio`、draw.io XML 校验，并可继续导出预览。
4. **验收层**：视觉管线负责 XML 校验、真实 draw.io 导出和预览检查；主 Agent 负责证据、跨视图一致性与参考图视觉复核。

边界上，AI 负责理解仓库和作出架构判断；脚本只负责确定性的布局、渲染、导出与校验，不替代架构分析。临时产物统一写入 workspace 根目录的 `.tmp/generate-3plus1-diagrams/<repo-name>/<view>/`，不写回目标仓库源码目录或 Skill 子仓。

## 运行视图：从 Prompt 到交付

一次正常执行沿以下路径进行：

```text
用户 Prompt
  → 主 Agent 明确范围、读取 Skill 规则与视觉基线
  → 每个请求视图启动一个且仅一个 view owner 子 Agent
  → 子 Agent 调查目标仓库并交接 <view>-view.json + evidence-assumptions.md
  → 主 Agent 审核证据、假设、遗漏与跨视图一致性，必要时要求 owner 定向补查
  → render_drawio.py：布局求解 → JSON 模型校验 → 生成 .drawio → XML 校验
  → draw.io webapp + Playwright：导出 PNG/SVG
  → validate_visual_pipeline.py：校验 .drawio → 重新导出 → 检查预览
  → 主 Agent 对照 ref/ 做视觉复核并交付全部产物与未解决不确定性
```

用例模型可能派生用例目录表和全量用例图；运行模型可能按 primary path 派生多张图。因此“一个 JSON”不一定只对应一个 `.drawio`。

## 开发视图：目录与资料分层

| 路径 | 职责 |
| --- | --- |
| `SKILL.md` | Agent 执行契约、委派规则、完成标准和整体工作流。 |
| `references/` | JSON DSL、渲染器契约、通用规则、样式、参考图使用规则和各视图建模策略。 |
| `ref/` | 只读视觉基线；用于接受前比较，不是待补齐的交付目录。 |
| `scripts/render_drawio.py` | 统一视图入口：布局、模型校验、渲染、XML 校验和可选预览导出。 |
| `scripts/views/` | 逻辑、开发、运行、用例视图各自的模型校验、布局与渲染实现。 |
| `scripts/tools/` | `.drawio` 校验、真实 draw.io 导出和导出结果检查。 |
| `docs/` | 面向用户发布的能力展示、使用方式、依赖说明和本架构概览。 |
| `tests/` | 渲染与校验实现的回归测试，不是用户任务的交付物。 |

## 多 Agent 与 Checker 边界

### 主 Agent

- 读取相关规则和 `ref/` 视觉基线，拆分用户请求并为每个视图指派唯一 owner。
- 不在默认流程中代替子 Agent 阅读源码做实质架构分析；发现证据缺口时，让对应 owner 定向补查。
- 审核 JSON 与证据说明，检查跨视图矛盾，统一执行渲染、导出、验证和最终视觉复核。
- 不修改、补画或再生成 `ref/` 参考图，也不把脚本检查通过当作架构判断正确。

### View owner 子 Agent

- 只负责被分配的一个视图，并在独立 `.tmp/.../<view>/` 目录工作。
- 从目标仓库收集可追踪证据，区分事实与推断，明确假设、遗漏和剪枝。
- 只交接 `<view>-view.json` 与 `evidence-assumptions.md`；默认不负责渲染、导出、验证或最终总结。
- 同一视图同时只能有一个 active owner，不能与其他 owner 混写同一模型。

### 自动 Checker 与人工 Reviewer

- `render_drawio.py` 内置的模型和 XML 校验负责结构性约束。
- `validate_visual_pipeline.py` 顺序调用 `.drawio` 校验、真实导出和预览检查；它不能判断架构证据是否充分，也不能证明图的业务含义正确。
- 最终 reviewer 是主 Agent：检查证据质量、跨视图一致性、导出可读性并对照 `ref/`。当前契约没有把独立 checker 子 Agent 设为必需角色；若用户另行要求独立复核，其角色仍只做审阅，不接管 view owner 的建模职责。

## 关键参考

- `references/drawio-dsl.md`：中间 JSON 模型的 schema 权威来源。
- `references/renderer-contract.md`：渲染器支持的 view、kind、alias 和默认行为。
- `references/3plus1-rules.md` 与 `references/view-checklists.md`：四类输出视图的共同规则和检查表。
- `references/logic-view-patterns.md`、`development-view-patterns.md`、`runtime-view-patterns.md`、`use-case-view-patterns.md`：各视图建模策略。
- `references/style-profiles.md` 与 `references/ref-usage.md`：视觉样式和只读参考图的使用边界。
