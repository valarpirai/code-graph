from pathlib import Path
from rdflib import Graph, Namespace

CG = Namespace("http://codegraph.dev/ontology#")

_ONTOLOGY_PATH = Path(__file__).parent.parent.parent / "ontology.ttl"

def load_ontology() -> Graph:
    g = Graph()
    g.parse(str(_ONTOLOGY_PATH), format="turtle")
    return g
