# 0010 Finding lifecycle, prioritization and detection strength

Status: AGREED by the team on 10 Oct 2026. Terms are defined in GLOSSARY.md. Numeric detector values are chosen on validation only and frozen in config before the test run.

## Lifecycle (per site and channel, scored hour by hour in the historical replay)

1. **Scoring.** Each scored hour gets anomaly_score = (actual - day-ahead forecast) / robust spread. Unobserved hours are skipped. They count neither toward persistence nor toward recovery, and never split or end a finding.
2. **Confirmation (persistence threshold).** A finding is confirmed when at least `persistence_periods` of the last `persistence_window` scored hours have a score of at least `detection_score_min`. That score is never below the agreed row gate of 2. `detected_ts` is the end of the confirming hour.
3. **Onset.** `start_ts` is found by walking back from confirmation through hours with score >= `continuation_score_min`, up to 30 days. The finding's hours from onset onward are replaced by their forecast in protected history, so an ongoing finding never becomes the new normal.
4. **Continuation.** While ongoing, each hour with score >= `continuation_score_min` extends the finding.
5. **Resolution (ended finding).** After `recovery_periods` consecutive scored hours below the continuation score, the finding ends. `end_ts` is the end of its last deviating hour. A finding still deviating at the end of the replay stays ongoing (`end_ts` null).
6. **Gap merging and reopening.** If a new confirmation on the same site and channel has its onset within 24 hours of the previous finding's end, the previous finding is reopened instead of a new one being created. It keeps its `finding_id` and `detected_ts`, and its `end_ts` is cleared. Beyond 24 hours, a recurrence is a new finding with a new ID.
7. **Flagged rows.** `is_anomalous` is true only for rows on the finding's channel, from `detected_ts` to `end_ts` (or open), with score >= 2. Rows are never back-filled before detection.
8. **Householder status.** Statuses are open, fixed, false alarm and away, stored on the device and keyed by `finding_id`. A status never changes detection, protected history, export or evaluation. Reopen in the UI sets the status back to open. A finding marked fixed that recurs more than 24 hours after it ended appears as a new finding.

## Prioritization

- **Ongoing section.** Ongoing findings with status open, ranked by projected monthly extra cost (highest first).
- **Ended or marked section.** Ended findings, plus findings the householder marked fixed, false alarm or away, ranked by historical extra cost, or by extra cost so far for those still ongoing.
- Whole-house and appliance findings can overlap, so their costs are never summed into a total.
- All costs come from one cost function and recompute when the tariff changes. The UI labels every amount as an estimate and keeps projections ("if it continues") visually separate from historical amounts. It never claims guaranteed waste or savings.

## Detection strength

The schema field `confidence` holds a heuristic detection strength: 0.5 x min(mean score of the hours >= `detection_score_min`, divided by 4, then 1) + 0.5 x min(count of those hours / (2 x `persistence_periods`), 1). The UI shows only "Low / Medium / High detection strength" (High >= 0.75, Medium >= 0.5). It is never a probability, and never a likelihood of equipment failure.
