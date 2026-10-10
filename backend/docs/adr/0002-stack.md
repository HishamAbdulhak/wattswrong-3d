# 0002 Stack

Status: adopted SUGGESTED default (the handoff did not lock a stack).

- Pipeline: Python 3.12 managed by `uv` (`uv.lock`), pandas + pyarrow + LightGBM + jsonschema. Reason: matches the handoff suggestion and the team's ML workflow.
- UI: React + TypeScript on Vite, recharts for the actual-vs-forecast chart. Reason: static build, no backend secrets, and recharts renders gaps and markers without custom SVG.
- Integration: static versioned JSON in `web/public/data/` plus sidecars (`manifest.json`, `metrics.json`). No API. Status edits stay in browser localStorage, labelled "saved on this device".
