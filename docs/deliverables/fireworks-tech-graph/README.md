# fireworks-tech-graph 交付件

这个 case 分析的是一个“用自然语言生成技术图”的 Skill 仓库。

输入是一整个目标仓库：README、`SKILL.md`、`scripts/`、`templates/`、`references/` 和 `fixtures/`。目标是把它整理成 3+1 / 4+1 架构视图，并交付可编辑图和预览图。

## 目录

- `use-case/`：用户能力图和能力目录。
- `logic/`：系统职责图。
- `development/`：代码维护视角图。
- `runtime/`：四条运行路径图。
- `package/`：本次运行打包归档。

每个视图目录通常包含：

- `*.json`：中间模型。
- `*.drawio`：可编辑 draw.io 图。
- `*.png`：文档预览图。
- `evidence-assumptions.md`：证据、假设和省略说明。
