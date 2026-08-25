"""Validate a mapped DataFrame and produce a Data Quality report.
Never silently discards: rejected rows are counted and reasons recorded."""
import numpy as np, pandas as pd

def _money(x):
    if pd.isna(x): return np.nan
    s = str(x).replace(",", "").replace("\u20b9", "").strip()
    s = "".join(ch for ch in s if (ch.isdigit() or ch == "." or ch == "-"))
    try: return float(s)
    except Exception: return np.nan

def _to_dates(s):
    """Explicit date handling. Parse ISO-8601 first (no dayfirst ambiguity or warning),
    then fall back to day-first parsing for any remaining non-ISO values (e.g. DD/MM/YYYY),
    which is the common Indian government format. Unparseable values become NaT."""
    s = s.astype("string")
    out = pd.to_datetime(s, errors="coerce", format="ISO8601")
    remaining = out.isna() & s.notna()
    if remaining.any():
        out.loc[remaining] = pd.to_datetime(s[remaining], errors="coerce", dayfirst=True, format="mixed")
    return out

def clean_and_validate(df):
    df = df.copy()
    report = {"received": int(len(df))}
    # parse money
    for col in ("sanctioned_amount","expenditure","fund_release"):
        if col in df: df[col] = df[col].map(_money)
    # parse dates
    for col in ("sanction_date","start_date","expected_completion_date","actual_completion_date"):
        if col in df: df[col] = _to_dates(df[col])
    # numeric
    for col in ("year","size","quantity","latitude","longitude"):
        if col in df: df[col] = pd.to_numeric(df[col], errors="coerce")
    # normalise text categories
    for col in ("district","state","implementing_agency","work_type","status"):
        if col in df: df[col] = df[col].astype(str).str.strip().replace({"nan": np.nan})

    reasons = pd.Series([""] * len(df), index=df.index)
    def flag(mask, why):
        reasons.loc[mask & (reasons == "")] = why
    if "work_id" not in df:
        report["fatal"] = "no work_id column mapped"; report["accepted"] = 0; report["rejected"] = len(df)
        return df.iloc[0:0], report
    flag(df["work_id"].isna() | (df["work_id"].astype(str).str.strip() == ""), "missing work_id")
    dup_ids = df["work_id"].duplicated(keep="first")
    flag(dup_ids, "duplicate work_id")
    if "sanctioned_amount" in df:
        flag(df["sanctioned_amount"].isna(), "missing/invalid sanctioned_amount")
        flag(df["sanctioned_amount"] <= 0, "non-positive sanctioned_amount")
    if "expenditure" in df:
        flag(df["expenditure"] < 0, "negative expenditure")
    now = pd.Timestamp.now().normalize()
    if "sanction_date" in df:
        flag((df["sanction_date"] > now).fillna(False), "sanction_date in the future")
    if {"sanction_date","actual_completion_date"}.issubset(df.columns):
        flag((df["actual_completion_date"] < df["sanction_date"]).fillna(False), "completion before sanction")
        flag((df["actual_completion_date"] > now).fillna(False), "completion date in the future")
    if {"sanction_date","expected_completion_date"}.issubset(df.columns):
        flag((df["expected_completion_date"] < df["sanction_date"]).fillna(False), "expected completion before sanction")
    if {"latitude","longitude"}.issubset(df.columns):
        bad = (df["latitude"].abs() > 90) | (df["longitude"].abs() > 180)
        flag(bad.fillna(False), "malformed coordinates")

    rejected = reasons != ""
    accepted = df[~rejected].copy()
    overspend = 0
    if {"expenditure","sanctioned_amount"}.issubset(accepted.columns):
        overspend = int((accepted["expenditure"] > accepted["sanctioned_amount"]).fillna(False).sum())
    report.update({
        "expenditure_over_sanctioned": overspend,
        "accepted": int((~rejected).sum()),
        "rejected": int(rejected.sum()),
        "reject_reasons": reasons[rejected].value_counts().to_dict(),
        "duplicate_ids": int(dup_ids.sum()),
        "missing_fields": {c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()},
        "date_range": _date_range(accepted),
        "has_size": bool("size" in accepted.columns and accepted["size"].notna().any()),
        "has_coords": bool({"latitude","longitude"}.issubset(accepted.columns) and accepted["latitude"].notna().any()),
        "has_status_labels": _label_counts(accepted),
    })
    return accepted, report

def _date_range(df):
    if "sanction_date" in df and df["sanction_date"].notna().any():
        return {"from": str(df["sanction_date"].min().date()), "to": str(df["sanction_date"].max().date())}
    if "year" in df and df["year"].notna().any():
        return {"from": int(df["year"].min()), "to": int(df["year"].max())}
    return None

def _label_counts(df):
    if "status" not in df: return {}
    s = df["status"].astype(str).str.lower()
    completed = int(s.str.contains("complet").sum())
    stalled = int(s.str.contains("stall|abandon|incomplete|delayed").sum())
    ongoing = int(s.str.contains("ongoing|progress|in-progress|running").sum())
    return {"completed": completed, "stalled": stalled, "ongoing": ongoing}
