from app.schemas.email import EmailRequest
from app.services.email_service import EmailService


class GenerateFollowUpEmailTool:
    def __init__(self) -> None:
        self.service = EmailService()

    async def run(self, payload: EmailRequest):
        return await self.service.generate_follow_up(payload)
