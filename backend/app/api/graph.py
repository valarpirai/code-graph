from pathlib import Path
from fastapi import APIRouter, HTTPException
from rdflib import RDF
from rdflib.namespace import OWL, RDFS
from app.rdf.graph_store import load_graph
from app.rdf.ontology import CG
from app.config import get_settings

# OWL/RDFS metaclasses — triples where these are the *object* of rdf:type
# describe ontology structure, not code entities, and must be skipped.
_OWL_META = {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.Ontology, RDFS.Class}

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

    node_ids: set[str] = set()
    for s, _, o in g.triples((None, RDF.type, None)):
        if o in _OWL_META:
            continue
        raw_label = g.value(s, CG.name)
        if raw_label:
            label = str(raw_label)
        else:
            # File nodes: show just the filename, not the full path
            fp = g.value(s, CG.filePath)
            if fp:
                label = str(fp).rstrip("/").split("/")[-1]
            else:
                label = str(s).rstrip("/").split("/")[-1]
        node_type = str(o).split("#")[-1]
        node_id = str(s)
        node_ids.add(node_id)
        data: dict = {
            "id": node_id,
            "label": label,
            "node_type": node_type,
        }
        # optional scalar properties — only emit non-empty values
        def _str(pred):  # noqa: E306
            v = g.value(s, pred)
            return str(v) if v is not None else None
        def _int(pred):  # noqa: E306
            v = g.value(s, pred)
            return int(v) if v is not None else None
        def _float(pred):  # noqa: E306
            v = g.value(s, pred)
            return round(float(v), 3) if v is not None else None
        def _bool(pred):  # noqa: E306
            v = g.value(s, pred)
            return bool(v) if v is not None else None

        if node_type == "ExternalSymbol":
            caller_count = sum(1 for _ in g.triples((None, CG.calls, s)))
            if caller_count:
                data["caller_count"] = caller_count

        for key, val in [
            ("file_path",        _str(CG.filePath)),
            ("language",         _str(CG.language)),
            ("line",             _int(CG.line)),
            ("qualified_name",   _str(CG.qualifiedName)),
            ("visibility",       _str(CG.visibility)),
            ("is_exported",      _bool(CG.isExported)),
            ("entry_point_score", _float(CG.entryPointScore)),
            ("framework_role",   _str(CG.frameworkRole)),
            ("value",            _str(CG.value)),
            ("class_kind",       _str(CG.classKind)),
            ("data_type",        _str(CG.dataType)),
            ("is_test",          _bool(CG.isTest)),
            ("is_abstract",      _bool(CG.isAbstract)),
            ("line_count",       _int(CG.lineCount)),
            ("file_size",        _int(CG.fileSize)),
        ]:
            if val is not None and val != "" and val is not False:
                data[key] = val
        nodes.append({"data": data})

    for s, p, o in g:
        if p in (CG.calls, CG.inherits, CG.implements, CG.mixes, CG.imports, CG.defines, CG.hasMethod, CG.hasField, CG.hasParameter, CG.containsFile, CG.containsClass):
            src, tgt = str(s), str(o)
            if src in node_ids and tgt in node_ids:
                edges.append({"data": {
                    "source": src,
                    "target": tgt,
                    "relation": str(p).split("#")[-1],
                }})

    return {"nodes": nodes, "edges": edges}
