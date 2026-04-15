---
name: generate-4plus1-diagrams
description: Analyze a source repository and generate editable draw.io files for the 4+1 architectural view model. Use when Codex needs to inspect project structure, infer module boundaries and component relationships, produce logic/development/process/physical/scenario views, align output to the reference diagrams in ref/, and validate diagram XML, style constraints, and exported previews.
---

# Generate 4+1 Diagrams

## Quick Start

Use this skill to turn a code repository into five editable `.drawio` architecture diagrams under `docs/architecture/`.

Treat repository analysis as an AI-led task. Explore the repository with intent, guided by the needs of each architectural view. Use scripts only when they reduce repetitive work or improve determinism for rendering and validation.

Always read `ref/` first. Use those images as the visual and structural baseline for the five views.

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
- suggested grouping/layout hints for the renderer

Use [references/view-checklists.md](references/view-checklists.md) to keep the exploration grounded.

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
- `elements`
- `relationships`
- `groups`
- `evidence`
- `uncertainties`
- `style_profile`

Keep the model conservative. If a relationship is inferred rather than explicit, mark it as inferred and cite the evidence that led to it.

See [references/drawio-dsl.md](references/drawio-dsl.md) for the expected shape.

### 5. Render editable draw.io files

Write the final diagrams to `docs/architecture/` as editable `.drawio` files.

Generate at least:
- `docs/architecture/logic-view.drawio`
- `docs/architecture/development-view.drawio`
- `docs/architecture/process-view.drawio`
- `docs/architecture/physical-view.drawio`
- `docs/architecture/scenario-view.drawio`

Prefer deterministic rendering through `scripts/render_drawio.py` or a compatible helper.

### 6. Validate before finishing

Run validation after rendering:
- XML parse check
- style-profile check
- file presence check for all five views
- preview export check
- image inspection for blank or obviously broken output

Use:
- `scripts/validate_drawio.py`
- `scripts/export_diagrams.py`
- `scripts/inspect_exports.py`

If validation fails, fix the model or rendering and run validation again.

## Output Requirements

Always place generated artifacts under `docs/architecture/`.

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
