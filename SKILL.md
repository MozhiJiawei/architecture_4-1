---
name: generate-4plus1-diagrams
description: Analyze a source repository and generate editable draw.io files for the 4+1 architectural view model. Use when Codex needs to inspect project structure, infer module boundaries and component relationships, produce logic/development/process/physical/scenario views, align output to the reference diagrams in ref/, and validate diagram XML, style constraints, and exported previews.
---

# Generate 4+1 Diagrams

## Quick Start

Use this skill to turn a code repository into five editable `.drawio` architecture diagrams.

Treat repository analysis as an AI-led task. Explore the repository with intent, guided by the needs of each architectural view. Use scripts only when they reduce repetitive work or improve determinism for rendering and validation.

Match the language of the output to the user's request. When the user is working in Chinese, produce the intermediate model, diagram labels, summaries, and review notes in Chinese unless they explicitly ask for bilingual or English output.

Do not leak English into diagram labels just because the repository code is in English. When producing Chinese output, keep group labels, node labels, edge labels, summaries, and review notes in Chinese. Only keep English when it is a literal product name, package name, protocol name, or API surface that would become less clear if translated.

Always read `ref/` first. Use those images as the visual and structural baseline for the five views.

When analyzing a different repository, keep temporary artifacts in this skill repository, not in the target repository. Use `tmp-artifacts/` at the root of this repository for intermediate JSON, notes, exports, and other scratch outputs. Treat that directory as disposable working state.

When scanning a repository, aggressively filter out generated and vendored noise unless the user explicitly wants those layers analyzed. Typical exclusions include `node_modules/`, `.venv/`, `dist/`, `build/`, coverage outputs, lockfile mirrors, vendored SDKs, generated docs, and binary assets that do not define architectural responsibilities.

Prefer a per-repository layout under `tmp-artifacts/`:
- `tmp-artifacts/<repo-name>/logic-view.json`
- `tmp-artifacts/<repo-name>/development-view.json`
- `tmp-artifacts/<repo-name>/process-view.json`
- `tmp-artifacts/<repo-name>/physical-view.json`
- `tmp-artifacts/<repo-name>/scenario-view.json`

If you need a separate render scratch area before finalizing outputs, use:
- `tmp-artifacts/<repo-name>/rendered/`

## Workflow

### 1. Read the reference views

Inspect the images in `ref/` before exploring the target repository.

Extract:
- the mapping between the five views and their expected content
- recurring visual structure such as lanes, containers, grouping boxes, and edge styles
- naming conventions and label density
- how much information each view should carry before it becomes unreadable

Use [references/ref-usage.md](references/ref-usage.md) and [references/style-profiles.md](references/style-profiles.md) to normalize those observations into explicit constraints.

### 2. Explore the repository by view

Do not rely on a fixed global scan as the primary analysis strategy.

Instead, analyze the repository from five angles:
- Logic view: identify domains, major capabilities, service boundaries, external systems
- Development view: identify modules, packages, repos, libraries, dependency directions
- Process view: identify runtime collaboration, request flow, async flow, caches, queues, background jobs
- Physical view: identify deployment units, containers, nodes, clusters, middleware, storage, networking clues
- Scenario view: identify representative user or system journeys that best explain the architecture

When sub-agents are available and the user has explicitly asked for them, delegate each view to a focused sub-agent. Otherwise perform the same exploration sequentially in the main thread.

For each view, produce:
- a short narrative of what the view explains
- candidate elements
- candidate relationships
- supporting evidence from repository files
- uncertainties or assumptions
- suggested grouping/layout hints for the renderer, with groups ordered as top-to-bottom layers and any non-adjacent relationships explicitly suppressed from rendering

Use [references/view-checklists.md](references/view-checklists.md) to keep the exploration grounded.

For a first pass on a new repository, prefer completing one view end to end before attempting all five.

Start with the logic view unless the user asks for a different view first. A good logic-view pass is the fastest way to discover:
- whether the repository has clear subsystem boundaries
- which concepts are business responsibilities versus implementation details
- which evidence patterns are easy or hard to extract reliably
- what the intermediate model must preserve for later rendering

### 3. Use scripts only where they help

Repository understanding is AI-led. Scripts are optional helpers, not the primary source of architectural judgment.

Use or create scripts when they help with:
- extracting repetitive signals from large repos
- transforming an intermediate model into draw.io XML
- validating XML structure and style constraints
- exporting previews and checking for obvious visual failures

Do not move architectural inference into scripts unless the rule is narrow, deterministic, and clearly reusable.

### 4. Build an intermediate view model

Before rendering, express each view as structured data.

Prefer a JSON document per view with fields like:
- `view`
- `title`
- `summary`
- `layout_suggestion`
- `elements`
- `relationships`
- `groups`
- `evidence`
- `uncertainties`
- `style_profile`

Keep the model conservative. If a relationship is inferred rather than explicit, mark it as inferred and cite the evidence that led to it.

Treat the intermediate model as the contract between repository analysis and rendering. Do not let the renderer rediscover architecture from raw files.

For the logic view in particular:
- prefer responsibilities, user-facing capabilities, stable subsystems, and external systems
- do not mirror source directories unless the directory boundary is itself an architectural boundary
- collapse low-level helper modules into a higher-level subsystem when they do not represent a distinct responsibility
- keep the number of top-level elements readable; merge noisy implementation fragments into one logical element
- attach evidence to each important element or relationship, either directly with `evidence_ids` or through a nearby evidence entry
- if a boundary or dependency is only suggested by naming, config, or repeated usage patterns, keep it but mark it as inferred
- prefer node labels without an extra English type suffix unless the user explicitly asks for type annotations

When the repository is large, explicitly narrow scope in the model with a short omission note rather than pretending the view is exhaustive.

See [references/drawio-dsl.md](references/drawio-dsl.md) for the expected shape.

### 5. Render editable draw.io files

Write the final diagrams to the user-requested destination as editable `.drawio` files.

Default destination:
- `docs/architecture/`

If the user asks for all artifacts to stay in a working area, scratch area, or temporary area, place the final `.drawio` files there instead. In this repository, that means using:
- `tmp-artifacts/<repo-name>/`

When the user explicitly asks for `tmp-artifacts`, treat that as the canonical destination for both intermediate models and final exported `.drawio` files.

Generate at least one editable `.drawio` file per 4+1 view.

Default filenames:
- `logic-view.drawio`
- `development-view.drawio`
- `process-view.drawio`
- `physical-view.drawio`
- `scenario-view.drawio`

Prefer deterministic rendering through `scripts/render_drawio.py` or a compatible helper.

### 6. Validate before finishing

Run validation after rendering:
- XML parse check
- style-profile check
- file presence check for all five views
- preview export check
- image inspection for blank or obviously broken output
- AI-assisted visual comparison between exported previews and `ref/`

Use:
- `scripts/validate_drawio.py`
- `scripts/export_diagrams.py`
- `scripts/inspect_exports.py`

If validation fails, fix the model or rendering and run validation again.

When the renderer reports edge conflicts, do not respond by deleting all cross-group edges or stripping the diagram down indiscriminately. Keep the diagram semantically intact and prefer the smallest possible set of `render: false` suppressions needed to resolve the specific conflicts the renderer reports.

Treat validation as two distinct passes:
- Rules pass: `validate_drawio.py` should catch structural and style violations such as missing grouping containers, inconsistent arrow usage, disallowed font settings, or palette drift.
- Visual pass: export previews, then inspect them against `ref/`. Use the exported images plus the matching reference images as input for a visual review that looks for layout, density, grouping, readability, and semantic omissions that rule-based validation cannot catch.

Run the validation steps sequentially, not in parallel, because preview export depends on rendered `.drawio` files and image inspection depends on the exported previews. Prefer:
- `scripts/validate_visual_pipeline.py`

If you run the underlying commands manually, keep the order strict:
1. `scripts/validate_drawio.py`
2. `scripts/export_diagrams.py`
3. `scripts/inspect_exports.py`
4. load both the exported preview and the matching `ref/` image into vision and compare them directly

## Output Requirements

Unless the user asks otherwise, follow the destination and scratch-space policy from Quick Start and Render editable draw.io files.

Unless the user asks otherwise, produce:
- five editable `.drawio` files
- exported preview images or SVGs
- a short summary of evidence, assumptions, and open questions

## Practical Rules

- Prefer evidence over confidence.
- Prefer a readable subset over an overstuffed diagram.
- Keep labels short enough to survive export.
- Match the reference diagrams without copying irrelevant details.
- Preserve uncertainty explicitly instead of inventing false precision.
- When the repository is too large, narrow the scope and say what was omitted.

## References

- [references/4plus1-rules.md](references/4plus1-rules.md)
- [references/view-checklists.md](references/view-checklists.md)
- [references/drawio-dsl.md](references/drawio-dsl.md)
- [references/style-profiles.md](references/style-profiles.md)
- [references/ref-usage.md](references/ref-usage.md)
