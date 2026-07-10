from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.interaction import ExtractedInteraction, InteractionRead


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    content: str = Field(min_length=1)
    history: list[ChatHistoryMessage] = Field(default_factory=list)
    save: bool = False
    draft: Optional[ExtractedInteraction] = None
    interaction_id: Optional[int] = None


class ChatResponse(BaseModel):
    message: str
    extracted: ExtractedInteraction
    next_best_action: list[str]
    save_result: InteractionRead | None = None
