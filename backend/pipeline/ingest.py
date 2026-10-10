"""REFIT cleaned CSV (8 s power, W) -> hourly energy (kWh) per channel, with coverage.

Usage: uv run python -m pipeline.ingest data/raw/refit/CLEAN_House1.csv house1

Energy: each sample's power is held until the next sample, for at most MAX_HOLD_S
seconds. Longer gaps are unobserved, never zero-filled. Hold intervals are split
exactly at hour boundaries. kWh = sum(W * held_seconds) / 3_600_000. An hour is
published only when observed seconds >= MIN_COVERAGE * 3600 (docs/adr/0004).
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.sites import SITES

ROOT = Path(__file__).resolve().parent.parent
MAX_HOLD_S = 60
MIN_COVERAGE = 0.95
HOUR = 3600



def hourly_energy(t, w):
    """t: int seconds (sorted, unique), w: watts. Returns (hour_start_s, kwh, observed_s) arrays."""
    dt = np.diff(t, append=t[-1]).astype(float)
    dt[dt > MAX_HOLD_S] = 0.0  # unobserved gap
    ok = np.isfinite(w) & (w >= 0)
    dt[~ok] = 0.0
    w = np.where(ok, w, 0.0)
    hour = t // HOUR
    first = np.minimum(t + dt, (hour + 1) * HOUR) - t  # part inside this sample's hour
    second = dt - first                                # spill into the next hour
    h0 = hour.min()
    n = hour.max() - h0 + 2
    joules = np.bincount(hour - h0, w * first, n) + np.bincount(hour - h0 + 1, w * second, n)
    seen = np.bincount(hour - h0, first, n) + np.bincount(hour - h0 + 1, second, n)
    hours = (np.arange(n) + h0) * HOUR
    return hours, joules / 3_600_000, seen


def ingest(csv_path, site):
    cols = SITES[site]["raw"]
    df = pd.read_csv(csv_path, usecols=["Unix", "Issues", *cols])
    raw_rows = len(df)
    df = df.sort_values("Unix").drop_duplicates("Unix", keep="first")
    t = df["Unix"].to_numpy(np.int64)
    out, quality = [], {"raw_rows": raw_rows, "duplicate_unix_dropped": raw_rows - len(df),
                        "issues_flag_rows": int(df["Issues"].sum()), "channels": {}}
    for col, name in cols.items():
        w = df[col].to_numpy(float)
        hours, kwh, seen = hourly_energy(t, w)
        keep = seen >= MIN_COVERAGE * HOUR
        quality["channels"][name] = {
            "source_column": col,
            "negative_or_nonfinite_samples": int((~np.isfinite(w) | (w < 0)).sum()),
            "hours_spanned": int(len(hours)),
            "hours_published": int(keep.sum()),
            "hours_dropped_low_coverage": int((~keep).sum()),
        }
        out.append(pd.DataFrame({"ts": pd.to_datetime(hours[keep], unit="s", utc=True),
                                 "channel": name, "kwh": kwh[keep], "coverage": seen[keep] / HOUR}))
    hourly = pd.concat(out, ignore_index=True)
    hourly.insert(0, "site_id", site)
    quality.update(
        site_id=site, source_file=Path(csv_path).name, md5=md5(csv_path),
        first_ts=str(pd.to_datetime(t[0], unit="s", utc=True)), last_ts=str(pd.to_datetime(t[-1], unit="s", utc=True)),
        max_hold_s=MAX_HOLD_S, min_coverage=MIN_COVERAGE,
    )
    return hourly, quality


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    csv_path, site = sys.argv[1], sys.argv[2]
    hourly, quality = ingest(csv_path, site)
    (ROOT / "data/interim").mkdir(parents=True, exist_ok=True)
    hourly.to_parquet(ROOT / f"data/interim/{site}_hourly.parquet", index=False)
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / f"reports/quality_{site}.json").write_text(json.dumps(quality, indent=2))
    print(json.dumps(quality, indent=2))
