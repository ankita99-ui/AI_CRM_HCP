from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hcp import HCP
from app.models.interaction import Interaction, InteractionProduct
from app.schemas.hcp import HCPRead


class HCPService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(self, query: str) -> list[HCPRead]:
        stmt = select(HCP)
        if query:
            like_query = f'%{query.lower()}%'
            stmt = stmt.where(
                or_(
                    func.lower(HCP.doctor_name).like(like_query),
                    func.lower(HCP.hospital).like(like_query),
                    func.lower(HCP.speciality).like(like_query),
                    func.lower(func.coalesce(HCP.city, '')).like(like_query),
                )
            )
        stmt = stmt.order_by(HCP.updated_at.desc()).limit(10)
        hcps = (await self.session.scalars(stmt)).all()
        return [await self._map_hcp(hcp) for hcp in hcps]

    async def get_by_id(self, hcp_id: int) -> HCPRead | None:
        hcp = await self.session.get(HCP, hcp_id)
        if not hcp:
            return None
        return await self._map_hcp(hcp)

    async def get_or_create_hcp(self, doctor_name: str, hospital: str | None = None) -> HCP:
        stmt = select(HCP).where(func.lower(HCP.doctor_name) == doctor_name.lower())
        hcp = (await self.session.scalars(stmt)).first()
        if hcp:
            if hospital and hcp.hospital in {'Independent Practice', ''}:
                hcp.hospital = hospital
            return hcp

        hcp = HCP(
            doctor_name=doctor_name,
            hospital=hospital or 'Independent Practice',
            speciality='General Medicine',
        )
        self.session.add(hcp)
        await self.session.flush()
        return hcp

    async def _map_hcp(self, hcp: HCP) -> HCPRead:
        product_stmt = (
            select(InteractionProduct.product_name)
            .join(Interaction, Interaction.id == InteractionProduct.interaction_id)
            .where(Interaction.hcp_id == hcp.id)
            .order_by(Interaction.updated_at.desc())
            .limit(3)
        )
        products = (await self.session.scalars(product_stmt)).all()

        last_visit_stmt = (
            select(Interaction.created_at)
            .where(Interaction.hcp_id == hcp.id)
            .order_by(Interaction.created_at.desc())
            .limit(1)
        )
        last_visit = (await self.session.execute(last_visit_stmt)).scalar_one_or_none()

        return HCPRead(
            id=hcp.id,
            doctor_name=hcp.doctor_name,
            hospital=hcp.hospital,
            speciality=hcp.speciality,
            city=hcp.city,
            email=hcp.email,
            history_summary=hcp.history_summary,
            last_visit=last_visit,
            recent_products=list(dict.fromkeys(products)),
        )
