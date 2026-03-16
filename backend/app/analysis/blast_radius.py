"""
Blast radius analysis.

For a given node URI (function or field):
- direct_callers: functions that directly call it (cg:calls) or reference/assign it
- transitive_callers: all ancestors in the cg:calls DiGraph (cycle-safe via networkx)
- severity: count of unique callers (direct + transitive)
- affected_files: files (cg:definedIn) of all callers
"""
from __future__ import annotations

from rdflib import Graph, URIRef, Namespace
import networkx as nx

from app.analysis.graph_to_networkx import calls_to_digraph

CG = Namespace("http://codegraph.io/ontology#")


def compute_blast_radius(rdf_graph: Graph, node_uri: str) -> dict:
    target = URIRef(node_uri)

    # direct callers via cg:calls
    direct: set[str] = set()
    for caller, _, _ in rdf_graph.triples((None, CG.calls, target)):
        direct.add(str(caller))

    # field accessors via cg:referencedBy / cg:assignedIn
    for _, _, reader in rdf_graph.triples((target, CG.referencedBy, None)):
        direct.add(str(reader))
    for _, _, writer in rdf_graph.triples((target, CG.assignedIn, None)):
        direct.add(str(writer))

    # transitive callers via networkx ancestors on cg:calls digraph
    dg = calls_to_digraph(rdf_graph)
    transitive: set[str] = set()
    if node_uri in dg:
        transitive = nx.ancestors(dg, node_uri)
    transitive_only = transitive - direct

    # affected files
    all_callers = direct | transitive_only
    affected_files: set[str] = set()
    for caller_uri in all_callers:
        for _, _, file_uri in rdf_graph.triples((URIRef(caller_uri), CG.definedIn, None)):
            affected_files.add(str(file_uri))

    severity = len(all_callers)

    return {
        "target_node": node_uri,
        "direct_callers": sorted(direct),
        "transitive_callers": sorted(transitive_only),
        "severity": severity,
        "affected_files": sorted(affected_files),
    }
