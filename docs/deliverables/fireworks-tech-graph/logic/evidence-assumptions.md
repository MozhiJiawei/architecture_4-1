# fireworks-tech-graph 逻辑视图证据与假设

## 核心证据

- `README.zh.md:15`：仓库目标是把自然语言描述转成 SVG 技术图，并通过 `rsvg-convert` 导出 PNG。
- `SKILL.md:85-96`：主流程是分类图类型、抽取结构、规划布局、加载风格/图标、验证、导出。
- `scripts/generate-from-template.py:29,404-410,1435-1539`：存在模板驱动、风格驱动的 SVG 生成内核，会读取模板并写出 SVG。
- `scripts/generate-diagram.sh:120-153` 与 `scripts/validate-svg.sh:269-278`：验证与导出职责独立存在，并显式依赖 `rsvg-convert`。
- `scripts/test-all-styles.sh:84-114` 与 `fixtures/*.json`：仓库有回归样例和批量测试闭环，说明质量保障是稳定职责而非临时脚本。
- `package.json:28-36`：发布物显式包含 `references/`、`scripts/`、`fixtures/`、`templates/`、`assets/`，支持把这些目录合并为知识资产/质量资产层。

## 关键假设

- “图结构规划”是逻辑职责，不是单文件模块：它主要由 `SKILL.md` 的工作流、图类型规则、形状词汇和箭头语义共同实现。
- “技能宿主”代表 Claude Code 或兼容运行时；仓库只提供 `agents/openai.yaml` 接口元数据，不包含宿主实现。
- “风格与图谱知识”合并了 style references、icons、shape vocabulary、arrow semantics，因为这些内容共同影响规划与生成，但单独拆开会把逻辑视图拖成资产清单。

## 刻意省略

- 未将 `assets/samples/`、`agentloop-core.svg`、静态徽章、许可证等展示/分发材料画入逻辑视图。
- 未将每个模板文件、每个 style 文件、每个 fixture 文件逐一建模，避免把仓库目录树直接误当架构图。
- 未渲染长跨层关系；逻辑模型优先保留稳定职责与依赖方向，而不是脚本内部的所有细部调用。

## 影响渲染的不确定点

- `diagram_planner -> svg_generator` 与 `caller -> runtime_host` 关系属于推断关系，渲染时如果想更保守，可以弱化边样式。
- 若渲染器对 `lines` 字段要求更严格的数值数组而不是字符串区间，需要在后续流水线里做一次格式适配。
