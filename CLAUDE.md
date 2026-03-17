# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Code Graph accepts a GitHub URL or ZIP upload, walks the source tree with Tree-sitter AST parsers, builds an OWL-based RDF knowledge graph (stored as `graph.ttl`), and serves it through a FastAPI backend + React frontend. Users can explore the graph visually (Cytoscape.js), run SPARQL queries, view blast-radius / execution-flow analysis, and generate a Markdown wiki from the graph.

---

## Commands

### Backend (Python 3.11+, uv)

Always use `uv` — never `pip` directly.

```bash
cd backend
uv sync                          # install / refresh deps
uv run uvicorn app.main:app --reload  # dev server on :8000
uv run pytest                    # full test suite
uv run pytest tests/test_parsing/test_java.py -v   # single file
uv run pytest -k "test_counts"   # single test by name
uv run pytest --tb=short -q      # compact output
```

### Frontend (Node 22 required — use `nvm use 22`)

```bash
cd frontend
npm install
npm run dev        # Vite dev server on :5173
npm run build      # production build
npm run test       # vitest run (non-watch)
npm run test:watch # vitest watch
```

### Docker

```bash
docker-compose up --build   # backend :8000, frontend :80
```

Data is persisted in `./data/` (mounted as `/data` in the container).

---

## Architecture

### Backend — `backend/`

```
app/
  main.py              FastAPI app — mounts all routers + WebSocket
  config.py            Settings (data_dir, cors_origins, anthropic_api_key) via pydantic-settings
  dependencies.py      get_store() — LRU-cached ProjectStore factory
  indexer.py           Indexer.run() — async orchestrator: walk source → parse → RDF → save
  parsing/
    base.py            BaseParser ABC + dataclasses (ParsedFile, ClassDef, FunctionDef, …)
    __init__.py        get_parser(extension) registry — 20 extensions, 10 code languages + markup types
    java.py … python.py  Tree-sitter AST parsers (Java, TS, JS, Go, Rust, Kotlin, Ruby, C, Python)
    markup.py          GenericXmlParser, GenericJsonParser, MarkdownParser, YamlParser, HtmlParser
    config_parsers.py  parse_tsconfig(), parse_go_mod(), parse_cargo_toml() → ConfigValue list
    framework_detector.py  Detects Spring/FastAPI/Gin/etc. → frameworkRole labels
    entry_point_scorer.py  Scores 0–1 for likely entry points
  rdf/
    ontology.py        CG = Namespace("http://codegraph.dev/ontology#"), load_ontology()
    builder.py         RDFBuilder — ParsedFile list → rdflib Graph (Turtle)
    graph_store.py     load_graph / save_graph (graph.ttl in data_dir/{project_id}/)
  analysis/
    graph_to_networkx.py  calls_to_digraph() — NOTE: uses "http://codegraph.io/ontology#" (not .dev)
    blast_radius.py    compute_blast_radius() → direct/transitive callers + severity
    execution_flow.py  trace_execution_flow() — DFS with active-stack cycle detection
    clustering.py      compute_clusters() — Louvain on undirected call graph
  api/
    projects.py        CRUD + /upload + /reindex
    graph.py           GET /{id}/graph → Cytoscape-format {nodes, edges}
    analysis.py        blast-radius, execution-flow, clusters, sparql (+ natural language query)
    wiki.py            POST /wiki/generate, GET /wiki, GET /wiki/{path}, POST /wiki/search
  wiki/
    sparql_queries.py  Named SPARQL query strings (cg: namespace)
    generator.py       WikiGenerator — queries graph → Jinja2 → writes .md files
    templates/         index.md.j2, class.md.j2, module.md.j2, function.md.j2
  ai/
    wiki_search.py     RAG-based semantic search over wiki files (Claude Sonnet 4.6)
    nl_sparql.py       Natural language → SPARQL query generation (Claude Sonnet 4.6)
  storage/
    project_store.py   ProjectStore — save/load/delete ProjectMeta, update_status,
                       wiki_dir(), graph_path(), source_dir()
  models/project.py    ProjectMeta, ProjectStatus enum (pending/indexing/ready/error)
  ws/indexing.py       IndexingNotifier — WebSocket broadcast per project_id
  ingestion/
    github.py          validate + clone GitHub repos
    zip_handler.py     extract ZIP uploads
    language_detector.py  extension → language name
```

**Data layout on disk** (`/data/{project_id}/`):
- `project.json` — serialised `ProjectMeta`
- `source/` — cloned/extracted source code
- `graph.ttl` — RDF graph in Turtle format
- `wiki/` — generated Markdown files (`index.md`, `classes/`, `functions/`, `modules/`)

**Key namespace gotcha:** `RDFBuilder` and SPARQL queries use `http://codegraph.dev/ontology#`. `graph_to_networkx.py` uses `http://codegraph.io/ontology#` — this is intentional (test fixture namespace) but means analysis endpoints operate on the same graph as long as triples were built with `.io`.

**Dependency injection:** API endpoints use `store: ProjectStore = Depends(get_store)`. In tests, override with `app.dependency_overrides[get_store] = lambda: ProjectStore(data_dir=str(tmp_path))`.

**`get_settings()` is LRU-cached** — tests must call `get_settings.cache_clear()` before patching (the `conftest.py` `autouse` fixture handles this).

### Frontend — `frontend/src/`

```
api/
  types.ts        All TypeScript interfaces (Project, GraphResponse, SparqlResponse, WikiFile, …)
  client.ts       apiFetch wrapper + all API functions (listProjects, getGraph, runSparql, …)
hooks/
  useProject.ts   useProjects, useProject (polls while indexing/cloning), useDeleteProject, useReindexProject
  useGraph.ts     useGraph, useClusters, useBlastRadius, useExecutionFlow
  useIndexingStatus.ts  WebSocket hook → IndexingState {message, progress, status, connected}
pages/
  LandingPage.tsx     GitHub URL input + ZIP upload + project list
  ProjectPage.tsx     4-tab layout (Graph / Hierarchy / Wiki / Query) + WebSocket status
components/
  landing/
    GitHubInput.tsx   GitHub URL text input + submit with inline error display
    ProjectList.tsx   List of previously indexed projects
    ZipUpload.tsx     ZIP drag-and-drop upload component
  project/
    GraphView/        Cytoscape.js canvas, NodeSidePanel, MiniMap, cytoscapeConfig
    HierarchyView/    Tree built from cg:contains edges
    WikiView/         WikiSidebar + react-markdown content pane
    QueryPanel/       SPARQL textarea + results table
    FilterPanel/      Node-type / edge-relation / cluster-overlay checkboxes
    ProjectHeader.tsx Back button, language tags, status badge, re-index
    IndexingStatus.tsx Progress bar strip
  shared/
    StatusBadge.tsx   Pill badge for 5 project statuses
    SearchBar.tsx     Search input
```

**Tech choices with non-obvious rationale:**
- Tailwind v3 (not v4) — v4 broke `@apply` and `tailwind.config.ts`; pinned at `tailwindcss@3.4.19`
- `cytoscape-cose-bilkent` layout — imported with `// @ts-expect-error` at module level
- `@tanstack/react-query v5` — hooks use `useQuery`/`useMutation` with object API
- `BASE_URL` cast: `(import.meta as { env?: {...} }).env?.VITE_API_BASE_URL ?? "http://localhost:8000"` — required to satisfy strict TypeScript

### Ontology — `backend/ontology.ttl`

Full OWL subclass hierarchy (rdflib SPARQL has no subclass inference — queries must enumerate subtypes via `VALUES` clauses):

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

Object properties: `cg:calls`, `cg:imports`, `cg:inherits`, `cg:implements`, `cg:mixes`, `cg:hasField`, `cg:hasMethod`, `cg:hasParameter`, `cg:defines`, `cg:containsFile`, `cg:containsClass`.
Datatype properties: `cg:name`, `cg:qualifiedName`, `cg:filePath`, `cg:language`, `cg:line`, `cg:visibility`, `cg:isExported`, `cg:frameworkRole`, `cg:entryPointScore`, `cg:dataType`, `cg:returnType`, `cg:classKind`, `cg:value`, `cg:isTest`, `cg:isAbstract`, `cg:lineCount`, `cg:fileSize`.

**Breaking change:** Existing `graph.ttl` files must be re-indexed after the hierarchy change (node URIs changed from `variable/` to `storage/`, rdf:type changed for all subtypes).

---

## LLM-Powered Features (NEW)

**Configuration Required**:
Set `ANTHROPIC_API_KEY` environment variable or in `.env` file. Both features return HTTP 503 if not configured.

### 1. Wiki Semantic Search (RAG)

**Endpoint**: `POST /api/v1/projects/{id}/wiki/search`
**Request**: `{"question": "What does the render method do?"}`
**Response**: `{"answer": "...", "sources": ["classes/Component.md", ...]}`

**How it works**:
- Ranks all wiki `.md` files by keyword relevance to the question
- Loads top-ranked files into Claude context (up to 80k chars)
- Claude generates natural language answer based only on wiki content
- Returns answer + source file paths

**Frontend**: Added "Ask the Wiki" input box at top of Wiki tab. Answer displayed in Markdown, sources clickable.

### 2. Natural Language → SPARQL

**Endpoint**: `POST /api/v1/projects/{id}/sparql/natural`
**Request**: `{"question": "Which functions call the render method?"}`
**Response**: `{"query": "PREFIX cg:...", "variables": [...], "results": {"bindings": [...]}}`

**How it works**:
- System prompt includes full ontology schema (node types, properties, relations)
- Claude generates SPARQL SELECT query from natural language
- Backend executes query against project graph
- Returns both the generated SPARQL AND the results

**Frontend**: Added NL input field at top of Query tab. Generated SPARQL populates editor (user can inspect/edit), results displayed in table.

**Model**: Both features use `claude-sonnet-4-6` (non-streaming, 1-2s latency typical).

---

## Testing patterns

**Backend:** TDD — write failing test first, then implement. Tests use `tmp_path` for isolated disk state. Analysis endpoint tests patch `app.api.analysis.get_project_graph` with a small inline `rdflib.Graph`. Wiki endpoint tests use `app.dependency_overrides`.

**Frontend:** vitest + `@testing-library/react`. Wrap components in `QueryClientProvider`. Mock API functions with `vi.spyOn(client, "functionName").mockResolvedValue(...)`. Vitest hoists `vi.mock()` — mock factories must be self-contained (no external variable references).
