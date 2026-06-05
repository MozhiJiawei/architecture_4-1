# UC06 开发视图证据与假设

输出文件：

- `D:\Agent Repo\Mozhi-s-AgentWorkspace\.tmp\generate-3plus1-diagrams\dynamo-main\development\development-view.json`
- `D:\Agent Repo\Mozhi-s-AgentWorkspace\.tmp\generate-3plus1-diagrams\dynamo-main\development\evidence-assumptions.md`

## 证据主线

1. 文档入口
   - `D:\Agent Repo\Insight-Repos\dynamo-main\README.md`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\docs\kubernetes\model-caching.md`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\docs\kubernetes\snapshot.md`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\docs\components\frontend\README.md`

2. PVC / modelCache -> DGD
   - `D:\Agent Repo\Insight-Repos\dynamo-main\components\src\dynamo\profiler\utils\dgdr_v1beta1_types.py`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\components\src\dynamo\profiler\rapid.py`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\components\src\dynamo\profiler\utils\config_modifiers\protocol.py`

3. frontend bootstrap / ModelExpress 接入
   - `D:\Agent Repo\Insight-Repos\dynamo-main\components\src\dynamo\frontend\frontend_args.py`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\components\src\dynamo\frontend\main.py`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\components\src\dynamo\vllm\backend_args.py`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\components\src\dynamo\vllm\args.py`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\components\src\dynamo\vllm\main.py`

4. Snapshot / DynamoCheckpoint / operator
   - `D:\Agent Repo\Insight-Repos\dynamo-main\deploy\operator\api\v1alpha1\common.go`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\deploy\operator\api\v1alpha1\dynamocheckpoint_types.go`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\deploy\operator\internal\checkpoint\resolve.go`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\deploy\operator\internal\checkpoint\hash.go`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\deploy\operator\internal\controller\dynamographdeployment_controller.go`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\deploy\operator\internal\dynamo\graph.go`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\deploy\helm\charts\platform\README.md`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\deploy\helm\charts\snapshot\README.md`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\deploy\snapshot\cmd\snapshotctl\README.md`

5. 回归验证
   - `D:\Agent Repo\Insight-Repos\dynamo-main\components\src\dynamo\profiler\tests\unit\test_helpers_rapid.py`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\components\src\dynamo\profiler\tests\integration\test_profile_sla_dgdr.py`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\components\src\dynamo\vllm\tests\test_vllm_unit.py`
   - `D:\Agent Repo\Insight-Repos\dynamo-main\tests\dgdr\README.md`

## 建模假设

1. `frontend-bootstrap` 只建模参数契约与启动入口，不继续展开 tokenizer/processor 内部，是因为 UC06 关心的是“如何复用已有模型元数据”，不是 tokenization 算法本身。
2. `operator-graph` 被单列成节点，是因为 `MODEL_EXPRESS_URL` 注入与 checkpoint pod metadata 注入都在这里会合，开发者通常需要先到这一层确认 chart/operator 配置是否真的落进 pod。
3. `snapshot-stack` 合并了 chart、guide 与 `snapshotctl`，因为它们共同构成 Snapshot 支撑栈；若拆开会把图拉成运维目录树。
4. `faststart-tests` 合并 profiler 与 vLLM 相关测试，是为了把“快速启动副本”的行为回归面集中呈现，而不是把测试按语言或目录分散。

## 主要不确定性

1. ModelExpress 主体实现不在本仓库，只能确认 Dynamo 侧存在接入参数、worker 类切换与 operator 注入点，不能把 modelexpress server 伪造成仓内模块。
2. Snapshot 文档明确标注 preview/experimental，因此 restore 路径我保留为支持链，不把它画成默认稳定路径。
3. `deploy/operator/internal/checkpoint` 里还有更细的 podspec/gms/restore 逻辑；本次只保留对 UC06 有解释力的 hash/resolve/controller 入口。

## 剪裁记录

1. 删除了 planner、mocker、KV-aware routing、服务发现等非 UC06 核心节点。
2. 删除了 CRD 生成产物与大体量 `deploy/helm/.../crds/*.yaml` 节点，保留更稳定的 Go API 类型与 controller 代码。
3. 删除了容器模板、镜像构建脚本、一般性 benchmark 目录与运行时日志/缓存目录。
4. 文档没有单独作为依赖节点渲染，只在 `build_roots` 和 `evidence` 中保留。
