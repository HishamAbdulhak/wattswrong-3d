"""Orchestrate tuning (validation only) and the single final test run, then export.

  uv run python -m pipeline.run tune     # replay train_end -> validation_end, grid on validation labels
  uv run python -m pipeline.run final    # needs every frozen value in config; runs the test once

Outputs (final): web/public/data/{timeseries,findings,manifest,metrics}.json,
artifacts/<run_id>/*.parquet, reports/metrics_final.json, reports/matches_final.json.
"""
import argparse
import hashlib
import itertools
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import evaluate as ev
from pipeline.labels import load_labels
from pipeline.model import TZ, DetectorParams, calendar, design, fit, grid, mae_wape, replay, robust_spread
from pipeline.sites import COLD, NICE, SITES

ROOT = Path(__file__).resolve().parent.parent
UNITS = [(site, ch) for site in SITES for ch in SITES[site]["model"]]
DETECT = {(site, ch) for site in SITES for ch in SITES[site]["detect"]}
FROZEN = ["source_timezone", "label_timezone", "train_end", "validation_end", "test_end", "detection_score_min", "persistence_periods",
          "persistence_window", "continuation_score_min", "recovery_periods", "residual_spread_method",
          "residual_spread_floor", "lgbm_objective", "use_four_week_median"]


def load_cfg():
    return json.loads((ROOT / "config/config.json").read_text())


def events_utc(label_tz):
    loc = (lambda s: s.dt.tz_localize("UTC")) if label_tz == "UTC" else \
        (lambda s: s.dt.tz_localize(label_tz, ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC"))
    return pd.concat([pd.DataFrame({"site_id": site, "channel": lab.channel, "start": loc(lab.start_naive),
                                    "end": loc(lab.end_naive), "status": lab.status})
                      for site in SITES for lab in [load_labels(site)]], ignore_index=True)


def load_hourly(input_root=None):
    return {site: pd.read_parquet((input_root or ROOT) / f"data/interim/{site}_hourly.parquet") for site in SITES}


def exclude_mask(index, events, channel):
    """Grid hours overlapping a labelled event (any channel for aggregate). `events` is one site's."""
    m = np.zeros(len(index), bool)
    for e in events.itertuples():
        if channel == "aggregate" or e.channel == channel:
            m |= (index + pd.Timedelta(hours=1) > e.start) & (index < e.end)
    return m


def prepare(hourly, site, channel, events, train_end, objective, use_med4w, floor):
    events = events[events.site_id == site]
    s = grid(hourly[site], channel)
    y, idx = s.to_numpy(), s.index
    cal = calendar(idx)
    pos = np.arange(len(y))
    t_end = idx.searchsorted(train_end)
    excl = exclude_mask(idx, events, channel) & (pos < t_end)  # only training labels, never later ones
    params = {"objective": objective, "num_boost_round": 400, "learning_rate": 0.05, "num_leaves": 31, "min_child_samples": 20}
    # Spread from out-of-sample residuals: fit on first 80% of train, score the last 20%.
    cut = int(t_end * 0.8)
    m80 = fit(y, cal, pos[:cut], excl, params, use_med4w)
    hold = pos[cut:t_end]
    yp = y.copy(); yp[excl] = np.nan
    X, ok = design(yp, cal, hold, use_med4w)
    r = np.full(len(hold), np.nan)
    r[ok] = y[hold[ok]] - m80.predict(X[ok])
    r[excl[hold]] = np.nan
    spread, overall = robust_spread(r, cal["hour"].to_numpy()[hold], floor)
    model = fit(y, cal, pos[:t_end], excl, params, use_med4w)
    return dict(site=site, channel=channel, y=y, idx=idx, cal=cal, excl=excl, t_end=t_end, model=model,
                spread=spread, spread_overall=overall)


def run_channel(P, end_ts, dp, use_med4w):
    end_pos = P["idx"].searchsorted(end_ts)
    pred, z, yp, found = replay(P["y"], P["cal"], P["model"], P["spread"], P["t_end"], end_pos, dp, P["excl"], use_med4w)
    for f in found:
        f.channel = P["channel"]
    return pred, z, found, end_pos


def forecast_metrics(P, pred, lo_ts, hi_ts):
    idx, y = P["idx"], P["y"]
    w = (idx >= lo_ts) & (idx < hi_ts)
    base = np.r_[np.full(168, np.nan), y[:-168]]
    ok = w & np.isfinite(y) & np.isfinite(pred) & np.isfinite(base)  # same valid periods for both
    out = []
    for name, p in (("baseline", base), ("lightgbm", pred)):
        mae, wape, n = mae_wape(np.where(ok, y, np.nan), np.where(ok, p, np.nan))
        out.append({"site_id": P["site"], "channel": P["channel"], "model": name, "mae_kwh": mae, "wape": wape,
                    "valid_periods": n, "reason": None if mae is not None else "no valid periods"})
    return out


def ts_of(P, p, end=False):
    return P["idx"][p] + (pd.Timedelta(hours=1) if end else pd.Timedelta(0))


def findings_from(P, pred, z, detected, end_pos, dp, tariff_rm, peak):
    out = []
    y, idx, hours = P["y"], P["idx"], P["cal"]["hour"].to_numpy()
    for inc in detected:
        last = inc.end if inc.end is not None else end_pos - 1
        span = np.arange(inc.start, last + 1)
        scored = span[np.isfinite(z[span])]
        r = y[scored] - pred[scored]
        excess = float(np.clip(r, 0, None).sum())
        hits = scored[z[scored] >= dp.z_hit]
        mean_z = float(np.mean(z[hits])) if len(hits) else float(np.max(z[scored]))
        conf = round(0.5 * min(mean_z / 4, 1) + 0.5 * min(len(hits) / (2 * dp.persist), 1), 3)
        ongoing = inc.end is None
        rm_month = excess / len(scored) * 24 * 30 * tariff_rm if ongoing and len(scored) else 0.0
        local = idx[scored].tz_convert(TZ)
        e_pos = np.clip(r, 0, None)
        night = e_pos[local.hour < 6].sum() / excess if excess else 0
        in_peak = (local.dayofweek < 5) & (local.hour >= peak[0]) & (local.hour < peak[1])
        peak_share = e_pos[in_peak].sum() / excess if excess else 0
        dur_h = (last - inc.start + 1)
        cat = categorize(P["channel"], dur_h, night, peak_share, (r > 0).mean(), r, local)
        start_ts, det_ts = ts_of(P, inc.start), ts_of(P, inc.detected, end=True)
        end_ts = ts_of(P, inc.end, end=True) if inc.end is not None else None
        title, expl, causes, action = wording(P["channel"], cat, excess, dur_h, start_ts, ongoing)
        out.append({
            "finding_id": f"{P['site']}-{P['channel']}-{det_ts:%Y%m%dT%H%M}",
            "site_id": P["site"], "channel": P["channel"], "category": cat,
            "start_ts": start_ts.isoformat(), "detected_ts": det_ts.isoformat(),
            "end_ts": end_ts.isoformat() if end_ts is not None else None,
            "excess_kwh": round(excess, 4), "rm_per_month": round(rm_month, 2), "confidence": conf,
            "title": title, "explanation": expl, "possible_causes": causes, "action": action,
            "source": "live", "status": "open",
        })
    return out


def categorize(channel, dur_h, night_share, peak_share, pos_share, r, local):
    """Pattern rules (frozen in docs/adr/0006). Aircon is never assigned: no aircon channel exists."""
    if channel != "aggregate":
        return "appliance_abnormal"
    if dur_h <= 12:
        return "spike"
    if night_share >= 0.5:
        return "overnight_excess"
    if dur_h >= 24 * 7:
        daily = pd.Series(r, index=local).resample("D").mean().dropna()
        if len(daily) >= 7 and np.polyfit(np.arange(len(daily)), daily.to_numpy(), 1)[0] > 0 and daily.iloc[-3:].mean() > daily.iloc[:3].mean():
            return "gradual_drift"
    if pos_share >= 0.8 and dur_h >= 24:
        return "baseload_creep"
    if peak_share >= 0.6:
        return "peak_hour_waste"
    return "spike"


def wording(channel, cat, excess, dur_h, start_ts, ongoing):
    when = start_ts.tz_convert(TZ).strftime("%a %d %b %Y %H:%M")
    span = f"{dur_h / 24:.1f} days" if dur_h >= 48 else f"{dur_h} hours"
    tail = "and it is still going" if ongoing else "before returning to normal"
    if channel != "aggregate":
        name = NICE[channel]
        cold = channel in COLD
        causes = (["Door not fully closed or seal not sealing", "Frost build-up", "Thermostat set colder than needed", "A large load of warm food"]
                  if cold else ["Left on longer than usual", "Timer or thermostat setting changed"]
                  if channel == "electric_heater" else ["More or longer cycles than usual", "Hotter programme than usual"])
        action = ("Check the door closes and seals fully, and look for frost build-up." if cold else
                  "Check the heater's timer and thermostat, and switch it off when the room is empty." if channel == "electric_heater" else
                  "Check recent programme choices; a cooler or shorter cycle uses less energy.")
        return (f"{name} using more than expected",
                f"{name}'s own plug meter used {excess:.2f} kWh more than its day-ahead forecast over {span} from {when} (UK time), {tail}. "
                "This is a usage pattern worth checking, not a confirmed fault.", causes, action)
    t = {
        "spike": ("Burst of extra household usage", "Look back at what was running at that time and whether it needed to be."),
        "overnight_excess": ("Extra usage overnight", "Do a walk-round after bedtime and switch off anything running that doesn't need to be."),
        "baseload_creep": ("Always-on usage has stepped up", "Read the meter when everything should be off and compare with a normal week."),
        "gradual_drift": ("Usage creeping up day by day", "Compare this week's habits and devices with a few weeks ago to find what changed."),
        "peak_hour_waste": ("Extra usage in the weekday 2pm-10pm window", "Check what runs on weekday afternoons and evenings and whether it can move or stop."),
    }[cat]
    return (t[0], f"The whole-house meter used {excess:.2f} kWh more than its day-ahead forecast over {span} from {when} (UK time), {tail}. "
            "The meter shows the pattern, not which device caused it.", [], t[1])


def flags(P, z, detected, n, dp):
    f = np.zeros(n, bool)
    for i in detected:
        lo = i.detected + 1  # rows from detected_ts (end of the confirming hour) onward
        hi = (i.end if i.end is not None else n - 1)
        f[lo:hi + 1] = True
    return f & (np.nan_to_num(z) >= dp.z_high)


def timeseries_rows(P, pred, z, fl, lo_pos, end_pos):
    y, idx = P["y"], P["idx"]
    rows = []
    for p in range(lo_pos, end_pos):
        if not (np.isfinite(y[p]) and np.isfinite(pred[p]) and np.isfinite(z[p])):
            continue
        a, pr = round(float(y[p]), 6), round(float(pred[p]), 6)
        rows.append({"site_id": P["site"], "channel": P["channel"], "ts": idx[p].isoformat(), "actual_kwh": a,
                     "predicted_kwh": pr, "residual_kwh": round(a - pr, 9), "anomaly_score": round(float(z[p]), 4),
                     "is_anomalous": bool(fl[p])})
    return rows


def evaluate_window(all_findings, events, lo, hi, exposure):
    """exposure: {(site, channel): scored hours in window}."""
    fdf = pd.DataFrame([{"finding_id": f["finding_id"], "site_id": f["site_id"], "channel": f["channel"],
                         "detected": pd.Timestamp(f["detected_ts"])} for f in all_findings],
                       columns=["finding_id", "site_id", "channel", "detected"])
    merged = ev.merge_events(events[["site_id", "channel", "start", "end"]])
    house_hours = sum(exposure[(s, "aggregate")] for s in SITES)
    res = [ev.score("all sites, all channels (appliance or whole-house finding)", fdf, merged, lo, hi, house_hours),
           ev.score("all sites, whole-house meter only", fdf[fdf.channel == "aggregate"], merged, lo, hi, house_hours)]
    for site, ch in UNITS:
        if ch != "aggregate" and (site, ch) in DETECT:
            res.append(ev.score(f"{site} {ch}", fdf[(fdf.site_id == site) & (fdf.channel == ch)],
                                merged[(merged.site_id == site) & (merged.channel == ch)], lo, hi, exposure[(site, ch)]))
    return res, merged


def detector(cfg_or_dict):
    s = cfg_or_dict
    return DetectorParams(z_high=2.0, z_hit=s["detection_score_min"], z_low=s["continuation_score_min"], window=s["persistence_window"],
                          persist=s["persistence_periods"], recovery=s["recovery_periods"])


def tune():
    cfg = load_cfg()
    s = cfg["suggested"]
    for k in ("label_timezone", "train_end", "validation_end"):
        if s.get(k) is None:
            sys.exit(f"config suggested.{k} is null; freeze it first")
    lo, hi = pd.Timestamp(s["train_end"]), pd.Timestamp(s["validation_end"])
    events = events_utc(s["label_timezone"])
    hourly = load_hourly()
    report = {"window": [str(lo), str(hi)], "forecast": [], "detector_grid": []}
    floor = 0.005
    prepared = {}
    for obj, med in itertools.product(("l2", "l1"), (True, False)):
        for site, ch in UNITS:
            P = prepare(hourly, site, ch, events, lo, obj, med, floor)
            prepared[(obj, med, site, ch)] = P
            pred, z, inc, end_pos = run_channel(P, hi, DetectorParams(2, 2, 1, 6, 3, 3), med)
            for m in forecast_metrics(P, pred, lo, hi):
                report["forecast"].append({**m, "objective": obj, "four_week_median": med})
    best = min(itertools.product(("l2", "l1"), (True, False)),
               key=lambda k: np.mean([m["wape"] for m in report["forecast"] if m["model"] == "lightgbm"
                                      and (m["objective"], m["four_week_median"]) == k and m["wape"] is not None]))
    report["chosen_forecast"] = {"objective": best[0], "four_week_median": best[1]}
    for zhit, persist, window, zlow, rec in itertools.product((2.0, 3.0), (3, 6, 12), (6, 24), (1.0, 1.5), (3,)):
        if persist > window:
            continue
        dp = DetectorParams(2.0, zhit, zlow, window, persist, rec)
        fs, exposure = [], {}
        for site, ch in UNITS:
            P = prepared[(best[0], best[1], site, ch)]
            pred, z, inc, end_pos = run_channel(P, hi, dp, best[1])
            if (site, ch) in DETECT:
                fs += findings_from(P, pred, z, inc, end_pos, dp, cfg["agreed"]["tariff_sen_per_kwh"] / 100, (14, 22))
            w = (P["idx"] >= lo) & (P["idx"] < hi)
            exposure[(site, ch)] = int((w & np.isfinite(z)).sum())
        res, _ = evaluate_window(fs, events, lo, hi, exposure)
        a = res[0]
        f1 = (2 * a["recall"] * a["precision"] / (a["recall"] + a["precision"])
              if a["recall"] and a["precision"] else 0.0)
        report["detector_grid"].append({"z_hit": zhit, "persist": persist, "window": window, "z_low": zlow, "recovery": rec,
                                        "f1_all": f1, "recall": a["recall"], "precision": a["precision"],
                                        "unmatched_per_house_month": a["unmatched_per_house_month"],
                                        "findings": a["findings"], "eligible_events": a["eligible_events"]})
    report["detector_grid"].sort(key=lambda r: (-r["f1_all"], r["unmatched_per_house_month"] or 0))
    (ROOT / "reports/tuning_validation.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({"chosen_forecast": report["chosen_forecast"], "top_detector": report["detector_grid"][:5]}, indent=2))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def config_sha256(path):
    # Git may check out JSON with CRLF on Windows; the frozen run used LF.
    content = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def reproduction_root(path):
    """Resolve aliases before checking that verification cannot touch the checkout."""
    out, root = Path(path).resolve(), ROOT.resolve()
    if out.is_relative_to(root) or root.is_relative_to(out):
        sys.exit("reproduction output must be outside the repository and not its ancestor")
    if out.exists():
        # Refuse reused directories, including symlinks/junctions within them.
        sys.exit("reproduction output already exists; choose a new folder")
    return out


def final(rerun_reason=None, output_root=None, input_root=None):
    destination = reproduction_root(output_root) if output_root is not None else ROOT
    cfg = load_cfg()
    s = cfg["suggested"]
    missing = [k for k in FROZEN if s.get(k) is None]
    if missing:
        sys.exit(f"config has unfrozen values {missing}; freeze them before the final test")
    lock = destination / "reports/metrics_final.json"
    if lock.exists() and not rerun_reason:
        sys.exit("final test already ran (reports/metrics_final.json). Re-running needs --rerun-reason, which is logged.")
    t_end, v_end, x_end = (pd.Timestamp(s[k]) for k in ("train_end", "validation_end", "test_end"))
    events = events_utc(s["label_timezone"])
    hourly = load_hourly(input_root) if input_root is not None else load_hourly()
    dp = detector(s)
    tariff = cfg["agreed"]["tariff_sen_per_kwh"] / 100
    rows, findings, forecast, exposure, spreads = [], [], [], {}, {}
    for site, ch in UNITS:
        P = prepare(hourly, site, ch, events, t_end, s["lgbm_objective"], s["use_four_week_median"], s["residual_spread_floor"])
        pred, z, inc, end_pos = run_channel(P, x_end, dp, s["use_four_week_median"])
        if (site, ch) in DETECT:
            fl = flags(P, z, inc, len(z), dp)
            rows += timeseries_rows(P, pred, z, fl, P["t_end"], end_pos)
            findings += findings_from(P, pred, z, inc, end_pos, dp, tariff, (14, 22))
        forecast += forecast_metrics(P, pred, v_end, x_end)
        w = (P["idx"] >= v_end) & (P["idx"] < x_end)
        exposure[(site, ch)] = int((w & np.isfinite(z)).sum())
        # No usable out-of-sample residuals (e.g. a labelled event covers the hold-out) leaves overall NaN; the
        # per-hour spread then sits at the floor. JSON has no NaN, so export it as null.
        overall = P["spread_overall"] if np.isfinite(P["spread_overall"]) else None
        spreads[f"{site}/{ch}"] = {"per_local_hour": [round(float(x), 5) for x in P["spread"]], "overall_mad": overall}
    det, merged = evaluate_window(findings, events, v_end, x_end, exposure)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    cfg_hash = config_sha256(ROOT / "config/config.json")[:12]
    quality = {site: json.loads(((input_root or ROOT) / f"reports/quality_{site}.json").read_text()) for site in SITES}
    metrics = {
        "run_id": run_id, "source": "real", "code_revision": rev, "config_sha256_12": cfg_hash,
        "split": {"train_end": str(t_end), "validation_end": str(v_end), "test_end": str(x_end)},
        "forecast": forecast,
        "detection": [{k: v for k, v in d.items() if k != "matches"} for d in det],
        "notes": [
            "Test window = validation_end to test_end, scored once; all settings were chosen on validation only.",
            "Labels are REFIT annotations of unusual appliance behaviour (Rashid et al. 2019), not confirmed faults; annotation may be incomplete.",
            "Exposure uses 30-day months of scored (valid) hours.",
            f"Merged labelled events in window are listed in reports/matches_final.json.",
        ] + ([f"Re-run reason: {rerun_reason}"] if rerun_reason else []),
    }
    data_dir = destination / "web/public/data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "timeseries.json").write_text(json.dumps(rows, allow_nan=False))
    (data_dir / "findings.json").write_text(json.dumps(findings, allow_nan=False, indent=1))
    (data_dir / "metrics.json").write_text(json.dumps(metrics, allow_nan=False, indent=1))
    def coverage(site):
        ts = [r["ts"] for r in rows if r["site_id"] == site and r["channel"] == "aggregate"]
        return {"coverage_start": ts[0], "coverage_end": ts[-1]} if ts else {"coverage_start": "", "coverage_end": ""}
    manifest = {
        "run_id": run_id, "generated_at": datetime.now(timezone.utc).isoformat(), "config_version": cfg_hash,
        "code_revision": rev, "resolution_minutes": 60, "source_timezone": s["source_timezone"],
        "sites": [{"site_id": site, "label": SITES[site]["label"], **coverage(site), "channels": SITES[site]["detect"]}
                  for site in SITES],
        "sources": [
            *({"name": f"REFIT: Electrical Load Measurements (Cleaned), {q['source_file']}, Murray & Stankovic, University of Strathclyde",
               "url": SITES[site]["source_url"], "licence": "CC BY 4.0", "md5": q["md5"]} for site, q in quality.items()),
            {"name": "Annotated load anomalies from the REFIT dataset, Rashid et al., ICASSP 2019",
             "url": "https://doi.org/10.15129/9729a2a0-11ce-4cce-b0d0-144c483fcb33", "licence": "CC BY 4.0",
             "sha256": sha256(ROOT / "data/raw/labels/REFIT_anomalies.csv")},
        ],
        "spread": spreads,
    }
    (data_dir / "manifest.json").write_text(json.dumps(manifest, allow_nan=False, indent=1))
    art = destination / "artifacts" / run_id
    art.mkdir(parents=True)
    pd.DataFrame(rows).to_parquet(art / "timeseries.parquet", index=False)
    pd.DataFrame(findings).to_parquet(art / "findings.parquet", index=False)
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps(metrics, indent=2))
    (destination / "reports/matches_final.json").write_text(json.dumps(
        {"events": merged.astype(str).to_dict("records"), "matches": {d["scope"]: d["matches"] for d in det}}, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    stages = parser.add_subparsers(dest="stage", required=True)
    stages.add_parser("tune")
    final_parser = stages.add_parser("final")
    final_parser.add_argument("--rerun-reason")
    final_parser.add_argument("--output-root", type=Path,
                              help="verification only: a new directory outside this checkout; leaves frozen outputs and lock intact")
    args = parser.parse_args()
    if args.stage == "tune":
        tune()
    else:
        final(args.rerun_reason, args.output_root)
