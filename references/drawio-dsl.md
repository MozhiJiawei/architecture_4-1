# Draw.io DSL

Use a structured intermediate model before rendering draw.io XML.

This file defines the shared schema only.

For renderer-supported `type` / `kind` values and default rendering behavior, read [`renderer-contract.md`](renderer-contract.md).
For view-specific modeling strategy, read the matching `*-view-patterns.md` file.

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

## Shared Top-Level Fields

Common top-level fields across views:
- `view`
- `title`
- optional `summary`
- optional `description`
- optional `scope`
- optional `omissions`
- optional `uncertainties`
- optional `review_notes`
- optional `layout_suggestion`
- optional `style_profile`
- optional `palette_overrides`
- optional `groups`
- optional `elements`
- optional `relationships`
- optional `evidence`

View-specific top-level fields may exist when a matching `*-view-patterns.md` file defines them.

## Shared Modeling Rules

- Keep stable IDs per element.
- Distinguish explicit and inferred relationships.
- Keep evidence paths close to the claims they support.
- Prefer evidence entries with stable `id` values and reference them from elements and relationships with `evidence_ids`.
- Model groups separately from elements so layout can change without rewriting semantics.
- Keep labels human-readable and short.
- Add optional top-level fields such as `scope`, `description`, `omissions`, or `review_notes` when they help preserve analysis intent before rendering.
- Subagents should treat the intermediate JSON file as the primary handoff artifact. Put unresolved caveats in `uncertainties` or `review_notes`, not in ad hoc side files.

## Shared Element Shape

Elements are usually objects with fields such as:
- `id`
- `label`
- `type`
- optional `group`
- optional `boundary`
- optional `color_role`
- optional `style`
- optional `render`
- optional `evidence_ids`

Additional element fields may exist when a view pattern defines them.

## Shared Relationship Shape

Relationships are usually objects with fields such as:
- `source`
- `target`
- optional `id`
- optional `label`
- optional `kind`
- optional `inferred`
- optional `render`
- optional `color_role`
- optional `style`
- optional `evidence_ids`

The allowed `kind` values and rendering behavior are defined in [`renderer-contract.md`](renderer-contract.md).

## Shared Group Shape

Groups are usually objects with fields such as:
- `id`
- `label`
- optional `layout_hint`
- optional `color_role`
- optional `style`

## Shared Evidence Shape

Evidence entries are usually objects with fields such as:
- `id`
- `path`
- optional `lines`
- `reason`

## Coloring Fields

- `style_profile`: select a named palette and default styling behavior.
- `palette_overrides`: optional top-level overrides for `defaults.group`, `defaults.node`, `defaults.edge`, or named `roles`.
- `color_role`: assign a semantic color role to a group, element, or relationship. The renderer only applies semantic palette roles when `color_role` is present.
- `style`: apply a local override with any subset of `fillColor`, `strokeColor`, and `fontColor`.

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
