# View Checklists

Use these checklists while exploring the repository.

## Logic View Checklist

- What are the top-level capabilities?
- What names recur across services, modules, and APIs?
- Which systems look external?
- Which components own business rules versus orchestration?
- Which relationships are explicit, and which are inferred?

## Development View Checklist

- What are the build roots?
- Where are module boundaries declared?
- Which packages are shared utilities versus domain modules?
- Are there layering rules in naming or folder structure?
- Which dependencies point inward versus outward?

## Process View Checklist

- Where do requests enter the system?
- What synchronous calls are visible?
- What asynchronous channels exist?
- Which jobs, schedulers, queues, or streams are present?
- Where do retries, caching, and state transitions appear?

## Physical View Checklist

- What deployment files are present?
- Are there container images, compose files, or Kubernetes manifests?
- Which middleware products are configured?
- What storage systems appear?
- What network edges or ingress clues exist?

## Scenario View Checklist

- Which user journeys or system flows best explain the architecture?
- Which scenario touches the most important boundaries?
- What happy path should be shown?
- What failure or authorization branch matters enough to include?
- Which components must appear for the scenario to make sense?
