# 3+1 Rules

Use the standard views in this skill as separate but connected explanations of the same system.

## Logic View

Show the major responsibilities of the system:
- business domains
- major services or subsystems
- external systems
- stable dependency directions

Avoid low-level implementation clutter unless it explains a major boundary.

## Development View

Show how the codebase is organized for developers:
- repositories
- packages
- modules
- shared libraries
- ownership or layering boundaries

Prefer compile-time and packaging relationships over runtime chatter.
Prefer maintained code units over raw folders.
When the user names a core use case, filter the development view to the code that realizes that use case before adding shared support modules.

## Runtime View

Show runtime collaboration:
- request paths
- async consumers
- queues
- caches
- jobs
- cross-service collaboration

This view should explain concurrency, communication, and operational behavior.

Keep the runtime view architecturally parallel to the logic view:
- build it from evidence-backed runtime participants and interactions
- preserve explicit versus inferred interaction edges
- prefer readable sequence or collaboration structure over a generic network sketch
- include branches only when they materially explain auth, failure, retries, or state transitions

## Use Case View

Use one or more representative use cases to tie the architecture together.

When the system exposes many first-class user-visible operating modes, treat the use-case view as the index into the rest of the 4+1 model:
- enumerate the core use case set
- render an all-use-cases picture rather than only one canonical journey

Prefer use cases that:
- cross important boundaries
- expose core responsibilities
- explain why the architecture is shaped this way

Prefer classic use-case diagrams when the goal is to explain actors, system boundary, and reused or conditional user goals.

Use:
- actors for external roles
- use cases for user-visible goals
- `include` for mandatory reused behavior
- `extend` for conditional or optional behavior

Avoid turning internal components or step-by-step runtime choreography into use cases.
