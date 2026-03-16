from functools import lru_cache
from app.config import get_settings
from app.storage.project_store import ProjectStore


@lru_cache
def get_store() -> ProjectStore:
    return ProjectStore(data_dir=get_settings().data_dir)
