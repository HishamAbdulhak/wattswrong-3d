# 0004 Power to hourly energy

Status: adopted SUGGESTED quality policy.

REFIT 8 s samples (W) are held until the next sample for at most 60 s. Longer gaps count as unobserved, never as zero power. Hold intervals are split exactly at hour boundaries. kWh = sum(W x held seconds) / 3,600,000. An hour is published only if at least 95% of its 3,600 s are observed. Below that, the period is dropped and the chart shows a gap. Negative or non-finite samples count as unobserved. Timestamps come from the `Unix` column, which is UTC (see reports/spike_house1.md). Calendar features use Europe/London.

Reason: exact under the spec's "W integrated over observed seconds" rule. The 95% gate keeps the under-count from small gaps below 5% without interpolating.
