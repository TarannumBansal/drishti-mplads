import os, pandas as pd
from .base import BaseConnector
class CSVConnector(BaseConnector):
    name = "csv"
    def fetch(self, path=None, **kw):
        df = pd.read_csv(path, dtype=str, keep_default_na=True)
        prov = {"source": "Official export (CSV)", "source_type": "csv_import",
                "source_file": os.path.basename(path), "record_count": int(len(df))}
        return df, prov
