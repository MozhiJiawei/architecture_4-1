# fireworks-tech-graph development 视图证据与假设

## 证据摘要

- `package.json`：给出 npm 包名、`main=SKILL.md`、`files` 白名单与 Node 版本约束，说明仓库是“可分发技能包”而不是常规应用。
- `SKILL.md`：定义标准工作流，明确要求加载 style 参考、`icons.md`、执行验证和 PNG 导出，并推荐使用 `scripts/` 下的四个脚本。
- `agents/openai.yaml`：提供运行时入口元数据，证明 `agents/` 不是随手附带的文档目录，而是兼容运行时的适配面。
- `scripts/generate-from-template.py`：是核心生成器，内置 `STYLE_PROFILES`，读取 `templates/`，消费 `nodes/arrows/legend` 结构并写出 SVG。
- `scripts/generate-diagram.sh` 与 `scripts/README.md`：把校验与 PNG 导出组织成稳定交付链路，并显式依赖 `rsvg-convert`。
- `references/style-diagram-matrix.md` 与 `references/icons.md`：构成视觉基线，分别约束图型与风格匹配、图标/语义形状词汇。
- `templates/architecture.svg`：说明模板库不是素材堆，而是带固定插槽的骨架。
- `fixtures/system-architecture-style6.json` 与 `scripts/test-all-styles.sh`：一起证明 `fixtures/` 是回归输入集合，`test-all-styles.sh` 是批量质量门。
- `assets/samples/*.png`：是 README 展示和人工审阅时的成品基线，因此保留为单独模块而不是完全忽略。

## 关键假设

- `SKILL.md + README + agents/openai.yaml` 被维护者当作同一类“入口契约”，因此合并为“技能入口契约”模块。
- `scripts/generate-from-template.py` 虽然体量很大，但维护者通常会把它当作单一生成引擎维护，而不是按内部绘图函数分模块维护。
- `fixtures/` 的 JSON 结构与 `templates/`、`references/` 的关系主要由字段约定驱动，不需要再细拆成每种图型一个模块。
- `assets/samples/` 主要服务展示和人工比对，不是强约束的自动化依赖，所以在图中保留为弱连接的独立质量资产。

## 刻意省略

- 省略 `node_modules`、未来导出的 `.svg/.png`、`test-output/`、缓存、日志等非维护单元。
- 省略每个风格文件、每个模板文件、每个夹具文件之间的一对一关系，避免开发视图退化成目录树。
- 省略 `validate-svg.sh` 内部各项检查规则、`generate-from-template.py` 内部节点绘制函数等实现细节。

## 剪枝决定

- 把 `references/` 折叠为“风格与图标规范”，因为对维护者更重要的是“视觉词汇表与选型规则”这一职责，而不是 10 个文档文件名。
- 把 `templates/` 折叠为“SVG 模板库”，因为模板文件共享同一种骨架职责。
- 把 `fixtures/` 折叠为“回归样例库”，只用一个代表性 JSON 文件作证据。
- 没有把 `package.json` 画成全局中心节点；它更像分发边界，而不是真正驱动业务能力的实现核心。

## 会影响渲染的注意点

- `showcase-assets` 与其他模块没有显式代码依赖边，只作为独立资产模块存在；如果渲染器强依赖连通图，可能需要在后续版本中增加一条“展示引用”关系。
- `batch-regression -> export-pipeline` 这条边是半推断：脚本直接调用 `validate-svg.sh` 和 `rsvg-convert`，并未直接调用 `generate-diagram.sh`；当前用“复用校验逻辑并串接 PNG 导出”来表达这一开发依赖。
