from rdflib import RDF
from app.rdf.ontology import CG, load_ontology

def test_cg_namespace_resolves():
    assert str(CG.Function) == "http://codegraph.dev/ontology#Function"
    assert str(CG.calls) == "http://codegraph.dev/ontology#calls"

def test_load_ontology_parses():
    g = load_ontology()
    assert len(g) > 0

def test_ontology_has_function_class():
    g = load_ontology()
    from rdflib import OWL
    assert (CG.Function, RDF.type, OWL.Class) in g

def test_ontology_has_calls_property():
    g = load_ontology()
    from rdflib import OWL
    assert (CG.calls, RDF.type, OWL.ObjectProperty) in g
