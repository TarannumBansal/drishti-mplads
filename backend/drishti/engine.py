"""
Drishti production analytics engine — REAL-DATA ONLY.
run_engine(df) takes a cleaned canonical DataFrame (from a real import) and returns
a results dict. It NEVER generates synthetic works. Missing fields are handled with
explicit fallbacks and reduced-confidence flags; metrics are only reported when
actually computed on the given data.
"""
import numpy as np, pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import cross_val_predict, train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error, roc_auc_score, average_precision_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PRIORITY_WEIGHTS = {"cost": 3, "duplicate": 3, "delivery_risk": 2, "concentration": 2}

def _status(s):
    x = str(s).lower()
    if "complet" in x: return "Completed"
    if any(k in x for k in ("stall","abandon","incomplete")): return "Stalled"
    if any(k in x for k in ("ongoing","progress","running")): return "Ongoing"
    return "Unknown"

def run_engine(df, cfg=None):
    cfg = cfg or {}
    df = df.copy().reset_index(drop=True)
    n = len(df)
    notes = []
    if "status" in df: df["_status"] = df["status"].map(_status)
    else: df["_status"] = "Unknown"; notes.append("No status column: delivery-risk & stalled signals limited.")
    has_size = "size" in df and df["size"].notna().sum() >= max(20, 0.5*n)
    if "work_type" not in df: df["work_type"] = "Unknown"; notes.append("No work_type: peer groups weaker.")
    if "district" not in df: df["district"] = "Unknown"; notes.append("No district: peer groups & concentration weaker.")
    if "year" not in df:
        df["year"] = df["sanction_date"].dt.year if "sanction_date" in df else 0

    signals = {i: [] for i in df.index}
    model_runs = {}

    # ---------------- EXPECTED-COST MODEL ----------------
    cost_conf = "full" if has_size else "reduced"
    if not has_size: notes.append("size/quantity unavailable — fair-comparison confidence reduced (fallback: type x district x year).")
    y = np.log(df["sanctioned_amount"].clip(lower=1))
    feats = ["work_type", "district", "year"]
    Xnum = []
    if has_size:
        df["_logsize"] = np.log(df["size"].fillna(df["size"].median()).clip(lower=0.1)); Xnum = ["_logsize"]
    X = df[feats + Xnum]
    pre = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), feats)], remainder="passthrough")
    model = Pipeline([("p", pre), ("l", LinearRegression())])
    ec = {"available": False}
    if n >= 40:
        try:
            k = min(5, max(2, n // 20))
            pred_cv = cross_val_predict(model, X, y, cv=k)   # honest out-of-fold residuals
            resid = y - pred_cv
            z = (resid - resid.mean()) / (resid.std() or 1)
            df["_pred_amt"] = np.exp(pred_cv); df["_z"] = z   # display uses the SAME out-of-fold prediction as z (consistent)
            flag = z >= 2.5
            for i in df.index[flag]:
                r = df.loc[i]
                signals[i].append(dict(kind="cost", label="Cost far above expectation", strength="Strong",
                    headline=f"Costs {r.sanctioned_amount/max(r._pred_amt,1):.1f}x the model-expected value for a comparable work.",
                    compared=f"Expected \u20b9{r._pred_amt:,.0f} (type x district x year{' x size' if has_size else ''}); residual z={r._z:.1f}."
                             + ("" if has_size else " Confidence REDUCED: size/quantity not in source."),
                    rule="Genuinely larger scope than recorded." + ("" if has_size else " Size not captured in data."),
                    verify="Request BOQ / detailed estimate; confirm physical scope."))
            ec = {"available": True, "confidence": cost_conf, "method": f"{k}-fold cross-validated residuals",
                  "r2": round(float(r2_score(y, pred_cv)), 3),
                  "mae_log": round(float(mean_absolute_error(y, pred_cv)), 3),
                  "rmse_log": round(float(mean_squared_error(y, pred_cv) ** 0.5), 3),
                  "n": int(n), "flagged": int(flag.sum())}
        except Exception as e:
            notes.append(f"Expected-cost model skipped: {e}")
    else:
        notes.append(f"Expected-cost model unavailable: only {n} records (need >= 40).")
    model_runs["expected_cost"] = ec

    # ---------------- DELIVERY-RISK MODEL ----------------
    dr = {"available": False}
    fin = df[df["_status"].isin(["Completed", "Stalled"])].copy()
    n_stall = int((fin["_status"] == "Stalled").sum()); n_comp = int((fin["_status"] == "Completed").sum())
    if n_stall >= 30 and n_comp >= 30:
        try:
            fin["_y"] = (fin["_status"] == "Stalled").astype(int)
            # LEAKAGE GUARD: for FINISHED works, expenditure / fund-release figures reflect the
            # OUTCOME (a stalled work under-spends), so any expenditure-derived ratio leaks the
            # label. Use only features known at/near sanction time.
            f_cat = [c for c in ("work_type","implementing_agency") if c in fin]
            f_num = [c for c in ("sanctioned_amount",) if c in fin]  # pre-outcome only; NO expenditure-derived features
            pre2 = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), f_cat)], remainder="passthrough")
            clf = Pipeline([("p", pre2), ("l", LogisticRegression(max_iter=1000))])
            # TEMPORAL split when year present, else stratified holdout
            if fin["year"].nunique() >= 2:
                cut = fin["year"].median()
                tr, te = fin[fin.year <= cut], fin[fin.year > cut]
                if len(te) < 20 or te["_y"].nunique() < 2:
                    tr, te = train_test_split(fin, test_size=0.3, random_state=1, stratify=fin["_y"]); method = "stratified holdout (too few recent years)"
                else: method = "temporal (train older years, test newer)"
            else:
                tr, te = train_test_split(fin, test_size=0.3, random_state=1, stratify=fin["_y"]); method = "stratified holdout"
            clf.fit(tr[f_cat + f_num], tr["_y"])
            proba = clf.predict_proba(te[f_cat + f_num])[:, 1]
            auc = float(roc_auc_score(te["_y"], proba)); prauc = float(average_precision_score(te["_y"], proba))
            k = max(1, int(0.1 * len(te)))
            order = np.argsort(-proba); topk = te["_y"].values[order][:k]
            prec_at_k = float(topk.mean())
            clf.fit(fin[f_cat + f_num], fin["_y"])
            ong = df[df["_status"] == "Ongoing"].copy()
            if len(ong):
                risk = clf.predict_proba(ong[f_cat + f_num])[:, 1]
                df.loc[ong.index, "_risk"] = risk
                for i in ong.index[risk >= 0.5]:
                    signals[i].append(dict(kind="delivery_risk", label="Delivery-risk early warning", strength="Medium",
                        headline=f"Predicted {df.loc[i,'_risk']*100:.0f}% risk of stalling — flagged while ongoing.",
                        compared=f"Logistic model, {method}; test AUC={auc:.2f}. Based on work type, agency and sanctioned amount (pre-outcome features only).",
                        rule="Procedural delay (land, clearances) rather than a problem.",
                        verify="Review progress log; nudge the agency early."))
            dr = {"available": True, "method": method, "auc": round(auc,3), "pr_auc": round(prauc,3),
                  "precision_at_10pct": round(prec_at_k,3), "train_n": int(len(tr)), "test_n": int(len(te)),
                  "labels": {"completed": n_comp, "stalled": n_stall}}
        except Exception as e:
            notes.append(f"Delivery-risk model skipped: {e}")
    else:
        dr = {"available": False, "reason": f"Insufficient labelled history (completed={n_comp}, stalled={n_stall}; need >=30 each). No AUC fabricated."}
        notes.append(dr["reason"])
    model_runs["delivery_risk"] = dr

    # ---------------- DUPLICATES (corroborated) ----------------
    if "district" in df:
        df["_d"] = df["sanction_date"] if "sanction_date" in df else pd.NaT
        text_col = "description" if "description" in df else ("title" if "title" in df else None)
        if text_col:
            for dist, g in df.groupby("district"):
                if len(g) < 2: continue
                try:
                    S = cosine_similarity(TfidfVectorizer(stop_words="english").fit_transform(g[text_col].fillna("")))
                except ValueError: continue
                idx = g.index.tolist()
                for a in range(len(idx)):
                    for b in range(a+1, len(idx)):
                        if S[a,b] < 0.85: continue
                        ra, rb = df.loc[idx[a]], df.loc[idx[b]]
                        same_ag = ("implementing_agency" in df) and (ra.get("implementing_agency")==rb.get("implementing_agency"))
                        amt_ok = abs(ra.sanctioned_amount/max(rb.sanctioned_amount,1)-1) <= 0.10
                        date_ok = (pd.notna(ra._d) and pd.notna(rb._d) and abs((ra._d-rb._d).days) <= 120)
                        if same_ag and amt_ok and date_ok:
                            for ix, pt in ((idx[a], rb), (idx[b], ra)):
                                signals[ix].append(dict(kind="duplicate", label="Corroborated duplicate", strength="Strong",
                                    headline=f"Near-identical to {pt.work_id}, with corroborating attributes.",
                                    compared=f"{S[a,b]:.0%} text match + same agency + ~same amount + within 120 days.",
                                    rule="Genuinely separate works at different sites.",
                                    verify="Check GPS coordinates and the asset register."))

    # ---------------- CONCENTRATION (contextual) ----------------
    if {"district","implementing_agency","work_type"}.issubset(df.columns):
        for (dist, wt), g in df.groupby(["district","work_type"]):
            if len(g) < 8: continue
            pool = df[df.work_type == wt]
            for ag, c in g["implementing_agency"].value_counts().items():
                here = c/len(g); norm = (pool.implementing_agency == ag).mean()
                if here-norm >= 0.30 and c >= 4:
                    for i in g.index[g.implementing_agency == ag]:
                        signals[i].append(dict(kind="concentration", label="Unusual agency concentration", strength="Weak",
                            headline=f"{ag} handles {here:.0%} of {wt} works in {dist} vs {norm:.0%} statewide.",
                            compared="Local share far exceeds this agency's own statewide norm for the work type.",
                            rule="May be the only empanelled agency here.",
                            verify="Check the district empanelment list."))

    # ---------------- PRIORITY + EVIDENCE ----------------
    rows = []
    for i in df.index:
        sg = signals[i]
        if not sg: continue
        kinds = {s["kind"] for s in sg}
        score = sum(PRIORITY_WEIGHTS[k] for k in kinds)
        conf = "High" if len(kinds) >= 2 else ("Medium" if any(s["strength"]=="Strong" for s in sg) else "Low")
        r = df.loc[i]
        top = "cost" if "cost" in kinds else "duplicate" if "duplicate" in kinds else "delivery_risk" if "delivery_risk" in kinds else "concentration"
        rows.append(dict(id=str(r.work_id), title=str(r.get("title") or r.get("description") or r.work_id),
            district=str(r.get("district","")), year=(int(r.year) if pd.notna(r.get("year")) else None),
            work_type=str(r.get("work_type","")), amount=float(r.sanctioned_amount), agency=str(r.get("implementing_agency","")),
            status=r._status, priority=int(score), confidence=conf, signals=len(kinds), top=top,
            expected=(float(r._pred_amt) if "cost" in kinds and "_pred_amt" in df else None),
            z=(round(float(r._z),1) if "cost" in kinds and "_z" in df else None),
            risk=(round(float(r._risk),2) if "_risk" in df and pd.notna(r.get("_risk")) else None),
            evidence=sg))
    queue = sorted(rows, key=lambda x: (x["priority"], x["z"] or 0), reverse=True)

    total = n
    portfolio = dict(total=total,
        completed=int((df._status=="Completed").sum()), ongoing=int((df._status=="Ongoing").sum()),
        stalled=int((df._status=="Stalled").sum()), under_review=len(queue),
        cost_anomaly=model_runs["expected_cost"].get("flagged",0),
        delivery_high=int(sum(1 for r in queue if any(e["kind"]=="delivery_risk" for e in r["evidence"]))),
        duplicate=int(sum(1 for r in queue if any(e["kind"]=="duplicate" for e in r["evidence"]))),
        priority_dist=dict(high=sum(1 for r in queue if r["priority"]>=3),
                           med=sum(1 for r in queue if 2<=r["priority"]<3),
                           low=sum(1 for r in queue if 0<r["priority"]<2)),
        top_districts=[dict(name=k, value=int(v)) for k,v in
                       pd.Series([r["district"] for r in queue if r["priority"]>=3]).value_counts().head(6).items()])
    def _has(r, k): return any(e["kind"] == k for e in r["evidence"])
    dups = [r for r in queue if _has(r, "duplicate")]
    risks = sorted([r for r in queue if r["risk"] is not None], key=lambda x: -x["risk"])
    return dict(portfolio=portfolio, queue=queue[:200], risk_cases=risks[:50],
                duplicates=dups[:50], model_runs=model_runs, notes=notes)
