from pathlib import Path
from rdflib import Graph
from .ontology import load_ontology

def load_graph(project_id: str, data_dir: Path) -> Graph:
    g = load_ontology()
    ttl = data_dir / project_id / "graph.ttl"
    if ttl.exists():
        g.parse(str(ttl), format="turtle")
    return g

def save_graph(g: Graph, project_id: str, data_dir: Path) -> None:
    out = data_dir / project_id / "graph.ttl"
    out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(out), format="turtle")
