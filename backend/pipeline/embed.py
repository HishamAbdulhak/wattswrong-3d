"""Embed the run's exports into the static app (../index.html), so it works from file://.

Usage: uv run python -m pipeline.embed [DATA_DIR]   (default: web/public/data; validated first)

wattswrong-data: {"manifest", "findings"} as exported.
wattswrong-series: compact form keyed "site/channel": runs of consecutive hours
[first_epoch_hour, count], then actual_kwh (a) and residual_kwh (r) per row, unchanged.
predicted = actual - residual.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from pipeline.validate import validate

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT.parent / "index.html"


def compact(rows):
    series = {}
    for row in sorted(rows, key=lambda x: (x["site_id"], x["channel"], x["ts"])):
        s = series.setdefault(f'{row["site_id"]}/{row["channel"]}', {"runs": [], "a": [], "r": []})
        hour = int(datetime.fromisoformat(row["ts"]).timestamp()) // 3600
        if s["runs"] and sum(s["runs"][-1]) == hour:
            s["runs"][-1][1] += 1
        else:
            s["runs"].append([hour, 1])
        s["a"].append(row["actual_kwh"])
        s["r"].append(row["residual_kwh"])
    # Check: runs expand to one unique hour per row, and every row is kept.
    count = 0
    for k, s in series.items():
        hours = [h0 + i for h0, n in s["runs"] for i in range(n)]
        assert len(hours) == len(s["a"]) == len(s["r"]) == len(set(hours)), f"{k}: repeated or lost hours"
        count += len(hours)
    assert count == len(rows), "rows lost"
    return series


def replace_block(html, tag, value):
    payload = json.dumps(value, separators=(",", ":")).replace("</", "<\\/")
    html, n = re.subn(rf'(<script type="application/json" id="{tag}">).*?(</script>)',
                      lambda m: m.group(1) + payload + m.group(2), html, count=1, flags=re.S)
    assert n == 1, f"no {tag} block in the app"
    return html


def embed(data_dir, app=APP):
    data_dir = Path(data_dir)
    read = lambda name: json.loads((data_dir / name).read_text())
    rows = read("timeseries.json")
    series = compact(rows)
    html = Path(app).read_text()
    html = replace_block(html, "wattswrong-data", {"manifest": read("manifest.json"), "findings": read("findings.json")})
    html = replace_block(html, "wattswrong-series", series)
    Path(app).write_text(html)
    return len(rows), len(series)


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "web/public/data"
    errors = validate(d)
    if errors:
        sys.exit(f"{len(errors)} contract violation(s) in {d}; run pipeline.validate. Nothing embedded.")
    rows, meters = embed(d)
    print(f"Embedded {rows} rows, {meters} meters into {APP}")
