from fastapi import APIRouter

from backend.app.core.config import settings
from backend.app.services.ollama_service import ollama_service


router = APIRouter()


@router.get("/health")
def health_check():

    ollama_available = ollama_service.is_available()

    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "ollama": {
            "available": ollama_available,
            "model": settings.OLLAMA_MODEL,
        },
    }


@router.get("/ollama")
def ollama_status():

    available = ollama_service.is_available()
    models = ollama_service.get_models()

    return {
        "available": available,
        "configured_model": settings.OLLAMA_MODEL,
        "installed_models": models,
    }