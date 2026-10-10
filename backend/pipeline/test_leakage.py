# Replay- and training-level leakage audit (issue #16). Extends test_model.py's feature-level check
# (features ignore the last 23 hours) to the whole causal replay and to model training.
# In-memory synthetic vectors only (docs/adr/0003): no measurements, nothing written to disk.
import numpy as np
import pandas as pd
import pytest

import pipeline.run as run
from pipeline.model import DetectorParams, calendar, fit, replay

DAYS = 110
TRAIN_DAYS = 70
# Grid starts mid-day on purpose, so replay days are 24-hour blocks from train_end, not calendar days.
START = pd.Timestamp("2014-03-01T07:00:00Z")
TRAIN_END = START + pd.Timedelta(days=TRAIN_DAYS)
PARAMS = {"objective": "l1", "num_boost_round": 25, "learning_rate": 0.1, "num_leaves": 15, "min_child_samples": 10}


def synthetic(seed=0):
    """Hourly kWh with a daily/weekly shape, gaps, and sustained excess both before and after train_end."""
    idx = pd.date_range(START, periods=DAYS * 24, freq="h", tz="UTC")
    rng = np.random.default_rng(seed)
    h = idx.tz_convert("Europe/London").hour.to_numpy()
    dow = idx.dayofweek.to_numpy()
    y = 0.2 + 0.4 * np.exp(-((h - 19) ** 2) / 8) + 0.05 * (dow >= 5) + rng.gamma(2.0, 0.03, len(idx))
    y[TRAIN_DAYS * 24 + 200: TRAIN_DAYS * 24 + 420] += 0.6     # long excess inside the replay
    y[TRAIN_DAYS * 24 + 700: TRAIN_DAYS * 24 + 712] += 1.5     # short burst inside the replay
    y[rng.choice(len(y), 60, replace=False)] = np.nan          # unobserved hours stay NaN
    return idx, y


def detector():
    return DetectorParams(z_high=2.0, z_hit=2.0, z_low=1.5, window=24, persist=6, recovery=3)


@pytest.mark.parametrize("use_med4w", [False, True])
def test_replay_day_D_forecast_ignores_readings_from_D_onward(use_med4w):
    idx, y = synthetic()
    cal = calendar(idx)
    pos = np.arange(len(y))
    t_end = idx.searchsorted(TRAIN_END)
    excl = np.zeros(len(y), bool)
    model = fit(y, cal, pos[:t_end], excl, PARAMS, use_med4w)
    spread = np.full(24, 0.05)
    dp = detector()
    end_pos = len(y)
    pred, z, _, found = replay(y, cal, model, spread, t_end, end_pos, dp, excl, use_med4w)
    assert found, "the synthetic excess must trigger findings so protected-history writes are exercised"

    # Every replay day D, including days inside and right after a finding.
    for D in range(t_end + 24, end_pos - 24, 24):
        for tamper in ("scale", "nan", "spike"):
            y2 = y.copy()
            if tamper == "scale":
                y2[D:] = y2[D:] * 7.0 + 3.0
            elif tamper == "nan":
                y2[D:] = np.nan
            else:
                y2[D:] = 1e6
            pred2, z2, _, _ = replay(y2, cal, model, spread, t_end, end_pos, dp, excl, use_med4w)
            # Day D's forecasts (and all earlier ones) are bit-identical: nothing from D onward was read.
            assert np.array_equal(pred[:D + 24], pred2[:D + 24], equal_nan=True), (D, tamper)
            # Scores before D are identical too (they only use readings and forecasts before D).
            assert np.array_equal(z[:D], z2[:D], equal_nan=True), (D, tamper)


def test_replay_tamper_check_is_sensitive():
    """Guard against a vacuous pass: changing day D-1 must change some of day D's forecasts."""
    idx, y = synthetic()
    cal = calendar(idx)
    pos = np.arange(len(y))
    t_end = idx.searchsorted(TRAIN_END)
    excl = np.zeros(len(y), bool)
    model = fit(y, cal, pos[:t_end], excl, PARAMS, False)
    spread = np.full(24, 0.05)
    D = t_end + 24 * 10
    pred, *_ = replay(y, cal, model, spread, t_end, len(y), detector(), excl, False)
    y2 = y.copy()
    y2[D - 24:D] *= 5.0
    pred2, *_ = replay(y2, cal, model, spread, t_end, len(y), detector(), excl, False)
    assert np.array_equal(pred[:D], pred2[:D], equal_nan=True)
    assert not np.array_equal(pred[D:D + 24], pred2[D:D + 24], equal_nan=True)


def _prepare(hourly, monkeypatch, spy=None):
    """Run the real pipeline.run.prepare on an in-memory site, optionally spying on fit()."""
    if spy is not None:
        real = run.fit

        def spying_fit(y, cal, positions, exclude, params, use_med4w=True):
            spy.append(np.asarray(positions).copy())
            return real(y, cal, positions, exclude, params, use_med4w)
        monkeypatch.setattr(run, "fit", spying_fit)
    events = pd.DataFrame({
        "site_id": ["contract-test", "contract-test"], "channel": ["fridge", "fridge"],
        "start": [START + pd.Timedelta(days=30), TRAIN_END + pd.Timedelta(days=5)],   # one in train, one after
        "end": [START + pd.Timedelta(days=31), TRAIN_END + pd.Timedelta(days=6)], "status": [1, 1],
    })
    return run.prepare({"contract-test": hourly}, "contract-test", "fridge", events, TRAIN_END, "l1", False, 0.005)


def _hourly(idx, y):
    return pd.DataFrame({"ts": idx, "channel": "fridge", "kwh": y})


def test_every_training_row_is_before_train_end(monkeypatch):
    idx, y = synthetic()
    spy = []
    P = _prepare(_hourly(idx, y), monkeypatch, spy)
    assert len(spy) == 2, "prepare fits the 80% spread model and the final model"
    t_end = P["t_end"]
    assert idx[t_end - 1] < TRAIN_END <= idx[t_end]
    for positions in spy:
        assert len(positions) > 0
        assert positions.max() < t_end, "a training target falls at or after train_end"
        assert (idx[positions] < TRAIN_END).all()
    # Labelled events after train_end are never used to mask training (only training labels are).
    assert not P["excl"][t_end:].any()


def test_training_ignores_everything_from_train_end_onward(monkeypatch):
    """Changing every reading at or after train_end leaves the trained model and spread bit-identical."""
    idx, y = synthetic()
    P = _prepare(_hourly(idx, y), monkeypatch)
    t_end = P["t_end"]
    y2 = y.copy()
    y2[t_end:] = y2[t_end:] * 9.0 + 5.0
    P2 = _prepare(_hourly(idx, y2), monkeypatch)
    assert P["model"].model_to_string() == P2["model"].model_to_string()
    assert np.array_equal(P["spread"], P2["spread"])
    assert P["spread_overall"] == P2["spread_overall"]
