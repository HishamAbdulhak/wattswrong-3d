# 0012 No detection on cycle appliances; Away Mode replaces the model absence guard

Status: AGREED by the team on 10 Oct 2026, before the test run.

- **Cycle appliances.** On validation the day-ahead model predicts about 0 kWh every hour for the washing machine, dishwasher and tumble dryer (WAPE exactly 100%), so every normal cycle would look like excess. They are still forecast and their error is reported, but no findings are detected on them. Their three labelled events still count in the pooled scopes, matchable by whole-house findings.
- **Return from absence.** The model-side guard (a four-week same-hour median feature) had mixed evidence on real absences (reports/absence_guard.json: two House 1 returns shrank from 4.9 and 8.7 kWh to 0.3 kWh, one House 3 return got worse) and no validation WAPE gain. It stays off (`use_four_week_median` = false).
- **Away Mode instead (householder-controlled, UI only).** An "I'm away from home" toggle starts an away period at "now" (in the replay, the end of recorded data). The householder can also add away date ranges at any time, before or after the fact. Each period plus `away_return_days` (7) after it is masked:
  - A finding detected inside a mask gets status away and leaves the ongoing ranking.
  - A finding that overlaps a mask has its excess and projected cost recomputed from its timeseries rows, without masked hours, through the same cost function.
  - The chart shades away dates.
  - Saved on this device only. Readings are kept, and detection, exports and evaluation are unchanged (consistent with 0010).
- Limitation: away dates are whole UTC days, which can differ from UK local days by an hour in summer.
