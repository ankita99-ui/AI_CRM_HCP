from sqlalchemy.ext.asyncio import AsyncSession

from app.services.hcp_service import HCPService


class SearchHCPTool:
    def __init__(self, session: AsyncSession):
        self.service = HCPService(session)

    async def run(self, query: str):
        return await self.service.search(query)
