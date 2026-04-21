---
name: code-graph
description: Query the Code Graph knowledge graph for this codebase. Use when the user asks about code structure, call relationships, dependencies, blast radius, or wants to run SPARQL queries against the project graph. Requires the backend and MCP server to be running.
---

# Code Graph

Query the indexed knowledge graph of a codebase using structured tools.

## Typical workflow

```
1. list_projects          — find the project_id for this codebase
2. get_graph_summary      — understand what's in the graph (node/edge counts)
3. run_sparql / natural_language_query  — answer structural questions
4. get_blast_radius       — check impact before refactoring
```

## Indexing a new repo

```
index_github_repo("https://github.com/owner/repo")
→ returns { project_id, status: "indexing" }

wait_for_indexing(project_id)
→ polls until status is "ready" or "error", returns progress log
```

## Graph summary

```
get_graph_summary(project_id)
→ {
    total_nodes: 1842,
    total_edges: 3210,
    nodes_by_type: { Function: 540, Class: 120, File: 82, ... },
    edges_by_relation: { calls: 1200, hasMethod: 800, imports: 600, ... }
  }
```

## SPARQL queries

Always use the `cg:` prefix. Ontology namespace: `http://codegraph.dev/ontology#`

```sparql
PREFIX cg: <http://codegraph.dev/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

# All functions in a file
SELECT ?name ?line WHERE {
  ?fn rdf:type cg:Function ;
      cg:name ?name ;
      cg:filePath "src/api/projects.py" ;
      cg:line ?line .
}

# All callers of a function
SELECT ?callerName WHERE {
  ?caller cg:calls <uri-of-target-function> ;
          cg:name ?callerName .
}

# Classes with their methods
SELECT ?className ?methodName WHERE {
  ?cls rdf:type cg:Class ; cg:name ?className .
  ?cls cg:hasMethod ?method .
  ?method cg:name ?methodName .
}
```

Node types: `Function`, `Method`, `Constructor`, `Class`, `AbstractClass`, `Interface`,
`Trait`, `Enum`, `Struct`, `Field`, `Parameter`, `File`, `Module`, `Import`, `ExternalSymbol`

Edge relations: `calls`, `inherits`, `implements`, `mixes`, `imports`, `defines`,
`hasMethod`, `hasField`, `hasParameter`, `containsFile`, `containsClass`

## Natural language queries

```
natural_language_query(project_id, "Which functions call the render method?")
→ { query: "PREFIX cg: ...", variables: [...], results: { bindings: [...] } }
```

Use this when the SPARQL is non-trivial. The generated query is returned so you can inspect or edit it.

## Blast radius

```
get_blast_radius(project_id, node_uri)
→ {
    node: "processPayment",
    direct_callers: ["checkout", "retryPayment"],
    transitive_callers: [...],
    severity: "high"
  }
```

Get `node_uri` from a SPARQL query result or `get_graph_summary`. URIs look like:
`http://codegraph.dev/resource/{project_id}/function/processPayment`

## Re-indexing after code changes

```
reindex_project(project_id)
wait_for_indexing(project_id)
```

## When the graph is stale

If answers seem wrong (functions that no longer exist, missing new code), re-index first.
The graph is a snapshot — it does not auto-update when source files change.
