"""HTTP-level tests for analysis endpoints.

These tests patch get_project_graph() to return a small inline rdflib Graph,
so no real project on disk is needed.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from rdflib import Graph, URIRef, Namespace

CG = Namespace("http://codegraph.io/ontology#")

PROJECT_ID = "test-proj-001"

A = URIRef("http://example.org/func/A")
B = URIRef("http://example.org/func/B")
C = URIRef("http://example.org/func/C")


def make_test_graph():
    g = Graph()
    g.add((A, CG.calls, B))
    g.add((B, CG.calls, C))
    return g


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def patch_graph():
    with patch("app.api.analysis.get_project_graph", return_value=make_test_graph()):
        yield


def test_blast_radius_200(client):
    resp = client.get(
        f"/api/v1/projects/{PROJECT_ID}/blast-radius",
        params={"node_uri": str(B)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["target_node"] == str(B)
    assert "direct_callers" in body
    assert "transitive_callers" in body
    assert "severity" in body
    assert "affected_files" in body


def test_blast_radius_missing_node_uri_422(client):
    resp = client.get(f"/api/v1/projects/{PROJECT_ID}/blast-radius")
    assert resp.status_code == 422


def test_execution_flow_200(client):
    resp = client.get(
        f"/api/v1/projects/{PROJECT_ID}/execution-flow",
        params={"node_uri": str(A)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["entry_point"] == str(A)
    assert "nodes" in body
    assert "edges" in body
    assert "cycle_edges" in body


def test_execution_flow_missing_node_uri_422(client):
    resp = client.get(f"/api/v1/projects/{PROJECT_ID}/execution-flow")
    assert resp.status_code == 422


def test_clusters_200(client):
    resp = client.get(f"/api/v1/projects/{PROJECT_ID}/clusters")
    assert resp.status_code == 200
    body = resp.json()
    assert "clusters" in body
    assert isinstance(body["clusters"], list)


def test_sparql_valid_query(client):
    query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5"
    resp = client.post(
        f"/api/v1/projects/{PROJECT_ID}/sparql",
        json={"query": query},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "columns" in body
    assert "rows" in body
    assert isinstance(body["rows"], list)


def test_sparql_invalid_query_returns_422(client):
    resp = client.post(
        f"/api/v1/projects/{PROJECT_ID}/sparql",
        json={"query": "THIS IS NOT SPARQL !!!"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body.get("error") == "sparql_error"
    assert "message" in body


def test_sparql_missing_body_returns_422(client):
    resp = client.post(f"/api/v1/projects/{PROJECT_ID}/sparql", json={})
    assert resp.status_code == 422
