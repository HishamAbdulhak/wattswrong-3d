"""Real-label evaluation rules (frozen before scoring; spec "Evaluation and evidence rules").

- Merge same-channel label rows separated by strictly less than 6 h.
- Eligible: event starts inside the window and end + 24 h <= window end. Events that
  straddle the window start are excluded; events whose follow-up runs past the end are
  censored. Both are counted and reported.
- A finding matches an event on the same site when it is on the event's channel or on
  aggregate and event.start <= detected_ts <= event.end + 24 h (inclusive).
- One-to-one greedy: pairs sorted by detected_ts, exact channel before aggregate,
  event start, then ids.
"""
import numpy as np
import pandas as pd

MERGE_LT = pd.Timedelta(hours=6)
FOLLOWUP = pd.Timedelta(hours=24)


def merge_events(ev):
    """ev: DataFrame[site_id, channel, start, end] in UTC. Returns merged events with event_id."""
    rows = []
    for (site, ch), g in ev.sort_values("start").groupby(["site_id", "channel"]):
        cur = None
        for r in g.itertuples():
            if cur and r.start - cur["end"] < MERGE_LT:
                cur["end"] = max(cur["end"], r.end)
                cur["n_rows"] += 1
            else:
                if cur:
                    rows.append(cur)
                cur = {"site_id": site, "channel": ch, "start": r.start, "end": r.end, "n_rows": 1}
        rows.append(cur)
    out = pd.DataFrame(rows).sort_values(["site_id", "start", "channel"]).reset_index(drop=True)
    out["event_id"] = [f"{s}-e{i:03d}" for i, s in enumerate(out.site_id)]
    return out


def eligibility(events, lo, hi):
    straddle = (events.start < lo) & (events.end >= lo)
    inside = events.start >= lo
    censored = inside & (events.end + FOLLOWUP > hi) & (events.start <= hi)
    eligible = inside & ~censored & (events.start <= hi)
    return eligible, censored, straddle


def match(findings, events):
    """findings: DataFrame[finding_id, site_id, channel, detected]; events: merged eligible events.
    Returns list of (finding_id, event_id, delay_hours)."""
    pairs = []
    for f in findings.itertuples():
        for e in events.itertuples():
            if f.site_id == e.site_id and f.channel in (e.channel, "aggregate") and e.start <= f.detected <= e.end + FOLLOWUP:
                pairs.append((f.detected, 0 if f.channel == e.channel else 1, e.start, f.finding_id, e.event_id,
                              (f.detected - e.start).total_seconds() / 3600))
    used_f, used_e, out = set(), set(), []
    for _, _, _, fid, eid, delay in sorted(pairs):
        if fid not in used_f and eid not in used_e:
            used_f.add(fid); used_e.add(eid); out.append((fid, eid, delay))
    return out


def score(scope, findings, events, lo, hi, exposure_hours):
    elig, cens, strad = eligibility(events, lo, hi)
    ev = events[elig]
    fs = findings[(findings.detected >= lo) & (findings.detected <= hi)]
    m = match(fs, ev)
    exposure_months = exposure_hours / (24 * 30)
    n_ev, n_f, n_m = len(ev), len(fs), len(m)
    unmatched_f = n_f - n_m
    return {
        "scope": scope,
        "eligible_events": int(n_ev), "censored_events": int(cens.sum()), "straddling_excluded": int(strad.sum()),
        "matched_events": int(n_m), "findings": int(n_f), "matched_findings": int(n_m),
        "recall": n_m / n_ev if n_ev else None,
        "precision": n_m / n_f if n_f else None,
        "median_delay_hours": float(np.median([d for *_, d in m])) if m else None,
        "unmatched_per_house_month": unmatched_f / exposure_months if exposure_months > 0 else None,
        "exposure_months": exposure_months,
        "reason": None if n_ev else "no eligible labelled events in window",
        "matches": [{"finding_id": f, "event_id": e, "delay_hours": d} for f, e, d in m],
    }
