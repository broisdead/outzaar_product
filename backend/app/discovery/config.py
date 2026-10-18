"""Discovery settings. Read from environment (and a local .env if present).

Kept independent from backend.app.core.config so the existing settings object
does not need to change. Only keys you actually set enable a provider.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def _list(name: str, default: list[str]) -> list[str]:
    v = os.environ.get(name)
    return default if v is None else [x.strip() for x in v.split(",") if x.strip()]


# Directory / association sites used for site-scoped search queries.
DEFAULT_DIRECTORY_SITES = [
    "f6s.com", "beststartup.asia", "getlatka.com", "wellfound.com",
    "tracxn.com", "clutch.co", "indiamart.com", "tradeindia.com",
    "exportersindia.com", "justdial.com",
]
DEFAULT_ASSOCIATION_SITES = [
    "nasscom.in", "fieo.org", "cii.in", "ficci.in", "eepcindia.org",
]


@dataclass
class DiscoverySettings:
    db_path: str = "outzaar_discovery.db"

    # Ollama (ICP interpretation / query expansion ONLY)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ollama_timeout: int = 90

    # Provider credentials (a provider is enabled only when its key is set)
    serpapi_key: str = ""
    google_cse_key: str = ""
    google_cse_cx: str = ""
    brave_key: str = ""
    apollo_key: str = ""
    enable_duckduckgo: bool = True          # keyless, best-effort, may be blocked
    directories_config: str = ""            # path to JSON, see directories.json.example

    directory_sites: list[str] = field(default_factory=lambda: list(DEFAULT_DIRECTORY_SITES))
    association_sites: list[str] = field(default_factory=lambda: list(DEFAULT_ASSOCIATION_SITES))

    # Run defaults
    max_queries_per_provider: int = 200
    max_pages: int = 5
    workers_per_provider: int = 3
    http_timeout: int = 20
    http_retries: int = 3
    provider_failure_threshold: int = 8     # consecutive failed queries before a provider is switched off for the run

    @classmethod
    def from_env(cls) -> "DiscoverySettings":
        _load_dotenv()
        e = os.environ.get
        return cls(
            db_path=e("DISCOVERY_DB_PATH", "outzaar_discovery.db"),
            ollama_url=e("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=e("OLLAMA_MODEL", "llama3.1"),
            ollama_timeout=int(e("OLLAMA_TIMEOUT", "90")),
            serpapi_key=e("SERPAPI_API_KEY", ""),
            google_cse_key=e("GOOGLE_CSE_API_KEY", ""),
            google_cse_cx=e("GOOGLE_CSE_CX", ""),
            brave_key=e("BRAVE_API_KEY", ""),
            apollo_key=e("APOLLO_API_KEY", ""),
            enable_duckduckgo=_bool("DISCOVERY_ENABLE_DDG", True),
            directories_config=e("DISCOVERY_DIRECTORIES_CONFIG", ""),
            directory_sites=_list("DISCOVERY_DIRECTORY_SITES", list(DEFAULT_DIRECTORY_SITES)),
            association_sites=_list("DISCOVERY_ASSOCIATION_SITES", list(DEFAULT_ASSOCIATION_SITES)),
            max_queries_per_provider=int(e("DISCOVERY_MAX_QUERIES", "200")),
            max_pages=int(e("DISCOVERY_MAX_PAGES", "5")),
            workers_per_provider=int(e("DISCOVERY_WORKERS", "3")),
        )
