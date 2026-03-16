from __future__ import annotations
import pandas as pd

def assign_dates(df, schedule_cfg):
    if df.empty: return df
    fix = pd.to_datetime(schedule_cfg["breakdown_fixed_date"])
    start = pd.to_datetime(schedule_cfg["even_start"])
    end   = pd.to_datetime(schedule_cfg["even_end"])

    months = pd.date_range(start=start, end=end, freq="MS")
    buckets = [pd.Timestamp(y,m,15) for y,m in zip(months.year,months.month)]

    out = df.copy()
    flags = out["Breakdown type"].isin(["freq other","time other"])
    out.loc[flags,"drive proposal date"] = fix

    rest = out.loc[~flags].copy()
    if not rest.empty:
        for br, sub in rest.groupby("vBranchID"):
            n = sub.shape[0]; k = len(buckets)
            dates = [buckets[i%k] for i in range(n)]
            out.loc[sub.index,"drive proposal date"] = dates

    out["drive proposal date"] = pd.to_datetime(out["drive proposal date"])
    out["2025 reply date"] = out["drive proposal date"] + pd.offsets.DateOffset(months=1)
    out["drive proposal date (format)"] = out["drive proposal date"].dt.strftime("%d %b %Y")
    out["2025 reply date (format)"] = out["2025 reply date"].dt.strftime("%d %b %Y")
    out["sent month"] = out["drive proposal date"].dt.strftime("%b %Y")
    return out
