# Contract-rule inputs below are in-memory test vectors for the validator only
# (site_id "contract-test"); they are never written to exports. See docs/adr/0003.
import json

import pytest

from pipeline.validate import cross_errors, load_json, schema_errors, validate


def row(**kw):
    r = dict(site_id="contract-test", channel="aggregate", ts="2014-01-01T00:00:00+00:00",
             actual_kwh=1.0, predicted_kwh=0.5, residual_kwh=0.5, anomaly_score=0.1, is_anomalous=False)
    return {**r, **kw}


def finding(**kw):
    f = dict(finding_id="t1", site_id="contract-test", channel="aggregate", category="baseload_creep",
             start_ts="2014-01-01T00:00:00+00:00", detected_ts="2014-01-01T06:00:00+00:00", end_ts=None,
             excess_kwh=1.0, rm_per_month=1.0, confidence=0.6, title="t", explanation="t",
             possible_causes=[], action="t", source="live", status="open")
    return {**f, **kw}


def test_empty_arrays_pass(tmp_path):
    (tmp_path / "timeseries.json").write_text("[]")
    (tmp_path / "findings.json").write_text("[]")
    assert validate(tmp_path) == []


def test_nan_rejected(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('[{"a": NaN}]')
    with pytest.raises(ValueError):
        load_json(p)


def test_schema_rejects_unknown_category_and_extra_column():
    assert schema_errors("findings", [finding(category="broken_fridge")])
    assert schema_errors("timeseries", [row(extra=1)])
    assert schema_errors("timeseries", [row(ts="not a time")])
    assert not schema_errors("findings", [finding()])


def test_cross_rules():
    assert not cross_errors([row()], [finding()])
    assert cross_errors([row(residual_kwh=0.4)], [])
    assert cross_errors([row(), row()], [])  # duplicate key
    assert cross_errors([row(ts="2014-01-01T01:00:00+00:00"), row()], [])  # out of order
    assert cross_errors([], [finding(end_ts="2014-01-02T00:00:00+00:00")])  # ended, rm != 0
    assert not cross_errors([], [finding(end_ts="2014-01-02T00:00:00+00:00", rm_per_month=0)])
    assert cross_errors([], [finding(start_ts="2014-01-02T00:00:00+00:00")])  # start > detected
    # anomalous row: before detection, wrong channel, low score -> errors; inside window -> ok
    hit = row(ts="2014-01-01T07:00:00+00:00", anomaly_score=2.5, is_anomalous=True)
    assert not cross_errors([hit], [finding()])
    assert cross_errors([row(anomaly_score=2.5, is_anomalous=True)], [finding()])
    assert cross_errors([hit], [finding(channel="fridge")])
    assert cross_errors([{**hit, "anomaly_score": 1.5}], [finding()])


def test_reads_exports_as_utf8_on_any_platform(tmp_path):
    # Raw UTF-8 ("←" is e2 86 90) must load the same on Windows, whose default encoding is cp1252.
    p = tmp_path / "findings.json"
    p.write_bytes(json.dumps([{"title": "Spike – check ←"}], ensure_ascii=False).encode("utf-8"))
    assert load_json(p) == [{"title": "Spike – check ←"}]
