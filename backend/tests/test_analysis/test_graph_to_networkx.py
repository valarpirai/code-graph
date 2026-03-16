import pytest
import networkx as nx
from rdflib import Graph, URIRef, Namespace

CG = Namespace("http://codegraph.io/ontology#")

A = URIRef("http://example.org/func/A")
B = URIRef("http://example.org/func/B")
C = URIRef("http://example.org/func/C")


def make_calls_graph(*call_pairs):
    g = Graph()
    for caller, callee in call_pairs:
        g.add((caller, CG.calls, callee))
    return g


def test_empty_graph_returns_empty_digraph():
    from app.analysis.graph_to_networkx import calls_to_digraph
    g = Graph()
    dg = calls_to_digraph(g)
    assert isinstance(dg, nx.DiGraph)
    assert dg.number_of_nodes() == 0
    assert dg.number_of_edges() == 0


def test_single_edge():
    from app.analysis.graph_to_networkx import calls_to_digraph
    g = make_calls_graph((A, B))
    dg = calls_to_digraph(g)
    assert dg.number_of_nodes() == 2
    assert dg.number_of_edges() == 1
    assert dg.has_edge(str(A), str(B))


def test_chain_a_calls_b_calls_c():
    from app.analysis.graph_to_networkx import calls_to_digraph
    g = make_calls_graph((A, B), (B, C))
    dg = calls_to_digraph(g)
    assert dg.number_of_nodes() == 3
    assert dg.has_edge(str(A), str(B))
    assert dg.has_edge(str(B), str(C))
    assert not dg.has_edge(str(A), str(C))


def test_cycle_preserved():
    from app.analysis.graph_to_networkx import calls_to_digraph
    g = make_calls_graph((A, B), (B, A))
    dg = calls_to_digraph(g)
    assert dg.has_edge(str(A), str(B))
    assert dg.has_edge(str(B), str(A))


def test_node_uris_are_strings():
    from app.analysis.graph_to_networkx import calls_to_digraph
    g = make_calls_graph((A, B))
    dg = calls_to_digraph(g)
    for node in dg.nodes():
        assert isinstance(node, str)
