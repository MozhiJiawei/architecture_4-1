# Draw.io DSL

Use a structured intermediate model before rendering draw.io XML.

## Minimal Shape

```json
{
  "view": "logic",
  "title": "Logic View",
  "summary": "High-level business structure",
  "style_profile": "ref-default",
  "elements": [
    {
      "id": "gateway",
      "label": "API Gateway",
      "type": "service",
      "group": "edge"
    }
  ],
  "relationships": [
    {
      "source": "gateway",
      "target": "order-service",
      "label": "routes",
      "kind": "sync",
      "inferred": false
    }
  ],
  "groups": [
    {
      "id": "edge",
      "label": "Access Layer"
    }
  ],
  "evidence": [
    {
      "path": "services/gateway/src/main.ts",
      "reason": "Entry point and route registration"
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
- Model groups separately from elements so layout can change without rewriting semantics.
- Keep labels human-readable and short.
