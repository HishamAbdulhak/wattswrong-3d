"""Embed data/timeseries.json into index.html so graphs and hourly costs work from file://.

Compact form, keyed "site/channel": runs of consecutive hours [first_epoch_hour, count],
then actual_kwh (a) and residual_kwh (r) per row, unchanged. predicted = actual - residual.
Run from this folder: python3 embed_series.py
"""
import json
import re
from datetime import datetime

rows = json.load(open("data/timeseries.json"))
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
    assert len(hours) == len(s["a"]) == len(s["r"]) == len(set(hours)), k
    count += len(hours)
assert count == len(rows)

payload = json.dumps(series, separators=(",", ":"))
tag = f'<script type="application/json" id="wattswrong-series">{payload}</script>'
html = open("index.html").read()
pattern = r'<script type="application/json" id="wattswrong-series">.*?</script>'
if re.search(pattern, html, flags=re.S):
    html = re.sub(pattern, lambda _: tag, html, count=1, flags=re.S)
else:
    html = re.sub(r'(<script type="application/json" id="wattswrong-data">.*?</script>)', lambda m: m.group(1) + "\n" + tag, html, count=1, flags=re.S)
open("index.html", "w").write(html)
print(f"Embedded {count} rows, {len(series)} meters, {len(payload) / 1e6:.2f} MB")
