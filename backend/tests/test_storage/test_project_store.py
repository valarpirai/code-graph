# tests/test_storage/test_project_store.py
import pytest
from pathlib import Path
from app.models.project import ProjectMeta, ProjectStatus
from app.storage.project_store import ProjectStore

# Uses `store` fixture from conftest.py (ProjectStore backed by tmp_path)

def test_create_project_creates_directory(store, tmp_path):
    meta = ProjectMeta(id="proj-1", name="test", source="https://github.com/a/b", languages=[])
    store.save(meta)
    assert (tmp_path / "proj-1").is_dir()
    assert (tmp_path / "proj-1" / "project.json").exists()

def test_load_project_round_trips(store):
    meta = ProjectMeta(id="proj-2", name="repo", source="https://github.com/x/y", languages=["go"])
    store.save(meta)
    loaded = store.load("proj-2")
    assert loaded.id == "proj-2"
    assert loaded.languages == ["go"]
    assert loaded.status == ProjectStatus.PENDING

def test_list_projects_returns_all(store):
    for i in range(3):
        meta = ProjectMeta(id=f"proj-{i}", name=f"repo-{i}", source="url", languages=[])
        store.save(meta)
    projects = store.list_all()
    assert len(projects) == 3

def test_delete_project_removes_directory(store, tmp_path):
    meta = ProjectMeta(id="proj-del", name="todelete", source="url", languages=[])
    store.save(meta)
    store.delete("proj-del")
    assert not (tmp_path / "proj-del").exists()

def test_load_nonexistent_project_raises(store):
    with pytest.raises(KeyError):
        store.load("does-not-exist")

def test_update_status(store):
    meta = ProjectMeta(id="proj-s", name="r", source="url", languages=[])
    store.save(meta)
    store.update_status("proj-s", ProjectStatus.INDEXING)
    loaded = store.load("proj-s")
    assert loaded.status == ProjectStatus.INDEXING

def test_update_status_with_error(store):
    meta = ProjectMeta(id="proj-e", name="r", source="url", languages=[])
    store.save(meta)
    store.update_status("proj-e", ProjectStatus.ERROR, error_message="Clone failed")
    loaded = store.load("proj-e")
    assert loaded.status == ProjectStatus.ERROR
    assert loaded.error_message == "Clone failed"

def test_update_status_ready_clears_error_message(store):
    meta = ProjectMeta(id="proj-retry", name="r", source="url", languages=[])
    store.save(meta)
    store.update_status("proj-retry", ProjectStatus.ERROR, error_message="Clone failed")
    store.update_status("proj-retry", ProjectStatus.READY)
    loaded = store.load("proj-retry")
    assert loaded.status == ProjectStatus.READY
    assert loaded.error_message is None
    assert loaded.last_indexed is not None
