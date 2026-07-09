from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.hcp import HCPRead
from app.tools.search_hcp_tool import SearchHCPTool

router = APIRouter(prefix='/api/hcp', tags=['hcp'])


@router.get('/search', response_model=list[HCPRead])
async def search_hcp(query: str = Query(default=''), session: AsyncSession = Depends(get_db_session)) -> list[HCPRead]:
    return await SearchHCPTool(session).run(query)


@router.get('/{hcp_id}', response_model=HCPRead)
async def get_hcp(hcp_id: int, session: AsyncSession = Depends(get_db_session)) -> HCPRead:
    from app.services.hcp_service import HCPService

    hcp = await HCPService(session).get_by_id(hcp_id)
    if not hcp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='HCP not found')
    return hcp
