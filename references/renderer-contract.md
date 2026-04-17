# Renderer Contract

This file defines what the renderer currently supports and how it behaves.

It is intentionally separate from [`drawio-dsl.md`](drawio-dsl.md), which only defines the shared schema.

## Supported Views

The renderer currently supports:
- `logic`
- `runtime`
- `use-case`
- `use-case-catalog`

## Supported Element Kinds

The renderer currently recognizes these element `type` values:

- Common topology kinds:
  - `service`
  - `interface`
  - `external`
  - `orchestrator`
  - `subsystem`
  - `component`
- Runtime-friendly aliases:
  - `job`
  - `queue`
  - `database`
  - `cache`
  - `broker`
  - `scheduler`
  - `worker`
- Use-case kinds:
  - `actor`
  - `use_case`
  - `usecase`
  - `system_boundary`
  - `boundary`
  - `note`

Prefer canonical forms such as `use_case` and `system_boundary` instead of aliases.

## Supported Relationship Kinds

The renderer currently recognizes these `kind` values:

- Shared/topology kinds:
  - `sync`
  - `async`
  - `event`
  - `stream`
  - `state`
  - `auth`
  - `cache`
  - `dependency`
- Use-case kinds:
  - `association`
  - `include`
  - `extend`
  - `generalization`

If a relationship does not need to be drawn, set `render: false` instead of inventing a new kind.

## Shared Default Behavior

- Elements and relationships render by default unless `render: false`.
- Keep labels short; the renderer will truncate and wrap when needed.
- Semantic palette roles apply only when `color_role` is present.
- `neutral` is baseline styling and does not count against the semantic color budget.

## Logic Rendering Contract

- The renderer assumes logic `groups` are vertical layers.
- Layers are stacked from top to bottom by ascending `layout_hint.order`.
- Direct rendered connections should stay within the same layer or adjacent layers.
- If a real dependency spans non-adjacent layers, keep it in evidence or mark it `render: false`.

## Runtime Rendering Contract

- Runtime renderers rely on ordered runtime participants and readable lane/group ordering.
- Stable relationship `id` values are preferred when runtime paths reference ordered steps.
- Runtime scenes are expected to preserve primary-path readability rather than render a global topology superset.

## Use-Case Rendering Contract

- `association` renders only when `render: true`.
- `include` and `extend` labels are normalized to `<<include>>` and `<<extend>>` when drawn.
- Grouped all-use-cases diagrams expect:
  - one main system boundary
  - one actor-owned panel per actor
  - per-element `group` assignments for actor grouping
- Child system boundaries or actor panels must keep visible spacing from parent edges and headers.

## Use-Case Catalog Rendering Contract

- The table renderer expects these exact rendered columns:
  - `编号`
  - `用例`
  - `主参与者`
  - `入口面`
  - `优先级`
  - `说明`
- The renderer reads row values from canonical fields such as:
  - `code`
  - `label`
  - `primary_actor`
  - `entry_surfaces`
  - `priority`
  - `summary`
- `P0`, `P1`, and later tiers may affect table sectioning and priority coloring.
