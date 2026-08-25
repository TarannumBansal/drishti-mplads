from abc import ABC, abstractmethod
class BaseConnector(ABC):
    """A connector returns a raw pandas DataFrame + provenance dict. It never fabricates rows."""
    name = "base"
    @abstractmethod
    def fetch(self, **kwargs): ...   # -> (df, provenance)
