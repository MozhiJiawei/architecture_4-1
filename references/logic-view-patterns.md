# Logic View Patterns

Use this reference when building `logic-view.json`.

`references/drawio-dsl.md` defines the shared schema.
`references/renderer-contract.md` defines supported logic kinds and default rendering behavior.
This file defines logic-view modeling strategy.

## Logic-first workflow

Do not start from folders.

Do not start from every service or class name either.

Instead:

1. Enumerate the top-level business capabilities or responsibility areas.
2. Collapse implementation detail into stable architectural responsibilities.
3. Separate internal responsibilities from external systems.
4. Arrange groups as readable layers.
5. Keep only the dependency directions that materially explain the system shape.

When the repository is large, do a bounded evidence pass first:

1. Start from README, architecture docs, top-level package roots, and obvious ingress modules.
2. Confirm recurring business responsibilities before inventing boxes.
3. Treat helper packages, frameworks, and generated code as evidence, not as first-class logical elements.

## Derived Structure

A strong logic view should:
- make the top-level capability set obvious
- show stable responsibility boundaries rather than code layout trivia
- show external systems clearly
- keep dependency directions readable
- preserve explicit versus inferred relationships
- keep layer/group structure obvious enough that the renderer does not have to guess intent
- keep labels short and architectural
- omit helper-heavy detail that would turn the view into a package map

## Layering Rules

For logic views:
- treat each `group` as one architectural layer or responsibility band
- use `layout_hint.order` to define vertical order
- keep rendered relationships within the same layer or adjacent layers when possible
- if a real dependency spans non-adjacent layers, keep it in evidence or mark it `render: false`

## Good Element Choices

Prefer logical elements such as:
- business domain
- subsystem
- orchestration service
- shared capability service
- external dependency
- state-bearing subsystem when it materially shapes responsibilities

Good omissions include:
- folders that do not correspond to stable responsibilities
- DTOs, serializers, schemas, and mappers
- individual framework adapters that do not own business behavior
- helper modules with no architectural boundary of their own
- tests, fixtures, and scripts unless they reveal a true subsystem boundary

## Common failure modes

Avoid these patterns:
- turning the logic view into a package tree
- creating one box per module or directory
- mixing runtime sequencing into logic dependencies
- drawing long skip-level arrows everywhere instead of preserving layered structure
- using labels so detailed that they read like implementation notes
- omitting external systems so the system looks more self-contained than it is
- merging distinct business responsibilities just because they live in one code root
