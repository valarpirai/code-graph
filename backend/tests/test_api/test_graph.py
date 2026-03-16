import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from rdflib import Graph, URIRef, Literal, RDF
from app.main import app
from app.rdf.ontology import CG


def make_test_graph() -> Graph:
    g = Graph()
    fn_uri = URIRef("http://codegraph.dev/node/proj1/function/pkg.main")
    g.add((fn_uri, RDF.type, CG.Function))
    g.add((fn_uri, CG.name, Literal("main")))
    g.add((fn_uri, CG.line, Literal(1)))
    return g


@pytest.mark.asyncio
async def test_get_graph_returns_nodes_and_edges(tmp_path):
    # Create a graph.ttl so the endpoint doesn't 404
    graph_dir = tmp_path / "proj1"
    graph_dir.mkdir()
    g = make_test_graph()
    g.serialize(destination=str(graph_dir / "graph.ttl"), format="turtle")

    with patch("app.api.graph._get_data_dir", return_value=tmp_path):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/projects/proj1/graph")

    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert any(n["data"]["label"] == "main" for n in data["nodes"])


@pytest.mark.asyncio
async def test_get_graph_not_found(tmp_path):
    with patch("app.api.graph._get_data_dir", return_value=tmp_path):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/projects/no-such-proj/graph")

    assert resp.status_code == 404
