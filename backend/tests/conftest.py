# tests/conftest.py
import pytest
from pathlib import Path
from app.storage.project_store import ProjectStore

@pytest.fixture
def data_dir(tmp_path) -> Path:
    return tmp_path

@pytest.fixture
def store(data_dir) -> ProjectStore:
    return ProjectStore(data_dir=str(data_dir))
