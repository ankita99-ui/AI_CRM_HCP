import re
from datetime import datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.schemas.interaction import InteractionUpdate
from app.services.interaction_service import InteractionService


class EditInteractionTool:
    """LangGraph tool: update an existing interaction from natural-language instructions."""

    def __init__(self, session: AsyncSession):
        self.service = InteractionService(session)
        self.session = session

    async def _resolve_interaction_id(self, interaction_id: int | None, doctor_name: str | None) -> int | None:
        if interaction_id:
            return interaction_id
        if not doctor_name:
            return None
        stmt = (
            select(Interaction)
            .join(HCP, HCP.id == Interaction.hcp_id)
            .where(HCP.doctor_name.ilike(f'%{doctor_name.replace("Dr.", "").strip()}%'))
            .order_by(desc(Interaction.created_at))
            .limit(1)
        )
        interaction = (await self.session.scalars(stmt)).first()
        return interaction.id if interaction else None

    async def run(
        self,
        instruction: str,
        interaction_id: int | None = None,
        doctor_name: str | None = None,
    ):
        resolved_id = await self._resolve_interaction_id(interaction_id, doctor_name)
        if not resolved_id:
            return None

        lower = instruction.lower()
        payload = InteractionUpdate()
        if 'monday' in lower:
            today = datetime.now().date()
            delta = (0 - today.weekday()) % 7 or 7
            payload.follow_up_date = today + timedelta(days=delta)
        elif 'friday' in lower:
            today = datetime.now().date()
            delta = (4 - today.weekday()) % 7 or 7
            payload.follow_up_date = today + timedelta(days=delta)
        elif 'tomorrow' in lower:
            payload.follow_up_date = datetime.now().date() + timedelta(days=1)

        match = re.search(r'change interaction type to (visit|call|email|conference)', lower)
        if match:
            payload.interaction_type = match.group(1)

        sentiment_match = re.search(r'change sentiment to (positive|neutral|negative)', lower)
        if sentiment_match:
            payload.sentiment = sentiment_match.group(1)

        summary_match = re.search(r'change summary to (.+)$', instruction, re.IGNORECASE)
        if summary_match:
            payload.summary = summary_match.group(1).strip()

        return await self.service.update_interaction(resolved_id, payload)
