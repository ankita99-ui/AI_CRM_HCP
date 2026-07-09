from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.common import NextActionRequest, NextActionResponse
from app.tools.next_best_action_tool import NextBestActionTool

router = APIRouter(tags=['recommendations'])


@router.post('/api/next-action', response_model=NextActionResponse)
async def next_action(payload: NextActionRequest, session: AsyncSession = Depends(get_db_session)) -> NextActionResponse:
    recommendations = await NextBestActionTool(session).run(payload.doctor_name, payload.products_discussed, payload.summary)
    return NextActionResponse(recommendations=recommendations)
