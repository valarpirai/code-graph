# tests/conftest.py
import pytest
from pathlib import Path
from app.storage.project_store import ProjectStore
from app.config import get_settings

@pytest.fixture
def data_dir(tmp_path) -> Path:
    return tmp_path

@pytest.fixture
def store(data_dir) -> ProjectStore:
    return ProjectStore(data_dir=str(data_dir))

@pytest.fixture(autouse=True)
def clear_settings_cache():
    from app.config import get_settings
    get_settings.cache_clear()
    yield
