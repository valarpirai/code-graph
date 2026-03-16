import pytest
from rdflib import Graph, URIRef, Namespace

CG = Namespace("http://codegraph.io/ontology#")

A = URIRef("http://example.org/func/A")
B = URIRef("http://example.org/func/B")
C = URIRef("http://example.org/func/C")
D = URIRef("http://example.org/func/D")


def make_graph(*call_pairs):
    g = Graph()
    for caller, callee in call_pairs:
        g.add((caller, CG.calls, callee))
    return g


def test_single_node_no_calls():
    from app.analysis.execution_flow import trace_execution_flow
    g = Graph()
    result = trace_execution_flow(g, str(A))
    assert result["entry_point"] == str(A)
    assert str(A) in result["nodes"]
    assert result["edges"] == []
    assert result["cycle_edges"] == []


def test_linear_chain():
    from app.analysis.execution_flow import trace_execution_flow
    g = make_graph((A, B), (B, C))
    result = trace_execution_flow(g, str(A))
    assert str(A) in result["nodes"]
    assert str(B) in result["nodes"]
    assert str(C) in result["nodes"]
    assert {"from": str(A), "to": str(B)} in result["edges"]
    assert {"from": str(B), "to": str(C)} in result["edges"]
    assert result["cycle_edges"] == []


def test_cycle_detected():
    from app.analysis.execution_flow import trace_execution_flow
    g = make_graph((A, B), (B, A))
    result = trace_execution_flow(g, str(A))
    assert len(result["cycle_edges"]) >= 1
    cycle = result["cycle_edges"][0]
    assert "from" in cycle and "to" in cycle


def test_diamond_no_cycle():
    from app.analysis.execution_flow import trace_execution_flow
    g = make_graph((A, B), (A, C), (B, D), (C, D))
    result = trace_execution_flow(g, str(A))
    assert str(D) in result["nodes"]
    assert result["cycle_edges"] == []


def test_unknown_entry_point_is_isolated_node():
    from app.analysis.execution_flow import trace_execution_flow
    g = make_graph((A, B))
    result = trace_execution_flow(g, str(D))
    assert result["entry_point"] == str(D)
    assert str(D) in result["nodes"]


def test_nodes_list_has_no_duplicates():
    from app.analysis.execution_flow import trace_execution_flow
    g = make_graph((A, B), (A, C), (B, C))
    result = trace_execution_flow(g, str(A))
    assert len(result["nodes"]) == len(set(result["nodes"]))
