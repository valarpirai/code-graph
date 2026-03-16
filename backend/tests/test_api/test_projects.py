# tests/test_api/test_projects.py
import io
import zipfile
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies import get_store
from app.storage.project_store import ProjectStore
from app.models.project import ProjectMeta, ProjectStatus

@pytest.mark.asyncio
async def test_list_projects_empty(tmp_path):
    store = ProjectStore(data_dir=str(tmp_path))
    app.dependency_overrides[get_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/projects")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.asyncio
async def test_list_projects_returns_existing(tmp_path):
    store = ProjectStore(data_dir=str(tmp_path))
    meta = ProjectMeta(id="p1", name="repo", source="https://github.com/a/b", languages=["go"])
    store.save(meta)
    app.dependency_overrides[get_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/projects")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "p1"

@pytest.mark.asyncio
async def test_get_project_not_found(tmp_path):
    store = ProjectStore(data_dir=str(tmp_path))
    app.dependency_overrides[get_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/projects/nonexistent")
    app.dependency_overrides.clear()
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_project(tmp_path):
    store = ProjectStore(data_dir=str(tmp_path))
    meta = ProjectMeta(id="del-me", name="r", source="url", languages=[])
    store.save(meta)
    app.dependency_overrides[get_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.delete("/api/v1/projects/del-me")
    app.dependency_overrides.clear()
    assert resp.status_code == 204
    with pytest.raises(KeyError):
        store.load("del-me")

@pytest.mark.asyncio
async def test_create_project_from_github_url(tmp_path):
    store = ProjectStore(data_dir=str(tmp_path))
    app.dependency_overrides[get_store] = lambda: store

    with patch("app.api.projects.check_repo_public", new_callable=AsyncMock, return_value=True), \
         patch("app.api.projects.clone_repo"), \
         patch("app.api.projects.detect_languages", return_value=["go"]):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/projects", json={"github_url": "https://github.com/foo/bar"})

    app.dependency_overrides.clear()
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "bar"
    assert data["languages"] == ["go"]
    assert data["status"] == "ready"

@pytest.mark.asyncio
async def test_create_project_clone_fails_returns_error_status(tmp_path):
    store = ProjectStore(data_dir=str(tmp_path))
    app.dependency_overrides[get_store] = lambda: store

    with patch("app.api.projects.check_repo_public", new_callable=AsyncMock, return_value=True), \
         patch("app.api.projects.clone_repo", side_effect=Exception("network error")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/projects", json={"github_url": "https://github.com/foo/bar"})

    app.dependency_overrides.clear()
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "error"
    assert data["error_message"] == "network error"

def make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()

@pytest.mark.asyncio
async def test_upload_zip_success(tmp_path):
    store = ProjectStore(data_dir=str(tmp_path))
    app.dependency_overrides[get_store] = lambda: store
    zip_bytes = make_zip({"src/Main.java": "class Main {}"})
    with patch("app.api.projects.detect_languages", return_value=["java"]):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/projects/upload", files={"file": ("repo.zip", zip_bytes, "application/zip")})
    app.dependency_overrides.clear()
    assert resp.status_code == 201
    assert resp.json()["status"] == "ready"
    assert resp.json()["languages"] == ["java"]

@pytest.mark.asyncio
async def test_upload_zip_too_large(tmp_path):
    store = ProjectStore(data_dir=str(tmp_path))
    app.dependency_overrides[get_store] = lambda: store
    big_content = b"x" * (201 * 1024 * 1024)  # 201 MB
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/projects/upload", files={"file": ("big.zip", big_content, "application/zip")})
    app.dependency_overrides.clear()
    assert resp.status_code == 413

@pytest.mark.asyncio
async def test_upload_zip_invalid(tmp_path):
    store = ProjectStore(data_dir=str(tmp_path))
    app.dependency_overrides[get_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/projects/upload", files={"file": ("bad.zip", b"not a zip", "application/zip")})
    app.dependency_overrides.clear()
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "invalid_zip"

@pytest.mark.asyncio
async def test_reindex_sets_indexing_and_deletes_wiki(tmp_path):
    store = ProjectStore(data_dir=str(tmp_path))
    meta = ProjectMeta(id="p-ri", name="r", source="url", languages=["go"], status=ProjectStatus.READY)
    store.save(meta)
    wiki_dir = store.wiki_dir("p-ri")
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "index.md").write_text("old wiki")
    app.dependency_overrides[get_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/projects/p-ri/reindex")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["status"] == "indexing"
    assert not wiki_dir.exists()

@pytest.mark.asyncio
async def test_reindex_not_found(tmp_path):
    store = ProjectStore(data_dir=str(tmp_path))
    app.dependency_overrides[get_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/projects/nonexistent/reindex")
    app.dependency_overrides.clear()
    assert resp.status_code == 404
