# AGENTS.md

Guidance for coding agents working in this repository.

## What this is

WattsWrong: a browser 3D "historical replay" of household electricity anomaly findings (REFIT dataset, 2014–15). The entire app — HTML, CSS, JS, and the embedded findings data — is the single file `index.html`. The static app has no build step, package.json, linter, or test suite. The independent offline Python backend lives in `backend/` and has its own lockfile and pytest suite.

## Running

```bash
npx serve .
```

Open the printed address, or open `index.html` via `file://`: the manifest, findings and hourly series (81k rows) are embedded as `<script type="application/json">` blocks (`wattswrong-data`, `wattswrong-series`), written from the backend's exports by `uv run --locked python -m pipeline.embed` in `backend/`. three.js (0.169.0), its addons and all textures/HDRI/sofa glTF come from CDNs, so internet access is needed for 3D.

Verification is manual in a browser, plus the console API: `window.WattsWrong.getState()`, `window.WattsWrong.setTime('2014-11-26T11:00:00Z')`, `window.WattsWrong.load({manifest, findings, timeseries})`.

## Offline backend

From `backend/`, run `uv sync --locked`, then `uv run --locked python -m pytest -q pipeline`. Rebuild hourly inputs with `uv run --locked python -m pipeline.ingest data/raw/refit/CLEAN_House1.csv house1` and the corresponding House 3, 10 and 18 commands. Check the exports with `uv run --locked python -m pipeline.validate`. Raw-file sources and MD5s are in README "Offline backend".

Layout: `pipeline/` (ingest, `sites.py` site and channel maps, labels, model, `run.py`, evaluate, validate, `embed.py`, and their `test_*.py`), `contracts/` (locked JSON schemas), `config/config.json` (frozen), `docs/adr/` (ADRs 0001–0014), `reports/` (the run's lock, matches and the disclosed crashed first attempt), `artifacts/<run_id>/` (parquet copies) and `web/public/data/` (the exports the app embeds). Raw data and hourly intermediates under `data/` are git-ignored. All runtime paths resolve inside `backend/`; nothing depends on another checkout. `.vercelignore` keeps `backend/` out of the deployment. Preserve the frozen config. Never run `pipeline.run tune`, and never re-run `pipeline.run final`: the frozen run over four sites is done, its lock is `reports/metrics_final.json`, and any re-run needs the owner's go-ahead and a logged `--rerun-reason` (ADR 0011). Its exports are in `backend/web/public/data/`; `pipeline.embed` validates them and writes them into `index.html`.

## Architecture of `index.html`

The JS is minified-style (one function per line, no whitespace) inside one `<script type="module">`. Search by function name rather than reading linearly. Sections are delimited by `// ====` banner comments:

1. **`ASSETS`** (top of module) — every external URL, texture map, glTF dependency and licence. Self-hosting means editing only this object. `README.md`'s licence table mirrors it.
2. **Data interface** (`Data` object) — the only place derived values are computed. Raw manifest/findings are embedded in `<script type="application/json" id="wattswrong-data">` and normalised by `Data.load`. Rendering and UI read derived views only (`Data.home`, `Data.meter`, `Data.cost`, `Data.timeline`, `Data.snapshot`), never raw records. Data contract rules (activity window `detected_ts <= t < end_ts + 1h`, fixed 0.50/0.75 strength bands, cost = prefix sum of positive residuals × 0.444, meter costs never summed because aggregate and appliance readings overlap) are documented in README "Data interface" — keep them exact.
3. **Engine load** — three.js modules are dynamically `import()`ed in a top-level `try`. On failure (or if `boot()` throws) the app runs `startTableOnly()`: the accessible replay table and controls must keep working without WebGL.
4. **Scene construction** — mostly procedural (`neighbourhood`, `house`, `buildInterior`, furniture helpers). `material()` caches by color+params and picks `MeshPhysicalMaterial` only when a physical-only property (transmission, sheen, anisotropy, …) is passed, otherwise `MeshStandardMaterial`. `batch()` merges static meshes per material after build; meshes flagged `userData.interactive` or `userData.keep` are excluded. Interiors are built lazily on `openHome` and torn down by `disposeInterior` (which must skip `sharedMaterials` / `geometryCache`). While inside, the interior grows to `INTERIOR_SCALE` during the camera flight, and the other homes plus the selected home's garden are hidden via `h.hidden` (restored in `leaveHome`). Metered appliances get per-mesh material clones so `updateStatus` can tint them with the status colour.
5. **View controller / accessible HTML** — interaction is click-only: hover never opens a card; `choose()` shows a card on first click; a second click on the same home enters it, on the same meter opens the dashboard (`#dash`, `openDash`/`renderDash`, plain HTML + SVG so it works without WebGL). The dashboard and the `#recap` story read `Data.focus` (incl. `highlights`), `Data.history`/`Data.dayLevels` (calm streak calendar), `Data.splits`, `Data.recap`, `Data.chart` and the view window `Data.from`/`Data.to` (`setRange`). Playback calls the cheap `updateClock()` every frame and the full `updateUI()` about 10×/s. tooltips, placards, timeline, table, keyboard routes. `reinitialize()` runs after every `WattsWrong.load`; `updateUI()` after time changes.
6. **Rendering** — two composers: `bloomComposer` renders the scene with non-bloom meshes swapped to `darkMaterial` (selective bloom via `userData.bloom`), then `composer` does scene + SSAO + bloom composite + FXAA. Graphics quality `high` ("Sharper") vs `balanced` ("Faster") is set in `setQuality`. `renderSelective()` runs every frame, so avoid per-frame allocations and full-scene traversals there.

Homes come from the manifest: its sites fill Homes A–D in order (`HOMES`, `Data.siteAt`, `bindHomes()` after every load), and a home without a site shows the no-data placard. The embedded run has four sites: A = REFIT House 1, B = House 3, C = House 10, D = House 18. Home C still uses the generic interior. Sites with garage channels add an attached garage to the exterior and a lazy garage room downstairs; the fridge-freezer stays in the kitchen. Never add per-site checks (`id==='house1'`): interiors place metered appliances by the site's channels (`has(ch)` in `buildInterior`).
Homes come from the manifest: its sites fill Homes A–D in order (`HOMES`, `Data.siteAt`, `bindHomes()` after every load), and a home without a site shows the no-data placard. The embedded run has four sites, so all four homes have data: A = REFIT House 1, B = House 3, C = House 10, D = House 18. A meter whose channel `buildInterior` has no appliance builder for gets no 3D appliance; it still appears in the meter table, timeline and dashboards. At present that applies to Home C's chest freezer and Kenwood kMix, and to Home D's garage fridge and garage freezer, whose attached garage is not built yet. When you add a builder for one of them, update this list. Never add per-site checks (`id==='house1'`): interiors place metered appliances by the site's channels (`has(ch)` in `buildInterior`).

Use the terms in `GLOSSARY.md` for UI copy (e.g. finding, detection strength, extra cost, confirmation time); never add emoji to the interface.

## Agent skills

### Issue tracker

Issues and specs are GitHub issues on HishamAbdulhak/wattswrong-3d, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default triage labels (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` at the root, ADRs in `backend/docs/adr/`. See `docs/agents/domain.md`.
