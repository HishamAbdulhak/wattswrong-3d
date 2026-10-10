# AGENTS.md

Guidance for coding agents working in this repository.

## What this is

WattsWrong: a browser 3D "historical replay" of household electricity anomaly findings (REFIT dataset, 2014–15). The entire app — HTML, CSS, JS, and the embedded findings data — is the single file `index.html`. There is no build step, package.json, linter, or test suite.

## Running

```bash
npx serve .
```

Open the printed address, or open `index.html` via `file://`: the hourly series (41k rows) is embedded as `<script type="application/json" id="wattswrong-series">`, generated from `data/timeseries.json` by `python3 embed_series.py` (re-run it after changing that file). three.js (0.169.0), its addons and all textures/HDRI/sofa glTF come from CDNs, so internet access is needed for 3D.

Verification is manual in a browser, plus the console API: `window.WattsWrong.getState()`, `window.WattsWrong.setTime('2014-11-26T11:00:00Z')`, `window.WattsWrong.load({manifest, findings, timeseries})`.

## Architecture of `index.html`

The JS is minified-style (one function per line, no whitespace) inside one `<script type="module">`. Search by function name rather than reading linearly. Sections are delimited by `// ====` banner comments:

1. **`ASSETS`** (top of module) — every external URL, texture map, glTF dependency and licence. Self-hosting means editing only this object. `README.md`'s licence table mirrors it.
2. **Data interface** (`Data` object) — the only place derived values are computed. Raw manifest/findings are embedded in `<script type="application/json" id="wattswrong-data">` and normalised by `Data.load`. Rendering and UI read derived views only (`Data.home`, `Data.meter`, `Data.cost`, `Data.timeline`, `Data.snapshot`), never raw records. Data contract rules (activity window `detected_ts <= t < end_ts + 1h`, fixed 0.50/0.75 strength bands, cost = prefix sum of positive residuals × 0.444, meter costs never summed because aggregate and appliance readings overlap) are documented in README "Data interface" — keep them exact.
3. **Engine load** — three.js modules are dynamically `import()`ed in a top-level `try`. On failure (or if `boot()` throws) the app runs `startTableOnly()`: the accessible replay table and controls must keep working without WebGL.
4. **Scene construction** — mostly procedural (`neighbourhood`, `house`, `buildInterior`, furniture helpers). `material()` caches by color+params and picks `MeshPhysicalMaterial` only when a physical-only property (transmission, sheen, anisotropy, …) is passed, otherwise `MeshStandardMaterial`. `batch()` merges static meshes per material after build; meshes flagged `userData.interactive` or `userData.keep` are excluded. Interiors are built lazily on `openHome` and torn down by `disposeInterior` (which must skip `sharedMaterials` / `geometryCache`). While inside, the interior grows to `INTERIOR_SCALE` during the camera flight, and the other homes plus the selected home's garden are hidden via `h.hidden` (restored in `leaveHome`). Metered appliances get per-mesh material clones so `updateStatus` can tint them with the status colour.
5. **View controller / accessible HTML** — interaction is click-only: hover never opens a card; `choose()` shows a card on first click; a second click on the same home enters it, on the same meter opens the dashboard (`#dash`, `openDash`/`renderDash`, plain HTML + SVG so it works without WebGL). The dashboard and the `#recap` story read `Data.focus` (incl. `highlights`), `Data.history`/`Data.dayLevels` (calm streak calendar), `Data.splits`, `Data.recap`, `Data.chart` and the view window `Data.from`/`Data.to` (`setRange`). Playback calls the cheap `updateClock()` every frame and the full `updateUI()` about 10×/s. tooltips, placards, timeline, table, keyboard routes. `reinitialize()` runs after every `WattsWrong.load`; `updateUI()` after time changes.
6. **Rendering** — two composers: `bloomComposer` renders the scene with non-bloom meshes swapped to `darkMaterial` (selective bloom via `userData.bloom`), then `composer` does scene + SSAO + bloom composite + FXAA. Graphics quality `high` ("Sharper") vs `balanced` ("Faster") is set in `setQuality`. `renderSelective()` runs every frame, so avoid per-frame allocations and full-scene traversals there.

Homes come from the manifest: its sites fill Homes A–D in order (`HOMES`, `Data.siteAt`, `bindHomes()` after every load), and a home without a site shows the no-data placard. The embedded run has two sites (A and B); C and D are in progress and will be filled by their own datasets. Never add per-site checks (`id==='house1'`): interiors place metered appliances by the site's channels (`has(ch)` in `buildInterior`).

Use the terms in `GLOSSARY.md` for UI copy (e.g. finding, detection strength, extra cost, confirmation time); never add emoji to the interface.

## Other files

- `DELIVERABLE.md` — a hand-made snapshot of `index.html` (fenced) plus the README. It does not regenerate itself and will drift from `index.html` after edits.
- `WattsWrong-3D/` — an older duplicate copy of the project; untracked (in `.gitignore`).

## Agent skills

### Issue tracker

Issues and specs are GitHub issues on HishamAbdulhak/wattswrong-3d, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default triage labels (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` at the root, ADRs in `backend/docs/adr/`. See `docs/agents/domain.md`.
