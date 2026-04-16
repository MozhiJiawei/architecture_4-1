# 4+1 Rules

Use the five standard views as separate but connected explanations of the same system.

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

## Physical View

Show deployment and infrastructure:
- containers
- hosts or nodes
- clusters
- middleware
- databases
- storage
- networking or ingress

Use evidence from deployment files, infrastructure code, CI/CD files, and production-oriented config.

## Scenario View

Use one or more representative journeys to tie the architecture together.

Prefer scenarios that:
- cross important boundaries
- expose core responsibilities
- explain why the architecture is shaped this way

Sequence diagrams are often appropriate here.
