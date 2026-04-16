# Draw.io DSL

Use a structured intermediate model before rendering draw.io XML.

## Minimal Shape

```json
{
  "view": "logic",
  "title": "Logic View",
  "summary": "High-level business structure",
  "layout_suggestion": {
    "strategy": "stacked-groups"
  },
  "style_profile": "ref-default",
  "palette_overrides": {
    "roles": {
      "agent-core": {
        "fillColor": "#e1d5e7",
        "strokeColor": "#9673a6",
        "fontColor": "#1f2937"
      }
    }
  },
  "elements": [
    {
      "id": "gateway",
      "label": "API Gateway",
      "type": "service",
      "group": "edge",
      "color_role": "blue",
      "evidence_ids": ["ev-gateway-entry"]
    }
  ],
  "relationships": [
    {
      "source": "gateway",
      "target": "order-service",
      "label": "routes",
      "kind": "sync",
      "inferred": false,
      "evidence_ids": ["ev-gateway-routes"]
    }
  ],
  "groups": [
    {
      "id": "edge",
      "label": "Access Layer",
      "layout_hint": {
        "order": 1
      }
    }
  ],
  "evidence": [
    {
      "id": "ev-gateway-entry",
      "path": "services/gateway/src/main.ts",
      "reason": "Entry point and route registration"
    },
    {
      "id": "ev-gateway-routes",
      "path": "services/gateway/src/routes.ts",
      "reason": "Gateway routes requests to order-service"
    }
  ],
  "uncertainties": [
    "Queue topology inferred from configuration only"
  ]
}
```

## Modeling Rules

- Keep stable IDs per element.
- Distinguish explicit and inferred relationships.
- Keep evidence paths close to the claims they support.
- Prefer evidence entries with stable `id` values and reference them from elements and relationships with `evidence_ids`.
- Model groups separately from elements so layout can change without rewriting semantics.
- Use optional `layout_suggestion` and per-group `layout_hint` fields to preserve a top-to-bottom layered layout. Prefer `layout_suggestion.strategy = "stacked-groups"` and use `layout_hint.order` to define layer order.
- For logic-view DSL, treat each `group` as one vertical layer. The renderer assumes layers are stacked from top to bottom by ascending `layout_hint.order`.
- Only model relationships that connect components within the same layer or in adjacent layers. Do not model direct rendered connections that skip one or more layers.
- If a real dependency spans non-adjacent layers, keep it in evidence or mark it `render: false` instead of drawing it directly.
- Keep labels human-readable and short.
- Add optional top-level fields such as `scope`, `description`, `omissions`, or `review_notes` when they help preserve analysis intent before rendering.

## Runtime View Conventions

Use the same intermediate-model discipline for the runtime view that you use for the logic view.

- Use `view: "runtime"` in models and outputs.
- Prefer including `description`, `scope`, and `omissions` so the runtime story stays explicit when the model is rendered later.
- `scope` may be a short string or a structured object when the repository is large enough that the included surfaces, focus, or reading strategy must be made explicit.
- Model runtime participants explicitly in `elements`, such as actors, gateways, services, jobs, queues, caches, databases, and external systems.
- Use `relationships` to capture time-ordered interactions. Keep `kind` explicit, such as `sync`, `async`, `cache`, `event`, or `auth`.
- Prefer stable relationship `id` values in runtime models so path objects can reference ordered steps directly.
- Preserve temporal or lane order in `groups` and `layout_hint.order` so the renderer can produce a readable execution narrative.
- Prefer `layout_suggestion.primary_paths` to name the main runtime paths that the model preserves.
- Prefer a top-level `primary_paths` array of objects when the runtime story needs explicit ordering. Include `id`, `label`, `summary`, `entrypoint`, ordered `main_step_ids`, and optional `branches`.
- When one path's lane order matters for readability, add an explicit per-path hint such as `participant_order` so the renderer does not have to guess.
- Prefer `render_hints.runtime.preferred_diagram = "sequence-collaboration"` when the later render should read like a collaboration or sequence-style diagram rather than a generic topology.
- Attach `evidence_ids` to important interactions just as rigorously as for logic-view dependencies.
- Mark inferred runtime hops with `inferred: true` when they come from configuration, naming, tracing, or repeated usage patterns instead of one explicit implementation point.
- Keep branch edges minimal and meaningful. Show auth, failure, retry, cache-miss, approval, or fallback branches only when they explain behavior the main path would otherwise hide. If a branch does not introduce a new participant, boundary, state transition, or materially different outcome, fold it back into the main path.
- Keep edge labels short and action-oriented so they survive sequence-style or collaboration-style layouts.
- Start by naming 3-5 primary runtime paths, then derive participants from those paths instead of from the directory tree.
- Runtime renderers should scope participants per `primary_path`. A scene should only show elements touched by its ordered steps or explicit branches.
- If a lane header would become crowded, prefer an element-level presentation field such as `short_label` instead of forcing the full raw label into every rendered section.
- Collapse helper-heavy implementation detail into the participant that owns the runtime responsibility unless the helper has its own lifecycle or queue boundary.
- In large repositories, include line-aware evidence when practical, for example `lines: "120-180"`, so later review can verify the runtime claim without rereading the whole file.
- Runtime views are usually incomplete without some representation of state persistence and result delivery. If either is absent, explain why in `omissions` or `review_notes`.

## Coloring Fields

- `style_profile`: select a named palette and default styling behavior.
- `palette_overrides`: optional top-level overrides for `defaults.group`, `defaults.node`, `defaults.edge`, or named `roles`.
- `color_role`: assign a semantic color role to a group, element, or relationship. The renderer only applies semantic palette roles when `color_role` is present.
- `style`: apply a local override with any subset of `fillColor`, `strokeColor`, and `fontColor`.
- Prefer a small role vocabulary such as `entry-surface`, `agent-core`, `capability-runtime`, `external-system`, `state-subsystem`, `blue`, `green`, `yellow`, `purple`, or `neutral`.
- Keep any single diagram to 4 semantic color families or fewer by default. `neutral` is baseline styling and does not count against that budget.

Example:

```json
{
  "id": "agent-core",
  "label": "Orchestrator",
  "type": "orchestrator",
  "group": "core",
  "color_role": "agent-core",
  "style": {
    "fontColor": "#111827"
  }
}
```
