# Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI backend with project management, GitHub/ZIP ingestion, language detection, disk storage, and WebSocket progress streaming — fully tested and Docker-ready.

**Architecture:** Single FastAPI application with modular routers. Projects are identified by UUID and stored under `/data/<project-id>/`. All state persists in `project.json` files. No database — filesystem is the store.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, httpx (GitHub API), gitpython (cloning), rdflib (imported but not used until Plan 2), pytest, Docker

---

## Chunk 1: Project Scaffold & Configuration

### File Map

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, router registration
│   ├── config.py            # Settings via pydantic-settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── project.py       # ProjectStatus enum, ProjectMeta pydantic models
│   └── storage/
│       ├── __init__.py
│       └── project_store.py # Read/write project.json, list/delete project dirs
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures: tmp data dir, test client
│   └── test_storage/
│       ├── __init__.py
│       └── test_project_store.py
├── ontology.ttl             # Placeholder (content added in Plan 2)
├── pyproject.toml
└── Dockerfile
```

---

### Task 1: pyproject.toml and project structure

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/storage/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_storage/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "code-graph-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "httpx>=0.27.0",
    "gitpython>=3.1.43",
    "rdflib>=7.0.0",
    "owlrl>=6.0.2",
    "networkx>=3.3",
    "python-louvain>=0.16",
    "tree-sitter>=0.22.0",
    "tree-sitter-java>=0.21.0",
    "tree-sitter-typescript>=0.21.0",
    "tree-sitter-javascript>=0.21.0",
    "tree-sitter-go>=0.21.0",
    "tree-sitter-rust>=0.21.0",
    "tree-sitter-kotlin>=0.3.0",
    "tree-sitter-ruby>=0.21.0",
    "tree-sitter-c>=0.21.0",
    "jinja2>=3.1.4",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create `backend/tests/conftest.py`**

```python
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
```

- [ ] **Step 4: Create empty `__init__.py` files**

```bash
touch backend/app/__init__.py \
      backend/app/models/__init__.py \
      backend/app/storage/__init__.py \
      backend/tests/__init__.py \
      backend/tests/test_storage/__init__.py
```

- [ ] **Step 5: Create placeholder `ontology.ttl`**

```turtle
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix cg:   <http://codegraph.io/ontology#> .

<http://codegraph.io/ontology> a owl:Ontology .
```

Save as `backend/ontology.ttl`.

- [ ] **Step 6: Install dependencies**

```bash
cd backend && pip install -e ".[dev]"
```

Expected: No errors. `fastapi`, `pytest`, `rdflib` etc. importable.

- [ ] **Step 7: Commit**

```bash
git init  # if not already a git repo
git add backend/pyproject.toml backend/app/ backend/tests/ backend/ontology.ttl
git commit -m "chore: scaffold backend project structure"
```

---

### Task 2: Configuration

**Files:**
- Create: `backend/app/config.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
import os
from app.config import Settings

def test_default_data_dir():
    s = Settings()
    assert s.data_dir == "/data"

def test_cors_origins_default():
    s = Settings()
    assert "http://localhost:5173" in s.cors_origins
    assert "http://localhost" in s.cors_origins

def test_data_dir_override(monkeypatch):
    monkeypatch.setenv("DATA_DIR", "/tmp/test-data")
    s = Settings()
    assert s.data_dir == "/tmp/test-data"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 3: Implement config**

```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    data_dir: str = "/data"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost",
        "http://localhost:80",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_config.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat: add settings configuration with env override"
```

---

### Task 3: Project models

**Files:**
- Create: `backend/app/models/project.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_models/test_project.py
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
```

- [ ] **Step 2: Create test directory and run test**

```bash
mkdir -p backend/tests/test_models && touch backend/tests/test_models/__init__.py
cd backend && pytest tests/test_models/test_project.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.models.project'`

- [ ] **Step 3: Implement models**

```python
# app/models/project.py
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ProjectStatus(str, Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    READY = "ready"
    ERROR = "error"

class ProjectMeta(BaseModel):
    id: str
    name: str
    source: str                          # GitHub URL or zip filename
    languages: list[str] = []
    status: ProjectStatus = ProjectStatus.PENDING
    error_message: Optional[str] = None
    last_indexed: Optional[datetime] = None

class ProjectCreate(BaseModel):
    github_url: Optional[str] = None
    # zip upload handled via multipart form, not this model
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_models/ -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/project.py backend/tests/test_models/
git commit -m "feat: add project models with status enum"
```

---

### Task 4: Project storage

**Files:**
- Create: `backend/app/storage/project_store.py`
- Create: `backend/tests/test_storage/test_project_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_storage/test_project_store.py
import pytest
import json
from pathlib import Path
from app.models.project import ProjectMeta, ProjectStatus
from app.storage.project_store import ProjectStore

@pytest.fixture
def store(tmp_path):
    return ProjectStore(data_dir=str(tmp_path))

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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_storage/ -v
```

Expected: `ModuleNotFoundError: No module named 'app.storage.project_store'`

- [ ] **Step 3: Implement ProjectStore**

```python
# app/storage/project_store.py
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from app.models.project import ProjectMeta, ProjectStatus

class ProjectStore:
    def __init__(self, data_dir: str = "/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _project_dir(self, project_id: str) -> Path:
        return self.data_dir / project_id

    def _meta_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "project.json"

    def save(self, meta: ProjectMeta) -> None:
        project_dir = self._project_dir(meta.id)
        project_dir.mkdir(parents=True, exist_ok=True)
        with open(self._meta_path(meta.id), "w") as f:
            f.write(meta.model_dump_json(indent=2))

    def load(self, project_id: str) -> ProjectMeta:
        path = self._meta_path(project_id)
        if not path.exists():
            raise KeyError(f"Project '{project_id}' not found")
        with open(path) as f:
            return ProjectMeta.model_validate_json(f.read())

    def list_all(self) -> list[ProjectMeta]:
        projects = []
        for project_dir in self.data_dir.iterdir():
            if project_dir.is_dir():
                meta_path = project_dir / "project.json"
                if meta_path.exists():
                    with open(meta_path) as f:
                        projects.append(ProjectMeta.model_validate_json(f.read()))
        return projects

    def delete(self, project_id: str) -> None:
        project_dir = self._project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir)

    def update_status(
        self,
        project_id: str,
        status: ProjectStatus,
        error_message: Optional[str] = None,
    ) -> None:
        meta = self.load(project_id)
        meta.status = status
        meta.error_message = error_message
        if status == ProjectStatus.READY:
            meta.last_indexed = datetime.now(timezone.utc)
        self.save(meta)

    def source_dir(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "source"

    def wiki_dir(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "wiki"

    def graph_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "graph.ttl"
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_storage/ -v
```

Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/storage/project_store.py backend/tests/test_storage/
git commit -m "feat: add project store for filesystem-based project persistence"
```

---

## Chunk 2: Ingestion Pipeline

### File Map

```
backend/app/ingestion/
├── __init__.py
├── github.py              # GitHub URL validation + shallow clone
├── zip_handler.py         # ZIP upload validation, zip-slip protection, extraction
└── language_detector.py   # File extension → language name mapping
backend/tests/test_ingestion/
├── __init__.py
├── test_github.py
├── test_zip_handler.py
└── test_language_detector.py
```

---

### Task 5: Language detection

**Files:**
- Create: `backend/app/ingestion/__init__.py`
- Create: `backend/app/ingestion/language_detector.py`
- Create: `backend/tests/test_ingestion/__init__.py`
- Create: `backend/tests/test_ingestion/test_language_detector.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_ingestion/test_language_detector.py
from pathlib import Path
import pytest
from app.ingestion.language_detector import detect_languages, EXTENSION_MAP

def test_java_detected(tmp_path):
    (tmp_path / "Main.java").write_text("class Main {}")
    langs = detect_languages(tmp_path)
    assert "java" in langs

def test_typescript_detected(tmp_path):
    (tmp_path / "app.ts").write_text("const x: number = 1;")
    langs = detect_languages(tmp_path)
    assert "typescript" in langs

def test_tsx_maps_to_typescript(tmp_path):
    (tmp_path / "App.tsx").write_text("export default function App() {}")
    langs = detect_languages(tmp_path)
    assert "typescript" in langs

def test_multiple_languages(tmp_path):
    (tmp_path / "Main.java").write_text("")
    (tmp_path / "main.go").write_text("")
    (tmp_path / "lib.rs").write_text("")
    langs = detect_languages(tmp_path)
    assert set(langs) == {"java", "go", "rust"}

def test_unknown_extensions_ignored(tmp_path):
    (tmp_path / "README.md").write_text("")
    (tmp_path / ".gitignore").write_text("")
    langs = detect_languages(tmp_path)
    assert langs == []

def test_nested_files_detected(tmp_path):
    sub = tmp_path / "src" / "main"
    sub.mkdir(parents=True)
    (sub / "App.kt").write_text("")
    langs = detect_languages(tmp_path)
    assert "kotlin" in langs

def test_extension_map_completeness():
    required = {".java", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs", ".kt", ".kts", ".rb", ".c", ".h"}
    assert required.issubset(set(EXTENSION_MAP.keys()))
```

- [ ] **Step 2: Run tests**

```bash
cd backend && pytest tests/test_ingestion/test_language_detector.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement language detector**

```python
# app/ingestion/language_detector.py
from pathlib import Path

EXTENSION_MAP: dict[str, str] = {
    ".java": "java",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".rb": "ruby",
    ".c": "c",
    ".h": "c",
}

def detect_languages(root: Path) -> list[str]:
    """Return deduplicated list of detected language names under root."""
    found: set[str] = set()
    for path in root.rglob("*"):
        if path.is_file():
            lang = EXTENSION_MAP.get(path.suffix.lower())
            if lang:
                found.add(lang)
    return sorted(found)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_ingestion/test_language_detector.py -v
```

Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
touch backend/app/ingestion/__init__.py backend/tests/test_ingestion/__init__.py
git add backend/app/ingestion/ backend/tests/test_ingestion/test_language_detector.py
git commit -m "feat: add language detection from file extensions"
```

---

### Task 6: ZIP handler

**Files:**
- Create: `backend/app/ingestion/zip_handler.py`
- Create: `backend/tests/test_ingestion/test_zip_handler.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_ingestion/test_zip_handler.py
import io
import zipfile
import pytest
from pathlib import Path
from app.ingestion.zip_handler import extract_zip, ZipTooLargeError, InvalidZipError, ZipSlipError

MAX_BYTES = 200 * 1024 * 1024  # 200 MB

def make_zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()

def test_extracts_files(tmp_path):
    data = make_zip({"src/Main.java": "class Main {}", "README.md": "hello"})
    dest = tmp_path / "out"
    extract_zip(io.BytesIO(data), dest, max_bytes=MAX_BYTES)
    assert (dest / "src" / "Main.java").exists()
    assert (dest / "README.md").exists()

def test_rejects_oversized(tmp_path):
    data = make_zip({"big.txt": "x" * 1000})
    dest = tmp_path / "out"
    with pytest.raises(ZipTooLargeError):
        extract_zip(io.BytesIO(data), dest, max_bytes=100)

def test_rejects_invalid_zip(tmp_path):
    dest = tmp_path / "out"
    with pytest.raises(InvalidZipError):
        extract_zip(io.BytesIO(b"not a zip file"), dest, max_bytes=MAX_BYTES)

def test_rejects_zip_slip(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../../etc/passwd", "evil")
    dest = tmp_path / "out"
    with pytest.raises(ZipSlipError):
        extract_zip(io.BytesIO(buf.getvalue()), dest, max_bytes=MAX_BYTES)

def test_rejects_absolute_path_zip_slip(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("/etc/passwd", "evil")
    dest = tmp_path / "out"
    with pytest.raises(ZipSlipError):
        extract_zip(io.BytesIO(buf.getvalue()), dest, max_bytes=MAX_BYTES)
```

- [ ] **Step 2: Run tests**

```bash
cd backend && pytest tests/test_ingestion/test_zip_handler.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement ZIP handler**

```python
# app/ingestion/zip_handler.py
import io
import zipfile
from pathlib import Path

class ZipTooLargeError(Exception): pass
class InvalidZipError(Exception): pass
class ZipSlipError(Exception): pass

def extract_zip(data: io.BytesIO, dest: Path, max_bytes: int) -> None:
    """Extract zip to dest, enforcing size limit and zip-slip protection."""
    raw = data.read()
    if len(raw) > max_bytes:
        raise ZipTooLargeError(f"ZIP exceeds {max_bytes // (1024*1024)} MB limit")

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as e:
        raise InvalidZipError("Invalid or corrupt ZIP file") from e

    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()

    for member in zf.infolist():
        member_path = (dest / member.filename).resolve()
        # Zip-slip: reject if resolved path escapes destination
        if not str(member_path).startswith(str(dest_resolved) + "/") and member_path != dest_resolved:
            raise ZipSlipError(f"Zip-slip detected: {member.filename!r}")
        zf.extract(member, dest)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_ingestion/test_zip_handler.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/zip_handler.py backend/tests/test_ingestion/test_zip_handler.py
git commit -m "feat: add zip extraction with size limit and zip-slip protection"
```

---

### Task 7: GitHub ingestion

**Files:**
- Create: `backend/app/ingestion/github.py`
- Create: `backend/tests/test_ingestion/test_github.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_ingestion/test_github.py
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from app.ingestion.github import (
    validate_github_url,
    check_repo_public,
    clone_repo,
    GitHubURLError,
    RepoNotAccessibleError,
    GitHubAPIUnavailableError,
)

def test_validate_github_url_valid():
    owner, repo = validate_github_url("https://github.com/torvalds/linux")
    assert owner == "torvalds"
    assert repo == "linux"

def test_validate_github_url_with_git_suffix():
    owner, repo = validate_github_url("https://github.com/foo/bar.git")
    assert owner == "foo"
    assert repo == "bar"

def test_validate_github_url_invalid():
    with pytest.raises(GitHubURLError):
        validate_github_url("https://gitlab.com/foo/bar")

def test_validate_github_url_too_short():
    with pytest.raises(GitHubURLError):
        validate_github_url("https://github.com/foo")

@pytest.mark.asyncio
async def test_check_repo_public_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"private": False, "name": "bar"}
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await check_repo_public("foo", "bar")
    assert result is True

@pytest.mark.asyncio
async def test_check_repo_public_private_repo():
    mock_response = MagicMock()
    mock_response.status_code = 404
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(RepoNotAccessibleError):
            await check_repo_public("foo", "private-repo")

@pytest.mark.asyncio
async def test_check_repo_public_api_unavailable():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=httpx.ConnectError("timeout")):
        with pytest.raises(GitHubAPIUnavailableError):
            await check_repo_public("foo", "bar")

@pytest.mark.asyncio
async def test_check_repo_public_rate_limited():
    mock_response = MagicMock()
    mock_response.status_code = 429
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(GitHubAPIUnavailableError):
            await check_repo_public("foo", "bar")

@pytest.mark.asyncio
async def test_check_repo_public_403_treated_as_rate_limit():
    # GitHub returns 403 for rate-limit abuse; treat as API unavailable (502)
    mock_response = MagicMock()
    mock_response.status_code = 403
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(GitHubAPIUnavailableError):
            await check_repo_public("foo", "bar")
```

- [ ] **Step 2: Run tests**

```bash
cd backend && pytest tests/test_ingestion/test_github.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement GitHub ingestion**

```python
# app/ingestion/github.py
import re
import httpx
import git
from pathlib import Path

class GitHubURLError(ValueError): pass
class RepoNotAccessibleError(Exception): pass
class GitHubAPIUnavailableError(Exception): pass

_GITHUB_RE = re.compile(
    r"^https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)

def validate_github_url(url: str) -> tuple[str, str]:
    """Parse and validate a GitHub URL. Returns (owner, repo)."""
    m = _GITHUB_RE.match(url.strip())
    if not m:
        raise GitHubURLError(f"Not a valid public GitHub URL: {url!r}")
    return m.group(1), m.group(2)

async def check_repo_public(owner: str, repo: str) -> bool:
    """Confirm repo exists and is public via GitHub API. Raises on failure."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(api_url, headers={"Accept": "application/vnd.github+json"})
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
        raise GitHubAPIUnavailableError(
            "Could not reach GitHub API. Try again shortly or check your network."
        ) from e

    if resp.status_code == 200:
        data = resp.json()
        if data.get("private", True):
            raise RepoNotAccessibleError("Repository is private. Only public repos are supported.")
        return True
    elif resp.status_code in (403, 429):
        raise GitHubAPIUnavailableError(
            "GitHub API rate limit reached. Try again in a few minutes."
        )
    else:
        raise RepoNotAccessibleError(
            "Repository is private or does not exist. Only public repos are supported."
        )

def clone_repo(owner: str, repo: str, dest: Path) -> None:
    """Shallow-clone a public GitHub repo into dest."""
    url = f"https://github.com/{owner}/{repo}.git"
    dest.mkdir(parents=True, exist_ok=True)
    git.Repo.clone_from(url, dest, depth=1, single_branch=True)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_ingestion/test_github.py -v
```

Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/github.py backend/tests/test_ingestion/test_github.py
git commit -m "feat: add GitHub URL validation and public repo check"
```

---

## Chunk 3: FastAPI Application & WebSocket

### File Map

```
backend/app/
├── main.py                    # FastAPI app + CORS + router registration
├── dependencies.py            # Dependency injection (get_store, get_settings)
├── api/
│   ├── __init__.py
│   └── projects.py            # POST/GET/DELETE /projects, POST reindex
├── ws/
│   ├── __init__.py
│   └── indexing.py            # WebSocket manager + indexing background task
backend/tests/
├── test_api/
│   ├── __init__.py
│   └── test_projects.py
└── test_ws/
    ├── __init__.py
    └── test_indexing_ws.py
```

---

### Task 8: FastAPI app skeleton + dependencies

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/dependencies.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/ws/__init__.py`

- [ ] **Step 1: Write smoke test**

```python
# tests/test_api/test_projects.py  (start with health check)
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test**

```bash
cd backend && pytest tests/test_api/test_projects.py::test_health_check -v
```

Expected: `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Create app skeleton**

```python
# app/dependencies.py
from functools import lru_cache
from app.config import get_settings
from app.storage.project_store import ProjectStore

@lru_cache
def get_store() -> ProjectStore:
    return ProjectStore(data_dir=get_settings().data_dir)
```

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Code Graph API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 4: Run test**

```bash
cd backend && pytest tests/test_api/test_projects.py::test_health_check -v
```

Expected: PASSED

- [ ] **Step 5: Commit**

```bash
mkdir -p backend/app/api backend/app/ws
touch backend/app/api/__init__.py backend/app/ws/__init__.py
git add backend/app/main.py backend/app/dependencies.py backend/app/api/ backend/app/ws/
git commit -m "feat: add FastAPI app skeleton with health check and CORS"
```

---

### Task 9: Projects API endpoints

**Files:**
- Create: `backend/app/api/projects.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_api/test_projects.py (add to existing file)
import io
import zipfile
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies import get_store          # import BEFORE fixtures that use it
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
```

- [ ] **Step 2: Run tests**

```bash
mkdir -p backend/tests/test_api && touch backend/tests/test_api/__init__.py
cd backend && pytest tests/test_api/test_projects.py -v
```

Expected: multiple failures — routes not defined yet

- [ ] **Step 3: Implement projects router**

```python
# app/api/projects.py
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import Response
from app.dependencies import get_store
from app.storage.project_store import ProjectStore
from app.models.project import ProjectMeta, ProjectStatus, ProjectCreate
from app.ingestion.github import (
    validate_github_url, check_repo_public, clone_repo,
    GitHubURLError, RepoNotAccessibleError, GitHubAPIUnavailableError,
)
from app.ingestion.zip_handler import extract_zip, ZipTooLargeError, InvalidZipError, ZipSlipError
from app.ingestion.language_detector import detect_languages
import io

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])
MAX_ZIP_BYTES = 200 * 1024 * 1024

@router.get("", response_model=list[ProjectMeta])
def list_projects(store: ProjectStore = Depends(get_store)):
    return store.list_all()

@router.get("/{project_id}", response_model=ProjectMeta)
def get_project(project_id: str, store: ProjectStore = Depends(get_store)):
    try:
        return store.load(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": f"Project {project_id!r} not found"})

@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, store: ProjectStore = Depends(get_store)):
    try:
        store.load(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Project not found"})
    store.delete(project_id)
    return Response(status_code=204)

@router.post("", response_model=ProjectMeta, status_code=201)
async def create_project(
    payload: ProjectCreate,
    store: ProjectStore = Depends(get_store),
):
    if not payload.github_url:
        raise HTTPException(status_code=422, detail={"error": "missing_source", "message": "github_url is required"})

    try:
        owner, repo = validate_github_url(payload.github_url)
    except GitHubURLError as e:
        raise HTTPException(status_code=422, detail={"error": "invalid_url", "message": str(e)})

    try:
        await check_repo_public(owner, repo)
    except RepoNotAccessibleError as e:
        raise HTTPException(status_code=422, detail={"error": "repo_not_accessible", "message": str(e)})
    except GitHubAPIUnavailableError as e:
        raise HTTPException(status_code=502, detail={"error": "github_api_unavailable", "message": str(e)})

    project_id = str(uuid.uuid4())
    meta = ProjectMeta(id=project_id, name=repo, source=payload.github_url, languages=[])
    store.save(meta)
    store.update_status(project_id, ProjectStatus.INDEXING)

    source_dir = store.source_dir(project_id)
    try:
        clone_repo(owner, repo, source_dir)
        languages = detect_languages(source_dir)
        meta = store.load(project_id)
        meta.languages = languages
        store.save(meta)
        store.update_status(project_id, ProjectStatus.READY)
    except Exception as e:
        store.update_status(project_id, ProjectStatus.ERROR, error_message=str(e))

    return store.load(project_id)

@router.post("/upload", response_model=ProjectMeta, status_code=201)
async def upload_zip(
    file: UploadFile = File(...),
    store: ProjectStore = Depends(get_store),
):
    content = await file.read()
    if len(content) > MAX_ZIP_BYTES:
        raise HTTPException(status_code=413, detail={"error": "zip_too_large", "message": "ZIP file exceeds 200 MB limit"})

    project_id = str(uuid.uuid4())
    name = Path(file.filename or "upload").stem
    meta = ProjectMeta(id=project_id, name=name, source=file.filename or "upload.zip", languages=[])
    store.save(meta)
    store.update_status(project_id, ProjectStatus.INDEXING)

    source_dir = store.source_dir(project_id)
    try:
        extract_zip(io.BytesIO(content), source_dir, max_bytes=MAX_ZIP_BYTES)
        languages = detect_languages(source_dir)
        meta = store.load(project_id)
        meta.languages = languages
        store.save(meta)
        store.update_status(project_id, ProjectStatus.READY)
    except (InvalidZipError, ZipSlipError) as e:
        store.update_status(project_id, ProjectStatus.ERROR, error_message=str(e))
        raise HTTPException(status_code=422, detail={"error": "invalid_zip", "message": str(e)})
    except Exception as e:
        store.update_status(project_id, ProjectStatus.ERROR, error_message=str(e))

    return store.load(project_id)

@router.post("/{project_id}/reindex", response_model=ProjectMeta)
def reindex_project(project_id: str, store: ProjectStore = Depends(get_store)):
    try:
        meta = store.load(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Project not found"})

    # Delete stale wiki
    import shutil
    wiki_dir = store.wiki_dir(project_id)
    if wiki_dir.exists():
        shutil.rmtree(wiki_dir)

    store.update_status(project_id, ProjectStatus.INDEXING)
    # Full re-parsing handled by indexing pipeline (Plan 2); for now just mark indexing
    return store.load(project_id)
```

- [ ] **Step 4: Register router in main.py**

```python
# app/main.py — add after existing code
from app.api.projects import router as projects_router
app.include_router(projects_router)
```

- [ ] **Step 5: Run tests**

```bash
cd backend && pytest tests/test_api/ -v
```

Expected: All PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/projects.py backend/app/main.py backend/tests/test_api/
git commit -m "feat: add project CRUD endpoints (list, get, delete, create from GitHub/ZIP)"
```

---

### Task 10: WebSocket indexing progress

**Files:**
- Create: `backend/app/ws/indexing.py`
- Create: `backend/tests/test_ws/__init__.py`
- Create: `backend/tests/test_ws/test_indexing_ws.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_ws/test_indexing_ws.py
import pytest
from app.ws.indexing import IndexingNotifier, IndexingEvent

@pytest.mark.asyncio
async def test_notifier_registers_and_sends():
    notifier = IndexingNotifier()
    messages = []

    async def fake_send(msg):
        messages.append(msg)

    notifier.register("test-proj", fake_send)
    await notifier.notify("test-proj", IndexingEvent(status="indexing", progress=0.5, message="Parsing..."))
    assert len(messages) == 1
    assert messages[0]["status"] == "indexing"
    assert messages[0]["progress"] == 0.5

@pytest.mark.asyncio
async def test_notifier_unregister():
    notifier = IndexingNotifier()
    messages = []

    async def fake_send(msg):
        messages.append(msg)

    notifier.register("p1", fake_send)
    notifier.unregister("p1")
    await notifier.notify("p1", IndexingEvent(status="done", progress=1.0, message="Done"))
    assert len(messages) == 0  # unregistered, no message sent

@pytest.mark.asyncio
async def test_ws_route_receives_event():
    """Test that the FastAPI WebSocket route delivers events pushed via notifier."""
    from app.ws.indexing import notifier as app_notifier
    from fastapi.testclient import TestClient

    client = TestClient(app)
    with client.websocket_connect("/ws/projects/proj-ws/status") as ws:
        import asyncio
        async def push():
            await app_notifier.notify("proj-ws", IndexingEvent(status="indexing", progress=0.3, message="started"))
        asyncio.get_event_loop().run_until_complete(push())
        data = ws.receive_json()
    assert data["status"] == "indexing"
    assert data["progress"] == 0.3
```

- [ ] **Step 2: Run tests**

```bash
mkdir -p backend/tests/test_ws && touch backend/tests/test_ws/__init__.py
cd backend && pytest tests/test_ws/ -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement WebSocket notifier**

```python
# app/ws/indexing.py
from typing import Callable, Awaitable
from pydantic import BaseModel

class IndexingEvent(BaseModel):
    status: str       # "indexing" | "done" | "error"
    progress: float   # 0.0 – 1.0
    message: str

SendFn = Callable[[dict], Awaitable[None]]

class IndexingNotifier:
    """Tracks active WebSocket connections per project and broadcasts events."""
    def __init__(self):
        self._listeners: dict[str, list[SendFn]] = {}

    def register(self, project_id: str, send_fn: SendFn) -> None:
        self._listeners.setdefault(project_id, []).append(send_fn)

    def unregister(self, project_id: str) -> None:
        self._listeners.pop(project_id, None)

    async def notify(self, project_id: str, event: IndexingEvent) -> None:
        fns = self._listeners.get(project_id, [])
        for fn in fns:
            await fn(event.model_dump())

# Singleton used by FastAPI app
notifier = IndexingNotifier()
```

- [ ] **Step 4: Add WebSocket route to main.py**

```python
# app/main.py — add WebSocket endpoint
from fastapi import WebSocket, WebSocketDisconnect
from app.ws.indexing import notifier

@app.websocket("/ws/projects/{project_id}/status")
async def ws_indexing_status(websocket: WebSocket, project_id: str):
    await websocket.accept()
    async def send(msg: dict):
        await websocket.send_json(msg)
    notifier.register(project_id, send)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        notifier.unregister(project_id)
```

- [ ] **Step 5: Run all tests**

```bash
cd backend && pytest -v
```

Expected: All PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/ws/indexing.py backend/tests/test_ws/ backend/app/main.py
git commit -m "feat: add WebSocket indexing progress notifier"
```

---

## Chunk 4: Dockerfile, Docker Compose & Local Dev Setup

### Task 11: Dockerfile

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: Write Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY app/ ./app/
COPY ontology.ttl ./ontology.ttl

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Build and verify**

```bash
cd backend && docker build -t code-graph-backend .
```

Expected: Builds successfully.

- [ ] **Step 3: Commit**

```bash
git add backend/Dockerfile
git commit -m "chore: add backend Dockerfile"
```

---

### Task 12: Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Create docker-compose.yml**

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
      - ./backend/ontology.ttl:/app/ontology.ttl:ro
    environment:
      - DATA_DIR=/data
      - CORS_ORIGINS=http://localhost:5173,http://localhost,http://localhost:80
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
```

- [ ] **Step 2: Create .env.example**

```bash
# .env.example
DATA_DIR=./data
CORS_ORIGINS=http://localhost:5173,http://localhost
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "chore: add docker-compose and env example"
```

---

### Task 13: Run full test suite and verify

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && pytest -v --tb=short
```

Expected: All tests PASS. No warnings about unclosed resources.

- [ ] **Step 2: Start server locally and smoke test**

```bash
cd backend && DATA_DIR=/tmp/cg-data uvicorn app.main:app --reload
```

In a second terminal:
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}

curl http://localhost:8000/api/v1/projects
# Expected: []
```

- [ ] **Step 3: Final commit**

```bash
git add backend/ docker-compose.yml .env.example
git commit -m "feat: backend foundation complete — ingestion, storage, API, WebSocket"
```

---

## Summary

After completing all tasks in this plan, the backend will have:

- ✅ Project CRUD API (`/api/v1/projects`)
- ✅ GitHub URL ingestion (validate → check public → clone → detect languages)
- ✅ ZIP upload ingestion (size limit → zip-slip protection → extract → detect languages)
- ✅ Filesystem-based project storage with `project.json`
- ✅ WebSocket progress endpoint (`/ws/projects/{id}/status`)
- ✅ Full test coverage for all modules
- ✅ Docker-ready

**Next plan:** `2026-03-16-ast-parsing-rdf.md` — Tree-sitter parsers for all 8 languages + OWL ontology + RDF graph builder.
