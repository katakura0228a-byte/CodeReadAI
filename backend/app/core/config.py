from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://coderead:coderead@localhost:5432/coderead"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-5-nano"

    # Application
    secret_key: str = "dev-secret-key"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Repository storage
    repo_storage_path: str = "/app/repositories"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
