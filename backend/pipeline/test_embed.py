# Embed step: exports in, the app's two embedded JSON blocks out. In-memory test vectors only
# (site_id "contract-test", docs/adr/0003).
import json
import re
from datetime import datetime, timezone

import pytest

from pipeline.embed import embed

HTML = ('<head><script type="application/json" id="wattswrong-data">{"old":1}</script>\n'
        '<script type="application/json" id="wattswrong-series">{"old":2}</script></head>')


def row(ts, a, r, ch="aggregate"):
    return dict(site_id="contract-test", channel=ch, ts=ts, actual_kwh=a, predicted_kwh=round(a - r, 6),
                residual_kwh=r, anomaly_score=0.1, is_anomalous=False)


def exports(tmp_path, rows):
    (tmp_path / "timeseries.json").write_text(json.dumps(rows))
    (tmp_path / "findings.json").write_text(json.dumps([{"finding_id": "f1"}]))
    (tmp_path / "manifest.json").write_text(json.dumps({"run_id": "r1", "sites": []}))
    (tmp_path / "index.html").write_text(HTML)
    return tmp_path / "index.html"


def block(html, tag):
    return json.loads(re.search(rf'id="{tag}">(.*?)</script>', html, re.S).group(1))


def test_writes_manifest_findings_and_compact_series(tmp_path):
    # Two runs on the aggregate (gap after 01:00), one row on the fridge, given out of order.
    rows = [row("2014-01-01T03:00:00+00:00", 0.3, 0.03), row("2014-01-01T00:00:00+00:00", 0.1, 0.01),
            row("2014-01-01T01:00:00+00:00", 0.2, -0.02), row("2014-01-01T00:00:00+00:00", 0.5, 0.05, "fridge")]
    page = exports(tmp_path, rows)
    embed(tmp_path, page)
    html = page.read_text()
    assert block(html, "wattswrong-data") == {"manifest": {"run_id": "r1", "sites": []}, "findings": [{"finding_id": "f1"}]}
    h0 = int(datetime(2014, 1, 1, tzinfo=timezone.utc).timestamp()) // 3600
    assert block(html, "wattswrong-series") == {
        "contract-test/aggregate": {"runs": [[h0, 2], [h0 + 3, 1]], "a": [0.1, 0.2, 0.3], "r": [0.01, -0.02, 0.03]},
        "contract-test/fridge": {"runs": [[h0, 1]], "a": [0.5], "r": [0.05]},
    }
    assert html.count("<script") == 2


def test_refuses_a_repeated_hour(tmp_path):
    # A real error, not an assert, so the check holds under python -O too.
    page = exports(tmp_path, [row("2014-01-01T00:00:00+00:00", 0.1, 0.01), row("2014-01-01T00:00:00+00:00", 0.2, 0.02)])
    with pytest.raises(ValueError, match="repeated or lost hours"):
        embed(tmp_path, page)
    assert page.read_text() == HTML


def test_leaves_the_rest_of_the_page_byte_for_byte(tmp_path):
    # The real page has non-ASCII text ("←" is e2 86 90 in UTF-8) and may be checked out with CRLF.
    page = exports(tmp_path, [row("2014-01-01T00:00:00+00:00", 0.1, 0.01)])
    original = HTML.replace("<head>", "<head><title>Replay – ← → UK time</title>").replace("\n", "\r\n").encode("utf-8")
    page.write_bytes(original)
    embed(tmp_path, page)
    outside = lambda raw: re.sub(rb'(id="wattswrong-(?:data|series)">).*?(</script>)', rb"\1\2", raw, flags=re.S)
    assert outside(page.read_bytes()) == outside(original)


def test_reads_exports_as_utf8(tmp_path):
    page = exports(tmp_path, [row("2014-01-01T00:00:00+00:00", 0.1, 0.01)])
    (tmp_path / "findings.json").write_bytes(json.dumps([{"title": "Spike – check ←"}], ensure_ascii=False).encode("utf-8"))
    embed(tmp_path, page)
    assert block(page.read_text(encoding="utf-8"), "wattswrong-data")["findings"] == [{"title": "Spike – check ←"}]


def test_a_failed_write_leaves_the_page_untouched(tmp_path, monkeypatch):
    page = exports(tmp_path, [row("2014-01-01T00:00:00+00:00", 0.1, 0.01)])
    before = page.read_bytes()

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr("pipeline.embed.os.replace", fail)
    with pytest.raises(OSError):
        embed(tmp_path, page)
    assert page.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["findings.json", "index.html", "manifest.json", "timeseries.json"]
