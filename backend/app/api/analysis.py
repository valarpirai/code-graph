"""
FastAPI router for analysis endpoints.

All endpoints load the project's rdflib Graph via get_project_graph(),
then delegate to the appropriate analysis module.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from rdflib import Graph

from app.analysis.blast_radius import compute_blast_radius
from app.analysis.execution_flow import trace_execution_flow
from app.analysis.clustering import compute_clusters

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["analysis"])


def get_project_graph(project_id: str) -> Graph:
    """
    Load the rdflib Graph for a project from disk.
    Raises HTTPException 404 if graph.ttl doesn't exist yet.
    Patched in tests.
    """
    from app.config import get_settings
    from app.rdf.graph_store import load_graph
    data_dir = Path(get_settings().data_dir)
    graph_path = data_dir / project_id / "graph.ttl"
    if not graph_path.exists():
        raise HTTPException(
            status_code=404,
            detail={"error": "graph_not_found", "message": "Graph not yet built for this project"},
        )
    return load_graph(project_id, data_dir)


@router.get("/blast-radius")
def blast_radius(
    project_id: str,
    node_uri: str = Query(..., description="URI of the function or field to analyse"),
):
    graph = get_project_graph(project_id)
    return compute_blast_radius(graph, node_uri)


@router.get("/execution-flow")
def execution_flow(
    project_id: str,
    node_uri: str = Query(..., description="URI of the entry-point function"),
):
    graph = get_project_graph(project_id)
    return trace_execution_flow(graph, node_uri)


@router.get("/clusters")
def clusters(project_id: str):
    graph = get_project_graph(project_id)
    return compute_clusters(graph)


class SparqlRequest(BaseModel):
    query: str


@router.post("/sparql")
def sparql_query(project_id: str, body: SparqlRequest):
    graph = get_project_graph(project_id)
    try:
        results = graph.query(body.query)
    except Exception as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "sparql_error", "message": str(exc)},
        )
    columns = [str(v) for v in results.vars] if results.vars else []
    rows = [
        [str(cell) if cell is not None else None for cell in row]
        for row in results
    ]
    return {"columns": columns, "rows": rows}
