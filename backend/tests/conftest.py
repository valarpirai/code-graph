# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def data_dir(tmp_path) -> Path:
    return tmp_path

# ProjectStore fixture will be added when app.storage.project_store is implemented
# @pytest.fixture
# def store(data_dir) -> ProjectStore:
#     return ProjectStore(data_dir=str(data_dir))

@pytest.fixture(autouse=True)
def clear_settings_cache():
    from app.config import get_settings
    get_settings.cache_clear()
    yield
