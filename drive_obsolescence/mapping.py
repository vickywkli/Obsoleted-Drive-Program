from __future__ import annotations
import ast, operator as op
import numpy as np
import pandas as pd

# ---- Safe arithmetic evaluator for YAML "material" expressions (e.g., "(458+3500+980)*9+2500+3000+4500")
_OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv}
def _safe_eval(expr: str) -> float:
    def _eval(node):
        if isinstance(node, ast.Num):           # numbers
            return node.n
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:  # a (+|-|*|/) b
            return _OPS[type(node.op)](_eval(noderight))
        raise ValueError(f"Unsupported expression: {expr}")
    return float(_eval(ast.parse(expr, mode="eval").body))

# ---- Normalize existing drive text to canonical types used in rules
def normalize_drive_type(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.upper()
    return np.where(s.str.contains(r"\bOVF\s*10\b"), "OVF 10",
           np.where(s.str.contains(r"\bOVF\s*20\b"), "OVF 20",
           np.where(s.str.contains(r"\bOVF\s*30\b"), "OVF 30",
           np.where(s.str.contains(r"\bOVF\s*428\b"),"OVF 428",
           np.where(s.str.contains(r"\bVFCU\b"),     "VFCU", "UNKNOWN")))))

# ---- Core: map to New Drive, compute costs and payment text
def compute_new_drive(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    """
    Inputs:
      df    : DataFrame containing at least ['ContractNo','UnitNo','Drive_x','Motor Power','Speed']
      rules : settings.rules from config.yaml (drive mapping, labor/margin, payment rules)

    Outputs (adds columns):
      'drive_type','New Drive','Drive Material','Drive SMH','drive unit rate',
      'Drive Qty','2025 drive total','paymenteng','paymentchi','Proposed Items'
    """
    out = df.copy()

    # 1) Normalize existing drive type
    out["drive_type"] = normalize_drive_type(out["Drive_x"])

    # 2) Ensure numeric fields
    out["Motor Power"] = pd.to_numeric(out.get("Motor Power"), errors="coerce")
    high_speed = out.get("Speed", pd.Series(index=out.index, dtype=float)).fillna(0) >= 2

    # 3) Initialize outputs
    out["New Drive"] = None
    out["Drive Material"] = np.nan

    # 4) If existing is VFCU → force VFCU 2 (or your override)
    vfc_new = rules.get("vfc u_new_drive", "VFCU 2")
    vmask = out["drive_type"].eq("VFCU")
    out.loc[vmask, "New Drive"] = vfc_new
    out.loc[vmask, "Drive Material"] = 0.0

    # 5) Power/speed bands from YAML
    for br in rules.get("new_drive_by_power", []):
        mask = (
            out["New Drive"].isna()
            & out["Motor Power"].le(br["max_kw"])
            & (high_speed == bool(br["speed_high"]))
        )
        out.loc[mask, "New Drive"] = br["new"]
        out.loc[mask, "Drive Material"] = _safe_eval(br["material"])

    # 6) Costing model
    smh    = float(rules.get("drive_smh", 60))
    labor  = float(rules.get("labor_rate", 266.5))
    margin = float(rules.get("gross_margin", 0.35))
    out["Drive SMH"] = smh
    out["drive unit rate"] = np.round(
        (out["Drive Material"].fillna(0) + labor * smh) / max(margin, 1e-6), 0
    )

    # 7) Drive target quantity per Contract (count distinct UnitNo with target drive types)
    target_mask = out["drive_type"].isin(["OVF 10","OVF 20","OVF 30","OVF 428","VFCU"])
    qty = (
        out.loc[target_mask]
          .groupby("ContractNo")["UnitNo"]
          .nunique()
          .rename("Drive Qty")
          .reset_index()
    )
    out = out.merge(qty, on="ContractNo", how="left")
    out["Drive Qty"] = out["Drive Qty"].fillna(0)

    # 8) Totals & payment terms
    out["2025 drive total"] = out["drive unit rate"] * out["Drive Qty"]

    pay_cfg   = rules.get("payment", {})
    small_thr = float(pay_cfg.get("small_job_threshold", 50000))
    eng_small = pay_cfg.get("eng_small", "")
    eng_large = pay_cfg.get("eng_large", "")
    zh_small  = pay_cfg.get("zh_small", "")
    zh_large  = pay_cfg.get("zh_large", "")

    out["paymenteng"] = np.where(out["2025 drive total"] <= small_thr, eng_small, eng_large)
    out["paymentchi"] = np.where(out["2025 drive total"] <= small_thr, zh_small,  zh_large)

    # 9) Line text used by letters
    out["Proposed Items"] = np.where(
        target_mask,
        out.apply(lambda r: f"Replacement of Drive from {r['drive_type']} to {r['New Drive']}", axis=1),
        ""
    )

    return out
