# UC06“快速启动副本”逻辑视图证据与假设

## 范围

- 只分析 Dynamo 仓库中与 UC06“快速启动副本”直接相关的稳定职责边界。
- 只输出 logic view 中间模型，不渲染 draw.io，不写最终总结。

## 关键证据归并

1. 部署入口与启动编排
   - `README.md` 将“新副本快速冷启动”列为 Dynamo 的适用场景。
   - `deploy/operator/api/v1alpha1/common.go` 把 checkpointRef / identity 做成服务级声明能力。
   - `deploy/operator/api/v1beta1/dynamographdeploymentrequest_types.go` 把 model cache 做成 DGDR 的正式配置项。

2. 模型供给与共享缓存
   - `docs/kubernetes/model-caching.md` 给出两条加速路径：共享 PVC + download job，以及 ModelExpress。
   - `deploy/operator/internal/controller/dynamographdeploymentrequest_controller.go` 说明 operator 会把 model cache PVC 挂入生成对象。
   - `deploy/operator/internal/dynamo/graph.go` 与 `lib/runtime/src/config/environment_names.rs` 说明 ModelExpress 通过 `MODEL_EXPRESS_URL` 接入组件 pod。

3. Snapshot / Checkpoint 恢复
   - `docs/kubernetes/snapshot.md` 说明 `DynamoCheckpoint` + `checkpointRef`/`mode: Auto` 是快速恢复 worker 的主路径。
   - `deploy/operator/api/v1alpha1/dynamocheckpoint_types.go` 给出 checkpoint 的 identity、job、phase、identityHash 等编目字段。
   - `components/src/dynamo/common/utils/snapshot.py` 说明 worker 内存在明确的 quiesce / ready / restore 生命周期控制。

4. 前端模型引导与可服务化
   - `docs/components/frontend/README.md` 说明 frontend 需要 `config.json`、`tokenizer.json` 等模型配置文件，并建议复用共享目录避免重复下载。
   - 同一文档说明 backend 在调用 `register_model` 后会被 frontend 自动发现。
   - `components/src/dynamo/common/backend/README.md` 说明统一 worker 会在引擎启动后注册模型。

## 主要假设

- `启动编排器` 作为逻辑元素，综合代表 operator/controller 对 `modelCache`、`checkpoint`、`MODEL_EXPRESS_URL` 等启动加速机制的编排职责；这不是单一文件或单一控制器名称，因此属于基于多处证据的抽象。
- `Checkpoint 编目` 与 `快照卷` 被拆成两个逻辑元素：前者表示由 `DynamoCheckpoint` CR 和 identity/status 驱动的命名与生命周期管理，后者表示实际 checkpoint 数据所在的共享存储。
- `前端引导` 被单列为稳定能力边界，而不是 frontend 全体职责；这里只保留与模型配置可得性、模型发现和副本就绪相关的部分。

## 明确不确定性

- ModelExpress 的核心分发实现不在当前仓库；因此图中把它标成 `external`，只保留本仓库已经明确暴露的接入边界。
- 当前证据没有明确说明 frontend 会直接从 ModelExpress 获取配置文件，所以没有建立 `ModelExpress -> 前端引导` 的直接关系。
- `部署声明 -> 启动编排器`、`启动编排器 -> 推理副本`、`Checkpoint 编目 -> 快照卷` 这些关系是从 CRD、controller 和文档流程合并得到的逻辑抽象，已在 JSON 中标记 `inferred: true`。

## 重要省略

- 不展开 worker 内部具体引擎类、下载脚本实现细节、placeholder image 构建细节、snapshot-agent 守护进程细节。
- 不展开与 UC06 无直接必要关系的路由、规划、KV cache、故障恢复、多模态或基准测试路径。

## 输出文件

- `D:\Agent Repo\Mozhi-s-AgentWorkspace\.tmp\generate-3plus1-diagrams\dynamo-main\logic\logic-view.json`
- `D:\Agent Repo\Mozhi-s-AgentWorkspace\.tmp\generate-3plus1-diagrams\dynamo-main\logic\evidence-assumptions.md`
