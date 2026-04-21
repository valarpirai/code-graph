import pytest
from rdflib import Graph, URIRef, Namespace

CG = Namespace("http://codegraph.dev/ontology#")

A = URIRef("http://example.org/func/A")
B = URIRef("http://example.org/func/B")
C = URIRef("http://example.org/func/C")
D = URIRef("http://example.org/func/D")
E = URIRef("http://example.org/func/E")
F = URIRef("http://example.org/func/F")


def make_graph(*call_pairs):
    g = Graph()
    for caller, callee in call_pairs:
        g.add((caller, CG.calls, callee))
    return g


def test_empty_graph_returns_empty_clusters():
    from app.analysis.clustering import compute_clusters
    g = Graph()
    result = compute_clusters(g)
    assert result["clusters"] == []


def test_single_node_isolated():
    from app.analysis.clustering import compute_clusters
    g = Graph()
    g.add((A, CG.calls, A))
    result = compute_clusters(g)
    assert len(result["clusters"]) >= 1
    all_nodes = [n for c in result["clusters"] for n in c["nodes"]]
    assert str(A) in all_nodes


def test_two_disconnected_components_form_separate_clusters():
    from app.analysis.clustering import compute_clusters
    g = make_graph(
        (A, B), (B, A), (B, C), (C, B), (A, C), (C, A),
        (D, E), (E, D), (E, F), (F, E), (D, F), (F, D),
    )
    result = compute_clusters(g)
    assert len(result["clusters"]) >= 2


def test_cluster_result_structure():
    from app.analysis.clustering import compute_clusters
    g = make_graph((A, B), (B, C))
    result = compute_clusters(g)
    assert "clusters" in result
    for cluster in result["clusters"]:
        assert "id" in cluster
        assert "nodes" in cluster
        assert "cohesion" in cluster
        assert isinstance(cluster["nodes"], list)
        assert 0.0 <= cluster["cohesion"] <= 1.0


def test_all_nodes_assigned_to_a_cluster():
    from app.analysis.clustering import compute_clusters
    g = make_graph((A, B), (B, C), (C, D))
    result = compute_clusters(g)
    all_nodes = {n for c in result["clusters"] for n in c["nodes"]}
    assert str(A) in all_nodes
    assert str(B) in all_nodes
    assert str(C) in all_nodes
    assert str(D) in all_nodes


def test_cohesion_is_between_0_and_1():
    from app.analysis.clustering import compute_clusters
    g = make_graph((A, B), (B, C), (C, A), (D, E))
    result = compute_clusters(g)
    for cluster in result["clusters"]:
        assert 0.0 <= cluster["cohesion"] <= 1.0
