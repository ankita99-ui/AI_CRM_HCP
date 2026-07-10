from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings, reload_settings
from app.core.logging import configure_logging
from app.database.seed import seed_database
from app.database.session import AsyncSessionLocal, engine
from app.models import Base

settings = reload_settings()
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

cors_kwargs: dict = {
    'allow_credentials': True,
    'allow_methods': ['*'],
    'allow_headers': ['*'],
}
if settings.app_env == 'development':
    # Allow localhost and 127.0.0.1 on any dev port (Vite may use either hostname).
    cors_kwargs['allow_origin_regex'] = r'https?://(localhost|127\.0\.0\.1)(:\d+)?'
else:
    cors_kwargs['allow_origins'] = settings.cors_origins

app.add_middleware(CORSMiddleware, **cors_kwargs)


@app.get('/health', tags=['health'])
async def health() -> dict[str, str]:
    return {'status': 'ok'}


app.include_router(api_router)
