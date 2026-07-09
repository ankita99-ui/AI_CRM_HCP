from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV = Path(__file__).resolve().parents[3] / '.env'
BACKEND_ENV = Path(__file__).resolve().parents[2] / '.env'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(ROOT_ENV), str(BACKEND_ENV), '.env'),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    app_name: str = 'AI-First CRM HCP Module'
    app_env: str = 'development'
    backend_host: str = '0.0.0.0'
    backend_port: int = 8000
    cors_origins: List[str] | str = Field(default=['http://localhost:5173'])

    database_url: str = 'postgresql+asyncpg://postgres:postgres@localhost:5432/ai_crm_hcp'

    groq_api_key: str = ''
    groq_model: str = 'gemma2-9b-it'

    @field_validator('cors_origins', mode='before')
    @classmethod
    def split_origins(cls, value: List[str] | str) -> List[str]:
        if isinstance(value, list):
            return value
        return [origin.strip() for origin in value.split(',') if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
