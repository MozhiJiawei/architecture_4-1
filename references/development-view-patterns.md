# Development View Patterns

Use this reference when the user wants a code view, development view, or module/package view.

`references/drawio-dsl.md` defines the shared schema.
`references/renderer-contract.md` records renderer support status.
This file defines the fixed intermediate-model contract for development-view subagents.

## Goal

Model how developers should understand and navigate the codebase.

Prefer stable code ownership and dependency boundaries over execution flow.

For repositories like Darwin Godel Machine, keep the view centered on first-class code units that explain the core use case. For the "开放式演化" use case, that usually means:

1. identifying the orchestration entrypoints that launch or continue evolution
2. separating evaluation harnesses from self-improvement and patch-generation flows
3. showing shared support modules such as prompts, tools, analysis, and container/runtime helpers only when they explain developer-facing boundaries
4. omitting helpers, logs, generated outputs, and transient experiment artifacts unless they are themselves a maintained module boundary

## Required intermediate artifacts

For development work, the subagent should produce:

1. `development-view.json`
2. `evidence-assumptions.md`

`development-view.json` is the source of truth for the code-view renderer.

## Source File Shape

Keep the source file architecture-facing rather than file-list-shaped.

Use the shared DSL top-level fields plus these development-specific fields when helpful:

- `build_roots`: entry repositories, top-level packages, or executable roots that shape the codebase
- `module_dependencies`: explicit compile-time or package-time dependencies between modules
- `ownership_notes`: short notes on why boundaries exist or who owns them conceptually

Each development `elements` entry should usually include:

- stable `id`
- short `label`
- `type`, usually `subsystem`, `component`, `service`, `interface`, or `external`
- `group` for its layer or ownership zone
- optional `code_kind` such as `repository`, `package`, `module`, `script-suite`, `shared-lib`, `adapter`, or `schema`
- optional `paths` as the concrete repository anchors; these render in each card under `涉及代码`
- optional `responsibility`
- optional `exposes`
- optional `depends_on`
- optional `evidence_ids`

Each development `relationships` entry should usually include:

- `source`
- `target`
- `label`: full relationship meaning for legends, review, and evidence
- `summary_label`: subagent-generated edge text, preferably Chinese when the task is in Chinese, no more than 10 characters
- `kind`, usually `dependency`
- optional `inferred`
- optional `evidence_ids`

Do not turn every source folder into an element.
Collapse implementation fragments into one element when a developer would reason about them as one maintained unit.

When the renderer consumes this file:

- keep `responsibility` semantically complete in JSON even if the rendered card later wraps it
- keep `paths` concrete and compact; prefer 1-5 maintained files or directories that a developer would open first
- keep every interface in `exposes`; do not pre-merge multiple interfaces into one string
- prefer one self-documenting interface signature or entrypoint per `exposes` item

## Discovery workflow

1. Start from the use-case conclusion rather than scanning the whole tree flatly.
2. Find the code roots that directly realize that use case.
3. Group roots into stable developer-facing modules.
4. Add shared libraries only when they are reused across multiple roots or explain an important boundary.
5. Record explicit compile-time, import-time, packaging, or script-to-module dependencies.
6. Mark inferred dependencies explicitly when they come from naming, conventions, or call sites rather than direct imports.

For "开放式演化", prefer following the path from the outer orchestration entry through:

- generation loop / parent selection
- self-improvement step orchestration
- evaluation harnesses
- prompt or tool substrates
- analysis or archive support when it is a maintained developer-facing module

## Layout guidance for future rendering

The reference style looks like a UML-ish code view with large maintained units, typed boxes, and a small number of semantically meaningful edges.

Prepare the model so the renderer can derive that shape:

- use `groups` for broad code layers such as orchestration, evolution workflow, evaluation, support, and external dependencies
- keep one element per developer-meaningful module, not per file
- keep element labels short enough to fit inside rectangular cards
- put detailed path lists in `paths` or evidence, not in the rendered label; visible `paths` should stay concise enough for the `涉及代码` card section
- generate `summary_label` for every rendered relationship; do not use opaque codes like `R1` or `R2` as the visible edge text
- keep `summary_label` as a short action or dependency phrase such as `读取字段`, `生成配置`, or `验证注入`
- keep `relationships` as the authoritative full dependency inventory for development view rendering
- use notes only when a crucial modeling caveat cannot live in `uncertainties`
- render dependencies as straight lines between cards; do not rely on hand-authored orthogonal polylines for this view
- use color to express `group` membership and show a legend in the top-right corner instead of insisting on group frames

## Fallback pruning when rendering fails

If the development view is too dense to render clearly, simplify the intermediate model before asking for renderer-side exceptions.

Use this order:

1. remove or fold low-information support / `utils` modules first
2. remove nodes whose connection to the target use case is secondary or weak
3. keep the core business path and its direct dependencies intact

For subagents, this means:

- never delete relationships between the core business nodes that explain the target theme
- prefer omitting a heavily reused helper node over omitting a use-case-defining node
- when pruning, explain the tradeoff and the removed node list in `evidence-assumptions.md`

## Canonical JSON example

```json
{
  "view": "development",
  "title": "Darwin Godel Machine 代码视图",
  "summary": "围绕开放式演化主用例整理的开发/代码视图中间模型。",
  "scope": "聚焦 DGM_outer、自改进、评测 harness 与共享支撑模块；不展开生成产物与零散 helper。",
  "groups": [
    {"id": "orchestration", "label": "演化编排层", "layout_hint": {"order": 1}},
    {"id": "workflow", "label": "自改进与评测层", "layout_hint": {"order": 2}},
    {"id": "support", "label": "共享支撑层", "layout_hint": {"order": 3}}
  ],
  "elements": [
    {
      "id": "outer-loop",
      "label": "DGM_outer",
      "type": "subsystem",
      "group": "orchestration",
      "code_kind": "script-suite",
      "paths": ["DGM_outer.py"],
      "responsibility": "驱动多代开放式演化，选择父代并调度每轮自改进。",
      "exposes": ["python DGM_outer.py", "run_generation(...)"],
      "evidence_ids": ["ev-outer-loop"]
    },
    {
      "id": "self-improve-step",
      "label": "self_improve_step",
      "type": "component",
      "group": "workflow",
      "code_kind": "module",
      "paths": ["self_improve_step.py"],
      "responsibility": "围绕单个失败样本执行诊断、补丁生成、回收与评测。",
      "exposes": ["self_improve_step(...)"],
      "evidence_ids": ["ev-self-improve"]
    }
  ],
  "relationships": [
    {
      "source": "outer-loop",
      "target": "self-improve-step",
      "label": "调度单次自改进",
      "summary_label": "调度改进",
      "kind": "dependency",
      "inferred": false,
      "evidence_ids": ["ev-outer-loop", "ev-self-improve"]
    }
  ],
  "evidence": [
    {"id": "ev-outer-loop", "path": "DGM_outer.py", "reason": "开放式演化主入口与代际编排。"},
    {"id": "ev-self-improve", "path": "self_improve_step.py", "reason": "单次自改进主流程与参数入口。"}
  ]
}
```

## Common failure modes

Avoid these patterns:

- turning the code view into a raw directory tree
- modeling runtime sequence chatter instead of code/module boundaries
- treating every script as a first-class module even when several scripts form one maintained unit
- hiding the use-case-driving orchestration code behind generic buckets like "core" or "utils"
- drawing dependencies that are only temporal workflow steps rather than developer-facing code coupling
- copying full filesystem paths into labels
- promoting generated run directories, logs, caches, or benchmark outputs into maintained modules
- mixing package ownership, runtime actors, and user roles into one grouping scheme
- replacing group meaning with geometric frames when color plus legend is sufficient
