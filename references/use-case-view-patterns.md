# Use Case View Patterns

Use this reference when a repository exposes multiple first-class operating modes and one single journey is not enough.

`references/drawio-dsl.md` defines the shared schema.
`references/renderer-contract.md` defines supported use-case kinds and default rendering behavior.
This file defines the single-source use-case file and how the renderer derives both outputs from it.

## Goal

Do not collapse multiple product entry surfaces into one generic use case.

Instead:

1. Enumerate the core user-visible use case set.
2. Assign one primary actor to each use case.
3. Record the entry surfaces that expose that use case.
4. Assign priority conservatively.
5. Derive the grouped all-use-cases diagram from that same file.

## Required intermediate artifacts

For use-case work, the subagent should produce:

1. `use-case-view.json`
2. `evidence-assumptions.md`

`use-case-view.json` is the source of truth. The renderer derives both the table artifact and the grouped all-use-cases diagram from it.

## Source File Shape

Keep the source file business-facing.

Use these rendered columns only:
- `编号`
- `用例`
- `主参与者`
- `入口面`
- `优先级`
- `说明`

Do not add logic, development, runtime/process, physical, evidence, or summary-rollup columns.

Each `use_cases` entry should usually include:
- stable `id`
- optional `code`
- short `label`
- `primary_actor`
- optional `secondary_actors`
- `entry_surfaces`
- `priority`
- short `summary`

The JSON row keys must stay on those canonical DSL field names.
Do not use rendered table column labels such as `编号`、`用例`、`主参与者`、`入口面`、`优先级`、`说明` as JSON keys inside `use_cases`.

## Discovery workflow

1. Identify the first-class entry surfaces.
2. Merge synonyms and implementation variants when the user goal is the same.
3. Split one capability into multiple use cases only when actor, entry surface, approval boundary, or user-visible behavior materially changes.
4. Assign one actor-owned group id for the later diagram.
5. Keep the source file at user-visible capability level.

## Priority Rules

Assign priority by user-facing role, not by implementation importance.

- `P0`: user-visible functional capabilities that the end user directly uses and can perceive the result of
- `P1`: systems and capability layers that directly support `P0`, such as access, configuration, approvals, and capability supply
- `P2`: operability, maintenance, governance, monitoring, and security-management capabilities

Do not assign `P0` merely because a subsystem is important to the architecture.

## Derived Diagram Rules

The grouped all-use-cases diagram is derived from this same file.

Derived diagram expectations:
- make the main actor set obvious
- make the core use case set obvious
- show the system boundary explicitly
- make the actor-owned panel structure obvious when the repository has multiple first-class modes
- keep labels short enough that the future ellipse layout stays readable
- keep explanation out of the use-case name; the `label` should stay short and the detail should live in `summary` or notes
- carry `priority` from source rows onto rendered `use_case` elements so the renderer can preserve visual emphasis
- keep nested frames visibly separated; touching borders should fail review

When deriving the grouped all-use-cases diagram:
- use the source file `actors` list as the source for actor-owned panels
- use each use case row's `primary_actor` as the panel/group key
- carry `label`, `priority`, and `summary` from each use case row onto the rendered use-case element
- derive one main `system_boundary` from the file title or explicit system name

Preferred layout:
- one main system boundary
- one actor-owned panel per actor
- no actor-to-use-case edges unless the source file later grows explicit relationship metadata worth rendering

Good omissions include:
- helper functions
- DTOs and schemas
- repositories and ORM models
- logging and telemetry
- every validation step that does not deserve separate architectural meaning
- secondary admin flows when the main user journey already explains the system shape

## Text Example

Typical rows may look like this:

- `UC01` 消息协作 - 主参与者：消息用户 - 入口面：消息网关 - 优先级：`P0`
- `UC02` 终端协作 - 主参与者：终端用户 - 入口面：CLI/TUI - 优先级：`P0`
- `UC03` 多渠道配置 - 主参与者：终端用户 - 入口面：CLI、消息入口配置 - 优先级：`P1`
- `UC04` 会话管理 - 主参与者：终端用户 - 入口面：CLI、Web - 优先级：`P1`
- `UC05` 模型提供商认证 - 主参与者：终端用户 - 入口面：CLI、Web - 优先级：`P1`
- `UC06` 工具审批 - 主参与者：终端用户 - 入口面：CLI、编辑器 - 优先级：`P1`
- `UC11` 技能管理 - 主参与者：终端用户 - 入口面：CLI、聊天内命令、Web - 优先级：`P1`
- `UC07` 网关运行 - 主参与者：维护者 - 入口面：CLI - 优先级：`P2`
- `UC21` 访问控制 - 主参与者：维护者 - 入口面：CLI - 优先级：`P2`
- `UC22` 安全防护 - 主参与者：维护者 - 入口面：CLI、网关 - 优先级：`P2`

This text example replaces any image-based category sample.

Canonical JSON example:

```json
{
  "view": "use-case-catalog",
  "title": "Hermes Agent 用例目录",
  "catalog_columns": ["编号", "用例", "主参与者", "入口面", "优先级", "说明"],
  "actors": [
    {"id": "terminal-user", "label": "终端用户"},
    {"id": "operator", "label": "维护者"}
  ],
  "use_cases": [
    {
      "id": "uc-terminal-chat",
      "code": "UC01",
      "label": "终端协作",
      "primary_actor": "terminal-user",
      "entry_surfaces": ["CLI/TUI (`hermes`)"],
      "priority": "P0",
      "summary": "用户在终端里直接与 Hermes 连续对话。"
    }
  ]
}
```

## Common failure modes

Avoid these patterns:
- choosing one heroic primary use case and hiding the rest
- adding non-business columns back into the source file
- turning internal modules into catalog rows
- assigning every use case to `P0`
- assigning `P0` to operator-only, governance, or maintenance capabilities
- using capability-area buckets when the later diagram needs actor-owned groups
- turning the use-case view into a sequence diagram
- turning internal services into use cases
- drawing `include` and `extend` for every sub-step
- omitting the system boundary so the actor and use cases float without context
- relying on actor-to-use-case edges when the grouped actor panels already express the same fact
- deriving panel grouping from anything other than the actor list and each use case row's `primary_actor`
- letting parent and child frames touch or nearly touch
- using full-sentence labels that cannot fit inside ellipses
- mixing runtime arrows and use-case dependency arrows without distinguishing semantics
- collapsing multiple first-class operating modes into one generic “协作完成任务” row when the source file should stay visible
