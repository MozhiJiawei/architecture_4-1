---
name: generate-3plus1-diagrams
description: Analyze a source repository and generate editable draw.io files for the architectural view model used by this skill. Use when Codex needs to inspect project structure, infer module boundaries and component relationships, produce logic/development/runtime/use-case views, align output to the reference diagrams in ref/, and validate diagram XML, style constraints, and exported previews.
---

# Generate 3+1 Diagrams

## Goal

Turn a source repository into one or more editable `.drawio` architecture diagrams that match the 3+1 view model and stay visually aligned with the reference diagrams in `ref/`.

When the user requests only some views, produce only those views.

When the user works in Chinese, keep the intermediate notes, diagram labels, summaries, and review notes in Chinese unless they explicitly ask for English or bilingual output.

Keep temporary artifacts under the project root `.tmp`, not in this skill repository or the target repository.

## Agent Setup

Launching subagents is required.

Start one dedicated subagent for each requested view:
- logic
- development
- runtime
- use-case

Use `gpt-5.4` for every view-owning subagent.

Each subagent should work in an isolated area under:
- `.tmp/generate-3plus1-diagrams/<repo-name>/logic/`
- `.tmp/generate-3plus1-diagrams/<repo-name>/development/`
- `.tmp/generate-3plus1-diagrams/<repo-name>/runtime/`
- `.tmp/generate-3plus1-diagrams/<repo-name>/use-case/`

The main agent owns review and completion:
- load the relevant images in `ref/` before dispatching subagents
- for the use-case reference specifically, use `ref/use-case-view.png`
- treat `ref/` as read-only visual baseline material
- do not create, modify, regenerate, or "fill in" reference images
- do not claim the main agent is "filling in reference diagrams" or "filling in missing evidence files"; its job is to read, compare, and supervise
- supervise subagent progress instead of waiting silently
- prefer artifact-based supervision over free-form status pings: inspect the assigned output directory first, and only send a follow-up when the files or timestamps show the subagent is stalled
- do not interrupt a subagent for a status-only reply unless you intend to redirect its work
- if you must ask for status, explicitly say `Reply with status and then continue the original task; do not treat this message as final delivery`
- render `.drawio` files from accepted intermediate JSON models
- run export and validation after rendering
- inspect the exported images and compare them against the matching `ref/` images before accepting the result

Main-agent scope is intentionally narrow:
- read the relevant reference images and modeling rules
- do not read repository source files for substantive architecture analysis unless the user explicitly overrides this rule
- dispatch one subagent per requested view with explicit constraints
- monitor progress, answer blockers, and review outputs
- cross-check subagent outputs against each other using the high-level summaries, evidence notes, and model artifacts included in their deliverables
- request follow-up investigation from the relevant subagent when a gap, contradiction, weak claim, or missing evidence appears
- perform final comparison/acceptance against `ref/`
- only produce artifacts that belong to the requested view deliverables
- do not create extra analysis work outside dispatch, review, and acceptance unless the user explicitly asks

Single-owner rule:
- keep exactly one active view-owning subagent per requested view
- do not let two subagents own the same view at the same time
- if replacement is needed, close the current owner before launching the replacement

Timeout supervision policy:
- after dispatch, the main agent should stay silent for the first 10 minutes for that view
- during this initial 10-minute window, inspect the assigned artifact directory but do not send status pings or reminder messages
- if the subagent has not completed after 10 minutes, inspect the artifact directory once per minute
- after the 10-minute mark, send at most one brief reminder per minute asking the subagent to continue the original task and finish the required artifacts
- reminders must reinforce the required output files and completion bar; do not ask for free-form status only
- if repeated reminders still do not produce meaningful artifact updates, the main agent may restart that subagent
- before restarting a subagent, close the current one first and keep the same output directory and expected filenames for the replacement

## Subagent Instruction Contract

Do not dispatch a subagent with only a one-line task description.

Every subagent prompt must include the minimum skill context it needs to behave
like an extension of this skill rather than a generic researcher.

At dispatch time, the main agent must explicitly pass:
- which 3+1 view the subagent owns
- the required output directory under `.tmp/generate-3plus1-diagrams/<repo-name>/<view>/`
- the required deliverables: intermediate JSON and evidence/assumptions note
- the exact expected filenames, for example `<view>-view.json` and `evidence-assumptions.md`
- the language requirement for labels and notes
- the relevant skill constraints for that view, summarized in the prompt
- the specific reference files the subagent must read before modeling
- the completion standard the subagent must satisfy before handing back results

At minimum, each subagent prompt should restate these rules in task-specific form:
- stay scoped to the assigned view
- keep repository understanding evidence-backed rather than directory-shaped
- mark inferred relationships as inferred
- state important omissions and assumptions explicitly
- write artifacts only inside its assigned `.tmp/generate-3plus1-diagrams/.../<view>/` area
- treat the intermediate JSON as the subagent's final artifact and stop after writing it and the evidence note
- treat later supervisor messages as incremental guidance unless they explicitly say to stop, restart, or hand off
- do not treat a request for status as permission to exit early

Before launching a subagent, the main agent should preload or summarize the most
relevant instructions from:
- `references/drawio-dsl.md`
- `references/renderer-contract.md`
- `references/3plus1-rules.md`
- `references/view-checklists.md`
- `references/logic-view-patterns.md` for logic view
- `references/development-view-patterns.md` for development view
- `references/runtime-view-patterns.md` for runtime view
- `references/use-case-view-patterns.md` for use-case view
- any view-specific reference the subagent must obey

Preload means "read and pass along constraints", not "author missing material".
For normal operation, the main agent should rely on the repository understanding
already surfaced by subagent deliverables rather than doing its own code reading.
When dispatch quality or review quality is insufficient, send the subagent back
for targeted investigation instead of reproducing the investigation in the parent thread.

When using generic delegation tooling that does not automatically inherit skill
files, the parent agent must inline the relevant constraints directly into the
subagent prompt. Do not assume the subagent has read this `SKILL.md` unless the
prompt itself makes the required instructions available.

## Working Shape

Each requested view should usually produce:
- an intermediate JSON model
- a short note on evidence, assumptions, and omissions

For use-case view specifically, keep the subagent handoff limited to:
- `use-case-view.json`
- `evidence-assumptions.md`

For development view specifically, keep the subagent handoff limited to:
- `development-view.json`
- `evidence-assumptions.md`

Current status note for development view:
- the schema is fixed and should be used now for subagent-generated intermediate files
- the renderer now supports `view: "development"` with full straight-line dependency rendering
- unless the user explicitly asks for renderer work, subagents should still stop after the JSON model and evidence note

Use-case subagents should treat `use-case-view.json` as the authoritative inventory of user-visible capabilities. The main agent and renderer derive both the table artifact and the grouped all-use-cases diagram from that file.

For use-case modeling, `references/drawio-dsl.md` is the schema authority.
Keep the prompt aligned to that DSL:
- use `groups` plus each element's `group` field for actor-based grouping
- keep use-case `label` short and move explanation into `summary`, `description`, `uncertainties`, or the evidence note
- in `use-case-view.json`, keep each row on the canonical DSL fields `id`, optional `code`, `label`, `primary_actor`, optional `secondary_actors`, `entry_surfaces`, `priority`, and `summary`
- reserve `编号`、`用例`、`主参与者`、`入口面`、`优先级`、`说明` for rendered table columns, not JSON row keys
- the renderer derives actor panels, use-case elements, and priority coloring from that single file
- assign priority by user-facing role: `P0` for end-user functional capabilities, `P1` for systems that directly support `P0`, and `P2` for maintenance, governance, monitoring, and security-management capabilities
- use `associations` only as optional actor-participation metadata; they render only when `render: true`
- keep visible spacing between nested frames and actor panels

For development modeling, `references/drawio-dsl.md` remains the schema authority and `references/development-view-patterns.md` defines the fixed handoff contract.
Keep the prompt aligned to that contract:
- model developer-facing code units, not a raw directory tree
- start from the user-named use case and follow the code that realizes it
- emit `development-view.json` with the shared DSL plus development-specific fields such as `build_roots`, `module_dependencies`, `ownership_notes`, element-level `code_kind`, `paths`, and `responsibility` when they help
- keep labels short and move filesystem detail into `paths`, evidence, or notes
- use `kind: "dependency"` for code/package relationships unless a future renderer contract defines something more specific
- generate `summary_label` for every rendered relationship; this is the visible edge label and must summarize the full relationship text in no more than 10 characters, using Chinese when the task is in Chinese
- keep the full relationship meaning in `label`; never make the visible edge label an opaque code such as `R1` or `R2`
- collapse helper fragments into one maintained module when that is how developers reason about the code
- keep `responsibility` complete in the JSON even if the renderer later wraps it for display
- keep `exposes` lossless: one interface or entrypoint per array item, with no pre-merged summary line
- render development dependencies as straight lines rather than hand-authored orthogonal routes
- keep `relationships` complete because the development renderer may draw the full edge inventory
- use `group` for semantic color coding and legend generation rather than assuming the picture will use group frames
- when a development view is hard to render cleanly, prune the JSON before asking for renderer exceptions
- prune in this order: low-information support/utils nodes first, theme-weak secondary nodes second, core business nodes last
- never delete the core business relationships that explain the target use case
- record every pruning decision in `evidence-assumptions.md`

Do not ask a use-case subagent to emit draw.io XML, screenshots, or final prose summaries unless the user explicitly asks. The single `use-case-view.json` file is the contract between the subagent and the main agent.

The main agent should then produce:
- for use-case work, a table-style `.drawio` and export derived from `use-case-view.json`
- an editable grouped all-use-cases `.drawio` derived from `use-case-view.json`
- an exported preview image or SVG for each rendered artifact
- validation and visual review results

For development work in the current phase, the main agent should:
- review `development-view.json` against `ref/development-view.jpg`, `references/development-view-patterns.md`, and the use-case conclusion that drove the selection
- request targeted refinement if the module cut, grouping, or dependency story is weak
- render, export, and visually review the development view when the user asks for the picture, while keeping the edge set sparse

Treat repository understanding as AI-led work. Use scripts to help with rendering, exporting, validation, or repetitive extraction, but do not rely on scripts to invent the architecture for you.

Filter out generated and vendored noise unless the user explicitly wants it included.

Prefer a readable, evidence-backed subset over a bloated diagram.

## Resources

Read these first when needed:
- [references/ref-usage.md](references/ref-usage.md): how to use `ref/` as the visual baseline
- [references/style-profiles.md](references/style-profiles.md): style constraints
- [references/drawio-dsl.md](references/drawio-dsl.md): shared intermediate-model schema only
- [references/renderer-contract.md](references/renderer-contract.md): supported renderer types, kinds, aliases, and default behavior
- [references/3plus1-rules.md](references/3plus1-rules.md): shared architectural rules
- [references/view-checklists.md](references/view-checklists.md): what each view should explain
- [references/logic-view-patterns.md](references/logic-view-patterns.md): logic-specific modeling strategy
- [references/development-view-patterns.md](references/development-view-patterns.md): development/code-view intermediate-model contract
- [references/runtime-view-patterns.md](references/runtime-view-patterns.md): runtime-specific modeling strategy
- [references/use-case-view-patterns.md](references/use-case-view-patterns.md): use-case-specific modeling strategy

Use these scripts in the main-agent completion phase:
- `scripts/render_drawio.py`: run the unified view pipeline for an intermediate model (`solve layout -> model validation -> render .drawio -> draw.io XML validation`)
- `scripts/tools/validate_visual_pipeline.py`: run draw.io validation, export, and inspection in order

Treat these scripts as command interfaces, not as modeling authority. Do not
depend on renderer internals or import private modules from prompts; use the
intermediate JSON contract and the documented commands above.

For normal view generation, split the workflow into two stages:
1. subagent stage: produce the intermediate JSON and evidence note
2. main-agent stage: render every required intermediate JSON artifact, including `use-case-view.json` when the requested view is use-case, by running `python scripts/render_drawio.py <json-path> --output-dir <view-dir> --export-previews --preview-dir <view-dir>\\exports --preview-format png`
3. main-agent stage: run `python scripts/tools/validate_visual_pipeline.py <drawio-path> --exports-dir <view-dir>\\exports` for each rendered `.drawio`, including the table artifact for use-case work
4. if rendering or validation fails, save the failing command, stderr summary, and current artifact list into `<view-dir>\\render-validation-failure.md` before replying

Do not ask a subagent to render, export, or validate unless the user explicitly overrides this workflow.

## View Notes

For all views:
- keep labels short and readable
- attach evidence to important elements and relationships
- mark inferred relationships as inferred
- say what you intentionally omitted when scope is large

For logic view:
- prefer stable responsibilities over folder names
- identify top-level capabilities first
- group the diagram into readable architectural layers
- keep dependency directions short and layered
- read [references/drawio-dsl.md](references/drawio-dsl.md), [references/renderer-contract.md](references/renderer-contract.md), and [references/logic-view-patterns.md](references/logic-view-patterns.md) before modeling

For development view:
- prefer code ownership, package boundaries, and maintained module cuts over runtime sequencing
- start from the target use case and keep only the code units needed to explain that slice plus its shared support modules
- use `paths` and evidence to anchor each module in the repository, but keep rendered labels short
- make the development subagent, not the renderer, author relationship `summary_label` values; use short action phrases such as `读取字段`, `生成配置`, or `验证注入`
- treat generated outputs, caches, logs, and run directories as omissions unless the user explicitly wants them
- render straight dependency lines only; do not introduce hand-authored orthogonal polylines for development view
- expect development group meaning to be expressed by color and legend instead of boxed lanes
- if a first-pass model renders poorly, tell the subagent to remove noisy support/utils nodes before touching the core path
- do not keep a support node just because many modules depend on it; keep it only when it materially improves understanding of the target theme
- read [references/drawio-dsl.md](references/drawio-dsl.md), [references/renderer-contract.md](references/renderer-contract.md), and [references/development-view-patterns.md](references/development-view-patterns.md) before modeling

For runtime view:
- prefer runtime collaboration over static package structure
- identify the main runtime paths first
- show lifecycle owners, execution boundaries, state or delivery boundaries, and external systems when they matter
- preserve ordering clearly enough that the renderer does not need to guess the story
- read [references/drawio-dsl.md](references/drawio-dsl.md), [references/renderer-contract.md](references/renderer-contract.md), and [references/runtime-view-patterns.md](references/runtime-view-patterns.md) before modeling

For use-case view:
- enumerate the core user-visible use case set first, then derive both rendered artifacts from `use-case-view.json`
- model the user-visible goal set, not the package structure
- prefer actor and use-case names that read as short user goals or system roles
- keep the use-case `label` short; move any explanation into `summary` instead of appending it into the rendered name
- group all-use-cases diagrams with `groups` and each use case element's `group` field
- keep each actor as the owner of exactly one rendered panel when that grouped layout is used
- do not draw actor-to-use-case edges unless an association explicitly sets `render: true`
- include `include`, `extend`, `dependency`, and `generalization` only when they add architectural meaning and do not turn the diagram into a hairball
- prefer one bounded system frame or a small number of bounded partitions instead of decorative containers
- keep visible spacing between nested frames; parent and child containers should never read as touching
- keep use-case labels short enough to fit inside ellipses without sentence wrapping
- use `include` for mandatory reused behavior and `extend` for conditional or optional behavior
- add notes in `uncertainties` when a user journey is inferred from routes, handlers, or tests rather than directly documented
- when the repository exposes multiple first-class operating modes, produce one single-source `use-case-view.json` that can render both the table artifact and the all-use-cases diagram instead of a single representative journey
- when producing `use-case-view.json`, use the canonical DSL row fields rather than rendered column names
- read [references/drawio-dsl.md](references/drawio-dsl.md), [references/renderer-contract.md](references/renderer-contract.md), and [references/use-case-view-patterns.md](references/use-case-view-patterns.md) before modeling

## Completion Standard

Do not treat an intermediate JSON file as finished work.

A requested view is complete only when all of these are true:
- every required `.drawio` artifact exists
- every required export exists
- validation has run for every rendered artifact
- for use-case work, both the table artifact and the all-use-cases diagram artifact exist
- the main agent has visually compared each diagram export against the matching `ref/` image when one exists

For delegated work, the subagent-side handoff bar is:
- the `use-case-view.json` file exists when the assigned view is use-case
- the evidence/assumptions note exists
- the final reply includes the absolute paths it wrote plus any unresolved uncertainty that might affect rendering

The parent agent should treat a subagent that only returned analysis notes without JSON as incomplete and send it back to finish the modeling step.

If the user requested multiple views, do not finish until every requested view meets that standard.
