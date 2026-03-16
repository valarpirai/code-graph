import pytest
from datetime import datetime, timezone
from app.models.project import ProjectStatus, ProjectMeta, ProjectCreate

def test_project_status_values():
    assert ProjectStatus.PENDING == "pending"
    assert ProjectStatus.INDEXING == "indexing"
    assert ProjectStatus.READY == "ready"
    assert ProjectStatus.ERROR == "error"

def test_project_meta_defaults():
    meta = ProjectMeta(
        id="abc-123",
        name="my-repo",
        source="https://github.com/foo/bar",
        languages=["python"],
    )
    assert meta.status == ProjectStatus.PENDING
    assert meta.error_message is None
    assert meta.last_indexed is None

def test_project_meta_serializes_to_dict():
    meta = ProjectMeta(
        id="abc-123",
        name="my-repo",
        source="https://github.com/foo/bar",
        languages=["java", "go"],
        status=ProjectStatus.READY,
    )
    d = meta.model_dump()
    assert d["status"] == "ready"
    assert d["languages"] == ["java", "go"]
