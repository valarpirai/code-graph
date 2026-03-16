"""
Execution flow tracing.

Follows cg:calls transitively from an entry-point function using
networkx depth-first search. Detects back-edges (cycles) and marks them.
"""
from __future__ import annotations

from rdflib import Graph
import networkx as nx

from app.analysis.graph_to_networkx import calls_to_digraph


def trace_execution_flow(rdf_graph: Graph, entry_point_uri: str) -> dict:
    dg = calls_to_digraph(rdf_graph)

    # Ensure the entry point is represented even if it has no edges
    if entry_point_uri not in dg:
        dg.add_node(entry_point_uri)

    visited_nodes: list[str] = []
    tree_edges: list[dict] = []
    cycle_edges: list[dict] = []

    visited_set: set[str] = set()
    # Track the current DFS stack to distinguish back-edges (cycles) from
    # cross/forward edges (diamonds). A "nontree" edge u->v is a back-edge
    # only when v is still on the active DFS stack.
    dfs_stack: set[str] = set()

    for u, v, direction in nx.dfs_labeled_edges(dg, source=entry_point_uri):
        if direction == "forward":
            if u == v:
                # Root self-loop emitted by dfs_labeled_edges for the source node
                if u not in visited_set:
                    visited_set.add(u)
                    visited_nodes.append(u)
                dfs_stack.add(u)
            else:
                # Tree edge: u -> v where v is newly discovered
                if v not in visited_set:
                    visited_set.add(v)
                    visited_nodes.append(v)
                dfs_stack.add(v)
                tree_edges.append({"from": u, "to": v})
        elif direction == "reverse":
            # Node is leaving the DFS stack
            dfs_stack.discard(v)
        elif direction == "nontree":
            # Only report as cycle if v is still on the active stack (back-edge)
            if v in dfs_stack:
                cycle_edges.append({"from": u, "to": v})

    return {
        "entry_point": entry_point_uri,
        "nodes": visited_nodes,
        "edges": tree_edges,
        "cycle_edges": cycle_edges,
    }
