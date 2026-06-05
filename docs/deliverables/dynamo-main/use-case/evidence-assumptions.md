# Dynamo use-case 证据与假设

## 范围

- 本交付只覆盖 `use-case` 视图。
- 建模对象是仓库 `D:\Agent Repo\Insight-Repos\dynamo-main` 暴露给用户或平台使用者的能力目录，不展开 logic/runtime/development。
- 依据用户要求，凡是 **可直接被平台使用者启用且结果可直接体现在吞吐、TTFT、ITL、冷启动时间、请求连续性或多模态处理时延上的能力**，尽量归为 `P0`。

## actor 取舍

- `推理调用方`：直接调用 OpenAI-compatible / KServe / `/v1/videos` 等接口的应用或上层系统。
- `平台使用者`：部署、调优、选型和启用加速能力的人，通常通过 DGDR、DGD、recipes、examples、AIC CLI、gateway config 等入口操作 Dynamo。
- `平台运维者`：负责监控、诊断和持续运营的人。

之所以没有继续拆成 “Agent 框架开发者 / Kubernetes 管理员 / Benchmark 工程师” 等更细角色，是为了让后续 grouped all-use-cases 渲染保持稳定、简洁，不把 use-case 图做成组织架构图。

## P0 判定规则（本次执行版）

本次采用以下更严格但偏向用户要求的判定：

1. 如果能力是面向请求路径或部署决策的第一类能力，并且开启后用户能直接感受到更低 TTFT、更高吞吐、更快启动、更少 SLA breach、更少故障中断，则按 `P0`。
2. 如果能力主要是为 `P0` 提供模型、缓存、镜像、PVC、checkpoint 等“供给/铺底”能力，而不是终端目标本身，则按 `P1`。
3. 如果能力主要用于观测、治理、维护与排障，则按 `P2`。

因此：

- `最优配置搜索`、`分离式推理`、`KV复用路由`、`长上下文卸载`、`快速启动副本`、`SLA自动扩缩`、`拓扑就近调度`、`请求迁移续跑`、`优先请求优先响应`、`重复图像复用`、`多模态分层推理`、`视频生成加速`、`Draft协同部署`、`多模态KV路由`、`下一轮预热`、`高优先级缓存保活`、`子代理固定会话` 都被保留为 `P0`。
- `共享模型供给` 被降为 `P1`，因为它更像加速基础设施。
- `性能与迁移观测` 被降为 `P2`，因为它直接服务运行维护。

本轮扩展后，原先过于打包的 `UC10 代理提示加速` 被拆成更细的 agentic `P0` 条目：

- `UC10 优先请求优先响应`
- `UC18 下一轮预热`
- `UC19 高优先级缓存保活`
- `UC20 子代理固定会话`

同时新增独立的 `UC17 多模态KV路由`，不再把它隐含在普通 KV-aware routing、embedding cache 或多模态分层推理里。

## 关键证据映射

### UC01 低延迟推理

- 证据：
  - [docs/components/frontend/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\frontend\README.md) 7-28 行给出 OpenAI-compatible HTTP、KServe gRPC、`/v1/videos/generations`、integrated KV-aware routing 与 `nvext`。
  - [docs/components/frontend/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\frontend\README.md) 44-49 行说明统一 frontend 负责 routing，并推荐与 ModelExpress / shared PVC 配合。
  - [docs/kubernetes/inference-gateway.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\kubernetes\inference-gateway.md) 11-17 行说明网关层也可走 token-aware KV 路由。
- 说明：
  - 我没有把“OpenAI-compatible”本身当作加速特性，而是把它作为所有加速路径可被直接消费的第一类入口面。

### UC02 最优配置搜索

- 证据：
  - [README.md](D:\Agent Repo\Insight-Repos\dynamo-main\README.md) 88-95 行把 `AIConfigurator` 与 `DGDR` 直接描述为自动找优和 zero-config deploy。
  - [docs/getting-started/introduction.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\getting-started\introduction.md) 107-117 行写明 AIConfigurator 可在 30 秒内找出最优配置，并原生接入 DGDR。
  - [docs/components/profiler/profiler-guide.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\profiler\profiler-guide.md) 9-11、59-66、78-88 行明确 rapid/thorough、AIC picking 与 DGD generation。
  - [docs/kubernetes/dgdr.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\kubernetes\dgdr.md) 19-27、95-104 行把 DGDR 定义为 deploy-by-intent。
- 说明：
  - 这里的 use case 名称不是 “AIConfigurator” 或 “Profiler”，而是用户目标“最优配置搜索”。

### UC03 分离式推理

- 证据：
  - [README.md](D:\Agent Repo\Insight-Repos\dynamo-main\README.md) 83 行与 96 行。
  - [docs/design-docs/disagg-serving.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\design-docs\disagg-serving.md) 7-15 行解释 prefill/decode 分离的性能动机。
  - [recipes/qwen3-32b/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\recipes\qwen3-32b\README.md) 132-140 行把 ITL 改善与 prefill injection 隔离直接对应起来。
- 说明：
  - 该 use case 只保留用户能理解的目标，不展开 PrefillRouter、KV transfer metadata 等内部实现。

### UC04 KV复用路由

- 证据：
  - [README.md](D:\Agent Repo\Insight-Repos\dynamo-main\README.md) 84 行。
  - [docs/components/router/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\router\README.md) 7-25 行。
  - [recipes/qwen3-32b/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\recipes\qwen3-32b\README.md) 39-40、132-140 行。
  - [docs/kubernetes/inference-gateway.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\kubernetes\inference-gateway.md) 11-17 行。
- 说明：
  - 网关插件没有单列成独立 use case，因为核心用户目标仍然是“让请求命中更有利的 KV 路径”；只是在 `entry_surfaces` 里保留 Gateway。

### UC05 长上下文卸载

- 证据：
  - [README.md](D:\Agent Repo\Insight-Repos\dynamo-main\README.md) 85、99 行。
  - [docs/getting-started/introduction.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\getting-started\introduction.md) 91、98-100 行。
  - [docs/components/kvbm/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\kvbm\README.md) 16-27 行。
- 说明：
  - 这里把 KVBM、storage-tier offload、cluster-wide KV visibility 合并成“长上下文卸载”，因为用户看到的是上下文能力和时延收益，而不是内部 block lifecycle。

### UC06 快速启动副本

- 证据：
  - [README.md](D:\Agent Repo\Insight-Repos\dynamo-main\README.md) 63、86 行。
  - [docs/getting-started/introduction.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\getting-started\introduction.md) 59 行。
  - [docs/kubernetes/model-caching.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\kubernetes\model-caching.md) 8-16、92、114-120 行。
  - [docs/kubernetes/snapshot.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\kubernetes\snapshot.md) 9-19 行。
- 说明：
  - 这是一个合并项：Model Express、PVC cache、Snapshot 都服务于“更快把新副本拉起来”这个用户目标。
  - 其中 Snapshot 仍是 preview，所以在 JSON `uncertainties` 里单独标了风险。

### UC07 SLA自动扩缩

- 证据：
  - [README.md](D:\Agent Repo\Insight-Repos\dynamo-main\README.md) 65、87、94 行。
  - [docs/components/planner/planner-guide.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\planner\planner-guide.md) 7-23、27-45、67-83 行。
  - [docs/getting-started/introduction.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\getting-started\introduction.md) 113-119 行。
- 说明：
  - 虽然 Planner 也有运维面，但其核心对外承诺是“围绕 SLA 做扩缩并减少 breach”，因此保留为 `P0`。

### UC08 拓扑就近调度

- 证据：
  - [README.md](D:\Agent Repo\Insight-Repos\dynamo-main\README.md) 88 行。
  - [docs/getting-started/introduction.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\getting-started\introduction.md) 121-135 行。
  - [docs/kubernetes/topology-aware-scheduling.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\kubernetes\topology-aware-scheduling.md) 7-18、24-37 行。
- 说明：
  - 这里建模的是“为了性能把 worker 摆对位置”，不是 Grove/KAI 的内部控制器设计。

### UC09 请求迁移续跑

- 证据：
  - [README.md](D:\Agent Repo\Insight-Repos\dynamo-main\README.md) 90 行。
  - [docs/getting-started/introduction.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\getting-started\introduction.md) 139-144 行。
  - [docs/fault-tolerance/request-migration.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\fault-tolerance\request-migration.md) 7-12、27-41、73-111 行。
  - [tests/fault_tolerance/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\tests\fault_tolerance\README.md) 5-18、21-43 行。
- 说明：
  - 之所以标 `P0`，是因为对最终请求而言“不中断/少中断”是可直接感知的结果。
  - 但 guided decoding 不支持迁移，这一点已在 `uncertainties` 中说明。

### UC10 优先请求优先响应

- 证据：
  - [docs/features/agentic_workloads.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\features\agentic_workloads.md) 25-39、43-54、76-78 行把 `priority` 定义为统一用户提示，并明确把 priority-aware routing 列为跨 backend 支持能力。
  - [docs/components/frontend/nvext.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\frontend\nvext.md) 57-67、117-121 行说明 `priority` 是用户可直接设置字段，影响 router queue ordering，并在支持的后端继续影响调度。
  - [docs/components/router/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\router\README.md) 24-25 行说明 `--router-queue-threshold` 与 `--router-queue-policy` 会启用 priority queue。
- 说明：
  - 该用例只保留“优先请求更快拿到响应”这一直接用户目标。
  - 我把它从旧 UC10 里拆出来，是因为它已经具备清晰的用户入口（`nvext.agent_hints.priority`）和独立的可感知结果（关键 turn 的 TTFT 改善）。

### UC11 重复图像复用

- 证据：
  - [README.md](D:\Agent Repo\Insight-Repos\dynamo-main\README.md) 96 行。
  - [docs/features/multimodal/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\features\multimodal\README.md) 34-39 行。
  - [docs/features/multimodal/embedding-cache.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\features\multimodal\embedding-cache.md) 10-18、24-35 行。
  - [recipes/qwen3-vl-30b/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\recipes\qwen3-vl-30b\README.md) 7-16、31-38、101-112 行。
- 说明：
  - 这里故意不直接叫 “EmbeddingCacheManager”，而用用户能理解的“重复图像复用”。
  - 它只覆盖 image -> embedding 的复用，不覆盖按图像内容选择哪个 worker 去命中已有 KV；后者单列为 `UC17`。

### UC12 多模态分层推理

- 证据：
  - [README.md](D:\Agent Repo\Insight-Repos\dynamo-main\README.md) 96 行。
  - [docs/features/multimodal/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\features\multimodal\README.md) 34-39、51-57 行。
  - [docs/features/multimodal/encoder-disaggregation.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\features\multimodal\encoder-disaggregation.md) 10-24、30-54、56-90 行。
- 说明：
  - E/PD 与 E/P/D 合并建模，因为用户目标都是“把多模态各阶段拆开、按瓶颈扩缩”。
  - 这里强调的是阶段拆分与独立扩缩，不是根据 `mm_hash` 做 worker 选择。

### UC17 多模态KV路由

- 证据：
  - [docs/features/multimodal/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\features\multimodal\README.md) 34-40 行把 `Multimodal KV Routing` 与 `Embedding Cache`、`Encoder Disaggregation` 并列成独立特性。
  - [docs/features/multimodal/multimodal-kv-routing.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\features\multimodal\multimodal-kv-routing.md) 10-13、16-22、34-51 行明确写出 MM router worker 会下载图像、计算 `mm_hash`、构造 `block_mm_infos`，再按 image-bearing KV block overlap 选 worker。
  - [docs/components/router/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\router\README.md) 41-44 行给出支持矩阵：TRT-LLM / vLLM 支持图像 routing，SGLang 暂不支持。
- 说明：
  - 这是本轮新增的核心独立条目，因为它有自己的文档、自己的工作流入口和与其他多模态加速能力不同的用户语义。
  - 和 `UC04 KV复用路由` 的区别：`UC04` 主要是文本前缀 / 普通 KV overlap；`UC17` 额外考虑图像内容与 `mm_hash`。
  - 和 `UC11 重复图像复用` 的区别：`UC11` 解决 encoder 复算；`UC17` 解决路由到哪个 worker 更容易命中已有图像相关 KV。
  - 和 `UC12 多模态分层推理` 的区别：`UC12` 是阶段拆分；`UC17` 是图像内容感知的 worker 选择。

### UC13 视频生成加速

- 证据：
  - [README.md](D:\Agent Repo\Insight-Repos\dynamo-main\README.md) 97 行。
  - [docs/components/frontend/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\frontend\README.md) 18-19 行。
  - [docs/features/diffusion/fastvideo.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\features\diffusion\fastvideo.md) 9-23、60-65、82-119 行。
- 说明：
  - 这里用“视频生成加速”而不是 “FastVideo” 作为 label，因为用户关心的是视频生成目标与速度，不是具体 worker 名。

### UC14 共享模型供给

- 证据：
  - [docs/kubernetes/model-caching.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\kubernetes\model-caching.md) 8-16、74-92、114-120 行。
  - [docs/components/frontend/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\frontend\README.md) 46-49 行。
  - [tests/dgdr/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\tests\dgdr\README.md) 19、185 行。
- 说明：
  - 它明显支撑 UC06，但本身更像供给/接入层，因此降为 `P1`。

### UC15 性能与迁移观测

- 证据：
  - [docs/components/planner/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\planner\README.md) 223-237 行附近说明 planner diagnostics 和 dashboard。
  - [docs/fault-tolerance/request-migration.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\fault-tolerance\request-migration.md) 105-111 行后续指标段。
  - [docs/getting-started/introduction.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\getting-started\introduction.md) 146-148 行。
- 说明：
  - 这类能力是支撑项，所以降为 `P2`。

### UC16 Draft协同部署

- 证据：
  - [examples/backends/vllm/launch/agg_spec_decoding.sh](D:\Agent Repo\Insight-Repos\dynamo-main\examples\backends\vllm\launch\agg_spec_decoding.sh) 21-35 行把 `speculative_config` 直接传给同一个 `dynamo.vllm` worker，其中 `model` 指向 `yuhuili/EAGLE3-LLaMA3.1-Instruct-8B`。
  - [recipes/kimi-k2.5/model-cache/nvidia/eagle-download.yaml](D:\Agent Repo\Insight-Repos\dynamo-main\recipes\kimi-k2.5\model-cache\nvidia\eagle-download.yaml) 25-38 行单独下载 `nvidia/Kimi-K2.5-Thinking-Eagle3`。
  - [recipes/kimi-k2.5/trtllm/agg/nvidia/deploy-specdec.yaml](D:\Agent Repo\Insight-Repos\dynamo-main\recipes\kimi-k2.5\trtllm\agg\nvidia\deploy-specdec.yaml) 36-40、51-68、86-96 行在单一 `TrtllmWorker` 服务里通过 `speculative_model_dir` 加载 draft model。
  - [recipes/glm-5-nvfp4/README.md](D:\Agent Repo\Insight-Repos\dynamo-main\recipes\glm-5-nvfp4\README.md) 8-10、91-99 行明确写出 `disaggregated prefill/decode and EAGLE speculative decoding via Dynamo`。
  - [recipes/glm-5-nvfp4/sglang/disagg/deploy.yaml](D:\Agent Repo\Insight-Repos\dynamo-main\recipes\glm-5-nvfp4\sglang\disagg\deploy.yaml) 12-14、59-64、76-109、177-218 行把 `decode` / `prefill` 拆成独立 worker，同时只在 `decode` worker 上开启 `--speculative-algorithm EAGLE`。
- 说明：
  - 这里我没有把用例命名成“Draft模型分离部署”，而是保守命名为 `Draft协同部署`。
  - 当前证据**足以支持**三点：
    1. 后端层面支持 speculative decoding；
    2. speculative decoding 可以和 aggregated / disaggregated serving 组合；
    3. draft model 可以作为单独模型资产被准备并由 worker 显式加载。
  - 但当前证据**不足以支持**：
    - draft model 被暴露成独立 `componentType` / 独立 `worker service` / 独立 `deployment unit`。
  - 因此 JSON 中把它建模为用户可直接启用的 `P0` 加速能力，但 summary 明确写成“在推理 worker 内附加 Draft/EAGLE 模型并与分离式部署组合”，避免夸大为独立 draft worker。

### UC18 下一轮预热

- 证据：
  - [docs/features/agentic_workloads.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\features\agentic_workloads.md) 72-74 行明确描述 speculative prefill，并给出多轮 benchmark 下 `turn 2+` TTFT 显著下降、最高约 `3x` 改善。
  - [docs/components/frontend/nvext.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\frontend\nvext.md) 96-105 行说明 `speculative_prefill` 的用户接口和执行流程。
  - [lib/llm/src/protocols/openai/nvext.rs](D:\Agent Repo\Insight-Repos\dynamo-main\lib\llm\src\protocols\openai\nvext.rs) 233-238 行把 `speculative_prefill` 固化为协议字段。
- 说明：
  - 该用例从旧 UC10 中拆出，因为它有独立的开关、独立的工作机制、独立的用户收益。
  - 它强调的是“提前把下一轮前缀打热”，不是优先级调度，也不是 sticky session。

### UC19 高优先级缓存保活

- 证据：
  - [docs/features/agentic_workloads.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\features\agentic_workloads.md) 64-68 行把 `Priority-based KV cache eviction` 作为实验特性单列。
  - [docs/backends/sglang/agents.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\backends\sglang\agents.md) 41-70 行详细说明 `--radix-eviction-policy priority` 以及和 HiCache 的交互。
  - [docs/components/frontend/nvext.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\frontend\nvext.md) 57-67、117-121 行说明 `priority` 会被转发给支持该能力的后端。
- 说明：
  - 这里我没有写成“TTL pinning”，因为本轮仓库证据更强的是优先级驱动的保活/淘汰，而不是一个通用、稳定、独立暴露的 TTL pinning 接口。
  - 之所以仍保留为 `P0`，是因为平台使用者可以直接启用，且结果会直接体现在 agentic workload 的 cache hit 稳定性和前缀保留上。

### UC20 子代理固定会话

- 证据：
  - [docs/components/frontend/nvext.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\frontend\nvext.md) 133-156 行给出 `session_control` 的用户接口和 sticky routing 语义。
  - [docs/components/router/router-configuration.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\router\router-configuration.md) 50-57 行说明 `StickySessionRouter` 和 `AgentController` 会在携带 `session_control` 的请求上自动激活。
  - [docs/backends/sglang/agents.md](D:\Agent Repo\Insight-Repos\dynamo-main\docs\backends\sglang\agents.md) 112-179、201-299 行完整说明 subagent KV isolation、session slot、`open/close` 生命周期与 OpenCode 集成。
  - [lib/llm/src/protocols/openai/nvext.rs](D:\Agent Repo\Insight-Repos\dynamo-main\lib\llm\src\protocols\openai\nvext.rs) 206-212、252-268 行把 `session_control` 固化为协议 schema。
- 说明：
  - 它之所以能从旧 UC10 里独立出来，是因为已经有清晰的请求接口、路由行为和 worker-side 会话语义。
  - label 不直接叫 “StickySessionRouter” 或 “SessionAwareCache”，而是保留用户视角的“子代理固定会话”。

## 推断与假设

### 明确推断

1. **UC01 被建模为 `低延迟推理` 而非“聊天补全/响应 API”**  
   这是一个命名层推断。证据显示 frontend 暴露了多个 API 面，但本次任务强调“加速能力”，因此把这些接口归为统一的低延迟推理入口，而不是逐 API 拆行。

2. **UC06 合并 Model Express、PVC cache 与 Snapshot**  
   这三个能力的入口不同，但用户可见目标都指向“更快拉起副本”。按规则，没有必要仅因实现手段不同就拆成多个 use case。

3. **UC11 与 UC12 分开**  
   我把 `embedding cache` 与 `encoder disaggregation` 分开，是因为两者的用户可见行为不同：前者强调重复内容命中，后者强调阶段拆分与独立扩缩。

4. **“Draft模型分离部署”被保守解释为 `Draft协同部署`**  
   这是本轮新增的关键解释：仓库内配置清楚证明了 speculative decoding 可与分离式部署组合，也证明了 draft model 是单独准备并挂给 worker 的模型资产；但没有直接证明 draft 自己就是一个独立 worker，所以不能把它画成独立部署单元。

5. **原 UC10 被拆成 4 条 agentic P0**  
   这是本轮的编号级调整。原因不是想把内部机制拆碎，而是因为仓库证据已经把 `priority`、`speculative_prefill`、priority-based eviction、`session_control` 暴露成不同的接口或启用路径；继续把它们塞在同一个 UC10 里，会掩盖哪些能力真的能被用户单独开启。

### 假设

1. `平台使用者` 在本仓库语境中既包含直接写 DGDR/DGD 的用户，也包含通过 recipes/examples 采用现成部署模式的用户。
2. `推理调用方` 既可以是业务应用，也可以是 LangChain / Codex / NeMo Agent Toolkit 之类的上层 agent harness。
3. `docs/backends/trtllm/trtllm-llama4-plus-eagle.md` 中提到的 `examples/backends/trtllm/engine_configs/llama4/eagle/` 在当前仓库快照下未出现，因此该文档被视为辅助背景，而不是本次 UC16 的主证据。
4. `UC17 多模态KV路由` 在本次目录里按仓库现有证据理解为“以图像内容感知为主的 MM-aware KV routing”，而不是所有模态都已稳定支持。
5. `UC19` 与 `UC20` 都是用户可启用、结果可感知的 agentic 能力，但支持面主要集中在 SGLang；因此保留 `P0` 的同时，在 JSON `uncertainties` 中明确标注 backend 边界和 experimental 状态。

## 明确未纳入项

- 未纳入 docs 发布、贡献、自定义 backend 开发、测试基础设施等非用户目标型条目。
- 未把 observability 细项拆成多条 use case，只保留一条 P2 支撑项。
- 未把 gateway、frontend、router、planner 等内部模块名直接当作 use case 名称。
- 未把每个 backend 的实现差异拆成独立目录条目；目前按统一用户目标合并，具体支持边界留给证据说明。
- 未把 README 提到但证据仍偏弱的“cache pinning TTL”单独建成一条用例；当前用更稳妥的 `高优先级缓存保活` 代替。
