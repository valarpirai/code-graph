# app/api/projects.py
import asyncio
import uuid
import io
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from app.dependencies import get_store
from app.storage.project_store import ProjectStore
from app.models.project import ProjectMeta, ProjectStatus, ProjectCreate
from app.indexer import Indexer
from app.ws.indexing import notifier, IndexingEvent
from app.ingestion.github import (
    validate_github_url, check_repo_public, clone_repo,
    GitHubURLError, RepoNotAccessibleError, GitHubAPIUnavailableError,
)
from app.ingestion.zip_handler import extract_zip, ZipTooLargeError, InvalidZipError, ZipSlipError
from app.ingestion.language_detector import detect_languages

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])
MAX_ZIP_BYTES = 200 * 1024 * 1024


async def _run_indexing(project_id: str, source_dir: Path, store: ProjectStore) -> None:
    """Run the indexer in the background and update project status."""
    async def _notify(msg: dict) -> None:
        if msg.get("type") == "progress":
            total = msg.get("total", 1) or 1
            progress = msg.get("current", 0) / total
            event = IndexingEvent(status="indexing", progress=progress, message=f"Parsing {msg.get('file', '')}")
        elif msg.get("type") == "done":
            event = IndexingEvent(status="done", progress=1.0, message=f"Indexed {msg.get('triples', 0)} triples")
        else:
            return
        await notifier.notify(project_id, event)

    try:
        await Indexer().run(project_id, source_dir, store.data_dir, notifier=_notify)
        store.update_status(project_id, ProjectStatus.READY)
    except Exception as e:
        store.update_status(project_id, ProjectStatus.ERROR, error_message=str(e))
        await notifier.notify(project_id, IndexingEvent(status="error", progress=0.0, message=str(e)))


@router.get("", response_model=list[ProjectMeta])
def list_projects(store: ProjectStore = Depends(get_store)):
    return store.list_all()


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
    except (InvalidZipError, ZipSlipError) as e:
        store.update_status(project_id, ProjectStatus.ERROR, error_message=str(e))
        raise HTTPException(status_code=422, detail={"error": "invalid_zip", "message": str(e)})
    except Exception as e:
        store.update_status(project_id, ProjectStatus.ERROR, error_message=str(e))
        return store.load(project_id)

    asyncio.create_task(_run_indexing(project_id, source_dir, store))
    return store.load(project_id)


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

    # Return existing project if same URL was already indexed
    for existing in store.list_all():
        if existing.source == payload.github_url:
            return existing

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
    except Exception as e:
        store.update_status(project_id, ProjectStatus.ERROR, error_message=str(e))
        return store.load(project_id)

    asyncio.create_task(_run_indexing(project_id, source_dir, store))
    return store.load(project_id)


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


@router.post("/{project_id}/reindex", response_model=ProjectMeta)
async def reindex_project(project_id: str, store: ProjectStore = Depends(get_store)):
    try:
        store.load(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Project not found"})

    wiki_dir = store.wiki_dir(project_id)
    if wiki_dir.exists():
        shutil.rmtree(wiki_dir)

    store.update_status(project_id, ProjectStatus.INDEXING)
    source_dir = store.source_dir(project_id)
    asyncio.create_task(_run_indexing(project_id, source_dir, store))
    return store.load(project_id)
