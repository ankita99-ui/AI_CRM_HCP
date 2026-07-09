from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.hcp import HCP
from app.models.interaction import Interaction


class NextBestActionTool:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def run(self, doctor_name: str, products_discussed: list[str], summary: str) -> list[str]:
        stmt = (
            select(Interaction)
            .join(HCP, HCP.id == Interaction.hcp_id)
            .where(HCP.doctor_name.ilike(doctor_name))
            .options(selectinload(Interaction.products))
            .order_by(desc(Interaction.created_at))
            .limit(3)
        )
        history = (await self.session.scalars(stmt)).all()

        actions = []
        if any('trial' in interaction.summary.lower() for interaction in history) or 'trial' in summary.lower():
            actions.append('Share the latest clinical trial data pack within 24 hours.')
        if products_discussed:
            actions.append(f'Plan a focused follow-up on {products_discussed[0]} with outcomes and patient profile alignment.')
        actions.append('Evaluate whether the HCP should be invited to the upcoming medical education event or conference.')
        actions.append('Send compliant medical literature and record the response in the next interaction.')
        return actions[:4]
