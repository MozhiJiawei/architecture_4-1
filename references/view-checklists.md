# View Checklists

Use these checklists while exploring the repository.

## Logic View Checklist

- What are the top-level capabilities?
- What names recur across services, modules, and APIs?
- Which systems look external?
- Which components own business rules versus orchestration?
- Which relationships are explicit, and which are inferred?
- Which candidate elements are true responsibilities versus just folders, frameworks, or helper code?
- If multiple files implement one responsibility, should they collapse into one logical element?
- Would a new engineer learn the system shape from this element, or only a code layout detail?
- Is each important relationship backed by repository evidence, not just intuition?
- What should be omitted so the view stays architectural instead of turning into a package map?

## Development View Checklist

- What are the build roots?
- Where are module boundaries declared?
- Which packages are shared utilities versus domain modules?
- Are there layering rules in naming or folder structure?
- Which dependencies point inward versus outward?

## Runtime View Checklist

- Where do requests enter the system?
- What synchronous calls are visible?
- What asynchronous channels exist?
- Which jobs, schedulers, queues, or streams are present?
- Where do retries, caching, and state transitions appear?
- Which actors or external systems must participate for the runtime story to make sense?
- What is the clearest ordering of interactions: tiers, lanes, or sequence-style participants?
- Can you name 3-5 primary runtime paths before listing components?
- For each primary path, can you justify every participant directly from its steps or branches?
- For each primary path, is the participant order readable enough that the trigger, orchestrator, execution branch, and state or delivery boundary are obvious at a glance?
- Would any path benefit from an explicit `participant_order` instead of relying on default group ordering?
- Are any lane labels too long for a readable header, and should they carry a shorter presentation label such as `short_label`?
- Which branches matter enough to show, such as auth failure, cache miss, retry, fallback, or timeout?
- Does each shown branch introduce a new participant, boundary, state transition, approval gate, or materially different outcome?
- Can each important hop be tied back to repository evidence rather than only inferred from naming?
- Does this runtime view explain collaboration structure, rather than drifting into a static module map?
- Which runtime responsibilities should be collapsed into one participant, such as adapter families, tool backends, or helper modules?

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
