from fastapi import APIRouter

from app.schemas.email import EmailRequest, EmailResponse
from app.tools.generate_followup_email_tool import GenerateFollowUpEmailTool

router = APIRouter(tags=['email'])


@router.post('/api/email', response_model=EmailResponse)
async def generate_email(payload: EmailRequest) -> EmailResponse:
    return await GenerateFollowUpEmailTool().run(payload)
