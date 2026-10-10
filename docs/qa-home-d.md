# Home C and D garage verification

Issue #8, checked 11 October 2026.

Home D now has a single-storey side annex with a roller door and driveway.
Its lazy downstairs garage contains only the garage fridge and garage freezer;
the fridge-freezer remains in the kitchen. Channel presence selects the layout,
including when a new manifest rebinds the street. The camera accommodates the
wider floor plan. Nearby trees hide on entry and restore on exit.

## Automated checks

With the app's pinned Three.js 0.169.0 package available locally:

```sh
node scripts/check-home-d.mjs /absolute/path/to/three-package
```

The check runs the actual scene helpers and data model with Three.js, using the
embedded frozen findings. It verifies exact Home C and D appliance placement, batching,
inherited garage scaling, tint activation/reset on every metered channel, three
build/dispose cycles, preservation of shared materials/cached geometry, and the
existing A/B meter layouts. It also checks that neighbourhood batching keeps
tree trunks and foliage together for visibility changes. Canvas serialization
warnings are expected from the test's minimal canvas stub.

The extracted application module passes `node --check`; `git diff --check` passes.

## Browser checks

Served the unchanged static app with `python -m http.server` on loopback and
checked it in Chromium with WebGL:

- The street shows the attached garage and roller door.
- Home D opens with both floors; downstairs shows the kitchen and garage clearly.
- All four metered scene buttons open the matching dashboards on the second click.
- Upstairs hides garage controls; returning to the street restores the exterior.
- Entry/exit and floor switching work after reloading the final change.

No animation-loop code was added or changed. Garage static meshes are batched;
appliance tinting reuses the existing status path. Tree geometry remains batched
per tree so it can be hidden as a unit. No quantitative FPS benchmark was run.
