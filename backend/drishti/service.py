"""Service layer: ingest a real DataFrame end-to-end and persist. No synthetic data."""
import json
import pandas as pd
from .mapping import detect_mapping, apply_mapping, mapping_report
from .validation import clean_and_validate
from .provenance import make_provenance
from .engine import run_engine
from . import db

def ingest_dataframe(raw_df, base_prov, mode="real", user="local", confirmed_mapping=None):
    src_cols = list(raw_df.columns)
    mapping = confirmed_mapping or detect_mapping(src_cols)
    mreport = mapping_report(mapping, src_cols)
    mapped = apply_mapping(raw_df, mapping)
    clean, quality = clean_and_validate(mapped)
    prov = make_provenance(base_prov, clean, user=user)
    quality["mapping"] = mreport
    results = run_engine(clean) if len(clean) else {"portfolio": {}, "queue": [], "risk_cases": [],
                                                    "duplicates": [], "model_runs": {}, "notes": ["No accepted records."]}
    s = db.SessionLocal()
    try:
        imp = db.DataImport(id=prov["import_id"], mode=mode,
                            provenance=json.dumps(prov), quality=json.dumps(quality), mapping=json.dumps(mapping))
        s.add(imp)
        for _, r in clean.iterrows():
            rec = {k: (None if pd.isna(v) else (str(v) if hasattr(v, "isoformat") else v)) for k, v in r.items()}
            s.add(db.Work(import_id=prov["import_id"], work_id=str(r.get("work_id")), record=json.dumps(rec, default=str)))
        s.add(db.AnalysisRun(import_id=prov["import_id"], mode=mode,
                             results=json.dumps(results, default=str), model_runs=json.dumps(results.get("model_runs", {}), default=str)))
        db.set_state(s, "active_import_" + mode, prov["import_id"])
        db.set_state(s, "mode", mode)
        s.commit()
    finally:
        s.close()
    return {"import_id": prov["import_id"], "provenance": prov, "quality": quality,
            "mapping": mapping, "model_runs": results.get("model_runs", {}), "notes": results.get("notes", [])}
