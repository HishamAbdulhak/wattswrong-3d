# 0013 Post-hoc evaluation on frozen forecasts

Status: AGREED by the team on 10 Oct 2026. Amends docs/adr/0011-test-discipline.md.

The forecasts exported by final run `20261010T065957Z` are frozen. New metrics and baselines may be computed from them after the test run without a `--rerun-reason`, because nothing is refitted, retuned or re-forecast. Everything computed this way is declared here before its test numbers are seen. Changing any feature, setting or model after seeing test results is still forbidden by 0011.

Declared before computing:

- **Baselines** (GLOSSARY.md): weekly naive (the existing one), daily naive, four-week mean. All are scored on the same hours as the day-ahead forecast. An hour is scored only if every model has a value for it.
- **Metrics**: MAE, RMSE and WAPE for every model and channel.
- **Headline**: whole-house meter, per site. Appliance meters are reported in a secondary table with a note that WAPE is high for intermittent loads.
- **Example days**: per site, the whole-house test day (local calendar day with at least 20 scored hours) at the median daily WAPE of the day-ahead forecast is shown as typical, and the day at the 90th percentile as one where it struggles. No hand-picking.
- **Stability**: the same metrics per calendar month across validation and test, for both sites. This replaces a refit rolling-origin backtest, which would have needed new fits.

Considered: a refit rolling-origin backtest limited to train and validation (rejected: new code and new fits for little extra evidence), and adding REFIT homes. Extra homes may be added only after the demo is verified, and only run under the frozen config with no tuning on them. That is the only further modelling work allowed. Alternative models are out of scope.
