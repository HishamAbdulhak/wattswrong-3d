# 0005 Forecast, protected history and detection

Status: adopted SUGGESTED defaults. Numeric values are frozen in `config/config.json` before the test run, chosen on validation only (reports/tuning_validation.json).

- Features (all >= 24 h old): local hour, weekday, England bank-holiday flag, same hour yesterday, same hour last week, 24 h and 168 h means ending 24 h back, and optionally the same-hour median of the last four weeks. The four-week median is the return-from-absence guard.
- Model: one LightGBM regressor per channel, fitted on the training split. Hours inside labelled training anomalies are dropped as targets and hidden from lag features.
- Replay: day by day from `train_end`. A day's forecasts use only history that ends before that day. Confirmed finding hours (onset through the last anomalous hour) are replaced by their forecast in protected history. Issued forecasts are never rewritten.
- Residual spread: per local hour, 1.4826 x MAD of out-of-sample residuals. Those residuals come from a model fitted on the first 80% of train and scored on the last 20%. Floor: max(0.005 kWh, half the channel's overall spread).
- anomaly_score = residual / spread. A finding is confirmed when `persistence_periods` hours with score >= `detection_score_min` (tuned, never below 2) fall within the last `persistence_window` scored hours. Onset is the earliest hour of the run with score >= `continuation_score_min` going back from confirmation. `detected_ts` is the end of the confirming hour. The finding ends after `recovery_periods` consecutive scored hours below the continuation score, and `end_ts` is the end of the last anomalous hour.
- `is_anomalous` = row on the finding channel, from `detected_ts` to `end_ts` (or open), with score >= 2. Rows are never back-filled before detection.
- Projection: ongoing `rm_per_month` = excess_kWh / scored finding hours x 24 x 30 x tariff. Ended findings get 0, and the UI shows excess x tariff as the accumulated cost.
- The test window is scored once. `pipeline.run final` refuses to run again unless a logged `--rerun-reason` is given.

The full finding lifecycle, including reopening within 24 h, is in docs/adr/0010-finding-lifecycle.md.
