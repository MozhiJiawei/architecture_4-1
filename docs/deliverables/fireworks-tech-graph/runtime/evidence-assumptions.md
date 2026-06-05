# fireworks-tech-graph 运行视图证据与假设

## 证据摘要

- `SKILL.md:3-8,85-96,401-405`：给出 skill 的触发入口、工作流顺序，以及 SVG/PNG 的输出规则。
- `agents/openai.yaml:1-4`：说明存在一个上层技能宿主入口，但宿主实现不在本仓库。
- `scripts/generate-from-template.py:28-40,1524-1540`：确认模板生成器会读取 `templates/`，接收 JSON 输入，并把 SVG 写到目标路径。
- `scripts/generate-diagram.sh:96-151`：确认导出脚本只消费已有 SVG，先校验，再调用 `rsvg-convert` 导出 PNG。
- `scripts/validate-svg.sh:13-28,30-80,240-279`：确认校验器以现有 SVG 为输入，执行静态检查、箭头碰撞检查与渲染级验证。
- `scripts/test-all-styles.sh:14-25,35-117`：确认批量测试会创建 `test-output/`，筛选 `fixtures/*.json`，逐个渲染、校验并导出 PNG。
- `fixtures/mem0-style1.json:1-8` 与 `templates/architecture.svg:1-23`：证明 fixtures 是模板化生成输入，templates 是被加载的静态骨架。

## 关键假设

- “技能运行时”作为参与者保留，是因为仓库通过 `SKILL.md` 和 `agents/openai.yaml` 明确声明了触发方式与默认 prompt；但它属于仓库外宿主，内部调度细节按黑盒处理。
- “模板与风格资源包”被折叠为单一参与者，汇总 `templates/`、`references/style-*.md`、`references/icons.md` 等静态资源，避免把纯静态文件拆成多条弱价值泳道。
- “图表输出目录”与“回归测试输出目录”分开建模，是为了清楚区分用户指定/默认输出路径与脚本内部 `test-output/` 的状态边界。
- `generate-diagram.sh` 不被视作 SVG 生成者；它的生命周期责任是参数解析、风格文件检查、调用校验器与调用 `rsvg-convert`。

## 刻意省略

- `assets/samples/` 展示 PNG、README 大段营销说明、许可证与 npm 元数据。
- 各种未在主路径中直接起作用的 UML 细节与样例内容。
- `templates/` 目录中每一种模板的具体 SVG 结构差异；运行视图只需表达“模板被读取并参与生成”。
