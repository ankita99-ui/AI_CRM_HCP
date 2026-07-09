from app.schemas.email import EmailRequest, EmailResponse
from app.services.llm_service import LLMService


class EmailService:
    def __init__(self) -> None:
        self.llm_service = LLMService()

    async def generate_follow_up(self, payload: EmailRequest) -> EmailResponse:
        email = await self.llm_service.generate_email(payload.model_dump())
        return EmailResponse(**email)
