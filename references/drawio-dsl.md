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
- Add optional top-level fields such as `scope`, `description`, or `omissions` when they help preserve analysis intent before rendering.

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
  "label": "AIAgent",
  "type": "orchestrator",
  "group": "core",
  "color_role": "agent-core",
  "style": {
    "fontColor": "#111827"
  }
}
```
