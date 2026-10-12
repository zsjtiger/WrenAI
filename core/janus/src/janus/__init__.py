"""Janus — semantic SQL layer for 20+ data sources."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from janus.engine import JanusEngine
from janus.model.data_source import DataSource
from janus.model.error import JanusError

try:
    __version__ = _pkg_version("janusai")
except PackageNotFoundError:  # editable install without metadata, dev checkouts
    __version__ = "0.0.0+unknown"

__all__ = ["JanusEngine", "DataSource", "JanusError", "__version__"]
