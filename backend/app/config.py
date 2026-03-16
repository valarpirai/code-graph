from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    data_dir: str = "/data"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost",
        "http://localhost:80",
    ]

@lru_cache
def get_settings() -> Settings:
    return Settings()
