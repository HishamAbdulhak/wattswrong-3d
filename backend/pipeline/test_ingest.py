# Arithmetic checks on in-memory vectors only (docs/adr/0003); not measurements.
import numpy as np

from pipeline.ingest import HOUR, hourly_energy


def test_constant_power_one_hour():
    t = np.arange(0, HOUR + 8, 8)          # samples every 8 s through the hour boundary
    hours, kwh, seen = hourly_energy(t, np.full(len(t), 1000.0))
    assert hours[0] == 0 and abs(kwh[0] - 1.0) < 1e-9 and seen[0] == HOUR


def test_boundary_split_and_gap():
    t = np.array([HOUR - 4, HOUR + 4, HOUR + 500])   # 8 s interval straddles boundary, then a 496 s gap
    hours, kwh, seen = hourly_energy(t, np.array([3600.0, 3600.0, 3600.0]))
    assert seen[0] == 4 and seen[1] == 4             # gap > MAX_HOLD_S is unobserved, not zero-power
    assert abs(kwh[0] - 3600 * 4 / 3.6e6) < 1e-12


def test_negative_power_is_unobserved():
    t = np.arange(0, 80, 8)
    w = np.full(len(t), 100.0); w[3] = -5
    _, _, seen = hourly_energy(t, w)
    assert seen[0] == 72 - 8
