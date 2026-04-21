from pathlib import Path
from functools import lru_cache
from rdflib import Graph
from .ontology import load_ontology


@lru_cache(maxsize=16)
def _load_cached(project_id: str, mtime_ns: int, data_dir_str: str) -> Graph:
    g = load_ontology()
    ttl = Path(data_dir_str) / project_id / "graph.ttl"
    g.parse(str(ttl), format="turtle")
    return g


def load_graph(project_id: str, data_dir: Path) -> Graph:
    ttl = data_dir / project_id / "graph.ttl"
    if not ttl.exists():
        return load_ontology()
    mtime_ns = ttl.stat().st_mtime_ns
    return _load_cached(project_id, mtime_ns, str(data_dir))


def save_graph(g: Graph, project_id: str, data_dir: Path) -> None:
    out = data_dir / project_id / "graph.ttl"
    out.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(out), format="turtle")
    _load_cached.cache_clear()
