# dynamo-main 交付件

这个 case 分析的是推理服务相关仓库，重点展示低延迟推理、分离式推理、KV cache 路由、长上下文卸载、SLA 自动扩缩、启动和恢复路径等能力。

输入是一整个目标仓库。目标是把复杂推理系统整理成用户能力、系统职责、代码维护视角和运行路径四类架构材料。

## 目录

- `use-case/`：用户能力图和能力目录。
- `logic/`：系统职责图。
- `development/`：代码维护视角图。
- `runtime/`：共享缓存启动、ModelExpress 启动和 Checkpoint 热恢复路径。

每个视图目录通常包含：

- `*.json`：中间模型。
- `*.drawio`：可编辑 draw.io 图。
- `*.png`：文档预览图。
- `evidence-assumptions.md`：证据、假设和省略说明。
