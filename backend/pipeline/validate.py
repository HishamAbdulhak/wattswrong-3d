"""Validate exported timeseries/findings JSON against the locked contracts.

Usage: uv run python -m pipeline.validate [DATA_DIR]   (default: web/public/data)
Exits non-zero and prints every violation if anything fails.
"""
import json
import math
import sys
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
RESIDUAL_TOL = 1e-6


def _reject_constant(name):
    raise ValueError(f"non-finite JSON constant {name}")


def load_json(path):
    # Python's json accepts NaN/Infinity by default; the contract forbids them.
    return json.loads(Path(path).read_text(), parse_constant=_reject_constant)


def schema_errors(name, rows):
    schema = load_json(ROOT / "contracts" / f"{name}.schema.json")
    v = Draft202012Validator(schema, format_checker=FormatChecker())
    return [f"{name}{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(rows)]


def ts(s):
    return datetime.fromisoformat(s)


def cross_errors(timeseries, findings):
    errs = []
    keys, last = set(), {}
    for i, r in enumerate(timeseries):
        nums = [r[k] for k in ("actual_kwh", "predicted_kwh", "residual_kwh", "anomaly_score")]
        if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in nums):
            errs.append(f"timeseries[{i}]: non-finite number")
            continue
        if abs(r["residual_kwh"] - (r["actual_kwh"] - r["predicted_kwh"])) > RESIDUAL_TOL:
            errs.append(f"timeseries[{i}]: residual_kwh != actual_kwh - predicted_kwh")
        t = ts(r["ts"])
        if t.tzinfo is None:
            errs.append(f"timeseries[{i}]: ts has no offset")
            continue
        series = (r["site_id"], r["channel"])
        if (series, t) in keys:
            errs.append(f"timeseries[{i}]: duplicate {series} {r['ts']}")
        keys.add((series, t))
        if series in last and t < last[series]:
            errs.append(f"timeseries[{i}]: ts out of order for {series}")
        last[series] = t

    ids = set()
    for i, f in enumerate(findings):
        if f["finding_id"] in ids:
            errs.append(f"findings[{i}]: duplicate finding_id {f['finding_id']}")
        ids.add(f["finding_id"])
        for k in ("excess_kwh", "rm_per_month", "confidence"):
            if not math.isfinite(f[k]):
                errs.append(f"findings[{i}]: non-finite {k}")
        start, det = ts(f["start_ts"]), ts(f["detected_ts"])
        if start > det:
            errs.append(f"findings[{i}]: start_ts after detected_ts")
        if f["end_ts"] is not None:
            if det > ts(f["end_ts"]):
                errs.append(f"findings[{i}]: detected_ts after end_ts")
            if f["rm_per_month"] != 0:
                errs.append(f"findings[{i}]: ended finding must have rm_per_month 0")

    windows = {}
    for f in findings:
        end = ts(f["end_ts"]) if f["end_ts"] else None
        windows.setdefault((f["site_id"], f["channel"]), []).append((ts(f["detected_ts"]), end))
    for i, r in enumerate(timeseries):
        if not r["is_anomalous"]:
            continue
        if r["anomaly_score"] < 2:
            errs.append(f"timeseries[{i}]: is_anomalous with anomaly_score < 2")
        t = ts(r["ts"])
        if not any(d <= t and (e is None or t <= e) for d, e in windows.get((r["site_id"], r["channel"]), [])):
            errs.append(f"timeseries[{i}]: is_anomalous outside any same-channel finding window")
    return errs


def validate(data_dir):
    data_dir = Path(data_dir)
    timeseries = load_json(data_dir / "timeseries.json")
    findings = load_json(data_dir / "findings.json")
    errs = schema_errors("timeseries", timeseries) + schema_errors("findings", findings)
    return errs or cross_errors(timeseries, findings)


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else ROOT / "web" / "public" / "data"
    errors = validate(d)
    for e in errors[:200]:
        print(e)
    print(f"{len(errors)} violation(s) in {d}")
    sys.exit(1 if errors else 0)
