# CLAUDE.md

Code Graph ingests a GitHub repo or ZIP, parses it with Tree-sitter, builds an OWL/RDF knowledge graph, and serves it via a FastAPI backend + React frontend. An MCP server exposes the graph as AI-callable tools.

## Docs

- [Architecture](docs/architecture.md) — system diagram, file trees, ontology, data layout, gotchas
- [MCP Server](docs/mcp-server.md) — tools, transports, integration guide, security

---

## Commands

### Backend (Python 3.11+, uv)

Always use `uv` — never `pip` directly.

```bash
cd backend
uv sync                                      # install / refresh deps
uv run uvicorn app.main:app --reload         # dev server :8000
uv run pytest                                # full test suite
uv run pytest tests/test_parsing/test_java.py -v
uv run pytest -k "test_counts"
uv run pytest --tb=short -q
```

### Frontend (Node 22 required — `nvm use 22`)

```bash
cd frontend
npm install
npm run dev        # Vite dev server :5173
npm run build
npm run test       # vitest (non-watch)
npm run test:watch
```

### All services

```bash
./dev.sh start     # backend :8000, frontend :5173, MCP server :8001
./dev.sh stop
./dev.sh status
./dev.sh logs
./dev.sh mcp       # MCP server only
```

### Docker

```bash
docker-compose up --build   # backend :8000, frontend :80
```

### Environment

```bash
# backend/.env
ANTHROPIC_API_KEY=sk-ant-...   # required for wiki search + NL SPARQL
DATA_DIR=/data                  # default; override for local dev
```

AI features (`wiki/search`, `sparql/natural`) return HTTP 503 without `ANTHROPIC_API_KEY`.

---

## API conventions

All REST routes follow: `POST|GET /api/v1/projects/{project_id}/<resource>`

Routers live in `backend/app/api/`. New routers must be mounted in `backend/app/main.py`.

---

## Testing

**Test layout:**
```
backend/tests/
  conftest.py        autouse fixture: clears get_settings() LRU cache
  test_config.py
  test_analysis/     blast_radius, clustering, execution_flow, graph_to_networkx
  test_api/          test_projects, test_graph, test_analysis_endpoints, test_wiki_endpoints
  test_ingestion/    github, zip_handler, language_detector
  test_models/       project
  test_parsing/      one file per language (java, python, typescript, …)
  test_rdf/          builder, graph_store, ontology
  test_storage/      project_store
  test_wiki/         generator, sparql_queries
  test_ws/           indexing_ws
```

**Backend:** TDD — write failing test first. Use `tmp_path` for disk state. Patch `app.api.analysis.get_project_graph` with an inline `rdflib.Graph` for analysis tests. Use `app.dependency_overrides` for wiki tests.

**Frontend:** vitest + `@testing-library/react`. Wrap in `QueryClientProvider`. Mock with `vi.spyOn(client, "fn").mockResolvedValue(...)`. `vi.mock()` factories must be self-contained (no external variable references).

**Frontend data fetching:** all server state goes through React Query hooks in `hooks/`. Components never call API functions directly — always use or create a hook.
