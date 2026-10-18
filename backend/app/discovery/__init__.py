"""OUTZAAR Discovery Engine (company discovery only)."""
from __future__ import annotations

from .config import DiscoverySettings
from .engine import DiscoveryEngine
from .providers import build_providers
from .store import Store

_engine: DiscoveryEngine | None = None


def get_engine() -> DiscoveryEngine:
    """Lazily-built singleton. Called from FastAPI startup and by the routes."""
    global _engine
    if _engine is None:
        settings = DiscoverySettings.from_env()
        _engine = DiscoveryEngine(Store(settings.db_path), settings, build_providers(settings))
    return _engine


def init_discovery() -> None:
    get_engine()
