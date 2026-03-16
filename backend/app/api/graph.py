from pathlib import Path
from fastapi import APIRouter, HTTPException
from rdflib import RDF
from app.rdf.graph_store import load_graph
from app.rdf.ontology import CG
from app.config import get_settings

router = APIRouter(prefix="/api/v1/projects", tags=["graph"])


def _get_data_dir() -> Path:
    return Path(get_settings().data_dir)


@router.get("/{project_id}/graph")
def get_graph(project_id: str):
    data_dir = _get_data_dir()
    graph_path = data_dir / project_id / "graph.ttl"
    if not graph_path.exists():
        raise HTTPException(status_code=404, detail={"error": "graph_not_found", "message": "Graph not yet built for this project"})

    g = load_graph(project_id, data_dir)
    nodes, edges = [], []

    for s, _, o in g.triples((None, RDF.type, None)):
        label = str(g.value(s, CG.name) or s)
        node_type = str(o).split("#")[-1]
        # skip ontology class definitions themselves
        if node_type in ("Class", "ObjectProperty", "DatatypeProperty", "Ontology"):
            continue
        nodes.append({"data": {
            "id": str(s),
            "label": label,
            "type": node_type,
            "language": str(g.value(s, CG.language) or ""),
            "file": str(g.value(s, CG.filePath) or ""),
            "line": int(g.value(s, CG.line) or 0),
        }})

    for s, p, o in g:
        if p in (CG.calls, CG.inherits, CG.implements, CG.imports, CG.defines, CG.hasMethod):
            edges.append({"data": {
                "source": str(s),
                "target": str(o),
                "relation": str(p).split("#")[-1],
            }})

    return {"nodes": nodes, "edges": edges}
