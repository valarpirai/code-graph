"""
Functional clustering via Louvain community detection.

Converts the cg:calls DiGraph to undirected (required by python-louvain),
runs best_partition(), computes a cohesion score per cluster.
"""
from __future__ import annotations

from rdflib import Graph
import networkx as nx
import community as community_louvain  # python-louvain

from app.analysis.graph_to_networkx import calls_to_digraph


def _cohesion(undirected: nx.Graph, nodes: list[str]) -> float:
    """Cohesion = internal_edges / total_degree_of_cluster_nodes."""
    node_set = set(nodes)
    internal = sum(
        1 for u, v in undirected.edges(nodes) if u in node_set and v in node_set
    )
    total_count = sum(d for _, d in undirected.degree(nodes))
    if total_count == 0:
        return 0.0
    return internal / total_count


def compute_clusters(rdf_graph: Graph) -> dict:
    dg = calls_to_digraph(rdf_graph)

    if dg.number_of_nodes() == 0:
        return {"clusters": []}

    ug: nx.Graph = dg.to_undirected()

    partition: dict[str, int] = community_louvain.best_partition(ug)

    groups: dict[int, list[str]] = {}
    for node, comm_id in partition.items():
        groups.setdefault(comm_id, []).append(node)

    clusters = []
    for comm_id, nodes in groups.items():
        cohesion = _cohesion(ug, nodes)
        clusters.append({
            "id": comm_id,
            "nodes": sorted(nodes),
            "cohesion": round(cohesion, 4),
        })

    clusters.sort(key=lambda c: c["id"])
    return {"clusters": clusters}
