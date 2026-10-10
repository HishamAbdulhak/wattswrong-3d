# Leakage audit on in-memory vectors (docs/adr/0003): features for hour p must not
# change when anything at p-23 or later changes.
import numpy as np

from pipeline.model import lag_features


def test_features_ignore_last_23_hours():
    rng = np.random.default_rng(0)
    yp = rng.random(2000)
    p = 1500
    before = lag_features(yp, [p])
    yp2 = yp.copy()
    yp2[p - 23:] = 1e6
    assert np.array_equal(before, lag_features(yp2, [p]))
    yp3 = yp.copy()
    yp3[p - 24] = 1e6  # same hour yesterday is allowed and must be used
    assert not np.array_equal(before, lag_features(yp3, [p]))
