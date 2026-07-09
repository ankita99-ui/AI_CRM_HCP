from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.interaction import ExtractedInteraction
from app.services.conversation_assistant import ConversationAssistantService


class LogInteractionTool:
    """LangGraph tool: extract, summarize, and optionally persist HCP interactions."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.assistant = ConversationAssistantService(session)

    async def run(self, conversation: str, save: bool = False) -> tuple[ExtractedInteraction, object | None]:
        extracted = await self.assistant._extract_from_conversation(conversation)
        self.assistant._apply_defaults(extracted)
        save_result = None
        if save:
            save_result = await self.assistant._save_interaction(extracted)
        return extracted, save_result
