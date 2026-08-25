from .csv_import import CSVConnector
from .json_import import JSONConnector
from .datagovin import DataGovInConnector
from .esakshi import ESakshiConnector
REGISTRY = {"csv": CSVConnector, "json": JSONConnector, "datagovin": DataGovInConnector, "esakshi": ESakshiConnector}
