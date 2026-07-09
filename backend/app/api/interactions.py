from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.interaction import InteractionCreate, InteractionRead, InteractionUpdate
from app.services.interaction_service import InteractionService

router = APIRouter(prefix='/api/interactions', tags=['interactions'])


@router.post('', response_model=InteractionRead, status_code=status.HTTP_201_CREATED)
async def create_interaction(payload: InteractionCreate, session: AsyncSession = Depends(get_db_session)) -> InteractionRead:
    service = InteractionService(session)
    return await service.create_interaction(payload)


@router.put('/{interaction_id}', response_model=InteractionRead)
async def update_interaction(interaction_id: int, payload: InteractionUpdate, session: AsyncSession = Depends(get_db_session)) -> InteractionRead:
    service = InteractionService(session)
    interaction = await service.update_interaction(interaction_id, payload)
    if not interaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Interaction not found')
    return interaction


@router.get('', response_model=list[InteractionRead])
async def list_interactions(session: AsyncSession = Depends(get_db_session)) -> list[InteractionRead]:
    return await InteractionService(session).list_interactions()
