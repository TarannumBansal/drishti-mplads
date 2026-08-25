"""Drishti FastAPI — REAL DATA MODE is the default. No synthetic fallback in real mode."""
import os, json, tempfile
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from drishti import db
from drishti.service import ingest_dataframe
from drishti.connectors import REGISTRY

app = FastAPI(title="Drishti API", version="1.0.0")
app.add_middleware(CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def _startup(): db.init_db()

def _active(mode):
    s = db.SessionLocal()
    try:
        imp_id = db.get_state(s, "active_import_" + mode)
        if not imp_id: return None, None
        run = s.query(db.AnalysisRun).filter_by(import_id=imp_id).order_by(db.AnalysisRun.id.desc()).first()
        imp = s.get(db.DataImport, imp_id)
        return (json.loads(run.results) if run else None), (json.loads(imp.provenance) if imp else None)
    finally: s.close()

def _mode():
    s = db.SessionLocal()
    try: return db.get_state(s, "mode", "real")
    finally: s.close()

EMPTY = {"connected": False, "message": "NO REAL DATA CONNECTED. Import an official e-SAKSHI export or configure the data.gov.in connector to begin analysis."}

@app.get("/mode")
def mode():
    m = _mode(); res, prov = _active(m)
    return {"mode": m, "connected": res is not None, "provenance": prov}

@app.post("/mode/{m}")
def set_mode(m: str):
    if m not in ("real", "demo"): raise HTTPException(400, "mode must be real|demo")
    s = db.SessionLocal()
    try: db.set_state(s, "mode", m); s.commit()
    finally: s.close()
    return {"mode": m}

@app.get("/portfolio/summary")
def portfolio():
    res, prov = _active(_mode())
    if not res: return EMPTY
    return {"connected": True, **res["portfolio"], "provenance": prov,
            "model_runs": res.get("model_runs", {}), "notes": res.get("notes", [])}

@app.get("/queue")
def queue():
    res, _ = _active(_mode())
    if not res: return EMPTY
    return {"connected": True, "works": res["queue"]}

@app.get("/works/{wid}")
def work(wid: str):
    res, _ = _active(_mode())
    if not res: raise HTTPException(404, "no data connected")
    for c in res["queue"]:
        if c["id"] == wid: return c
    # fall back to raw record from DB
    s = db.SessionLocal()
    try:
        w = s.query(db.Work).filter_by(work_id=wid).first()
        if not w: raise HTTPException(404, "work not found")
        return {"id": wid, "record": json.loads(w.record), "evidence": [], "priority": 0}
    finally: s.close()

@app.get("/works/{wid}/evidence")
def evidence(wid: str):
    c = work(wid); return {"id": wid, "evidence": c.get("evidence", [])}

@app.get("/risk")
def risk():
    res, _ = _active(_mode());  return EMPTY if not res else {"connected": True, "works": res["risk_cases"]}

@app.get("/duplicates")
def duplicates():
    res, _ = _active(_mode());  return EMPTY if not res else {"connected": True, "pairs": res["duplicates"]}

@app.get("/model-runs")
def model_runs():
    res, _ = _active(_mode());  return EMPTY if not res else {"connected": True, **res.get("model_runs", {})}

@app.get("/data-quality")
def data_quality():
    m = _mode(); s = db.SessionLocal()
    try:
        imp_id = db.get_state(s, "active_import_" + m)
        if not imp_id: return EMPTY
        imp = s.get(db.DataImport, imp_id)
        return {"connected": True, "quality": json.loads(imp.quality), "provenance": json.loads(imp.provenance)}
    finally: s.close()

@app.get("/data-source")
def data_source():
    m = _mode(); res, prov = _active(m)
    return {"mode": m, "connected": res is not None, "provenance": prov,
            "api_status": {"datagovin": "available (needs DATAGOVIN_API_KEY + resource id)",
                           "esakshi": "live API NOT verified — use official export/import"}}

# ---- import endpoints ----
@app.post("/imports/file")
async def import_file(file: UploadFile = File(...), fmt: str = Form("csv"), mode: str = Form("real")):
    suffix = ".csv" if fmt == "csv" else ".json"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(await file.read()); tmp.close()
    conn = REGISTRY["csv" if fmt == "csv" else "json"]()
    raw, base = conn.fetch(path=tmp.name); base["source_file"] = file.filename
    return ingest_dataframe(raw, base, mode=mode)

class DataGovIn(BaseModel):
    resource_id: str
    api_key: Optional[str] = None
    max_records: int = 20000

@app.post("/imports/datagovin")
def import_datagovin(cfg: DataGovIn):
    try:
        raw, base = REGISTRY["datagovin"]().fetch(resource_id=cfg.resource_id, api_key=cfg.api_key, max_records=cfg.max_records)
    except Exception as e:
        raise HTTPException(400, str(e))
    if len(raw) == 0: raise HTTPException(400, "API returned no records.")
    return ingest_dataframe(raw, base, mode="real")

# ---- reviews (persisted) ----
class ReviewIn(BaseModel):
    work_id: str; action: str; note: Optional[str] = ""; role: Optional[str] = "District Authority"; signals_snapshot: Optional[list] = []

@app.post("/reviews")
def add_review(r: ReviewIn):
    s = db.SessionLocal()
    try:
        m = db.get_state(s, "mode", "real"); imp = db.get_state(s, "active_import_" + m, "")
        s.add(db.Review(work_id=r.work_id, import_id=imp, action=r.action, note=r.note or "",
                        role=r.role, signals_snapshot=json.dumps(r.signals_snapshot)))
        s.commit()
        hist = [dict(action=x.action, note=x.note, role=x.role, at=x.created_at.isoformat())
                for x in s.query(db.Review).filter_by(work_id=r.work_id).order_by(db.Review.id).all()]
        return {"ok": True, "work_id": r.work_id, "history": hist}
    finally: s.close()

@app.get("/reviews/{wid}")
def review_history(wid: str):
    s = db.SessionLocal()
    try:
        hist = [dict(action=x.action, note=x.note, role=x.role, at=x.created_at.isoformat())
                for x in s.query(db.Review).filter_by(work_id=wid).order_by(db.Review.id).all()]
        return {"work_id": wid, "history": hist}
    finally: s.close()
