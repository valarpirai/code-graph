# Backend

FastAPI backend for Code Graph. Ingests source code via GitHub URL or ZIP, parses it with Tree-sitter, builds an OWL-based RDF knowledge graph, and exposes REST + WebSocket APIs. Also ships an MCP server for AI tooling.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — the only package manager used here (never `pip` directly)

## Setup

```bash
cd backend
uv sync                        # install all dependencies
cp ../.env.example ../.env     # set ANTHROPIC_API_KEY for LLM features
```

## Running

```bash
# API server (port 8000, auto-reload)
uv run uvicorn app.main:app --reload

# MCP server (port 8001, Streamable HTTP)
uv run python mcp_server.py --transport http --port 8001

# Or start everything via the repo root helper:
../dev.sh start
```

Data is read/written to `../data/{project_id}/` (configurable via `DATA_DIR` env var).

## Tests

```bash
uv run pytest                          # full suite
uv run pytest tests/test_parsing/test_java.py -v   # single file
uv run pytest -k "test_blast"          # filter by name
uv run pytest --tb=short -q            # compact output
```

Tests are organised to mirror the source tree:

```
tests/
  conftest.py              autouse fixture: clears get_settings() LRU cache
  test_config.py
  test_analysis/           blast_radius, clustering, execution_flow, graph_to_networkx
  test_api/                projects, graph, analysis endpoints, wiki endpoints
  test_ingestion/          github, language_detector, zip_handler
  test_models/             project
  test_parsing/            java, typescript, javascript, python, go, rust, kotlin, ruby, c
  test_rdf/                builder, graph_store, ontology
  test_storage/            project_store
  test_wiki/               generator, sparql_queries
  test_ws/                 indexing WebSocket
```

API tests inject a temporary `ProjectStore` via `app.dependency_overrides`. Analysis tests build a minimal `rdflib.Graph` inline and patch `app.api.analysis.get_project_graph`.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DATA_DIR` | `./data` | Root directory for project data |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins (JSON array or comma-separated) |
| `ANTHROPIC_API_KEY` | — | Required for wiki semantic search and NL→SPARQL features |

## API routes

All routes are prefixed `/api/v1/`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/projects` | List all projects |
| `POST` | `/projects` | Create project from GitHub URL |
| `POST` | `/projects/upload` | Create project from ZIP upload |
| `GET` | `/projects/{id}` | Get project metadata |
| `POST` | `/projects/{id}/reindex` | Trigger re-indexing |
| `DELETE` | `/projects/{id}` | Delete project |
| `GET` | `/projects/{id}/graph` | Graph in Cytoscape format `{nodes, edges}` |
| `GET` | `/projects/{id}/graph/summary` | Node/edge counts by type |
| `POST` | `/projects/{id}/sparql` | Run SPARQL SELECT query |
| `POST` | `/projects/{id}/sparql/natural` | Natural language → SPARQL + results |
| `GET` | `/projects/{id}/blast-radius/{uri}` | Blast radius analysis |
| `GET` | `/projects/{id}/execution-flow/{uri}` | Execution flow trace |
| `GET` | `/projects/{id}/clusters` | Louvain community clusters |
| `POST` | `/projects/{id}/wiki/generate` | Generate Markdown wiki from graph |
| `GET` | `/projects/{id}/wiki` | List wiki pages |
| `GET` | `/projects/{id}/wiki/{path}` | Fetch a wiki page |
| `POST` | `/projects/{id}/wiki/search` | Semantic search over wiki (RAG) |
| `WS` | `/ws/{id}` | Indexing progress notifications |
| `GET` | `/health` | Health check |

## MCP server

`mcp_server.py` wraps the REST API as an MCP tool server for AI clients (Claude Desktop, Claude Code, etc.).

```
mcp_tools/
  client.py            shared httpx client + error handler
  tools_projects.py    list, get, index, wait, reindex, delete
  tools_graph.py       summary, sparql, natural language query
  tools_analysis.py    blast radius
```

Add a new tool module by creating `mcp_tools/tools_<name>.py` with a `register(mcp)` function, then importing it in `mcp_server.py`.

See `../docs/mcp-server.md` for integration instructions.

## Package structure

```
app/
  main.py              FastAPI app, router mounts, WebSocket
  config.py            Settings via pydantic-settings
  dependencies.py      get_store() LRU-cached factory
  indexer.py           Async orchestrator: source → parse → RDF → save
  parsing/             Tree-sitter parsers (one file per language) + BaseParser ABC
  rdf/                 RDFBuilder, graph_store (load/save graph.ttl), ontology namespace
  analysis/            blast_radius, execution_flow, clustering, graph_to_networkx
  api/                 FastAPI routers (projects, graph, analysis, wiki)
  wiki/                WikiGenerator + Jinja2 templates + SPARQL query strings
  ai/                  wiki_search (RAG), nl_sparql (NL→SPARQL)
  storage/             ProjectStore (disk I/O for project metadata)
  models/              ProjectMeta, ProjectStatus
  ingestion/           GitHub clone, ZIP extraction, language detection
  ws/                  WebSocket indexing notifier
```
