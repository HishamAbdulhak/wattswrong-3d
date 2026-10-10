# 0008 Timezones of REFIT data and labels

Status: finding from real data (reports/spike_house1.md), not a preference.

- Meter timestamps come from the `Unix` column: the epoch at which the Strathclyde server received each reading (Murray et al. 2017, Scientific Data), so they are true UTC. The `Time` column equals `Unix` rendered as UTC, even inside British Summer Time. Exports are in UTC with offset. Calendar features and display use Europe/London (`source_timezone`).
- Label times in REFIT_anomalies.csv have no stated timezone. Reading them as UTC aligns better with the labelled appliance's raw ON state in 6 of 9 BST-period House 1 events (2 ties, 1 against). For example, 0.98 vs 0.79-0.80 ON fraction for the April and May 2015 freezer events. `label_timezone` = UTC.
- The daily-profile test across clock changes was inconclusive for House 1 (low profile correlation), so it is not relied on.

Update after House 3 (reports/spike_house3.md): in BST-period events, UTC fits better in 12 and London in 9. Pooled over both houses it is 18 to 10 for UTC, so `label_timezone` stays UTC, with weaker confidence than House 1 alone gave. Impact is small: matching allows detection up to event end + 24 h, so a one-hour label offset changes almost no matches. It only shifts the training-exclusion mask by an hour.
