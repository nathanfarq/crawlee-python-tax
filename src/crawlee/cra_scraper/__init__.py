"""CRA (Canada Revenue Agency) scraping module for tax data collection."""

from ._config import CRAConfig
from ._data_validator import CRADataValidator
from ._rate_limiter import CRARateLimiter

# Optional imports that depend on extras
try:
    from ._cra_crawler import CRACrawler

    _crawler_available = True
except ImportError:
    CRACrawler = None  # type: ignore
    _crawler_available = False

try:
    from ._vectorizer import CRAVectorizer

    _vectorizer_available = True
except ImportError:
    CRAVectorizer = None  # type: ignore
    _vectorizer_available = False

try:
    from ._qdrant_client import CRAQdrantClient

    _qdrant_available = True
except ImportError:
    CRAQdrantClient = None  # type: ignore
    _qdrant_available = False

__all__ = [
    'CRAConfig',
    'CRADataValidator',
    'CRARateLimiter',
]

if _crawler_available:
    __all__.append('CRACrawler')

if _vectorizer_available:
    __all__.append('CRAVectorizer')

if _qdrant_available:
    __all__.append('CRAQdrantClient')
