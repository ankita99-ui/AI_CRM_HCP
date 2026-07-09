from fastapi import APIRouter

from app.api.chat import router as chat_router
from app.api.email import router as email_router
from app.api.hcp import router as hcp_router
from app.api.interactions import router as interactions_router
from app.api.recommendations import router as recommendations_router

api_router = APIRouter()
api_router.include_router(chat_router)
api_router.include_router(interactions_router)
api_router.include_router(hcp_router)
api_router.include_router(recommendations_router)
api_router.include_router(email_router)
