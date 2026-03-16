# Code Graph — Design Spec
**Date:** 2026-03-16
**Status:** Approved

---

## Overview

A local-first web application that ingests a codebase (via GitHub URL or ZIP upload), parses it into an OWL-based RDF knowledge graph using Tree-sitter AST parsing, and provides graph visualization, analysis features, and markdown wiki generation. Designed for individual developers exploring unfamiliar codebases and AI/LLM tooling that needs structured code context.

---

## Users

- Individual developers exploring unfamiliar codebases
- AI/LLM agents querying the knowledge graph via SPARQL for code context

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser (React)                   │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ Graph View  │  │  Wiki View   │  │ Query Panel│  │
│  │(Cytoscape)  │  │  (Markdown)  │  │  (SPARQL)  │  │
│  └──────┬──────┘  └──────┬───────┘  └─────┬──────┘  │
└─────────┼────────────────┼────────────────┼─────────┘
          │           REST / WebSocket       │
┌─────────▼────────────────▼────────────────▼─────────┐
│                  FastAPI Backend                     │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Ingestion│  │ AST Parser   │  │  RDF Builder  │  │
│  │ (GitHub/ │  │ (Tree-sitter)│  │  (rdflib)     │  │
│  │  ZIP)    │  └──────────────┘  └───────────────┘  │
│  └──────────┘  ┌──────────────┐  ┌───────────────┐  │
│                │ Wiki Generator│  │ SPARQL Engine │  │
│                │  (rdflib→md) │  │  (rdflib)     │  │
│                └──────────────┘  └───────────────┘  │
└──────────────────────────┬──────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   Disk Storage          │
              │  /data/<project-id>/    │
              │   graph.ttl  (Turtle)   │
              │   wiki/  (Markdown)     │
              │   source/  (cloned/zip) │
              │   project.json          │
              └─────────────────────────┘
```

**Key principle:** `graph.ttl` is the single source of truth. All views and exports are derived from it.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| AST Parsing | tree-sitter (+ language grammars) |
| RDF / SPARQL | rdflib, owlrl |
| Graph traversal | networkx, python-louvain |
| Frontend | React, Cytoscape.js |
| Wiki templates | Jinja2 |
| Deployment | Local (uvicorn) + Docker Compose |

---

## Supported Languages

Java, TypeScript, JavaScript, Go, Rust, Kotlin, Ruby, C, Python

### Language Grammar Mapping

| File Extension | Tree-sitter Grammar |
|---|---|
| `.java` | `tree-sitter-java` |
| `.ts` | `tree-sitter-typescript` (TypeScript grammar) |
| `.tsx` | `tree-sitter-typescript` (TSX grammar) |
| `.js`, `.mjs`, `.cjs` | `tree-sitter-javascript` |
| `.jsx` | `tree-sitter-javascript` (JSX grammar) |
| `.go` | `tree-sitter-go` |
| `.rs` | `tree-sitter-rust` |
| `.kt`, `.kts` | `tree-sitter-kotlin` |
| `.rb` | `tree-sitter-ruby` |
| `.c`, `.h` | `tree-sitter-c` |
| `.py` | `tree-sitter-python` |

### Markup / Config File Parsing

Non-code files are parsed by lightweight built-in parsers (no Tree-sitter) in `markup.py`:

| File Extension | Parser |
|---|---|
| `.xml` | `GenericXmlParser` — extracts Maven pom.xml deps + generic XML structure |
| `.json` | `GenericJsonParser` — extracts top-level keys as constants |
| `.md`, `.markdown` | `MarkdownParser` — extracts headings as structure |
| `.yml`, `.yaml` | `YamlParser` — extracts top-level keys |
| `.html`, `.htm` | `HtmlParser` — lightweight structural extraction |

Toolchain config files (`tsconfig.json`, `go.mod`, `Cargo.toml`, `build.gradle`) are parsed by `config_parsers.py` to extract module aliases and root paths into `cg:ConfigValue` nodes.

---

## Ingestion Pipeline

### GitHub URL
1. Validate URL format; confirm repo is public via GitHub API
   - If private or not found: HTTP 422 `{"error": "repo_not_accessible", "message": "Repository is private or does not exist. Only public repos are supported."}` — displayed inline in UI.
   - If GitHub API is unreachable or rate-limited (60 req/hr unauthenticated): HTTP 502 `{"error": "github_api_unavailable", "message": "Could not reach GitHub API. Try again shortly or check your network."}` — displayed inline in UI. Do **not** fall through to clone on API failure.
2. `git clone --depth=1` into `/data/<project-id>/source/`
3. Detect languages via file extensions
4. Store `project.json` with metadata

### ZIP Upload
1. Accept multipart upload; reject files over **200 MB** (HTTP 413)
2. Validate ZIP integrity; reject invalid archives (HTTP 422)
3. Sanitize extraction paths to prevent zip-slip attacks (reject any entry with `..` in path)
4. Extract to `/data/<project-id>/source/`
5. Detect languages via file extensions
6. Store `project.json` with metadata

### Project Metadata (`project.json`)
```json
{
  "id": "<uuid>",
  "name": "...",
  "source": "github_url | zip_filename",
  "languages": ["java", "typescript"],
  "last_indexed": "ISO8601 timestamp",
  "status": "pending | indexing | ready | error",
  "error_message": "null or string"
}
```

### Source Retention
The `source/` directory is **retained** after indexing so that re-indexing does not require re-uploading. Users can delete a project (and all its data) via the UI.

### Re-indexing
Manual only — triggered via UI button. Re-runs full parse pipeline, overwrites `graph.ttl`, and deletes existing wiki files. Wiki is **not** automatically regenerated — user must trigger wiki generation manually afterward via the Wiki Export button or `POST /projects/{id}/wiki/generate`.

---

## OWL Ontology

Stored as `backend/ontology.ttl` (shipped with the app). Namespace: `http://codegraph.dev/ontology#` (prefix `cg:`). Loaded into rdflib at startup alongside each project graph.

**Important:** rdflib's SPARQL engine does not perform OWL subclass inference. All SPARQL queries that match TypeDefinition, Callable, or StorageNode subtypes must enumerate them explicitly via `VALUES` clauses.

### Class Hierarchy

```
cg:TypeDefinition  (abstract)
  ├─ cg:Class           regular class
  │    ├─ cg:AbstractClass
  │    └─ cg:DataClass   (Java record, Kotlin data class, Python @dataclass)
  ├─ cg:Interface        (Java/TS/Go interface, Python Protocol)
  ├─ cg:Trait            (Rust trait)
  ├─ cg:Enum             (all languages)
  ├─ cg:Struct           (Rust/Go struct, C struct/union)
  └─ cg:Mixin            (Ruby module used as mixin)

cg:Callable  (abstract)
  ├─ cg:Function         standalone function
  └─ cg:Method           owned by TypeDefinition
       └─ cg:Constructor

cg:StorageNode  (abstract)
  ├─ cg:Field            class/struct member
  ├─ cg:Parameter        function argument
  ├─ cg:LocalVariable    function-scoped
  └─ cg:Constant         immutable binding

Infrastructure: cg:File, cg:Module, cg:Import, cg:ExternalSymbol, cg:ConfigValue
```

### Object Properties

`cg:calls`, `cg:imports`, `cg:inherits`, `cg:implements`, `cg:mixes`, `cg:defines`, `cg:hasField`, `cg:hasMethod`, `cg:hasParameter`, `cg:containsFile`, `cg:containsClass`, `cg:contains`, `cg:dependsOn`

### Datatype Properties

`cg:name`, `cg:qualifiedName`, `cg:filePath`, `cg:language`, `cg:line`, `cg:column`, `cg:visibility`, `cg:isExported`, `cg:frameworkRole`, `cg:entryPointScore`, `cg:dataType`, `cg:returnType`, `cg:classKind`, `cg:value`, `cg:isTest`, `cg:isAbstract`, `cg:lineCount`, `cg:fileSize`

### Node URI scheme
`http://codegraph.dev/node/{project-id}/{kind}/{qualified-name}`

Kinds: `file`, `class`, `function`, `field`, `parameter`, `storage`, `import`, `module`, `external`

**Breaking change note:** Re-indexing required after ontology changes — existing `graph.ttl` files use old URI scheme and rdf:type values.

---

## AST Parsing — Extracted Constructs

### Core Constructs

| Construct | Java | TS/JS | Go | Rust | Kotlin | Ruby | C | Python |
|---|---|---|---|---|---|---|---|---|
| Function/method defs | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Function calls | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Class definitions | ✓ | ✓ | — | ✓ (struct/impl) | ✓ | ✓ | — (struct) | ✓ |
| Interface / trait | ✓ | ✓ | interface | trait | interface | module | — | — |
| Inheritance / implements | ✓ | ✓ | — | — | ✓ | ✓ (include/extend) | — | ✓ |
| Imports / use statements | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (require/include) | ✓ (#include) | ✓ |
| Fields | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Local variables | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Parameters | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Constants | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Advanced Constructs

**Imports & Exports**
- **Cross-file import resolution:** resolve import paths to actual files within the repo; emit `cg:imports` edge to resolved `cg:File` node (unresolvable → `cg:ExternalSymbol`)
- **Named bindings:** track `import { X as Y }` alias mappings and re-exports (`export { X } from './foo'`); stored as `cg:alias` data property on the import edge
- **Exports / public symbols:** detect exported/public symbols per language (`export`, `public`, `pub`, `open`); stored as `cg:isExported true` data property on Function/Class/Field nodes

**Heritage**
- **Class inheritance:** `cg:inherits` edges (all languages where applicable)
- **Interface implementation:** `cg:implements` edges
- **Mixins:** Ruby `include`/`extend`, Kotlin delegation — modelled as `cg:mixes` object property

**Type System**
- **Type annotations:** extract explicit type from variable/parameter/field declarations; stored in `cg:dataType` data property for use in receiver resolution
- **Constructor inference:** infer receiver type from `new Foo()` / `Foo()` / `Foo.new` constructor call patterns; store resolved type URI in `cg:receiverType` data property on the call site node. Covers `self`/`this` within method bodies for all languages.

**Toolchain Config Parsing**
Parse project config files to resolve module aliases and root paths:
- `tsconfig.json` — `paths`, `baseUrl` (TypeScript)
- `go.mod` — module name for import resolution (Go)
- `Cargo.toml` — crate name and workspace members (Rust)
- `build.gradle` / `settings.gradle` — module names (Kotlin/Java)
- `Gemfile` — gem dependencies (Ruby)
Config values stored in `cg:ConfigValue` nodes linked to the project root via `cg:hasConfig`.

**Framework Detection**
AST-based heuristics detect common framework patterns and annotate nodes:
- REST entry points: Spring `@GetMapping`/`@PostMapping`, Express `app.get()`/`app.post()`, FastAPI `@router.get()`, Gin `r.GET()`
- Test functions: JUnit `@Test`, Go `func TestXxx`, Rust `#[test]`, Jest `it()`/`test()`
- ORM models: JPA `@Entity`, ActiveRecord subclasses, GORM struct tags
Detected patterns stored as `cg:frameworkRole` data property (e.g. `"rest_endpoint"`, `"test"`, `"orm_model"`)

**Entry Point Scoring**
Score each function as a candidate entry point (0.0–1.0) using heuristics:
- Named `main`, `run`, `start`, `execute`, `handle` (+weight)
- Has `cg:frameworkRole` of `rest_endpoint` (+weight)
- Zero incoming `cg:calls` edges (nothing calls it — likely an entry) (+weight)
- Is exported/public (+weight)
- In a file named `main.*`, `index.*`, `app.*`, `server.*` (+weight)
Score stored as `cg:entryPointScore` data property. UI uses score ≥ 0.7 to pre-populate execution flow entry point suggestions.

---

**Unresolvable callees** (stdlib, external dependencies not in repo): represented as `cg:ExternalSymbol` nodes with `cg:isExternal true`. They appear in call graphs but are visually distinguished and excluded from blast radius calculations.

Parsing streams triples into rdflib; at completion, graph is serialized to `graph.ttl`. Progress is pushed to the frontend via WebSocket.

---

## Analysis Features

### Blast Radius Analysis
Given a function or field:
- Find all direct callers (1 hop via `cg:calls`) — SPARQL query
- Find all transitive callers — `networkx.ancestors()` on the `cg:calls` digraph (not owlrl)
- Find all functions that read/write the field (`cg:referencedBy`, `cg:assignedIn`)
- Group affected nodes by file/module
- **Severity score:** count of unique transitive callers (node count, not path count — avoids cycle issues). Cycles in the call graph are handled naturally by networkx's BFS/DFS traversal.

### Execution Flow Tracing
Given an entry point (e.g. `main()`, REST handler):
- Follow `cg:calls` transitively depth-first via networkx
- Detect and mark cycles (recursive calls) — cycle edges rendered as dashed in UI
- Return ordered call chain as a graph path

### Functional Clustering
- Export `cg:calls` edges to a networkx DiGraph
- Convert to undirected graph (`G.to_undirected()`) before running Louvain — `python-louvain`'s `community.best_partition()` requires an undirected `Graph`
- Run Louvain community detection (via `python-louvain` package)
- Each cluster gets a cohesion score: internal edges / total edges
- Clusters overlaid as color groups in the graph visualization

### SPARQL Query Panel
- Raw SPARQL 1.1 query input against the full project graph
- Results displayed as table or highlighted subgraph
- Available to users and AI agents via REST API (see API section)

---

## REST API

Base path: `/api/v1`

| Method | Path | Description |
|---|---|---|
| `POST` | `/projects` | Create project from GitHub URL or ZIP |
| `GET` | `/projects` | List all projects |
| `GET` | `/projects/{id}` | Get project metadata + status |
| `DELETE` | `/projects/{id}` | Delete project and all data |
| `POST` | `/projects/{id}/reindex` | Trigger manual re-index |
| `GET` | `/projects/{id}/graph` | Return graph nodes+edges as JSON for Cytoscape (no pagination in v1 — acceptable for local single-user use; large graphs may load slowly) |
| `POST` | `/projects/{id}/sparql` | Execute SPARQL query; body: `{"query": "..."}` |
| `GET` | `/projects/{id}/blast-radius?node_uri=<encoded>` | Blast radius for a node |
| `GET` | `/projects/{id}/execution-flow?node_uri=<encoded>` | Execution flow from entry point |
| `GET` | `/projects/{id}/clusters` | Return cluster assignments |
| `POST` | `/projects/{id}/wiki/generate` | Trigger wiki generation |
| `GET` | `/projects/{id}/wiki` | List generated wiki files |

WebSocket: `/ws/projects/{id}/status` — path is relative; resolved by the frontend using a configurable `VITE_API_BASE_URL` env var (defaults to `http://localhost:8000` in local dev, proxied through nginx in Docker). This avoids hardcoding `ws://localhost:8000` which breaks in Docker.

**Auth:** None (local-first). **Rate limiting:** None (single-user local tool).

**CORS:** Backend must allow `http://localhost:5173` (local dev) and `http://localhost` (Docker). Configured via `CORS_ORIGINS` environment variable with sensible defaults.

All error responses: `{"error": "<error_code>", "message": "<human-readable>"}` with appropriate HTTP status.

---

## Graph Visualization UI

**Stack:** React + Cytoscape.js

### Views
**Force-directed view**
- Nodes colored by type: 17 distinct node types across 4 families (TypeDefinitions, Callables, StorageNodes, Infrastructure) — each with its own color; Interface/Trait have dashed borders
- Edges colored by relation type (calls, imports, inherits, implements, mixes, hasMethod, hasField, hasParameter, etc.)
- Side panel on node click: name, type, file, line/column number, properties, connections
- Blast radius button → highlights affected subgraph in red
- Execution flow button → animates call chain path

**Hierarchical view**
- Tree: Module → File → Class/Interface/Enum/… → Method/Constructor/Function → Field/Parameter (via `cg:containsFile`, `cg:containsClass`, `cg:defines`)
- Collapse/expand nodes
- Linked selection with force-directed view

### Interactions
- Pan & zoom (mouse wheel, click-drag)
- Node drag (reposition in force-directed view)
- Double-click → zoom to node's neighborhood
- Box select (drag to multi-select)
- Pinch-to-zoom (touch/trackpad)
- Fit button (reset zoom to show full graph)
- Mini-map (overview for large graphs)

### Other UI Elements
- Search bar — client-side filter over already-loaded graph data (no server round-trip); filters visible nodes in Cytoscape by name substring match
- Filter panel — grouped by node family (Type Definitions / Callables / Storage / Other); show/hide by node type, edge relation, method visibility; cluster overlay; test file toggle
- Cluster color overlay
- Index status bar with WebSocket progress
- Re-index button
- Wiki export button

### Landing Page
- GitHub URL text input + Submit (inline error display)
- ZIP drag-and-drop upload (max 200 MB shown in UI)
- List of previously indexed projects (load from `GET /api/v1/projects`)

---

## Wiki Generation

Triggered manually via UI (Wiki Export button) or `POST /api/v1/projects/{id}/wiki/generate`. On re-index, existing wiki files are deleted but **not** regenerated automatically — the user must trigger generation again as a separate step.

SPARQL queries → Jinja2 templates → `.md` files written to `/data/<project-id>/wiki/`.

### Output Structure
```
wiki/
  index.md                    # project overview, language stats, cluster summary
  modules/
    <module-name>.md
  classes/
    <ClassName>.md
  functions/
    <module>_<FunctionName>.md  # standalone functions (Go, Rust, JS module-level)
```

### Class Wiki Page Contents
- Class name, file, language, inheritance chain
- Fields table: name, type, visibility, mutability, default value
- Methods table: name, parameters, return type, line number
- Callers: what calls into this class
- Dependencies: what this class calls out to
- Cluster membership + cohesion score

### Function Wiki Page Contents (standalone)
- Function name, file, language, line number
- Parameters table: name, type
- Variables table: name, type, mutability
- Callers and callees
- Cluster membership

---

## Storage Layout

```
/data/
  <project-id>/
    project.json       # metadata + status
    graph.ttl          # RDF knowledge graph (Turtle)
    source/            # cloned repo or extracted ZIP (retained for re-index)
    wiki/              # generated markdown files (deleted on re-index)

backend/
  ontology.ttl         # OWL ontology (read-only, shipped with app)
```

---

## Deployment

**Local:**
```
uvicorn app.main:app --reload   # backend on :8000
npm run dev                     # frontend on :5173
```

**Docker Compose** (`docker-compose.yml`):
- `backend` service: Python image, mounts `./data` volume and `./backend/ontology.ttl` read-only
- `frontend` service: React build served via nginx on port 80
- `./data` host directory mounted into backend for persistence

---

## Out of Scope (v1)

- Private GitHub repos (no auth)
- Automatic re-indexing on repo changes
- Multi-user / auth
- Cloud hosting
- Languages beyond the 9 supported (Java, TS, JS, Go, Rust, Kotlin, Ruby, C, Python)
- OWL reasoning beyond class hierarchy (no transitive property materialization)
- Full type inference (only explicit annotations extracted — no Hindley-Milner)
- Dynamic dispatch resolution (virtual method calls resolved to declared type only)
