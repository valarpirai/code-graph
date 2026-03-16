import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_store
from app.storage.project_store import ProjectStore
from app.models.project import ProjectMeta, ProjectStatus

PROJECT_ID = "test-wiki-project-001"


def _make_project_meta() -> ProjectMeta:
    return ProjectMeta(
        id=PROJECT_ID,
        name="Wiki Test Project",
        source="https://github.com/example/repo",
        status=ProjectStatus.READY,
    )


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory with a stub graph.ttl."""
    proj_dir = tmp_path / PROJECT_ID
    proj_dir.mkdir()

    store = ProjectStore(data_dir=str(tmp_path))
    store.save(_make_project_meta())

    # Minimal valid Turtle graph
    ttl_content = """\
@prefix cg: <http://codegraph.dev/ontology#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://example.org/file1> a cg:File ;
    cg:language "python" .
"""
    (proj_dir / "graph.ttl").write_text(ttl_content)
    return proj_dir


@pytest.fixture
def client(project_dir):
    """TestClient with store dependency overridden to point at tmp_path."""
    tmp_path = project_dir.parent
    override_store = ProjectStore(data_dir=str(tmp_path))
    app.dependency_overrides[get_store] = lambda: override_store
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_project(tmp_path):
    """TestClient pointing at an empty data dir (no projects)."""
    override_store = ProjectStore(data_dir=str(tmp_path))
    app.dependency_overrides[get_store] = lambda: override_store
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGenerateWikiEndpoint:
    def test_returns_200_on_success(self, client):
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        assert response.status_code == 200

    def test_response_body_has_message(self, client):
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        body = response.json()
        assert "message" in body

    def test_response_body_has_file_count(self, client):
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        body = response.json()
        assert "files_generated" in body
        assert isinstance(body["files_generated"], int)

    def test_wiki_dir_created_on_disk(self, client, project_dir):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        assert (project_dir / "wiki").exists()

    def test_index_md_created_on_disk(self, client, project_dir):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        assert (project_dir / "wiki" / "index.md").exists()

    def test_returns_404_for_missing_project(self, client_no_project):
        response = client_no_project.post("/api/v1/projects/nonexistent-id/wiki/generate")
        assert response.status_code == 404

    def test_returns_400_if_graph_ttl_missing(self, client, project_dir):
        (project_dir / "graph.ttl").unlink()
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        assert response.status_code == 400


class TestListWikiEndpoint:
    def test_returns_200(self, client):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki")
        assert response.status_code == 200

    def test_returns_list(self, client):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki")
        assert isinstance(response.json(), list)

    def test_index_entry_present(self, client):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki")
        paths = [entry["path"] for entry in response.json()]
        assert any("index.md" in p for p in paths)

    def test_entry_has_required_keys(self, client):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki")
        entries = response.json()
        assert len(entries) > 0
        entry = entries[0]
        assert "path" in entry
        assert "type" in entry
        assert "name" in entry

    def test_returns_empty_list_if_wiki_not_generated(self, client):
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_404_for_missing_project(self, client_no_project):
        response = client_no_project.get("/api/v1/projects/nonexistent-id/wiki")
        assert response.status_code == 404


class TestFetchWikiFileEndpoint:
    def test_returns_markdown_content(self, client):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki/index.md")
        assert response.status_code == 200
        assert "Wiki Test Project" in response.text

    def test_content_type_is_text(self, client):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki/index.md")
        assert "text" in response.headers["content-type"]

    def test_nested_file_path_works(self, client, project_dir):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        wiki_dir = project_dir / "wiki" / "classes"
        class_files = list(wiki_dir.glob("*.md"))
        if class_files:
            rel = "classes/" + class_files[0].name
            response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki/{rel}")
            assert response.status_code == 200

    def test_returns_404_for_missing_file(self, client):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki/classes/Nonexistent.md")
        assert response.status_code == 404

    def test_returns_404_for_missing_project(self, client_no_project):
        response = client_no_project.get("/api/v1/projects/nonexistent-id/wiki/index.md")
        assert response.status_code == 404
