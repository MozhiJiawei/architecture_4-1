# Reference Usage

Treat `ref/` as the canonical example set for this skill.

## How to use the reference images

1. Identify which image corresponds to each of the four 3+1 views.
2. Note the recurring structure:
   - grouping boxes
   - lanes or tiers
   - component density
   - arrow usage
   - label granularity
3. Abstract those observations into reusable style constraints.
4. Apply the constraints to the target repository without copying irrelevant domain details from the example.
5. During visual review, load both the exported preview and the matching reference image into vision at the same time and compare them explicitly; do not stop at a text-only reminder.

## What to borrow

- overall readability target
- grouping logic
- level of abstraction
- placement of infrastructure and middleware
- how sequence or use-case information is narrated
- the language discipline of labels and captions when the target output language is Chinese

## What not to borrow blindly

- domain-specific names from the sample
- exact component counts
- exact topology when the target repository differs
- decorative elements without architectural meaning
- English label leakage caused by repository identifiers when the requested output language is Chinese
