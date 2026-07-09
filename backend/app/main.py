from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.seed import seed_database
from app.database.session import AsyncSessionLocal, engine
from app.models import Base

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    yield


app = FastAPI(
    title=settings.app_name,
    version='1.0.0',
    description='AI-first CRM HCP logging module with FastAPI, LangGraph, PostgreSQL, and Groq.',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health', tags=['health'])
async def health() -> dict[str, str]:
    return {'status': 'ok'}


app.include_router(api_router)
