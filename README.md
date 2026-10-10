# WattsWrong — browser 3D historical replay

## Run

- Open `index.html` directly in a modern WebGL2 browser. Embedded findings and manifest work immediately; external three.js, font and optional visual assets need internet access. Direct-file mode deliberately skips the optional series request to avoid file-origin restrictions and shows **Total extra cost**.
- For cumulative hourly costs, keep `data/timeseries.json` beside the HTML under `data/`, and run `npx serve .` from this folder. Open the printed address. No build step is required.
- Choose a home, drag to orbit, and use Ground / First / Both. Tab and Enter operate the home and meter buttons. Escape closes details, then returns to the street. The table offers a separate keyboard route to every meter.
- High enables SSAO, 2048-pixel sun shadows and a pixel ratio capped at 2. Balanced disables SSAO, uses 1024-pixel shadows and caps the pixel ratio at 1.25. Both use selective status bloom and FXAA.

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

REFIT electricity data: David Murray and Lina Stankovic, University of Strathclyde, **CC BY 4.0**, [dataset](https://doi.org/10.5281/zenodo.5063428). Research annotations: Rashid et al., ICASSP 2019, **CC BY 4.0**, [source](https://doi.org/10.15129/9729a2a0-11ce-4cce-b0d0-144c483fcb33). The supplied exported findings are embedded unchanged; raw annotation CSVs were not converted into additional findings.

## Data interface

`window.WattsWrong.load({ manifest, findings, timeseries })` validates and replaces the replay, stops playback, returns to the street, rebuilds controls, and starts at the exact busiest hourly timestamp. Omit `timeseries` to use labelled total costs. A later explicit load takes precedence over the initial optional fetch. The initial run is **20261010T065957Z**, with **64 findings**, **two homes**, and **eight meters**. The optional series contains **41,321 rows**.

The original manifest and finding records are embedded in `<script type="application/json" id="wattswrong-data">`. The clearly marked data section normalises them; rendering uses derived home and meter views. Homes C and D have no data bindings.

Activity is exactly `detected_ts <= t < end_ts + 1 hour`; a null end runs through the site's final coverage hour. Strength uses the fixed 0.50 / 0.75 thresholds. Hourly cost uses a prefix sum of positive residuals for the same site and channel from `start_ts` through `min(t, end_ts)`, multiplied by 0.444. If no series is available for a channel, the UI labels `excess_kwh × 0.444` as **Total extra cost**. Meter costs are not added together because aggregate and appliance readings overlap.

Convenience methods: `window.WattsWrong.getState()` returns a derived snapshot; `window.WattsWrong.setTime('2014-11-26T11:00:00Z')` selects a replay hour.

## Assumptions and practical limits

- Room layouts, furniture and positions are illustrative. Both-floor mode separates the upper floor vertically so ground-floor rooms remain visible. Ground and First isolate their respective floors. The camera-facing room walls lower as the camera moves.
- Golden-hour lighting stays fixed as replay time changes. The optional day/night lighting and depth-of-field effects were omitted. Camera transitions take about 1.5 seconds; reduced-motion settings replace flights with cuts and remove pulsing.
- Architecture, appliances, vegetation and most furniture are procedural. The CC0 sofa loads on first entry and retains a procedural fallback if unavailable. A reflected HDRI, PBR texture maps, raster shadows, SSAO and selective bloom provide the architectural rendering; this is not path tracing, and photographic equivalence is not claimed.
- Connected homes open cutaways. C and D provide the required no-data tooltip and placards without invented interiors or meter readings.
- The supplied series has gaps. Costs sum the supplied positive residual rows; missing hours are not estimated. Total fallback costs are expressly labelled and can include hours later than the selected replay time, as required by the data contract.
- The forecast models are not rerun here. This is a visualisation of the discovered original exports, not a new evaluation.
- The application is self-contained in its HTML/CSS/JS and embedded small data, but external three.js modules still require a working CDN connection unless mirrored locally. Optional visual-asset errors keep procedural materials/models. If the engine or WebGL is unavailable, the accessible replay table remains usable. Browser-generated network diagnostics cannot be prevented when remote assets are deliberately blocked.
- 60 fps is a performance target, not a measured guarantee. Instanced foliage and roof tiles, static geometry batching, lazy interiors, shared resources and the Balanced toggle reduce cost. GPU/driver performance varies.

## Verification

Automated checks passed for all 64 detection/end boundaries, the busiest hourly timestamp, null-ended coverage, fixed strength bands, replacement data, missing-series totals and cumulative costs against raw series rows. Browser checks covered both connected homes, keyboard entry, floor switching, playback/pause, return navigation, quality switching and a 375-pixel viewport without horizontal document overflow. The inspected browser run had no console errors. Deliberately blocked assets and a broad cross-browser/device matrix were not exercised. The busiest hour is **26 November 2014, 11:00 Europe/London**, with three active findings.
