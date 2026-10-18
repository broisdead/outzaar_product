from pydantic import BaseModel


class AIMessageRequest(BaseModel):
    message: str