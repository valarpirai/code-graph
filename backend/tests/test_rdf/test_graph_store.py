from rdflib import Graph, URIRef, RDF
from app.rdf.ontology import CG
from app.rdf.graph_store import save_graph, load_graph

def test_round_trip(tmp_path):
    g = Graph()
    node = URIRef("http://example.com/fn/foo")
    g.add((node, RDF.type, CG.Function))
    g.add((node, CG.name, __import__('rdflib').Literal("foo")))
    save_graph(g, "proj1", tmp_path)
    g2 = load_graph("proj1", tmp_path)
    assert (node, RDF.type, CG.Function) in g2
    assert (node, CG.name, __import__('rdflib').Literal("foo")) in g2

def test_load_graph_no_file(tmp_path):
    # Should return ontology-only graph without error
    g = load_graph("missing-proj", tmp_path)
    assert len(g) > 0  # has ontology triples
