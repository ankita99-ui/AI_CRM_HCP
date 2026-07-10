import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import InteractionOrchestrator
from app.api.deps import get_db_session
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.interaction import ExtractedInteraction, InteractionRead

router = APIRouter(prefix='/api/chat', tags=['chat'])


@router.post('', response_model=ChatResponse)
async def chat(request: ChatRequest, session: AsyncSession = Depends(get_db_session)) -> ChatResponse:
    orchestrator = InteractionOrchestrator(session)
    result = await orchestrator.process(
        request.content,
        request.history,
        save=request.save,
        draft=request.draft,
        interaction_id=request.interaction_id,
    )
    extracted = ExtractedInteraction(**result['interaction'])
    save_result = InteractionRead(**result['save_result']) if result.get('save_result') else None
    return ChatResponse(
        message=result['message'],
        extracted=extracted,
        next_best_action=result.get('next_best_action', []),
        save_result=save_result,
    )


@router.post('/stream')
async def chat_stream(request: ChatRequest, session: AsyncSession = Depends(get_db_session)) -> StreamingResponse:
    orchestrator = InteractionOrchestrator(session)

    async def event_generator():
        result = await orchestrator.process(
        request.content,
        request.history,
        save=request.save,
        draft=request.draft,
        interaction_id=request.interaction_id,
    )
        yield f'data: {json.dumps({"type": "token", "content": result["message"]})}\n\n'
        payload = {
            'type': 'complete',
            'message': result['message'],
            'extracted': result['interaction'],
            'next_best_action': result.get('next_best_action', []),
            'save_result': result.get('save_result'),
        }
        yield f'data: {json.dumps(payload, default=str)}\n\n'

    return StreamingResponse(event_generator(), media_type='text/event-stream')
