"""
REAL connector for the Government of India Open Data API (data.gov.in / NIC).
Verified endpoint shape (Aug 2026):
    https://api.data.gov.in/resource/{resource_id}?api-key=KEY&format=json&offset=&limit=
Requires a free API key from data.gov.in, supplied via env DATAGOVIN_API_KEY.
This is a genuine API path; it does NOT bypass any auth. If no key/resource is
configured it raises — it never returns fabricated data.
"""
import os, requests, pandas as pd
from .base import BaseConnector
class DataGovInConnector(BaseConnector):
    name = "datagovin"
    BASE = "https://api.data.gov.in/resource"
    def fetch(self, resource_id=None, api_key=None, max_records=20000, filters=None, **kw):
        api_key = api_key or os.environ.get("DATAGOVIN_API_KEY")
        if not api_key: raise RuntimeError("DATAGOVIN_API_KEY not set. Get a free key at data.gov.in.")
        if not resource_id: raise RuntimeError("resource_id required (the MPLADS dataset UUID from data.gov.in).")
        rows, offset, limit = [], 0, 100
        while offset < max_records:
            params = {"api-key": api_key, "format": "json", "offset": offset, "limit": limit}
            for k, v in (filters or {}).items(): params[f"filters[{k}]"] = v
            r = requests.get(f"{self.BASE}/{resource_id}", params=params, timeout=30)
            r.raise_for_status()
            recs = r.json().get("records", [])
            if not recs: break
            rows += recs; offset += limit
        df = pd.DataFrame(rows)
        prov = {"source": "data.gov.in Open Data API (NIC)", "source_type": "datagovin_api",
                "source_url": f"{self.BASE}/{resource_id}", "resource_id": resource_id, "record_count": int(len(df))}
        return df, prov
