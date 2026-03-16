import pytest
from rdflib import Graph, URIRef, Namespace

CG = Namespace("http://codegraph.io/ontology#")

ENTRY   = URIRef("http://example.org/func/entry")
CALLER1 = URIRef("http://example.org/func/caller1")
CALLER2 = URIRef("http://example.org/func/caller2")
TARGET  = URIRef("http://example.org/func/target")
FIELD   = URIRef("http://example.org/field/f1")
READER  = URIRef("http://example.org/func/reader")
WRITER  = URIRef("http://example.org/func/writer")

FILE_A = URIRef("http://example.org/file/a.py")
FILE_B = URIRef("http://example.org/file/b.py")


def make_graph(*triples):
    g = Graph()
    for s, p, o in triples:
        g.add((s, p, o))
    return g


def test_no_callers_returns_empty():
    from app.analysis.blast_radius import compute_blast_radius
    g = make_graph()
    result = compute_blast_radius(g, str(TARGET))
    assert result["target_node"] == str(TARGET)
    assert result["direct_callers"] == []
    assert result["transitive_callers"] == []
    assert result["severity"] == 0
    assert result["affected_files"] == []


def test_direct_caller_only():
    from app.analysis.blast_radius import compute_blast_radius
    g = make_graph((CALLER1, CG.calls, TARGET))
    result = compute_blast_radius(g, str(TARGET))
    assert str(CALLER1) in result["direct_callers"]
    assert result["severity"] == 1


def test_transitive_callers():
    from app.analysis.blast_radius import compute_blast_radius
    g = make_graph(
        (ENTRY, CG.calls, CALLER1),
        (CALLER1, CG.calls, TARGET),
    )
    result = compute_blast_radius(g, str(TARGET))
    assert str(CALLER1) in result["direct_callers"]
    assert str(ENTRY) in result["transitive_callers"]
    assert result["severity"] == 2


def test_field_readers_and_writers():
    from app.analysis.blast_radius import compute_blast_radius
    g = make_graph(
        (FIELD, CG.referencedBy, READER),
        (FIELD, CG.assignedIn, WRITER),
    )
    result = compute_blast_radius(g, str(FIELD))
    assert str(READER) in result["direct_callers"]
    assert str(WRITER) in result["direct_callers"]


def test_affected_files_grouped():
    from app.analysis.blast_radius import compute_blast_radius
    g = make_graph(
        (CALLER1, CG.calls, TARGET),
        (CALLER1, CG.definedIn, FILE_A),
        (CALLER2, CG.calls, TARGET),
        (CALLER2, CG.definedIn, FILE_B),
    )
    result = compute_blast_radius(g, str(TARGET))
    assert str(FILE_A) in result["affected_files"]
    assert str(FILE_B) in result["affected_files"]


def test_cycle_safe_severity():
    from app.analysis.blast_radius import compute_blast_radius
    g = make_graph(
        (CALLER1, CG.calls, TARGET),
        (CALLER2, CG.calls, CALLER1),
        (CALLER2, CG.calls, TARGET),
    )
    result = compute_blast_radius(g, str(TARGET))
    all_callers = set(result["direct_callers"]) | set(result["transitive_callers"])
    assert result["severity"] == len(all_callers)


def test_cycle_in_call_graph_does_not_hang():
    from app.analysis.blast_radius import compute_blast_radius
    g = make_graph(
        (CALLER1, CG.calls, CALLER2),
        (CALLER2, CG.calls, CALLER1),
        (CALLER1, CG.calls, TARGET),
    )
    result = compute_blast_radius(g, str(TARGET))
    assert result["severity"] >= 1
