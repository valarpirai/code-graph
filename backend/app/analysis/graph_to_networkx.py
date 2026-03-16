"""Convert an rdflib Graph's cg:calls triples into a networkx DiGraph."""
from rdflib import Graph, Namespace
import networkx as nx

CG = Namespace("http://codegraph.io/ontology#")


def calls_to_digraph(rdf_graph: Graph) -> nx.DiGraph:
    """
    Extract all (subject, cg:calls, object) triples from rdf_graph and
    return them as a networkx DiGraph where nodes are URI strings.
    """
    dg = nx.DiGraph()
    for s, _p, o in rdf_graph.triples((None, CG.calls, None)):
        dg.add_edge(str(s), str(o))
    return dg
