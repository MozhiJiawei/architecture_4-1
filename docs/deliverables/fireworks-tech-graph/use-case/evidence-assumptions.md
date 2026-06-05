# fireworks-tech-graph 用例视图证据与假设

## 证据

### Actor

- `技能使用者/架构师`
  - `README.zh.md:5,15`：仓库主张是“用中文描述你的系统，几秒钟得到 SVG + PNG 技术图”，直接面向描述系统并出图的人。
  - `README.zh.md:195-215`：公开了聊天式基本用法、指定风格和指定输出路径，证明主要入口面是交互式出图。
- `技能维护者`
  - `scripts/README.md:97-108,173-183`：维护者可运行 `test-all-styles.sh` 批量渲染、验证和导出回归样例。
  - `scripts/README.md:216-233`：开发说明明确允许新增验证规则、扩展图表类型。
- `AI/子Agent运行时`
  - `agents/openai.yaml:1-4`：提供兼容运行时接口元数据，默认提示词也是“把用户的系统或工作流描述转成 SVG 并导出 PNG”。

### P0 用例

- `UC01 生成架构图`
  - `README.zh.md:199,256`：显式给出 Agentic Search 架构图、微服务架构图等架构类目标。
  - `package.json:4`：包描述直接包含 architecture。
- `UC02 生成流程时序图`
  - `README.zh.md:273`：显式给出 OAuth2 授权码流程的序列图。
  - `package.json:4`：包描述直接包含 flowchart、sequence。
- `UC03 生成 AI/Agent 图`
  - `README.zh.md:15`：明确覆盖 RAG、Agentic Search、Mem0、Multi-Agent、Tool Call。
  - `README.zh.md:195,199`：给出 RAG 流程图与 Agentic Search 架构图入口。
- `UC04 生成 UML 图`
  - `README.zh.md:125`：明确“完整支持全部 UML 图类型”。
  - `SKILL.md:186-198`：单独定义 Use Case Diagram (UML) 等 UML 图布局规则。
  - `templates/use-case.svg`：仓库包含 UML 用例图模板。
- `UC05 生成对比概念图`
  - `README.zh.md:290`：显式给出 RAG vs Fine-tuning vs Prompt Engineering 的功能对比图。
  - `README.zh.md:302`：显式给出 AI Agent 核心能力地图。

### P1 用例

- `UC11 安装升级 Skill`
  - `README.zh.md:139-153`：公开安装与升级命令。
- `UC12 配置风格输出`
  - `README.zh.md:205,215`：显式支持指定风格与输出路径。
  - `scripts/README.md:35-52`：`generate-diagram.sh` 暴露 `-s/-o/-w` 参数。
- `UC13 模板生成 SVG`
  - `SKILL.md:49-55`：主 skill 推荐 `generate-from-template.py`。
  - `scripts/README.md:57-95`：脚本接受模板类型、输出 SVG 路径和 JSON 结构数据。
- `UC14 校验导出 PNG`
  - `SKILL.md:41-47,57-59`：主 skill 推荐 `generate-diagram.sh` 与 `validate-svg.sh`。
  - `scripts/README.md:7-26,165-170`：显式给出“验证现有 SVG”和“生成并验证图表”场景。
  - `README.zh.md:131`：仓库承诺 SVG + PNG 双输出。

### P2 用例

- `UC21 批量回归测试`
  - `scripts/README.md:97-108,173-183`：说明会读取 `fixtures/*.json`，验证 SVG，并导出 PNG 与测试报告。
- `UC22 扩展治理规则`
  - `scripts/README.md:216-233`：明确允许新增验证规则与扩展支持的图表类型。

## 关键假设

- 仓库公开入口以 README、SKILL、脚本文档为主，因此用例按“用户目标 + 入口面”归并，而不是按内部函数或渲染步骤拆分。
- `AI/子Agent运行时` 已有元数据入口，但缺少更完整的自动化编排示例；因此它作为多项 P0 用例的次要参与者，而不是单独拆成新的核心业务用例。
- “架构图”“流程时序图”“AI/Agent 图”“UML 图”“对比概念图”之间存在能力重叠，但它们在 README 和包描述里都作为对外可感知的一级目标出现，所以保留为独立 P0 行。
- `generate-diagram.sh` 只负责验证与导出，不负责生成 SVG 内容；所以把模板生成与校验导出拆成两个 P1 用例。

## 刻意省略

- 没把 `references/*.md` 的风格 token、形状词汇表、箭头语义拆成单独用例，因为它们是生成规则，不是最终用户目标。
- 没把 `fixtures/*.json` 的每个样例图单独列成用例，因为它们是回归资产，不是独立业务能力。
- 没把 `validate-svg.sh` 内部的 XML、marker、碰撞等单项检查拆分成用例，因为它们属于校验实现细节。
