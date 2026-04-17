# Runtime View Patterns

Use this reference when building `runtime-view.json` for systems with multiple execution modes, asynchronous workers, platform adapters, or agent loops.

`references/drawio-dsl.md` defines the shared schema.
`references/renderer-contract.md` defines supported runtime kinds and default rendering behavior.

## Runtime-first workflow

Do not start by listing modules.

Instead:

1. Identify 3-5 primary runtime paths.
2. Name the runtime participants that appear on those paths.
3. Collapse implementation detail behind the participant that owns the runtime responsibility.
4. Encode only the interactions needed to explain execution.

In large repositories, insert a bounded evidence step before path modeling:

1. Pick roughly 6-12 candidate files that are most likely to define entrypoints, orchestration, persistence, delivery, or delegation.
2. Explicitly exclude generated or vendored trees before scanning further.
3. Use docs and READMEs to seed hypotheses, then confirm each chosen runtime path with code-level evidence.

For many agentic or platform-style repositories, the primary paths are often:
- interactive CLI turn
- messaging or API ingress turn
- scheduled automation or cron turn
- tool execution or delegation branch

Not every repository needs all four, but most large agent systems need at least two distinct runtime paths.

## Participant classes

Prefer participant classes like:
- human or external trigger
- ingress controller
- session or routing layer
- orchestrator or agent loop
- memory or state subsystem
- tool dispatcher
- async worker or delegated executor
- delivery or adapter layer
- external model or external service

Do not create a separate participant for every helper module. Merge helpers into the participant that owns the runtime responsibility unless the helper has an independent lifecycle.

For rendered runtime sections, include only the participants referenced by that primary path or its explicit branches. Do not render a global participant superset for every scene.

Before finalizing a large-repo runtime view, do two quick audits per primary path:
- participant audit: every rendered participant must be justifiable from a main step or explicit branch
- ordering audit: make the lane order readable from left to right, usually trigger -> ingress -> orchestrator -> execution branch -> state or delivery boundary

If the default ordering would still be awkward, record an explicit `participant_order` on that path instead of hoping the renderer guesses correctly.

If a participant name is architecturally right but visually too long for a lane header, keep the precise label in `label` and add a shorter presentation label such as `short_label`.

Before keeping a branch, apply a branch-value test:
- keep it when it introduces a new participant, boundary crossing, state change, approval gate, retry/fallback path, or materially different outcome
- fold it back into the main path when it only restates a normal step without changing who participates or what boundary is crossed

## Quality bar for `runtime-view.json`

A strong runtime-view intermediate model should:
- explain who starts the work
- explain which component owns the turn or job lifecycle
- show where model calls happen
- show where tool execution or background execution branches off
- show where state is loaded or persisted
- show how results get streamed, delivered, or returned
- separate explicit edges from inferred edges
- keep labels short enough for future arrows or sequence lanes
- give every primary path at least one entrypoint evidence file and one lifecycle-owner evidence file
- keep the path list readable enough that a renderer can turn it into numbered sequence steps without reverse-engineering prose
- include review-oriented notes when a large-repo simplification or omission could otherwise be mistaken for ignorance
- keep each primary path to the minimum participant set that still explains the behavior; if the path needs many adapters or helpers, collapse them behind the owner participant
- when a path gets visually wide, prefer splitting it into another primary path over keeping weak-value participants in the same panel

If the diagram would be unreadable without full sentences on edges, the participants are probably too granular.

## Required top-level fields

For runtime-view models, prefer including these top-level fields in addition to the shared DSL:
- `description`
- `scope`
- `omissions`
- `layout_suggestion.primary_paths`
- `primary_paths`
- `render_hints.runtime`

When the repository is large, `scope` can be an object instead of a plain string, for example:
- `focus`
- `included_surfaces`
- `reading_strategy`

These fields help later rendering preserve the runtime story instead of flattening into a topology graph.

## Preferred `primary_paths` shape

When the runtime story matters more than topology completeness, prefer a top-level `primary_paths` array with objects like:

```json
{
  "id": "gateway-turn",
  "label": "Messaging Gateway Turn",
  "summary": "One-sentence runtime story",
  "entrypoint": "src/ingress/gateway.py:start",
  "main_step_ids": ["rel-a", "rel-b", "rel-c"],
  "branches": [
    {
      "label": "Interruption Branch",
      "when": "same session receives a new message",
      "step_ids": ["rel-x"]
    }
  ]
}
```

This keeps ordering, branching, and readability explicit without forcing the renderer to infer sequence from the full relationship graph.

## Recommended `layout_suggestion`

When the repository has a clear execution narrative, prefer:

```json
{
  "strategy": "runtime-lanes",
  "orientation": "left-to-right",
  "lane_style": "participant-sequence",
  "primary_paths": ["path-a", "path-b"]
}
```

Use `groups` as ordered runtime lanes or phases, not merely ownership buckets.

## Relationship patterns

Prefer a small set of runtime `kind` values:
- `sync`
- `async`
- `event`
- `stream`
- `state`
- `auth`
- `cache`

Do not invent a new kind for each edge unless the distinction materially affects runtime understanding.

Also prefer:
- stable relationship `id` values so paths can reference steps directly
- one short action label per edge
- one architectural meaning per edge; split overloaded edges if a single label would hide ordering
- line-aware evidence when a file is large or the runtime claim is subtle

## Good omissions

Good omissions include:
- static web assets
- packaging or release automation unrelated to the runtime story
- tests, docs, examples, and fixtures
- every individual platform adapter when a shared adapter layer explains the runtime better
- every individual tool backend when a single tool-dispatch edge is enough

## Common failure modes

Avoid these patterns:
- turning the runtime view into a package map
- showing every queue, callback, or helper even when they do not change the main runtime story
- omitting state and delivery surfaces so the system looks stateless
- omitting delegation or background execution in agent systems
- drawing only the happy path when auth, retry, cache, or delivery behavior is architecturally important
- using docs alone to define a primary path when the code-level entrypoint or lifecycle owner was never confirmed
- encoding the whole runtime sequence in `summary` paragraphs instead of ordered step references
