from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interaction import ActivityLog, Attachment, Interaction, InteractionProduct
from app.schemas.interaction import ExtractedInteraction, InteractionCreate, InteractionRead, InteractionUpdate
from app.services.hcp_service import HCPService


class InteractionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.hcp_service = HCPService(session)

    async def list_interactions(self) -> list[InteractionRead]:
        stmt = (
            select(Interaction)
            .options(selectinload(Interaction.hcp), selectinload(Interaction.attachments), selectinload(Interaction.products))
            .order_by(desc(Interaction.created_at))
            .limit(50)
        )
        interactions = (await self.session.scalars(stmt)).all()
        return [self._to_schema(item) for item in interactions]

    async def create_interaction(self, payload: InteractionCreate | ExtractedInteraction, user_id: int = 1) -> InteractionRead:
        hcp = await self.hcp_service.get_or_create_hcp(
            payload.doctor_name,
            getattr(payload, 'hospital', None),
        )
        interaction = Interaction(
            hcp_id=hcp.id,
            user_id=user_id,
            interaction_type=payload.interaction_type,
            discussion_notes=payload.discussion_notes,
            summary=payload.summary or payload.discussion_notes,
            sentiment=payload.sentiment,
            follow_up_date=payload.follow_up_date,
            status=getattr(payload, 'status', 'logged') or 'logged',
        )
        self.session.add(interaction)
        await self.session.flush()

        for product in payload.products_discussed:
            self.session.add(InteractionProduct(interaction_id=interaction.id, product_name=product))

        attachments = getattr(payload, 'attachments', []) or []
        for attachment in attachments:
            self.session.add(
                Attachment(
                    interaction_id=interaction.id,
                    file_name=attachment.file_name,
                    file_url=attachment.file_url,
                )
            )

        self.session.add(
            ActivityLog(
                interaction_id=interaction.id,
                user_id=user_id,
                action='interaction_created',
                details=f'Interaction logged for {payload.doctor_name}',
            )
        )
        await self.session.commit()
        await self.session.refresh(interaction)
        return await self.get_interaction(interaction.id)

    async def update_interaction(self, interaction_id: int, payload: InteractionUpdate, user_id: int = 1) -> InteractionRead | None:
        interaction = await self.session.get(Interaction, interaction_id)
        if not interaction:
            return None

        if payload.doctor_name:
            hcp = await self.hcp_service.get_or_create_hcp(
                payload.doctor_name,
                getattr(payload, 'hospital', None),
            )
            interaction.hcp_id = hcp.id

        for field in ['interaction_type', 'discussion_notes', 'summary', 'sentiment', 'follow_up_date', 'status']:
            value = getattr(payload, field)
            if value is not None:
                setattr(interaction, field, value)

        if payload.products_discussed is not None:
            await self.session.execute(InteractionProduct.__table__.delete().where(InteractionProduct.interaction_id == interaction.id))
            for product in payload.products_discussed:
                self.session.add(InteractionProduct(interaction_id=interaction.id, product_name=product))

        if payload.attachments is not None:
            await self.session.execute(Attachment.__table__.delete().where(Attachment.interaction_id == interaction.id))
            for attachment in payload.attachments:
                self.session.add(Attachment(interaction_id=interaction.id, file_name=attachment.file_name, file_url=attachment.file_url))

        self.session.add(
            ActivityLog(
                interaction_id=interaction.id,
                user_id=user_id,
                action='interaction_updated',
                details='Interaction updated via AI or structured form',
            )
        )
        await self.session.commit()
        return await self.get_interaction(interaction.id)

    async def get_interaction(self, interaction_id: int) -> InteractionRead:
        stmt = (
            select(Interaction)
            .where(Interaction.id == interaction_id)
            .options(selectinload(Interaction.hcp), selectinload(Interaction.attachments), selectinload(Interaction.products))
        )
        interaction = (await self.session.scalars(stmt)).one()
        return self._to_schema(interaction)

    def _to_schema(self, interaction: Interaction) -> InteractionRead:
        return InteractionRead(
            id=interaction.id,
            hcp_id=interaction.hcp_id,
            doctor_name=interaction.hcp.doctor_name if interaction.hcp else '',
            interaction_type=interaction.interaction_type,
            discussion_notes=interaction.discussion_notes,
            summary=interaction.summary,
            products_discussed=[product.product_name for product in interaction.products],
            follow_up_date=interaction.follow_up_date,
            sentiment=interaction.sentiment,
            status=interaction.status,
            created_at=interaction.created_at,
            updated_at=interaction.updated_at,
            attachments=[{'file_name': item.file_name, 'file_url': item.file_url} for item in interaction.attachments],
        )
