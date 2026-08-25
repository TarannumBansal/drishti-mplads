import os, pandas as pd
from .base import BaseConnector
class JSONConnector(BaseConnector):
    name = "json"
    def fetch(self, path=None, records_key=None, **kw):
        import json
        obj = json.load(open(path))
        if records_key: obj = obj[records_key]
        df = pd.json_normalize(obj)
        prov = {"source": "Official export (JSON)", "source_type": "json_import",
                "source_file": os.path.basename(path), "record_count": int(len(df))}
        return df, prov
