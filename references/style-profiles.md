# Style Profiles

Use `ref-default` unless the user provides a different style target.

## ref-default

Derived from the diagrams in `ref/`.

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

- Reuse a restrained palette instead of many unrelated colors.
- Keep container and node styles consistent within a view.
- Use arrows consistently for directionality.
- Avoid ornamental shapes that do not carry architectural meaning.

### Validation hints

Flag output when:
- the page is nearly empty
- labels visibly overflow nodes
- the diagram has no clear grouping structure
- every element uses a different visual style
