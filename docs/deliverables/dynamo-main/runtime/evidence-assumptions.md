# UC06 运行视图证据与假设

## 产物

- `D:\Agent Repo\Mozhi-s-AgentWorkspace\.tmp\generate-3plus1-diagrams\dynamo-main\runtime\runtime-view.json`
- `D:\Agent Repo\Mozhi-s-AgentWorkspace\.tmp\generate-3plus1-diagrams\dynamo-main\runtime\evidence-assumptions.md`

## 建模范围

- 只覆盖 UC06“快速启动副本”。
- 只建模能显著缩短新副本进入可服务状态的运行协作。
- 不展开常规推理请求、router 细节、planner/autoscaling、NATS/etcd 控制流。

## 采用的主运行路径

1. 共享 PVC + 下载任务路径  
   证据主轴：`docs/kubernetes/model-caching.md`、`benchmarks/frontend/dgd/templates/vllm-gpt-oss-20b.yaml`、`docs/components/frontend/README.md`

2. Model Express 启动路径  
   证据主轴：`docs/kubernetes/model-caching.md`、`README.md`、`deploy/operator/internal/dynamo/graph.go`、`deploy/operator/api/config/v1alpha1/types.go`

3. Snapshot / DynamoCheckpoint 热恢复路径  
   证据主轴：`docs/kubernetes/snapshot.md`、`deploy/helm/charts/snapshot/README.md`、`deploy/operator/api/v1alpha1/common.go`、`deploy/operator/internal/checkpoint/checkpoint_test.go`、`deploy/operator/config/samples/nvidia.com_v1alpha1_dynamocheckpoint.yaml`

## 关键证据摘记

- `README.md:41`  
  仓库级目标明确包含 “fast cold-starts when spinning up new replicas”。

- `docs/kubernetes/model-caching.md:12`  
  推荐路径是“共享 PVC + 一次性下载 Job + 在 DGD 中挂载 PVC”。

- `docs/kubernetes/model-caching.md:92`  
  worker 可直接从共享 cache 读取，frontend 也可以复用同一 PVC 读取 tokenizer/config。

- `docs/kubernetes/model-caching.md:120-144`  
  Model Express 路径由服务端缓存权重、worker 以 `mx-source` / `mx-target` 装载、operator 注入 `MODEL_EXPRESS_URL` 构成。

- `docs/components/frontend/README.md:46-50`  
  frontend 只需要模型配置文件，不需要权重；默认会下载这些文件，且推荐使用 modelexpress-server 与共享 PVC 减少重复下载。

- `lib/bindings/c/src/lib.rs:1426-1493`  
  frontend bootstrap 相关代码会先经 discovery 找 model card，再 `download_config()` 拉取 tokenizer/config，说明 frontend 启动就绪与模型元数据可达性直接相关。

- `deploy/operator/internal/dynamo/graph.go:953-956`  
  operator 确实在生成 pod 环境时注入 `MODEL_EXPRESS_URL`。

- `docs/kubernetes/snapshot.md:9-18`  
  Snapshot 的标准路径是：先启动一次 worker 并 checkpoint，存入 snapshot volume，后续 worker 再从 checkpoint restore。

- `docs/kubernetes/snapshot.md:184-218`  
  DGD 可以显式通过 `checkpointRef` 恢复 worker。

- `docs/kubernetes/snapshot.md:226-275`  
  `mode: Auto` 会基于 identity hash 复用已有 `DynamoCheckpoint`，缺失时才创建新的 checkpoint。

- `docs/kubernetes/snapshot.md:410`  
  checkpoint 只有在 `snapshot-agent` 验证内容后才会变成 Ready。

## 关键假设与推断

### 明确标记为 inferred 的边

- `DGD -> Frontend/Worker 启动`  
  文档与模板都表明 DGD 定义 frontend / worker 组件，但具体“启动时序”不是代码里逐行展开的运行序列，因此边保留为运行语义上的推断。

- `Model Express -> Worker 分发权重`  
  Dynamo 仓库文档确认 P2P 分发目标与 load format，但服务端实现位于外部仓库 `ai-dynamo/modelexpress`，所以具体传输 hop 标为推断。

- `Worker -> Snapshot Agent 触发检查点`、`Snapshot Agent -> Worker 恢复进程`  
  Snapshot 文档与子系统代码能确认 agent 执行 checkpoint/restore、checkpoint Ready 受 agent 确认影响，但缺少一个在当前范围内足够稳定且高层的单文件直接描述完整 hop，因此保守标为推断。

- `Frontend -> Worker 发现已恢复模型`  
  这是由 frontend bootstrap 的 discovery 流与 snapshot 恢复后的 worker 可用性拼接出的运行关系，当前没有单一文件把这条边写成一句话。

### 主要不确定性

1. Model Express 的服务端行为不在本仓库内，无法进一步细化其内部缓存与网络传输阶段。  
2. frontend 挂载共享 PVC 在文档中是推荐做法、在 benchmark 模板中有实例，但不等于所有 operator 生成的部署都会默认这样做。  
3. snapshot 底层恢复涉及 `snapshot-agent`、`nsrestore`、CRIU、`cuda-checkpoint` 等低层流程；为保证 runtime 视图可读性，当前只保留 checkpoint 生命周期与存储边界。  
4. `tests/dgdr/README.md` 更适合作为行为佐证，不作为运行参与者证据本体。

## 有意省略

- 普通 `/v1/chat/completions` 请求处理链路
- KV-aware routing 与前后端消息面
- profiler / planner 选型流程
- 具体后端框架内部的权重装载微步骤
- docs/tests/examples 自身作为参与者
