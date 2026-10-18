from fastapi import FastAPI

from backend.app.core.config import settings
from backend.app.core.database import init_db

from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.ai import router as ai_router
from backend.app.api.routes.conversations import router as conversations_router
from backend.app.api.routes.webhooks import router as webhooks_router

from backend.app.discovery import init_discovery
from backend.app.discovery.api import router as discovery_router

# Import models so their tables are registered before init_db() runs.
from backend.app.models import messaging as _messaging_models  # noqa: F401


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered B2B outbound sales platform",
    version="0.1.0",
)


@app.on_event("startup")
def startup():

    # Create database tables
    init_db()

    # Discovery engine: opens its own SQLite store and builds the provider list
    init_discovery()


@app.get("/")
def root():

    return {
        "product": "OUTZAAR",
        "description": "AI-powered B2B outbound sales platform",
        "status": "running",
    }


app.include_router(
    health_router,
    prefix="/api",
    tags=["System"],
)


app.include_router(
    ai_router,
    prefix="/api/ai",
    tags=["AI"],
)


app.include_router(
    discovery_router,
    prefix="/api",
    tags=["Discovery"],
)


app.include_router(
    conversations_router,
    prefix="/api",
    tags=["Conversations"],
)


app.include_router(
    webhooks_router,
    prefix="/api",
    tags=["Webhooks"],
)