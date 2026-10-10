# WattsWrong — browser 3D historical replay

## Run

- Open `index.html` directly in a modern WebGL2 browser, or run `npx serve .` from this folder and open the printed address. The manifest, findings and the full hourly series are embedded, so graphs and **Extra cost so far** work either way; external three.js, font and optional visual assets need internet access. No build step is required.
- The embedded series is a compact copy of the backend's `web/public/data/timeseries.json` (runs of consecutive hours, `actual_kwh` and `residual_kwh` per row, unchanged; forecast = actual − residual). `uv run --locked python -m pipeline.embed` (from `backend/`) validates the exports and re-embeds the manifest, findings and series; it checks every row is kept and every hour is unique per meter.
- Homes with active findings show a **!** marker. Click a home once for its card and again to go inside; the home dashboard opens (meters, active findings, whole-house actual-vs-forecast graph). Click a meter once for its card and again (or double-click) for its detail: excess energy, excess cost, pattern, graph, possible causes and the next step. Drag to orbit and use Downstairs / Upstairs / Both floors. Tab and Enter operate the home and meter buttons. Escape closes the card, then the meter detail, then returns to the street. The table offers a separate keyboard route to every meter's detail.
- **Replay recap** (header) plays a full-screen story of the whole replay: findings spotted, typical confirmation time, the largest finding that lasted under a week, the most common category and the longest calm streak, then buttons into each home. Slides advance every 5 s; tap the sides or use ←/→, Escape closes. Totals are finding counts or single findings, never costs summed across meters.
- A home's dashboard opens with a status circle (findings right now and the whole-home extra cost), cards for each active finding, and a calm-streak calendar of the last four weeks; click a day to jump the replay there. A meter's detail adds highlights (confirmed within 6 hours of starting, largest on this meter, longest in this home) and **Day by day** bars of extra kWh per day, which add up to its extra energy so far. While a finding is active it also shows its **projected monthly extra cost**: the backend's formula (`pipeline/run.py`: extra energy so far ÷ recorded hours × 24 × 30 × tariff) applied at the replay hour. Ended findings show **Total extra cost** and no projection; projections are never added across meters.
- **Day / Week / Month / All** set the replay window to the day being replayed, the week or 30 days ending on it, or every date; **‹ ›** move it by its own length. The From / To dates also set the replay window: the slider, finding lanes and graphs follow it, and **Show only this finding's dates** sets it to a finding ±2 days. Graphs are hourly for windows up to 21 days, otherwise daily totals of recorded hours; up to 240 hours they draw one bar per hour, coloured inside a finding, against a dashed expected line. Each graph has a **kWh / RM** switch and a "What does this graph show?" note. A meter's detail leads with its extra cost, then the next step and possible causes as cards with a way to check each. Play covers the window in about a minute. **Pop out** pops the replay panel out into a floating widget over the page: move it by its top handle (drag, or focus it and use the arrow keys), resize it from its bottom-right corner, and press **Put back** or drag it back to the bottom edge (it outlines when it will snap) to put it back.
- Graphics **Sharper** (`high`) enables SSAO, 2048-pixel sun shadows and a pixel ratio capped at 2. **Faster** (`balanced`) disables SSAO, uses 1024-pixel shadows and caps the pixel ratio at 1.25. Both use selective status bloom and FXAA.

## Offline backend

`backend/` is a one-way fork of the WattsWrong pipeline at commit `b57cde9`, with its own Python project and freshly generated `uv.lock`. It is independent and is never synced with its origin. Run all backend commands from that directory:

```bash
cd backend
uv sync --locked
uv run --locked python -m pytest -q pipeline
uv run --locked python -m pipeline.ingest data/raw/refit/CLEAN_House1.csv house1
uv run --locked python -m pipeline.ingest data/raw/refit/CLEAN_House3.csv house3
uv run --locked python -m pipeline.ingest data/raw/refit/CLEAN_House10.csv house10
uv run --locked python -m pipeline.ingest data/raw/refit/CLEAN_House18.csv house18
uv run --locked python -m pipeline.validate
uv run --locked python -m pipeline.embed
```

Python 3.12+ and `uv` are required. `pipeline.validate` checks the frozen run's exports in `web/public/data/` against the locked contracts and cross-table rules, and prints every violation. `pipeline.embed` validates them again, then writes the manifest, findings and hourly series into `../index.html`; it fails if any row is lost or an hour repeats. Neither needs the raw files: from a clean checkout, `uv sync --locked`, `pipeline.validate` and `pipeline.embed` leave `index.html` unchanged. Ingest writes `data/interim/<site>_hourly.parquet` and `reports/quality_<site>.json` for each of `house1`, `house3`, `house10` and `house18`, all relative to `backend/`. Raw inputs, hourly intermediates, quality reports and the virtual environment are git-ignored. Hourly files are rebuilt from raw CSVs, never copied.

Place the following real source files under `backend/data/raw/`. Houses 1 and 3 are individual cleaned CSVs on Zenodo. Houses 10 and 18 are not on Zenodo: extract them from Strathclyde's cleaned archive (`CLEAN_REFIT_081116.7z`, md5 `a3ba34e6e8073f1aea490e62cb731d2b`), whose House 1 and 3 files match Zenodo's md5s. The annotation source supplies the labels and their readme. All files are CC BY 4.0.

| Raw file (relative to `backend/`) | MD5 | Download source |
|---|---|---|
| `data/raw/refit/CLEAN_House1.csv` | `f5336d80c700f866af0d997ea8d39146` | [REFIT House 1](https://zenodo.org/records/5063428/files/CLEAN_House1.csv?download=1) |
| `data/raw/refit/CLEAN_House3.csv` | `ab6e34ea386eb4563bfcb9762619dc8f` | [REFIT House 3](https://zenodo.org/records/5063428/files/CLEAN_House3.csv?download=1) |
| `data/raw/refit/CLEAN_House10.csv` | `e442a1b1dc7ce73fae516a000efb1215` | [REFIT House 10](https://doi.org/10.15129/9ab14b0e-19ac-4279-938f-27f643078cec), in `CLEAN_REFIT_081116.7z` |
| `data/raw/refit/CLEAN_House18.csv` | `7fbb09fd62860b3aef0c19c545b66342` | [REFIT House 18](https://doi.org/10.15129/9ab14b0e-19ac-4279-938f-27f643078cec), in `CLEAN_REFIT_081116.7z` |
| `data/raw/labels/REFIT_anomalies.csv` | `dd96a35285b2b207000650867ace10c2` | [REFIT anomaly annotations](https://doi.org/10.15129/9729a2a0-11ce-4cce-b0d0-144c483fcb33) |
| `data/raw/labels/README_ICASSP.txt` | `9d0bfaf94c936f215f3e86c357fd5221` | [Annotation readme](https://doi.org/10.15129/9729a2a0-11ce-4cce-b0d0-144c483fcb33) |

The fork includes ingest, site/channel maps, labels, model, run orchestration, evaluation and validation, with their five existing test files. The frozen config, locked JSON contracts and ADRs 0001–0013 are preserved verbatim alongside ADR 0014. Historical ADRs retain their original context; [GLOSSARY.md](GLOSSARY.md) governs this app's terminology. The web app, hosted-demo check, reproduction harness, post-hoc evaluation, site-facts tool and judging scripts are excluded.

### Frozen run

This repo's frozen run, **20261010T190414Z** (code `f18f389`, config `d3020c3ee48d`), scored the test window (31 Jan – 31 May 2015) once over four sites on the unchanged frozen config, with no tuning. Its lock is `backend/reports/metrics_final.json`; `pipeline.run final` refuses to run again without a logged `--rerun-reason`. Exports are in `backend/web/public/data/`, the matches in `reports/matches_final.json` and parquet copies in `artifacts/20261010T190414Z/`.

- **Re-run, disclosed.** The first attempt (code `557fb17`) scored the window and wrote timeseries, findings and metrics, then crashed writing the manifest: a spread value was NaN (see House 10 below). Only its serialisation was fixed. The logged re-run produced bit-identical timeseries, findings and metrics. The first attempt's outputs are kept in `reports/attempt1_crashed/`.
- **Homes A and B** have the same 64 findings as before the split, unchanged.
- **Houses 10 and 18 were scored blind** (ADR 0014). Their per-meter results, as they came out (`metrics_final.json`): House 10 chest freezer recall 0 of 10 labelled events, 3 unmatched findings (1.1 per month); fridge-freezer 0 of 1, no findings; kMix no labelled events in the window, no findings. House 18 garage freezer 1 of 4 (delay 5 h), no unmatched findings; garage fridge no labelled events, 6 unmatched findings (2.2 per month); fridge-freezer 0 of 3, no findings. Their whole-house findings count only in the pooled scopes: all sites and channels, recall 11 of 37 with 56 unmatched findings (5.2 per house-month) and a median delay of 7.3 h; whole-house only, 4 of 37 (median delay 26.5 h).
- **House 10 caveats.** Its labelled chest-freezer event from 7 Jun to 4 Oct 2014 covers the whole training hold-out, so the whole-house and chest-freezer meters have no out-of-sample residuals and their spread sits at the frozen floor (0.005 kWh) every hour. Its overall spread is exported as `null`. The REFIT ReadMe also notes that House 10's fridge-freezer was replaced in March 2015 and a second freezer was added after April 2015, apparently on the chest-freezer channel. Both fall inside the test window and may cause findings that aren't anomalies. Per ADR 0014 they are disclosed, not tuned away.

## Assets and licences

All URLs, auxiliary maps and glTF dependencies are in the single `ASSETS` object at the beginning of the module. Replace these URLs with local equivalents to self-host. Texture sets include colour, normal, roughness and AO at 1K. The HDRI is 2K.

| Asset / use | Author | Licence | Source |
|---|---|---|---|
| hdri | Greg Zaal | CC0 1.0 | [Poly Haven](https://polyhaven.com/a/kloppenheim_06) |
| brick | Rob Tuytel, Dimitrios Savva | CC0 1.0 | [Poly Haven](https://polyhaven.com/a/brick_wall_001) |
| roof | Rob Tuytel | CC0 1.0 | [Poly Haven](https://polyhaven.com/a/roof_tiles_14) |
| road | Rob Tuytel | CC0 1.0 | [Poly Haven](https://polyhaven.com/a/asphalt_02) |
| grass | Charlotte Baglioni | CC0 1.0 | [Poly Haven](https://polyhaven.com/a/grass_ground) |
| wood | Dimitrios Savva | CC0 1.0 | [Poly Haven](https://polyhaven.com/a/wood_floor_deck) |
| tile | Charlotte Baglioni | CC0 1.0 | [Poly Haven](https://polyhaven.com/a/interior_tiles) |
| plaster | Amal Kumar | CC0 1.0 | [Poly Haven](https://polyhaven.com/a/painted_plaster_wall) |
| fabric | Rob Tuytel | CC0 1.0 | [Poly Haven](https://polyhaven.com/a/fabric_pattern_07) |
| sofa | Fran Calvente | CC0 1.0 | [Poly Haven](https://polyhaven.com/a/sofa_03) |
| font | IBM | SIL Open Font License 1.1 | [Source](https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap) |
| engine | three.js contributors | MIT | [Source](https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.js) |
| procedural | WattsWrong implementation | CC0 1.0 | Generated in this file |

REFIT electricity data: David Murray and Lina Stankovic, University of Strathclyde, **CC BY 4.0**, Houses 1 and 3 from the [Zenodo dataset](https://doi.org/10.5281/zenodo.5063428), Houses 10 and 18 from the [original Strathclyde dataset](https://doi.org/10.15129/9ab14b0e-19ac-4279-938f-27f643078cec). Research annotations: Rashid et al., ICASSP 2019, **CC BY 4.0**, [source](https://doi.org/10.15129/9729a2a0-11ce-4cce-b0d0-144c483fcb33). The supplied exported findings are embedded unchanged; raw annotation CSVs were not converted into additional findings.

## Data interface

`window.WattsWrong.load({ manifest, findings, timeseries })` validates and replaces the replay, stops playback, returns to the street, rebuilds controls, and starts at the exact busiest hourly timestamp. Omit `timeseries` to use labelled total costs. The embedded run is **20261010T190414Z**, with **179 findings**, **four homes**, and **16 meters**. The embedded series contains **81,046 rows**.

The original manifest and finding records are embedded in `<script type="application/json" id="wattswrong-data">`. The clearly marked data section normalises them; rendering uses derived home and meter views. Manifest sites fill Homes A–D in order: REFIT Houses 1, 3, 10 and 18.

Activity is exactly `detected_ts <= t < end_ts + 1 hour`; a null end runs through the site's final coverage hour. Strength uses the fixed 0.50 / 0.75 thresholds. Hourly cost uses a prefix sum of positive residuals for the same site and channel from `start_ts` through `min(t, end_ts)`, multiplied by 0.444. If no series is available for a channel, the UI labels `excess_kwh × 0.444` as **Total extra cost**. Meter costs are not added together because aggregate and appliance readings overlap.

Possible causes: appliance findings show the exported `possible_causes`. Whole-house findings have none and the meter cannot name a device, so the dashboard estimates three from the average extra power (`excess_kwh` over the finding's hours, banded with typical US DOE appliance wattages) plus one from the pattern's timing, labelled as estimates to check, not a diagnosis. Findings longer than 7 days carry a note that their cost may be overstated.

Convenience methods: `window.WattsWrong.getState()` returns a derived snapshot; `window.WattsWrong.setTime('2014-11-26T11:00:00Z')` selects a replay hour.

## Assumptions and practical limits

- Room layouts, furniture and positions are illustrative. Both-floor mode separates the upper floor vertically so ground-floor rooms remain visible. Ground and First isolate their respective floors. The camera-facing room walls lower as the camera moves.
- Golden-hour lighting stays fixed as replay time changes. The optional day/night lighting and depth-of-field effects were omitted. Camera transitions take about 0.9 seconds; reduced-motion settings replace flights with cuts and remove pulsing.
- Architecture, appliances, vegetation and most furniture are procedural. The CC0 sofa loads on first entry and retains a procedural fallback if unavailable. A reflected HDRI, PBR texture maps, raster shadows, SSAO and selective bloom provide the architectural rendering; this is not path tracing, and photographic equivalence is not claimed.
- All four homes have data and open cutaways. Homes C and D use the shared interior: their whole-house meter and fridge-freezer are placed, but Home C's chest freezer and Kenwood kMix and Home D's garage fridge and garage freezer have no 3D appliance yet. Those meters appear in the meter table, timeline and dashboards. A home without a manifest site would show a "No meter connected" placard; the embedded run fills all four.
- The supplied series has gaps. Costs sum the supplied positive residual rows; missing hours are not estimated. Total fallback costs are expressly labelled and can include hours later than the selected replay time, as required by the data contract.
- The app never runs the forecast models. It replays the exports of the backend's frozen run, embedded by `pipeline.embed`; recall and other evaluation results stay in `backend/reports/`.
- The application is self-contained in its HTML/CSS/JS and embedded small data, but external three.js modules still require a working CDN connection unless mirrored locally. Optional visual-asset errors keep procedural materials/models. If the engine or WebGL is unavailable, the accessible replay table remains usable. Browser-generated network diagnostics cannot be prevented when remote assets are deliberately blocked.
- 60 fps is a performance target, not a measured guarantee. If frames run slow, the pixel ratio steps down and Sharper falls back to Faster; choosing a quality again resets this. Status glows use emissive materials and bloom (rendered at half resolution) rather than point lights, so status changes never force shader recompiles. Instanced foliage and roof tiles, static geometry batching, lazy interiors, shared resources and the Balanced toggle reduce cost. GPU/driver performance varies.

## Verification

The data interface's checks were first run on the two-home data (64 findings): every detection/end boundary, the busiest hourly timestamp, null-ended coverage, fixed strength bands, replacement data, missing-series totals and cumulative costs against raw series rows. Browser checks then covered both homes with data, keyboard entry, floor switching, playback/pause, return navigation, quality switching and a 375-pixel viewport without horizontal document overflow, with no console errors.

For the four-home run, the backend's tests and validator pass, and a browser check confirmed four homes on the street, all 16 meters in the meter table, Homes C and D opening their interiors, and no console errors. The busiest hour is now **24 October 2014, 05:00 Europe/London**, with five active findings; the replay opens there. Deliberately blocked assets and a broad cross-browser/device matrix were not exercised.

## Wording

[GLOSSARY.md](GLOSSARY.md) defines every term the app uses; it is the only authority for terms. Interface text is written for householders: "expected use" for the day-ahead forecast, "Whole home" for the whole-house meter, plain category labels, and "Normal" as a meter state, never a detection strength. *Confirmation time* (a finding's start to its detection) is not the evaluated *detection delay*. Whole-house findings get *estimated causes*, labelled as guesses; only appliance meters get *possible causes*. The interface uses no emoji. Finding titles, explanations and actions are the exported text, passed through `clean()`.
