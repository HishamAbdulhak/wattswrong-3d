# 0006 Category rules and detection strength

Status: adopted SUGGESTED defaults (thresholds not locked by the team).

Order of rules, first match wins:
1. Appliance channel -> `appliance_abnormal`. This is the only case with appliance names and possible causes.
2. Whole-house finding of 12 hours or less -> `spike`.
3. 50% or more of excess falls between 00:00 and 06:00 UK time -> `overnight_excess`.
4. 7 days or more with a rising daily residual (positive slope, and the last 3 days above the first 3) -> `gradual_drift`.
5. 24 hours or more with positive residual in at least 80% of hours -> `baseload_creep`.
6. 60% or more of excess falls Mon-Fri 14:00-22:00 UK time -> `peak_hour_waste`. This is an illustrative window, not a proven ToU saving.
7. Otherwise -> `spike` (a short or irregular burst).

`aircon_overnight` is never assigned, because no aircon channel exists in REFIT House 1.

Detection strength (schema field `confidence`) = 0.5 x min(mean score of the >= 2 hours / 4, 1) + 0.5 x min(count of those hours / (2 x persistence), 1). The UI shows only Low/Medium/High detection strength (see 0010).
