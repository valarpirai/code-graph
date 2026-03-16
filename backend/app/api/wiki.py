from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from rdflib import Graph

from app.dependencies import get_store
from app.storage.project_store import ProjectStore
from app.wiki.generator import WikiGenerator

router = APIRouter(prefix="/api/v1/projects", tags=["wiki"])


def _get_project_or_404(project_id: str, store: ProjectStore):
    try:
        return store.load(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")


def _get_graph_or_400(project_id: str, store: ProjectStore) -> Graph:
    graph_path = store.graph_path(project_id)
    if not graph_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"graph.ttl not found for project '{project_id}'. Run indexing first.",
        )
    g = Graph()
    g.parse(str(graph_path), format="turtle")
    return g


@router.post("/{project_id}/wiki/generate")
def generate_wiki(project_id: str, store: ProjectStore = Depends(get_store)) -> dict:
    project = _get_project_or_404(project_id, store)
    graph = _get_graph_or_400(project_id, store)

    output_dir = store.wiki_dir(project_id)
    gen = WikiGenerator(project=project, graph=graph, output_dir=output_dir)
    gen.generate()

    md_files = list(output_dir.rglob("*.md"))
    return {
        "message": "Wiki generated successfully",
        "files_generated": len(md_files),
    }


@router.get("/{project_id}/wiki")
def list_wiki(project_id: str, store: ProjectStore = Depends(get_store)) -> list[dict]:
    _get_project_or_404(project_id, store)

    wiki_dir = store.wiki_dir(project_id)
    if not wiki_dir.exists():
        return []

    entries = []
    for md_file in sorted(wiki_dir.rglob("*.md")):
        rel = md_file.relative_to(wiki_dir)
        parts = rel.parts
        file_type = "index" if len(parts) == 1 else parts[0]
        entries.append({
            "path": str(rel),
            "type": file_type,
            "name": md_file.stem,
        })
    return entries


@router.get("/{project_id}/wiki/{file_path:path}", response_class=PlainTextResponse)
def fetch_wiki_file(
    project_id: str,
    file_path: str,
    store: ProjectStore = Depends(get_store),
) -> str:
    _get_project_or_404(project_id, store)

    wiki_dir = store.wiki_dir(project_id)
    target = (wiki_dir / file_path).resolve()

    # Guard against path traversal
    try:
        target.relative_to(wiki_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Wiki file '{file_path}' not found")

    return target.read_text(encoding="utf-8")
