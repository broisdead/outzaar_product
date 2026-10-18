from __future__ import annotations

from ..config import DiscoverySettings
from .apollo import ApolloProvider
from .base import Page, Provider, ProviderQuery, RawItem
from .directories import load_directory_providers
from .search import (BraveProvider, DuckDuckGoProvider, GoogleCseProvider,
                     SerpApiMapsProvider, SerpApiProvider)


def build_providers(s: DiscoverySettings) -> list[Provider]:
    sites = dict(directory_sites=s.directory_sites, association_sites=s.association_sites)
    providers: list[Provider] = [
        SerpApiProvider(s.serpapi_key, **sites),
        SerpApiMapsProvider(s.serpapi_key),
        GoogleCseProvider(s.google_cse_key, s.google_cse_cx, **sites),
        BraveProvider(s.brave_key, **sites),
        ApolloProvider(s.apollo_key),
    ]
    if s.enable_duckduckgo:
        providers.append(DuckDuckGoProvider(**sites))
    try:
        providers += load_directory_providers(s.directories_config)
    except Exception as e:                     # bad config must not break startup
        print(f"[discovery] directories config ignored: {e}")
    return [p for p in providers if p.enabled()]
