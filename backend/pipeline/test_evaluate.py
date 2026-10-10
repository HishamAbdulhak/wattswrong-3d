# Matching-rule checks on in-memory vectors (docs/adr/0003); not labels or results.
import pandas as pd

from pipeline.evaluate import eligibility, match, merge_events

T = lambda s: pd.Timestamp(s, tz="UTC")


def test_merge_strictly_less_than_6h():
    ev = pd.DataFrame({"site_id": "s", "channel": ["fridge"] * 3,
                       "start": [T("2015-01-01 00:00"), T("2015-01-01 07:59"), T("2015-01-01 20:00")],
                       "end": [T("2015-01-01 02:00"), T("2015-01-01 09:00"), T("2015-01-01 21:00")]})
    m = merge_events(ev)
    assert len(m) == 2 and m.end[0] == T("2015-01-01 09:00")  # 5h59 gap merges, 11h gap does not


def test_exact_channel_preferred_and_one_to_one():
    ev = merge_events(pd.DataFrame({"site_id": "s", "channel": ["fridge"], "start": [T("2015-01-01")], "end": [T("2015-01-02")]}))
    fs = pd.DataFrame({"site_id": "s", "finding_id": ["agg", "fr", "late"], "channel": ["aggregate", "fridge", "fridge"],
                       "detected": [T("2015-01-01 05:00"), T("2015-01-01 05:00"), T("2015-01-03 00:00")]})
    m = match(fs, ev)
    assert [(f, e) for f, e, _ in m] == [("fr", "s-e000")]
    other_site = fs.assign(site_id="t")
    assert match(other_site, ev) == []
    assert m[0][2] == 5.0


def test_followup_window_inclusive_and_censoring():
    ev = merge_events(pd.DataFrame({"site_id": "s", "channel": ["fridge", "fridge"], "start": [T("2015-01-01"), T("2015-01-10")],
                                    "end": [T("2015-01-02"), T("2015-01-10 05:00")]}))
    fs = pd.DataFrame({"site_id": "s", "finding_id": ["a"], "channel": ["fridge"], "detected": [T("2015-01-03")]})
    assert len(match(fs, ev)) == 1  # exactly end + 24 h
    elig, cens, strad = eligibility(ev, T("2015-01-01"), T("2015-01-10 12:00"))
    assert list(elig) == [True, False] and list(cens) == [False, True]
