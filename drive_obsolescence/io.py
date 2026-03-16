from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
from .settings import Settings

def _read_excel(path):
    if not path:
        return pd.DataFrame()
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_excel(p)

def _read_csv(path):
    if not path:
        return pd.DataFrame()
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)

def load_units(settings: Settings) -> pd.DataFrame:
    master_path = settings.paths.get("units_master")
    master = _read_csv(master_path) if str(master_path).endswith(".csv") else _read_excel(master_path)
    if master.empty:
        alt_path = settings.paths.get("units_all")
        master = _read_csv(alt_path) if str(alt_path or "").endswith(".csv") else _read_excel(alt_path)

    active = _read_csv(settings.paths.get("units_active"))

    needed_cols = [
        "ContractNo","UnitNo","Drive_x","Motor Power","Speed",
        "BuildingName","vBranchID","CustomerId","active unit list/contract"
    ]
    for col in needed_cols:
        if col not in master:
            master[col] = np.nan

    master["UnitNo"] = master["UnitNo"].astype(str)
    master["ContractNo"] = master["ContractNo"].astype(str)

    if not active.empty:
        active["UnitNo"] = active["UnitNo"].astype(str)
        master = master.merge(
            active[["UnitNo","ContractNo"]].drop_duplicates("UnitNo"),
            on="UnitNo",
            how="left"
        )

    return master

def load_customer_addresses(settings: Settings) -> pd.DataFrame:
    path = settings.paths.get("customer_address")
    df = _read_csv(path) if str(path).endswith(".csv") else _read_excel(path)
    if df.empty:
        return df

    df["CustomerAddress"] = df["CustomerAddress"].astype(str)
    parts = df["CustomerAddress"].str.split(r"_x000D_\n|_x000D_|\\n", expand=True)
    parts = parts.rename(columns={0:"custadd1",1:"custadd2",2:"custadd3",3:"custadd4"})
    return pd.concat([df, parts], axis=1)

def load_cycle_summary(settings: Settings) -> pd.DataFrame:
    path = settings.paths.get("cycle_summary")
    df = _read_csv(path) if str(path).endswith(".csv") else _read_excel(path)
    if "sent date" in df:
        df = df.rename(columns={"sent date":"cycle actual sent date"})
    return df

def load_callbacks(settings: Settings) -> pd.DataFrame:
    dfs = []
    for key in ("callbacks_2023","callbacks_2024","callbacks_2025"):
        path = settings.paths.get(key)
        if path:
            df = _read_csv(path) if str(path).endswith(".csv") else _read_excel(path)
            if not df.empty:
                dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    cb = pd.concat(dfs, axis=0, ignore_index=True)

    cb["CallbackDate"] = pd.to_datetime(cb.get("CallbackDate"), errors="coerce")
    cb["Callback Year"] = cb["CallbackDate"].dt.year
    cb["Callback Month"] = cb["CallbackDate"].dt.month

    for col in ["vT1","T2","vT3"]:
        if col not in cb:
            cb[col] = 0

    drive_mask = cb.get("MainComponentName", pd.Series(dtype=str)).astype(str).str.contains("drive", case=False, na=False)
    cb["Drive Callback"] = drive_mask.astype(float)
    cb["Drive time"] = np.where(drive_mask, cb[["vT1","T2","vT3"]].sum(axis=1), 0.0)
    cb["Total Callback"] = 1.0
    cb["Callback time"] = cb[["vT1","T2","vT3"]].sum(axis=1)

    return cb
