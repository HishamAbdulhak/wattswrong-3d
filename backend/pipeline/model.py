"""Day-ahead forecast, causal protected-history replay, persistence detection, findings.

Every feature for target hour p reads the protected series at p-24 or older
(forecast_minimum_lag_hours = 24). The replay walks one UTC day at a time:
predict the whole day from history ending yesterday, then score each hour as
its measurement "arrives", then update protected history. A confirmed finding's
hours are replaced by their forecast in protected history, so an ongoing fault
never becomes the new normal. Already-issued predictions are never rewritten.
"""
from dataclasses import dataclass, field

import lightgbm as lgb
import numpy as np
import pandas as pd

TZ = "Europe/London"
LAG = 24
REOPEN_GAP_H = 24  # a new confirmation within 24 h of a finding's end reopens it
# England & Wales bank holidays in the data span (gov.uk/bank-holidays).
HOLIDAYS = {pd.Timestamp(d).date() for d in [
    "2013-12-25", "2013-12-26", "2014-01-01", "2014-04-18", "2014-04-21", "2014-05-05", "2014-05-26",
    "2014-08-25", "2014-12-25", "2014-12-26", "2015-01-01", "2015-04-03", "2015-04-06", "2015-05-04",
    "2015-05-25", "2015-08-31",
]}
FEATURES = ["hour", "dow", "holiday", "lag24", "lag168", "roll24", "roll168", "med4w"]


def grid(hourly, channel):
    """Full hourly UTC grid for one channel; unobserved hours are NaN."""
    s = hourly.loc[hourly.channel == channel].set_index("ts")["kwh"].sort_index()
    return s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="h", tz="UTC"))


def calendar(index):
    local = index.tz_convert(TZ)
    return pd.DataFrame({
        "hour": local.hour, "dow": local.dayofweek,
        "holiday": [d in HOLIDAYS for d in local.date],
    }, index=index).astype({"holiday": int})


def lag_features(yp, positions, use_med4w=True):
    """Features from protected history yp (numpy, NaN = unobserved) for target positions.
    Returns array (n, 5); rows lacking complete lag support have NaN in lag24/lag168."""
    out = np.full((len(positions), 5), np.nan)
    for i, p in enumerate(positions):
        if p < 168 + 3 * 168:  # need four weeks for the median window
            continue
        out[i, 0] = yp[p - 24]
        out[i, 1] = yp[p - 168]
        w24 = yp[p - 47:p - 23]          # 24 hours ending exactly 24 h back
        w168 = yp[p - 191:p - 23]        # 168 hours ending 24 h back
        if np.isfinite(w24).sum() >= 12:
            out[i, 2] = np.nanmean(w24)
        if np.isfinite(w168).sum() >= 84:
            out[i, 3] = np.nanmean(w168)
        if use_med4w:
            wk = yp[[p - 168 * k for k in (1, 2, 3, 4)]]
            if np.isfinite(wk).sum() >= 2:
                out[i, 4] = np.nanmedian(wk)
    return out


def design(yp, cal, positions, use_med4w=True):
    X = np.column_stack([cal.iloc[positions][["hour", "dow", "holiday"]].to_numpy(float),
                         lag_features(yp, positions, use_med4w)])
    supported = np.isfinite(X[:, 3]) & np.isfinite(X[:, 4])  # same hour yesterday and last week present
    return X, supported


def fit(y, cal, positions, exclude, params, use_med4w=True):
    """Train LightGBM on target positions. `exclude` (bool array over the grid) marks labelled
    training anomalies: they are not used as targets and are hidden from lag features."""
    yp = y.copy()
    yp[exclude] = np.nan
    positions = positions[np.isfinite(y[positions]) & ~exclude[positions]]
    X, ok = design(yp, cal, positions, use_med4w)
    params = {"verbosity": -1, "seed": 0, "deterministic": True, **params}
    rounds = params.pop("num_boost_round")
    return lgb.train(params, lgb.Dataset(X[ok], y[positions[ok]]), num_boost_round=rounds)


def robust_spread(resid, hours, floor):
    """Per local-hour 1.4826*MAD of residuals, floored at max(floor, half the overall spread)."""
    def mad(x):
        x = x[np.isfinite(x)]
        return 1.4826 * np.median(np.abs(x - np.median(x))) if len(x) else np.nan
    overall = mad(resid)
    lo = max(floor, 0.5 * overall)
    return np.array([max(lo, np.nan_to_num(mad(resid[hours == h]), nan=lo)) for h in range(24)]), overall


@dataclass
class Finding:
    """Detector state for one finding (lifecycle: docs/adr/0010)."""
    channel: str
    start: int
    detected: int        # position of the confirming hour (detected_ts = its end)
    last_anom: int
    end: int | None = None
    hits: list = field(default_factory=list)


@dataclass
class DetectorParams:
    z_high: float        # published anomalous-row gate (agreed 2)
    z_hit: float         # score an hour needs to count toward persistence (tuned, >= z_high)
    z_low: float         # continuation / onset threshold
    window: int          # persistence window, scored hours
    persist: int         # hits >= z_high within window to confirm
    recovery: int        # consecutive scored hours below z_low to close


def replay(y, cal, model, spread, start_pos, end_pos, dp: DetectorParams, exclude_before, use_med4w=True):
    """Causal replay from start_pos (inclusive) to end_pos (exclusive), one UTC day at a time.
    Returns per-position pred and z arrays, the protected series and a list of Findings."""
    n = len(y)
    yp = y.copy()
    yp[exclude_before] = np.nan
    pred = np.full(n, np.nan)
    z = np.full(n, np.nan)
    findings, live = [], None
    recent = []  # scored positions within the persistence window: (pos, hit)
    below = 0
    hours = cal["hour"].to_numpy()
    for day0 in range(start_pos, end_pos, 24):
        P = np.arange(day0, min(day0 + 24, end_pos))
        X, ok = design(yp, cal, P, use_med4w)  # history ends >= 24 h before every target in P
        if ok.any():
            pred[P[ok]] = model.predict(X[ok])
        for p in P:
            if not (np.isfinite(y[p]) and np.isfinite(pred[p])):
                continue
            z[p] = (y[p] - pred[p]) / spread[hours[p]]
            if live is None:
                recent = [(q, h) for q, h in recent if q > p - dp.window] + [(p, z[p] >= dp.z_hit)]
                if sum(h for _, h in recent) >= dp.persist:
                    s = p
                    q = p - 1
                    while q >= 0 and (not np.isfinite(z[q]) or z[q] >= dp.z_low) and p - q <= 24 * 30:
                        if np.isfinite(z[q]):
                            s = q
                        q -= 1
                    prev = findings[-1] if findings else None
                    if prev is not None and s - prev.end <= REOPEN_GAP_H:
                        live = findings.pop()            # same deviation resumed: reopen, keep its ID
                        live.end, live.last_anom, s = None, p, prev.end + 1
                    else:
                        live = Finding("", s, p, p)
                    yp[s:p + 1] = np.where(np.isfinite(pred[s:p + 1]), pred[s:p + 1], np.nan)  # protect onset
                    below, recent = 0, []
            else:
                if z[p] >= dp.z_low:
                    live.last_anom, below = p, 0
                    yp[p] = pred[p]
                else:
                    below += 1
                    if below >= dp.recovery:
                        live.end = live.last_anom
                        findings.append(live)
                        live, below = None, 0
    if live is not None:
        findings.append(live)
    return pred, z, yp, findings


def mae_wape(actual, pred):
    ok = np.isfinite(actual) & np.isfinite(pred)
    if ok.sum() == 0 or actual[ok].sum() == 0:
        return None, None, int(ok.sum())
    err = np.abs(actual[ok] - pred[ok])
    return float(err.mean()), float(err.sum() / actual[ok].sum()), int(ok.sum())
