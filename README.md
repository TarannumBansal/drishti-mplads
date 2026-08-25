# Drishti — Real-Data MPLADS Oversight & Early-Warning System (SIH26102)

Government decision-support over **real** MPLADS data. It ranks works for human
review with explainable evidence and forecasts delivery risk. **Real Data Mode is
the default; there is no synthetic fallback in real mode** — with nothing connected,
the app shows an empty state and an import screen, not fake numbers.

## What is real vs what needs access
| Capability | Status |
|---|---|
| CSV / JSON official-export import (auto column-mapping, validation, DQ report) | **Implemented & tested** |
| Real analytics engine (expected-cost, delivery-risk, duplicates, concentration) on imported data | **Implemented & tested** |
| PostgreSQL/SQLite persistence, provenance, officer-review history | **Implemented & tested** |
| REST API (FastAPI) + API-driven React UI (empty/loading/error states) | **Implemented** |
| **data.gov.in** Open Data API connector | **Implemented** — needs a free `DATAGOVIN_API_KEY` + a MPLADS resource id |
| **Live e-SAKSHI API** pull | **NOT available** — no public e-SAKSHI API was verifiable; use official export/import (the connector says so honestly and never fakes an endpoint) |
| Real accuracy numbers | **Pending real data** — all model metrics are computed on whatever you import; on the shipped test fixture they are honest but weak |

## Architecture
`React UI  →  FastAPI  →  service  →  connectors → mapping → validation → engine → DB`
The frontend holds no business logic; it renders whatever the API returns.

## Quick start (SQLite, zero setup)
```
cd backend
pip install -r requirements.txt
uvicorn app:app --reload            # API at http://localhost:8000  (creates drishti.db)
cd ../frontend
npm install && npm run dev          # UI at http://localhost:5173
```
Open the UI → **Data Sources** → import an official export (or the test fixture
`backend/tests/fixtures/esakshi_sample.csv`). The dashboard then populates from real records.

## Production (PostgreSQL via Docker)
```
cp .env.example .env         # set DATAGOVIN_API_KEY if using the API connector
docker compose up --build    # db + api (8000) + web (8080)
```

## Connecting real MPLADS data
1. **Official export (guaranteed):** download a work-level export from e-SAKSHI, import via UI or
   `POST /imports/file`. Columns are auto-mapped; a data-quality report is returned.
2. **data.gov.in API (real):** get a free key at data.gov.in, find a MPLADS resource id, then
   `POST /imports/datagovin {"resource_id": "...", "api_key": "..."}`.
3. **e-SAKSHI API:** not verified/public. If MoSPI documents one, configure
   `ESAKSHI_API_BASE`/`ESAKSHI_API_TOKEN` and implement `connectors/esakshi.py::fetch`.

## Machine-learning honesty
- **Expected-cost:** regression of log(cost) on type × district × year × size; anomaly = cross-validated
  standardised residual (z ≥ 2.5). If size/quantity is absent, confidence is **reduced** and flagged.
  Reported R² is out-of-fold fit quality — **not** detection accuracy.
- **Delivery-risk:** logistic model on pre-outcome features only (leakage-guarded), trained on
  completed-vs-stalled history, temporal split when possible. If labelled history is insufficient
  (**< 30 each**), the model is **unavailable** and **no AUC is fabricated**.
- **Duplicates:** require corroboration (text + agency + amount + dates), not text alone.
- **Concentration:** an agency's local share vs its own statewide norm.
- Output is **investigation priority**, never a fraud verdict; a human decides and the decision is stored.

## Acceptance-criteria checklist
- [x] No hardcoded analysis data in real mode — engine runs on imported DataFrame (`tests/test_pipeline.py`)
- [x] Import a CSV/JSON → auto-map → validate → data-quality report (`/imports/file`, `validation.py`)
- [x] Engine computes signals from real records; flagged IDs ⊆ source IDs (test asserts this)
- [x] Delivery-risk uses real labels *when sufficient*, else declines honestly (guard tested)
- [x] PostgreSQL/SQLite persistence + provenance + officer-review history (`db.py`, `/reviews`)
- [x] Frontend calls the API; empty/loading/error states; no embedded data (`DrishtiApp.jsx`)
- [x] e-SAKSHI reality documented honestly; data.gov.in connector real (`connectors/`)
- [ ] Real e-SAKSHI numbers — requires you to import an actual export (path is ready)

## Tests
```
cd backend && python -m pytest tests/ -q
```

## Known limitations
Live e-SAKSHI pull unavailable; RBAC is a design (role selector is a view filter, not enforced auth);
map view needs coordinates in the source; date parsing assumes ISO/`dayfirst` and may need per-export
configuration; model quality depends entirely on the real data you connect.
