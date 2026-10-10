"""REFIT annotated anomalies (Rashid et al., ICASSP 2019; CC BY 4.0).

Label times are naive strings (dd/mm/YYYY HH:MM). Their timezone is not stated in
README_ICASSP.txt; reports/spike_<site>.md resolves it empirically.
"""
from pathlib import Path

import pandas as pd

from pipeline.sites import SITES

ROOT = Path(__file__).resolve().parent.parent
LABELS_CSV = ROOT / "data/raw/labels/REFIT_anomalies.csv"


def load_labels(site):
    s = SITES[site]
    d = pd.read_csv(LABELS_CSV, index_col=0)
    d = d[d.House_No == s["number"]]
    unknown = set(d.Appliance) - set(s["labels"])
    if unknown:
        raise ValueError(f"{site}: unmapped label appliances {unknown}")
    fmt = "%d/%m/%Y %H:%M"
    return pd.DataFrame({
        "appliance": d.Appliance,
        "channel": d.Appliance.map(s["labels"]),
        "start_naive": pd.to_datetime(d.start_anomaly, format=fmt),
        "end_naive": pd.to_datetime(d.end_anomaly, format=fmt),
        "status": d.Status,
        "explanation": d.Explanation,
    })
