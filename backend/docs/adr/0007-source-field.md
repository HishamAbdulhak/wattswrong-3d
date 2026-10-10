# 0007 Meaning of `source` in exported findings

Status: adopted SUGGESTED semantics (Guide (3) is ambiguous; documented before export as required).

Findings from the historical replay of REFIT House 1 are exported with `source = "live"`, and the UI shows a prominent "historical replay" banner. A finding is never marked `real` just because the meter data is real: that would read as researcher-confirmed. Whether a finding matched a labelled REFIT event is kept in the sidecar `reports/matches_final.json`. The evaluation sidecar `metrics.json` carries `source: "real"` because it is scored against real labels. `synthetic` is unused: no injection was run.
