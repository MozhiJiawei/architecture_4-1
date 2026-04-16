---
name: generate-4plus1-diagrams
description: Analyze a source repository and generate editable draw.io files for the 4+1 architectural view model. Use when Codex needs to inspect project structure, infer module boundaries and component relationships, produce logic/development/runtime/physical/scenario views, align output to the reference diagrams in ref/, and validate diagram XML, style constraints, and exported previews.
---

# Generate 4+1 Diagrams

## Goal

Turn a source repository into one or more editable `.drawio` architecture diagrams that match the 4+1 view model and stay visually aligned with the reference diagrams in `ref/`.

When the user requests only some views, produce only those views.

When the user works in Chinese, keep the intermediate notes, diagram labels, summaries, and review notes in Chinese unless they explicitly ask for English or bilingual output.

Keep temporary artifacts in this skill repository, not in the target repository.

## Agent Setup

Launching subagents is required.

Start one dedicated subagent for each requested view:
- logic
- development
- runtime
- physical
- scenario

Use `gpt-5.4` for every view-owning subagent.

Each subagent should work in an isolated area under:
- `tmp-artifacts/<repo-name>/logic/`
- `tmp-artifacts/<repo-name>/development/`
- `tmp-artifacts/<repo-name>/runtime/`
- `tmp-artifacts/<repo-name>/physical/`
- `tmp-artifacts/<repo-name>/scenario/`

The main agent owns review and completion:
- load the relevant images in `ref/` before dispatching subagents
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
- which 4+1 view the subagent owns
- the required output directory under `tmp-artifacts/<repo-name>/<view>/`
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
- write artifacts only inside its assigned `tmp-artifacts/.../<view>/` area
- treat the intermediate JSON as the subagent's final artifact and stop after writing it and the evidence note
- treat later supervisor messages as incremental guidance unless they explicitly say to stop, restart, or hand off
- do not treat a request for status as permission to exit early

Before launching a subagent, the main agent should preload or summarize the most
relevant instructions from:
- `references/view-checklists.md`
- `references/drawio-dsl.md`
- `references/4plus1-rules.md`
- `references/runtime-view-patterns.md` for runtime view
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

The main agent should then produce:
- an editable `.drawio`
- an exported preview image or SVG
- validation and visual review results

Treat repository understanding as AI-led work. Use scripts to help with rendering, exporting, validation, or repetitive extraction, but do not rely on scripts to invent the architecture for you.

Filter out generated and vendored noise unless the user explicitly wants it included.

Prefer a readable, evidence-backed subset over a bloated diagram.

## Resources

Read these first when needed:
- [references/ref-usage.md](references/ref-usage.md): how to use `ref/` as the visual baseline
- [references/style-profiles.md](references/style-profiles.md): style constraints
- [references/view-checklists.md](references/view-checklists.md): what each view should explain
- [references/drawio-dsl.md](references/drawio-dsl.md): expected intermediate model shape
- [references/runtime-view-patterns.md](references/runtime-view-patterns.md): runtime-view modeling guidance
- [references/4plus1-rules.md](references/4plus1-rules.md): shared architectural rules

Use these scripts in the main-agent completion phase:
- `scripts/render_drawio.py`: render `.drawio` from the intermediate model
- `scripts/validate_drawio.py`: structural and style validation
- `scripts/export_diagrams.py`: export previews from `.drawio`
- `scripts/inspect_exports.py`: inspect exported previews for obvious failures
- `scripts/validate_visual_pipeline.py`: run the validation/export/inspection pipeline in order

For normal view generation, split the workflow into two stages:
1. subagent stage: produce the intermediate JSON and evidence note
2. main-agent stage: run `python scripts/render_drawio.py <json-path> --output-dir <view-dir> --export-previews --preview-dir <view-dir>\\exports --preview-format png`
3. main-agent stage: run `python scripts/validate_visual_pipeline.py <view-dir>\\<view>-view.drawio --exports-dir <view-dir>\\exports`
4. if rendering or validation fails, save the failing command, stderr summary, and current artifact list into `<view-dir>\\render-validation-failure.md` before replying

Do not ask a subagent to render, export, or validate unless the user explicitly overrides this workflow.

## View Notes

For all views:
- keep labels short and readable
- attach evidence to important elements and relationships
- mark inferred relationships as inferred
- say what you intentionally omitted when scope is large

For runtime view:
- prefer runtime collaboration over static package structure
- identify the main runtime paths first
- show lifecycle owners, execution boundaries, state or delivery boundaries, and external systems when they matter
- preserve ordering clearly enough that the renderer does not need to guess the story
- read [references/runtime-view-patterns.md](references/runtime-view-patterns.md) before modeling

## Completion Standard

Do not treat an intermediate JSON file as finished work.

A requested view is complete only when all of these are true:
- the `.drawio` file exists
- the export exists
- validation has run
- the main agent has visually compared the export against the matching `ref/` image

For delegated work, the subagent-side handoff bar is:
- the JSON exists
- the evidence/assumptions note exists
- the final reply includes the absolute paths it wrote plus any unresolved uncertainty that might affect rendering

The parent agent should treat a subagent that only returned analysis notes without JSON as incomplete and send it back to finish the modeling step.

If the user requested multiple views, do not finish until every requested view meets that standard.
