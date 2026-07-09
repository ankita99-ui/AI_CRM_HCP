from typing import TypedDict

from app.schemas.interaction import ExtractedInteraction


class InteractionGraphState(TypedDict, total=False):
    doctor: str
    interaction: dict
    summary: str
    products: list[str]
    follow_up: str | None
    status: str
    conversation: str
    latest_user_message: str
    content: str
    validation_errors: list[str]
    intent: str
    extracted: ExtractedInteraction
    save: bool
    save_result: dict | None
    next_best_action: list[str]
    response_message: str
    hcp_results: list[dict]
    email_draft: dict | None
    interaction_id: int | None
    tools_used: list[str]
