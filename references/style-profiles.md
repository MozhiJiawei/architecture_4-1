# Style Profiles

Use `ref-default` unless the user provides a different style target.

## ref-default

Derived from the diagrams in `ref/`.

### Palette roles

Use a restrained, reusable palette. Prefer semantic roles over one-off hex values.
Keep each diagram to 4 semantic color families or fewer unless the user explicitly asks for a richer palette. Treat `neutral` as baseline styling, not as part of that 4-family budget.

Default roles:

- `neutral`: `#f8f9fa / #6c757d`
- `blue` or `entry-surface`: `#dae8fc / #6c8ebf`
- `green` or `capability-runtime`: `#d5e8d4 / #82b366`
- `yellow` or `external-system`: `#fff2cc / #d6b656`
- `purple` or `agent-core`: `#e1d5e7 / #9673a6`
- `state-subsystem`: reuse runtime green unless there is a strong reason to call state out separately
- `automation-subsystem`: reuse runtime green unless the user explicitly wants automation highlighted as its own class

Use the first color as `fillColor` and the second as `strokeColor`. Keep `fontColor` dark unless there is a strong readability reason to change it. Use `color_role` explicitly when you want semantic coloring; do not rely on `type` names to imply palette choices.

### Structural preferences

- Use layered or lane-based organization where the reference suggests it.
- Use grouping containers for related components.
- Keep a clear top-to-bottom or left-to-right flow per diagram.
- Prefer moderate density over maximal completeness.

### Labeling preferences

- Keep labels short and noun-oriented.
- Use consistent naming across views for the same component.
- Use relationship labels only when they add meaning.

### Visual preferences

- Reuse a restrained palette and color by semantic role first.
- When in doubt, collapse related subsystem roles onto the same color instead of adding a fifth semantic family.
- Use stronger fills for grouping containers and slightly calmer node fills when too many saturated blocks reduce readability.
- Keep container and node styles consistent within a view.
- Use arrows consistently for directionality.
- Avoid ornamental shapes that do not carry architectural meaning.

### Validation hints

Flag output when:
- the page is nearly empty
- labels visibly overflow nodes
- the diagram has no clear grouping structure
- every element uses a different visual style
- the semantic palette exceeds 4 families after excluding baseline `neutral` / default colors
