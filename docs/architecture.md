# Architecture

A local-first web app that ingests a codebase (GitHub URL or ZIP), parses it into an OWL-based RDF knowledge graph using Tree-sitter AST parsers, and provides graph visualisation, analysis, wiki generation, and an MCP server for AI tooling.

**Key principle:** `graph.ttl` is the single source of truth. All views and exports are derived from it.

---

## System Diagram

```
┌──────────────────────────────────────────────────────┐
│                    Browser (React)                    │
│  ┌────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │ Graph View │  │  Wiki View  │  │  Query Panel  │  │
│  │(Cytoscape) │  │ (Markdown)  │  │   (SPARQL)    │  │
│  └─────┬──────┘  └──────┬──────┘  └──────┬────────┘  │
└────────┼────────────────┼────────────────┼───────────┘
         │           REST / WebSocket       │
┌────────▼────────────────▼────────────────▼───────────┐
│                   FastAPI Backend                     │
│  ┌───────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ Ingestion │  │ AST Parser  │  │  RDF Builder   │  │
│  │(GitHub/   │  │(Tree-sitter)│  │   (rdflib)     │  │
│  │  ZIP)     │  └─────────────┘  └────────────────┘  │
│  └───────────┘  ┌─────────────┐  ┌────────────────┐  │
│                 │Wiki Generator│  │ SPARQL Engine  │  │
│                 │ (rdflib→md) │  │   (rdflib)     │  │
│                 └─────────────┘  └────────────────┘  │
└─────────────────────────┬────────────────────────────┘
                          │ HTTP (httpx)
┌─────────────────────────▼────────────────────────────┐
│              MCP Server (fastmcp)                     │
│  stdio · Streamable HTTP :8001/mcp                    │
└──────────────────────────────────────────────────────┘
                          │
             ┌────────────▼────────────┐
             │      Disk Storage       │
             │  /data/<project-id>/    │
             │   graph.ttl  (Turtle)   │
             │   wiki/  (Markdown)     │
             │   source/ (clone/zip)   │
             │   project.json          │
             └─────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind v3, Cytoscape.js |
| Backend | FastAPI, uvicorn, Python 3.11+ |
| Graph storage | rdflib 7, Turtle format |
| AST parsing | Tree-sitter (Java, TS, JS, Go, Rust, Kotlin, Ruby, C, Python) |
| Analysis | NetworkX, python-louvain |
| Wiki generation | rdflib SPARQL + Jinja2 templates |
| AI features | Anthropic Claude API (`claude-sonnet-4-6`) |
| MCP server | fastmcp 2.x, Streamable HTTP + stdio |
| Package manager | uv (backend), npm (frontend) |
| Container | Docker Compose |

---

## Backend — `backend/app/`

```
main.py              FastAPI app — mounts all routers + WebSocket
config.py            Settings (data_dir, cors_origins, anthropic_api_key) via pydantic-settings
dependencies.py      get_store() — LRU-cached ProjectStore factory
indexer.py           Indexer.run() — async orchestrator: walk source → parse → RDF → save
parsing/
  base.py            BaseParser ABC + dataclasses (ParsedFile, ClassDef, FunctionDef, …)
  __init__.py        get_parser(extension) registry — 20 extensions, 10 languages + markup
  java.py … python.py  Tree-sitter AST parsers
  markup.py          XML, JSON, Markdown, YAML, HTML parsers
  config_parsers.py  parse_tsconfig(), parse_go_mod(), parse_cargo_toml()
  framework_detector.py  Detects Spring/FastAPI/Gin/etc. → frameworkRole labels
  entry_point_scorer.py  Scores 0–1 for likely entry points
rdf/
  ontology.py        CG = Namespace("http://codegraph.dev/ontology#"), load_ontology()
  builder.py         RDFBuilder — ParsedFile list → rdflib Graph (Turtle)
  graph_store.py     load_graph (lru_cache by mtime) / save_graph
analysis/
  graph_to_networkx.py  calls_to_digraph()
  blast_radius.py    compute_blast_radius() → direct/transitive callers + severity
  execution_flow.py  trace_execution_flow() — DFS with cycle detection
  clustering.py      compute_clusters() — Louvain on undirected call graph
api/
  projects.py        CRUD + /upload + /reindex
  graph.py           GET /{id}/graph (Cytoscape format), GET /{id}/graph/summary
  analysis.py        blast-radius, execution-flow, clusters, sparql, sparql/natural
  wiki.py            generate, list, fetch, search
wiki/
  sparql_queries.py  Named SPARQL query strings
  generator.py       WikiGenerator — SPARQL → Jinja2 → .md files
  templates/         index.md.j2, class.md.j2, module.md.j2, function.md.j2
ai/
  wiki_search.py     RAG search over wiki files
  nl_sparql.py       Natural language → SPARQL generation
storage/
  project_store.py   ProjectStore — save/load/delete ProjectMeta
models/project.py    ProjectMeta, ProjectStatus enum
ws/indexing.py       IndexingNotifier — WebSocket broadcast per project_id
ingestion/
  github.py          validate + shallow-clone GitHub repos
  zip_handler.py     extract ZIP with zip-slip protection
  language_detector.py  extension → language name
```

---

## Frontend — `frontend/src/`

```
api/
  types.ts        All TypeScript interfaces
  client.ts       apiFetch wrapper + all API functions
hooks/
  useProject.ts   useProjects, useProject (polls while indexing), useDeleteProject, useReindexProject
  useGraph.ts     useGraph, useClusters, useBlastRadius, useExecutionFlow
  useIndexingStatus.ts  WebSocket hook → IndexingState
pages/
  LandingPage.tsx     GitHub URL input + ZIP upload + project list
  ProjectPage.tsx     4-tab layout (Graph / Hierarchy / Wiki / Query)
components/
  landing/            GitHubInput, ProjectList, ZipUpload
  project/
    GraphView/        Cytoscape.js canvas, NodeSidePanel, MiniMap, cytoscapeConfig
    HierarchyView/    Tree from cg:contains edges
    WikiView/         WikiSidebar + react-markdown pane
    QueryPanel/       SPARQL editor + NL query + results table
    FilterPanel/      Node-type / edge-relation / cluster checkboxes
    ProjectHeader.tsx  Back, language tags, status badge, re-index
    IndexingStatus.tsx Progress bar strip
  shared/
    StatusBadge.tsx   Pill badge for project statuses
    SearchBar.tsx     Search input
```

**Non-obvious tech choices:**
- Tailwind v3 (not v4) — v4 broke `@apply` and `tailwind.config.ts`; pinned at `tailwindcss@3.4.19`
- `cytoscape-cose-bilkent` imported with `// @ts-expect-error` at module level
- `@tanstack/react-query v5` — object API (`useQuery`, `useMutation`)
- `BASE_URL` cast: `(import.meta as { env?: {...} }).env?.VITE_API_BASE_URL ?? "..."` — required for strict TS

---

## Ontology — `backend/ontology.ttl`

Namespace: `http://codegraph.dev/ontology#` (prefix `cg:`)

rdflib has no subclass inference — SPARQL queries must enumerate subtypes via `VALUES` clauses.

```
cg:TypeDefinition  (abstract)
  ├─ cg:Class, cg:AbstractClass, cg:DataClass
  ├─ cg:Interface, cg:Trait, cg:Enum, cg:Struct, cg:Mixin
cg:Callable  (abstract)
  ├─ cg:Function, cg:Method, cg:Constructor
cg:StorageNode  (abstract)
  ├─ cg:Field, cg:Parameter, cg:LocalVariable, cg:Constant
Infrastructure: cg:File, cg:Module, cg:Import, cg:ExternalSymbol
```

Object properties: `calls`, `imports`, `inherits`, `implements`, `mixes`, `hasField`, `hasMethod`, `hasParameter`, `defines`, `containsFile`, `containsClass`

Datatype properties: `name`, `qualifiedName`, `filePath`, `language`, `line`, `visibility`, `isExported`, `frameworkRole`, `entryPointScore`, `dataType`, `returnType`, `classKind`, `value`, `isTest`, `isAbstract`, `lineCount`, `fileSize`

---

## Data Layout on Disk

```
/data/{project_id}/
  project.json    ProjectMeta (id, name, source, status, languages)
  graph.ttl       RDF graph in Turtle format
  source/         Cloned or extracted source code
  wiki/           Generated Markdown (index.md, classes/, functions/, modules/)
```

---

## Key Gotchas

**Namespace mismatch:** `RDFBuilder` and SPARQL queries use `http://codegraph.dev/ontology#`. `graph_to_networkx.py` uses `http://codegraph.io/ontology#` (test fixture namespace). Analysis endpoints work as long as triples were built consistently.

**Dependency injection:** API endpoints use `store: ProjectStore = Depends(get_store)`. Tests override with `app.dependency_overrides[get_store] = lambda: ProjectStore(data_dir=str(tmp_path))`.

**LRU-cached settings:** `get_settings()` is cached — tests must call `get_settings.cache_clear()` before patching (handled by `conftest.py` autouse fixture).

**Re-index required:** Existing `graph.ttl` files built before the storage node hierarchy change (URIs `variable/` → `storage/`) must be re-indexed.
