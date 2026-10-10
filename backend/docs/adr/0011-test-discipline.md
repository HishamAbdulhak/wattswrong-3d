# 0011 Test-window discipline and disclosed uncertainty

Status: AGREED by the team on 10 Oct 2026.

- Every modelling and detection assumption (splits, timezones, features, detector values, category rules, channels modelled, matching and censoring rules) is frozen in config and ADRs before `pipeline.run final` scores the test window. None may be changed because of test results. If a defect forces a re-run, it needs a logged `--rerun-reason`, and both results are kept and disclosed.
- Median detection delay is computed only over labelled events that were detected, and is always shown next to recall. Estimated earlier notice (the 15-day bill-notice assumption minus that median) is illustrative, not measured real-world notice or savings.
- **Disclosed uncertainty: House 3 label timezone.** In House 3's BST-period labelled events, reading label times as UTC fits better in 12 cases and London time in 9 (reports/spike_house3.md). UTC is kept for both houses (18 to 10 pooled). Matching tolerates the offset (detection allowed up to event end + 24 h), but the training-exclusion mask and onset-based delay can shift by up to an hour. This is stated in the metrics notes and the pitch limitations.
