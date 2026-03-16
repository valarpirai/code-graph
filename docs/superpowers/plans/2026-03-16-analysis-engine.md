# Analysis Engine Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add blast radius analysis, execution flow tracing, functional clustering, and a SPARQL query panel on top of the RDF graph built in Plan 2.

**Architecture:** A shared `graph_to_networkx` converter turns the rdflib `cg:calls` subgraph into a networkx DiGraph; all three graph-analysis modules (`blast_radius`, `execution_flow`, `clustering`) import it. A single FastAPI router in `app/api/analysis.py` exposes four endpoints and is registered in `main.py`. No new persistence layer — analysis is always recomputed from the in-memory/on-disk RDF graph.

**Tech Stack:** Python 3.11+, rdflib, networkx, python-louvain (`community`), FastAPI, pytest

---

## Chunk 1: graph_to_networkx Converter + Blast Radius Module + Tests

### File Map

```
backend/
  app/
    analysis/
      __init__.py
      graph_to_networkx.py
      blast_radius.py
  tests/
    test_analysis/
      __init__.py
      test_graph_to_networkx.py
      test_blast_radius.py
```

---

### Task 1.1: Add `python-louvain` and `networkx` to dependencies

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add dependencies**

Open `backend/pyproject.toml` and add the following entries to the `dependencies` list:

```toml
"networkx>=3.3",
"python-louvain>=0.16",
```

- [ ] **Step 2: Install**

```bash
cd backend
pip install -e ".[dev]"
```

Expected output: both `networkx` and `python-louvain` installed without errors.

---

### Task 1.2: Write failing tests for `graph_to_networkx`

**Files:**
- Create: `backend/app/analysis/__init__.py`
- Create: `backend/tests/test_analysis/__init__.py`
- Create: `backend/tests/test_analysis/test_graph_to_networkx.py`

- [ ] **Step 1: Create `__init__.py` stubs**

`backend/app/analysis/__init__.py` — empty file.

`backend/tests/test_analysis/__init__.py` — empty file.

- [ ] **Step 2: Write test file**

`backend/tests/test_analysis/test_graph_to_networkx.py`:

```python
import pytest
import networkx as nx
from rdflib import Graph, URIRef, Namespace

CG = Namespace("http://codegraph.io/ontology#")

A = URIRef("http://example.org/func/A")
B = URIRef("http://example.org/func/B")
C = URIRef("http://example.org/func/C")


def make_calls_graph(*call_pairs):
    """Build an rdflib Graph with cg:calls triples from (caller, callee) pairs."""
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
```

- [ ] **Step 3: Run tests — expect failures**

```bash
cd backend
pytest tests/test_analysis/test_graph_to_networkx.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `app.analysis.graph_to_networkx`.

---

### Task 1.3: Implement `graph_to_networkx.py`

**Files:**
- Create: `backend/app/analysis/graph_to_networkx.py`

- [ ] **Step 1: Write implementation**

`backend/app/analysis/graph_to_networkx.py`:

```python
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
```

- [ ] **Step 2: Run tests — expect all pass**

```bash
cd backend
pytest tests/test_analysis/test_graph_to_networkx.py -v
```

Expected output (all 5 pass):
```
PASSED tests/test_analysis/test_graph_to_networkx.py::test_empty_graph_returns_empty_digraph
PASSED tests/test_analysis/test_graph_to_networkx.py::test_single_edge
PASSED tests/test_analysis/test_graph_to_networkx.py::test_chain_a_calls_b_calls_c
PASSED tests/test_analysis/test_graph_to_networkx.py::test_cycle_preserved
PASSED tests/test_analysis/test_graph_to_networkx.py::test_node_uris_are_strings
```

---

### Task 1.4: Write failing tests for `blast_radius`

**Files:**
- Create: `backend/tests/test_analysis/test_blast_radius.py`

- [ ] **Step 1: Write test file**

`backend/tests/test_analysis/test_blast_radius.py`:

```python
import pytest
from rdflib import Graph, URIRef, Namespace

CG = Namespace("http://codegraph.io/ontology#")

# URI fixtures
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
    g = make_graph(
        (CALLER1, CG.calls, TARGET),
    )
    result = compute_blast_radius(g, str(TARGET))
    assert str(CALLER1) in result["direct_callers"]
    assert result["severity"] == 1


def test_transitive_callers():
    from app.analysis.blast_radius import compute_blast_radius
    # ENTRY -> CALLER1 -> TARGET
    g = make_graph(
        (ENTRY, CG.calls, CALLER1),
        (CALLER1, CG.calls, TARGET),
    )
    result = compute_blast_radius(g, str(TARGET))
    assert str(CALLER1) in result["direct_callers"]
    assert str(ENTRY) in result["transitive_callers"]
    assert result["severity"] == 2  # CALLER1 + ENTRY


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
    # A -> B -> TARGET, A -> TARGET  (A and B form no cycle, but TARGET is reached twice)
    g = make_graph(
        (CALLER1, CG.calls, TARGET),
        (CALLER2, CG.calls, CALLER1),
        (CALLER2, CG.calls, TARGET),
    )
    result = compute_blast_radius(g, str(TARGET))
    # severity = unique transitive callers count, not path count
    all_callers = set(result["direct_callers"]) | set(result["transitive_callers"])
    assert result["severity"] == len(all_callers)


def test_cycle_in_call_graph_does_not_hang():
    from app.analysis.blast_radius import compute_blast_radius
    # A -> B -> A (cycle), both call TARGET
    g = make_graph(
        (CALLER1, CG.calls, CALLER2),
        (CALLER2, CG.calls, CALLER1),
        (CALLER1, CG.calls, TARGET),
    )
    # must return without infinite loop
    result = compute_blast_radius(g, str(TARGET))
    assert result["severity"] >= 1
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd backend
pytest tests/test_analysis/test_blast_radius.py -v
```

Expected: `ImportError` for `app.analysis.blast_radius`.

---

### Task 1.5: Implement `blast_radius.py`

**Files:**
- Create: `backend/app/analysis/blast_radius.py`

- [ ] **Step 1: Write implementation**

`backend/app/analysis/blast_radius.py`:

```python
"""
Blast radius analysis.

For a given node URI (function or field):
- direct_callers: functions that directly call it (cg:calls) or reference/assign it
                  (cg:referencedBy / cg:assignedIn)
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

    # --- direct callers via cg:calls ---
    direct: set[str] = set()
    for caller, _, _ in rdf_graph.triples((None, CG.calls, target)):
        direct.add(str(caller))

    # --- field accessors via cg:referencedBy / cg:assignedIn ---
    for _, _, reader in rdf_graph.triples((target, CG.referencedBy, None)):
        direct.add(str(reader))
    for _, _, writer in rdf_graph.triples((target, CG.assignedIn, None)):
        direct.add(str(writer))

    # --- transitive callers via networkx ancestors on cg:calls digraph ---
    dg = calls_to_digraph(rdf_graph)
    transitive: set[str] = set()
    if node_uri in dg:
        transitive = nx.ancestors(dg, node_uri)
    # transitive includes direct callers; remove them to separate the two sets
    transitive_only = transitive - direct

    # --- affected files ---
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
```

- [ ] **Step 2: Run tests — expect all pass**

```bash
cd backend
pytest tests/test_analysis/test_blast_radius.py -v
```

Expected output (all 7 pass):
```
PASSED tests/test_analysis/test_blast_radius.py::test_no_callers_returns_empty
PASSED tests/test_analysis/test_blast_radius.py::test_direct_caller_only
PASSED tests/test_analysis/test_blast_radius.py::test_transitive_callers
PASSED tests/test_analysis/test_blast_radius.py::test_field_readers_and_writers
PASSED tests/test_analysis/test_blast_radius.py::test_affected_files_grouped
PASSED tests/test_analysis/test_blast_radius.py::test_cycle_safe_severity
PASSED tests/test_analysis/test_blast_radius.py::test_cycle_in_call_graph_does_not_hang
```

---

### Task 1.6: Commit Chunk 1

- [ ] **Step 1: Stage and commit**

```bash
cd backend
git add app/analysis/__init__.py app/analysis/graph_to_networkx.py app/analysis/blast_radius.py \
        tests/test_analysis/__init__.py tests/test_analysis/test_graph_to_networkx.py \
        tests/test_analysis/test_blast_radius.py pyproject.toml
git commit -m "feat(analysis): graph_to_networkx converter and blast radius module"
```

---

## Chunk 2: Execution Flow + Clustering Modules + Tests

### File Map

```
backend/
  app/
    analysis/
      execution_flow.py
      clustering.py
  tests/
    test_analysis/
      test_execution_flow.py
      test_clustering.py
```

---

### Task 2.1: Write failing tests for `execution_flow`

**Files:**
- Create: `backend/tests/test_analysis/test_execution_flow.py`

- [ ] **Step 1: Write test file**

`backend/tests/test_analysis/test_execution_flow.py`:

```python
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
    # A -> B -> C
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
    # A -> B -> A (cycle)
    g = make_graph((A, B), (B, A))
    result = trace_execution_flow(g, str(A))
    assert len(result["cycle_edges"]) >= 1
    cycle = result["cycle_edges"][0]
    assert "from" in cycle and "to" in cycle


def test_diamond_no_cycle():
    from app.analysis.execution_flow import trace_execution_flow
    # A -> B, A -> C, B -> D, C -> D
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
    # A -> B, A -> C, B -> C (C reachable via two paths)
    g = make_graph((A, B), (A, C), (B, C))
    result = trace_execution_flow(g, str(A))
    assert len(result["nodes"]) == len(set(result["nodes"]))
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd backend
pytest tests/test_analysis/test_execution_flow.py -v
```

Expected: `ImportError` for `app.analysis.execution_flow`.

---

### Task 2.2: Implement `execution_flow.py`

**Files:**
- Create: `backend/app/analysis/execution_flow.py`

- [ ] **Step 1: Write implementation**

`backend/app/analysis/execution_flow.py`:

```python
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

    # DFS from entry point only — restrict to nodes reachable from it
    # nx.dfs_labeled_edges yields (u, v, direction) where direction in
    # {"forward", "nontree", "reverse"}
    visited_set: set[str] = set()

    for u, v, direction in nx.dfs_labeled_edges(dg, source=entry_point_uri):
        if direction == "forward":
            if u not in visited_set:
                visited_set.add(u)
                visited_nodes.append(u)
            if u != v:  # skip the self-loop dfs emits for the root
                tree_edges.append({"from": u, "to": v})
        elif direction == "nontree":
            # back-edge or cross-edge — treat as cycle marker
            cycle_edges.append({"from": u, "to": v})

    # Add any nodes discovered but not yet in visited_nodes
    for node in visited_set:
        if node not in visited_nodes:
            visited_nodes.append(node)

    return {
        "entry_point": entry_point_uri,
        "nodes": visited_nodes,
        "edges": tree_edges,
        "cycle_edges": cycle_edges,
    }
```

- [ ] **Step 2: Run tests — expect all pass**

```bash
cd backend
pytest tests/test_analysis/test_execution_flow.py -v
```

Expected output (all 6 pass):
```
PASSED tests/test_analysis/test_execution_flow.py::test_single_node_no_calls
PASSED tests/test_analysis/test_execution_flow.py::test_linear_chain
PASSED tests/test_analysis/test_execution_flow.py::test_cycle_detected
PASSED tests/test_analysis/test_execution_flow.py::test_diamond_no_cycle
PASSED tests/test_analysis/test_execution_flow.py::test_unknown_entry_point_is_isolated_node
PASSED tests/test_analysis/test_execution_flow.py::test_nodes_list_has_no_duplicates
```

---

### Task 2.3: Write failing tests for `clustering`

**Files:**
- Create: `backend/tests/test_analysis/test_clustering.py`

- [ ] **Step 1: Write test file**

`backend/tests/test_analysis/test_clustering.py`:

```python
import pytest
from rdflib import Graph, URIRef, Namespace

CG = Namespace("http://codegraph.io/ontology#")

A = URIRef("http://example.org/func/A")
B = URIRef("http://example.org/func/B")
C = URIRef("http://example.org/func/C")
D = URIRef("http://example.org/func/D")
E = URIRef("http://example.org/func/E")
F = URIRef("http://example.org/func/F")


def make_graph(*call_pairs):
    g = Graph()
    for caller, callee in call_pairs:
        g.add((caller, CG.calls, callee))
    return g


def test_empty_graph_returns_empty_clusters():
    from app.analysis.clustering import compute_clusters
    g = Graph()
    result = compute_clusters(g)
    assert result["clusters"] == []


def test_single_node_isolated():
    from app.analysis.clustering import compute_clusters
    g = Graph()
    g.add((A, CG.calls, A))  # self-loop just to register A
    result = compute_clusters(g)
    assert len(result["clusters"]) >= 1
    all_nodes = [n for c in result["clusters"] for n in c["nodes"]]
    assert str(A) in all_nodes


def test_two_disconnected_components_form_separate_clusters():
    from app.analysis.clustering import compute_clusters
    # Group 1: A <-> B <-> C (dense)
    # Group 2: D <-> E <-> F (dense, disconnected from group 1)
    g = make_graph(
        (A, B), (B, A), (B, C), (C, B), (A, C), (C, A),
        (D, E), (E, D), (E, F), (F, E), (D, F), (F, D),
    )
    result = compute_clusters(g)
    # Louvain should detect at least 2 clusters
    assert len(result["clusters"]) >= 2


def test_cluster_result_structure():
    from app.analysis.clustering import compute_clusters
    g = make_graph((A, B), (B, C))
    result = compute_clusters(g)
    assert "clusters" in result
    for cluster in result["clusters"]:
        assert "id" in cluster
        assert "nodes" in cluster
        assert "cohesion" in cluster
        assert isinstance(cluster["nodes"], list)
        assert 0.0 <= cluster["cohesion"] <= 1.0


def test_all_nodes_assigned_to_a_cluster():
    from app.analysis.clustering import compute_clusters
    g = make_graph((A, B), (B, C), (C, D))
    result = compute_clusters(g)
    all_nodes = {n for c in result["clusters"] for n in c["nodes"]}
    assert str(A) in all_nodes
    assert str(B) in all_nodes
    assert str(C) in all_nodes
    assert str(D) in all_nodes


def test_cohesion_is_between_0_and_1():
    from app.analysis.clustering import compute_clusters
    g = make_graph((A, B), (B, C), (C, A), (D, E))
    result = compute_clusters(g)
    for cluster in result["clusters"]:
        assert 0.0 <= cluster["cohesion"] <= 1.0
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd backend
pytest tests/test_analysis/test_clustering.py -v
```

Expected: `ImportError` for `app.analysis.clustering`.

---

### Task 2.4: Implement `clustering.py`

**Files:**
- Create: `backend/app/analysis/clustering.py`

- [ ] **Step 1: Write implementation**

`backend/app/analysis/clustering.py`:

```python
"""
Functional clustering via Louvain community detection.

Converts the cg:calls DiGraph to undirected (as required by python-louvain),
runs best_partition(), computes a cohesion score per cluster, and returns
results in memory (not persisted).
"""
from __future__ import annotations

from rdflib import Graph
import networkx as nx
import community as community_louvain  # python-louvain

from app.analysis.graph_to_networkx import calls_to_digraph


def _cohesion(undirected: nx.Graph, nodes: list[str]) -> float:
    """
    Cohesion = internal_edges / total_edges_incident_to_cluster_nodes.

    Returns 0.0 when there are no edges at all.
    """
    node_set = set(nodes)
    internal = sum(
        1 for u, v in undirected.edges(nodes) if u in node_set and v in node_set
    )
    total = undirected.degree(nodes)
    total_count = sum(d for _, d in total)
    if total_count == 0:
        return 0.0
    return internal / total_count


def compute_clusters(rdf_graph: Graph) -> dict:
    dg = calls_to_digraph(rdf_graph)

    if dg.number_of_nodes() == 0:
        return {"clusters": []}

    ug: nx.Graph = dg.to_undirected()

    partition: dict[str, int] = community_louvain.best_partition(ug)

    # Group nodes by community id
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

    # Sort clusters by id for deterministic output
    clusters.sort(key=lambda c: c["id"])

    return {"clusters": clusters}
```

- [ ] **Step 2: Run tests — expect all pass**

```bash
cd backend
pytest tests/test_analysis/test_clustering.py -v
```

Expected output (all 6 pass):
```
PASSED tests/test_analysis/test_clustering.py::test_empty_graph_returns_empty_clusters
PASSED tests/test_analysis/test_clustering.py::test_single_node_isolated
PASSED tests/test_analysis/test_clustering.py::test_two_disconnected_components_form_separate_clusters
PASSED tests/test_analysis/test_clustering.py::test_cluster_result_structure
PASSED tests/test_analysis/test_clustering.py::test_all_nodes_assigned_to_a_cluster
PASSED tests/test_analysis/test_clustering.py::test_cohesion_is_between_0_and_1
```

---

### Task 2.5: Run all Chunk 1 + Chunk 2 tests together

- [ ] **Step 1: Full analysis test suite**

```bash
cd backend
pytest tests/test_analysis/ -v
```

Expected: all 19 tests pass (5 + 7 + 6 + 6 from the four modules, minus overlap).

---

### Task 2.6: Commit Chunk 2

- [ ] **Step 1: Stage and commit**

```bash
cd backend
git add app/analysis/execution_flow.py app/analysis/clustering.py \
        tests/test_analysis/test_execution_flow.py \
        tests/test_analysis/test_clustering.py
git commit -m "feat(analysis): execution flow tracing and Louvain clustering modules"
```

---

## Chunk 3: FastAPI Router + HTTP-Level Tests + Wire into main.py

### File Map

```
backend/
  app/
    api/
      analysis.py           # FastAPI router with 4 endpoints
    main.py                 # register analysis router (modify)
  tests/
    test_api/
      test_analysis_endpoints.py
```

---

### Task 3.1: Write failing HTTP-level tests

**Files:**
- Create: `backend/tests/test_api/test_analysis_endpoints.py`

Precondition: the test fixture must inject a pre-built rdflib Graph into the project store so endpoints have data to work with. Assume the project store from Plan 1 exposes a way to retrieve a project's graph by project id. The fixture patches `app.api.analysis.get_project_graph` — a helper function that will be created alongside the router.

- [ ] **Step 1: Write test file**

`backend/tests/test_api/test_analysis_endpoints.py`:

```python
"""HTTP-level tests for analysis endpoints.

These tests patch get_project_graph() to return a small inline rdflib Graph,
so no real project on disk is needed.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from rdflib import Graph, URIRef, Namespace

CG = Namespace("http://codegraph.io/ontology#")

PROJECT_ID = "test-proj-001"

A = URIRef("http://example.org/func/A")
B = URIRef("http://example.org/func/B")
C = URIRef("http://example.org/func/C")


def make_test_graph():
    g = Graph()
    g.add((A, CG.calls, B))
    g.add((B, CG.calls, C))
    return g


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def patch_graph(make_test_graph=make_test_graph):
    with patch("app.api.analysis.get_project_graph", return_value=make_test_graph()):
        yield


# --- blast-radius ---

def test_blast_radius_200(client):
    resp = client.get(
        f"/api/v1/projects/{PROJECT_ID}/blast-radius",
        params={"node_uri": str(B)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["target_node"] == str(B)
    assert "direct_callers" in body
    assert "transitive_callers" in body
    assert "severity" in body
    assert "affected_files" in body


def test_blast_radius_missing_node_uri_422(client):
    resp = client.get(f"/api/v1/projects/{PROJECT_ID}/blast-radius")
    assert resp.status_code == 422


# --- execution-flow ---

def test_execution_flow_200(client):
    resp = client.get(
        f"/api/v1/projects/{PROJECT_ID}/execution-flow",
        params={"node_uri": str(A)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["entry_point"] == str(A)
    assert "nodes" in body
    assert "edges" in body
    assert "cycle_edges" in body


def test_execution_flow_missing_node_uri_422(client):
    resp = client.get(f"/api/v1/projects/{PROJECT_ID}/execution-flow")
    assert resp.status_code == 422


# --- clusters ---

def test_clusters_200(client):
    resp = client.get(f"/api/v1/projects/{PROJECT_ID}/clusters")
    assert resp.status_code == 200
    body = resp.json()
    assert "clusters" in body
    assert isinstance(body["clusters"], list)


# --- SPARQL panel ---

def test_sparql_valid_query(client):
    query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5"
    resp = client.post(
        f"/api/v1/projects/{PROJECT_ID}/sparql",
        json={"query": query},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "columns" in body
    assert "rows" in body
    assert isinstance(body["rows"], list)


def test_sparql_invalid_query_returns_422(client):
    resp = client.post(
        f"/api/v1/projects/{PROJECT_ID}/sparql",
        json={"query": "THIS IS NOT SPARQL !!!"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body.get("error") == "sparql_error"
    assert "message" in body


def test_sparql_missing_body_returns_422(client):
    resp = client.post(f"/api/v1/projects/{PROJECT_ID}/sparql", json={})
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd backend
pytest tests/test_api/test_analysis_endpoints.py -v
```

Expected: `ImportError` or `AttributeError` because `app.api.analysis` does not exist yet.

---

### Task 3.2: Implement `app/api/analysis.py`

**Files:**
- Create: `backend/app/api/analysis.py`

- [ ] **Step 1: Write router**

`backend/app/api/analysis.py`:

```python
"""
FastAPI router for analysis endpoints.

All four endpoints load the project's rdflib Graph via get_project_graph(),
then delegate to the appropriate analysis module.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from rdflib import Graph

from app.analysis.blast_radius import compute_blast_radius
from app.analysis.execution_flow import trace_execution_flow
from app.analysis.clustering import compute_clusters

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["analysis"])


# ---------------------------------------------------------------------------
# Dependency / helper — patched in tests
# ---------------------------------------------------------------------------

def get_project_graph(project_id: str) -> Graph:
    """
    Load and return the rdflib Graph for a project from disk.

    Raises HTTPException 404 if the project does not exist.
    This function is patched in tests; in production it reads
    the graph.ttl produced by Plan 2's AST/RDF pipeline.
    """
    from app.storage.project_store import load_project_graph  # Plan 2 module
    graph = load_project_graph(project_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return graph


# ---------------------------------------------------------------------------
# Blast Radius
# ---------------------------------------------------------------------------

@router.get("/blast-radius")
def blast_radius(
    project_id: str,
    node_uri: str = Query(..., description="URI-encoded function or field URI"),
):
    graph = get_project_graph(project_id)
    return compute_blast_radius(graph, node_uri)


# ---------------------------------------------------------------------------
# Execution Flow
# ---------------------------------------------------------------------------

@router.get("/execution-flow")
def execution_flow(
    project_id: str,
    node_uri: str = Query(..., description="URI-encoded entry-point function URI"),
):
    graph = get_project_graph(project_id)
    return trace_execution_flow(graph, node_uri)


# ---------------------------------------------------------------------------
# Clusters
# ---------------------------------------------------------------------------

@router.get("/clusters")
def clusters(project_id: str):
    graph = get_project_graph(project_id)
    return compute_clusters(graph)


# ---------------------------------------------------------------------------
# SPARQL Panel
# ---------------------------------------------------------------------------

class SparqlRequest(BaseModel):
    query: str


@router.post("/sparql")
def sparql_query(project_id: str, body: SparqlRequest):
    graph = get_project_graph(project_id)
    try:
        results = graph.query(body.query)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "sparql_error", "message": str(exc)},
        )

    columns = [str(v) for v in results.vars] if results.vars else []
    rows = [
        [str(cell) if cell is not None else None for cell in row]
        for row in results
    ]
    return {"columns": columns, "rows": rows}
```

Note on the SPARQL 422 response: FastAPI wraps `HTTPException.detail` in a `{"detail": ...}` envelope by default. To return the flat `{"error": ..., "message": ...}` structure the spec requires, add a custom exception handler (see Task 3.4).

---

### Task 3.3: Register the router in `main.py`

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add router import and include**

Open `backend/app/main.py` and add:

```python
from app.api.analysis import router as analysis_router
```

Then inside the app setup block (after existing router registrations):

```python
app.include_router(analysis_router)
```

---

### Task 3.4: Add custom exception handler for SPARQL errors

The SPARQL endpoint must return `{"error": "sparql_error", "message": "..."}` directly at the top level with HTTP 422. To achieve this, override FastAPI's default `HTTPException` handler for 422 responses from the SPARQL route, or use a `JSONResponse` directly in the route instead of raising `HTTPException`.

- [ ] **Step 1: Replace the SPARQL error raise with a JSONResponse**

Edit `backend/app/api/analysis.py` — replace the `except` block in `sparql_query`:

```python
from fastapi.responses import JSONResponse

# inside sparql_query:
    except Exception as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "sparql_error", "message": str(exc)},
        )
```

This ensures the response body is exactly `{"error": "sparql_error", "message": "..."}`.

---

### Task 3.5: Run HTTP tests — expect all pass

- [ ] **Step 1: Run endpoint tests**

```bash
cd backend
pytest tests/test_api/test_analysis_endpoints.py -v
```

Expected output (all 9 pass):
```
PASSED tests/test_api/test_analysis_endpoints.py::test_blast_radius_200
PASSED tests/test_api/test_analysis_endpoints.py::test_blast_radius_missing_node_uri_422
PASSED tests/test_api/test_analysis_endpoints.py::test_execution_flow_200
PASSED tests/test_api/test_analysis_endpoints.py::test_execution_flow_missing_node_uri_422
PASSED tests/test_api/test_analysis_endpoints.py::test_clusters_200
PASSED tests/test_api/test_analysis_endpoints.py::test_sparql_valid_query
PASSED tests/test_api/test_analysis_endpoints.py::test_sparql_invalid_query_returns_422
PASSED tests/test_api/test_analysis_endpoints.py::test_sparql_missing_body_returns_422
```

---

### Task 3.6: Full test suite

- [ ] **Step 1: Run all tests**

```bash
cd backend
pytest --tb=short -q
```

Expected: all analysis tests pass; no regressions from Plan 1 or Plan 2 tests.

---

### Task 3.7: Commit Chunk 3

- [ ] **Step 1: Stage and commit**

```bash
cd backend
git add app/api/analysis.py app/main.py \
        tests/test_api/test_analysis_endpoints.py
git commit -m "feat(api): analysis endpoints — blast radius, execution flow, clusters, SPARQL panel"
```

---

## Summary

| Chunk | Files Created | Tests Added | Key Dependencies |
|-------|--------------|-------------|-----------------|
| 1 | `graph_to_networkx.py`, `blast_radius.py` | 12 unit tests | networkx, rdflib |
| 2 | `execution_flow.py`, `clustering.py` | 12 unit tests | networkx, python-louvain |
| 3 | `api/analysis.py`, `main.py` (modified) | 9 HTTP tests | FastAPI, TestClient |

All analysis is stateless and recomputed on each request. No new persistence is introduced. The `get_project_graph` helper is the single seam between Plan 2's storage layer and Plan 3's analysis layer — making it easy to mock in tests and swap implementations later.
