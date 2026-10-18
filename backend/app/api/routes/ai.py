from fastapi import APIRouter, HTTPException

from backend.app.services.ollama_service import ollama_service
from backend.app.schemas.ai import AIMessageRequest

router = APIRouter()


@router.post("/chat")
def chat_with_ai(request: AIMessageRequest):

    if not ollama_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama is not running.",
        )

    try:

        response = ollama_service.chat(
            request.message
        )

        return {
            "success": True,
            "response": response,
        }

    except RuntimeError as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )