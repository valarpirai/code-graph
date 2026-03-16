# code-graph

Index a codebase from a GitHub URL or ZIP upload, build an RDF knowledge graph with Tree-sitter AST parsing, and explore it visually.

**Features:**
- AST parsing for Java, TypeScript, JavaScript, Go, Rust, Kotlin, Ruby, C, Python
- OWL-based RDF knowledge graph (SPARQL-queryable, stored as Turtle)
- Graph visualization with Cytoscape.js (blast radius, execution flow, Louvain clustering)
- Auto-generated Markdown wiki from the graph
- Real-time indexing status via WebSocket

---

## Quick start (local)

Requires **uv** and **Node 22** (`nvm use 22`).

```bash
./dev.sh start    # backend :8000, frontend :5173
./dev.sh stop
./dev.sh status
./dev.sh logs
```

Open **http://localhost:5173**, paste a GitHub URL or upload a ZIP, and click Index.

---

## Quick start (Docker)

```bash
docker-compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:80

Project data is persisted in `./data/`.

---

## Development

### Backend (Python 3.11+)

```bash
cd backend
uv sync
uv run pytest                            # full suite
uv run pytest tests/test_parsing/ -v    # single directory
uv run pytest -k "test_blast_radius"    # single test
uv run uvicorn app.main:app --reload    # dev server
```

### Frontend (Node 22)

```bash
cd frontend
npm install
npm run dev      # Vite dev server :5173
npm run test     # vitest run
npm run build    # production build
```

---

## Architecture

```
backend/app/
  parsing/        Tree-sitter AST parsers → ParsedFile dataclasses
  rdf/            RDFBuilder: ParsedFile list → rdflib Graph (graph.ttl)
  analysis/       Blast radius, execution flow, Louvain clustering
  wiki/           WikiGenerator: SPARQL queries → Jinja2 templates → .md files
  api/            FastAPI routers (projects, graph, analysis, wiki)
  storage/        ProjectStore: project metadata + disk layout

frontend/src/
  api/            API client + TypeScript types
  hooks/          React Query hooks (projects, graph, wiki, WebSocket)
  pages/          LandingPage, ProjectPage (Graph / Hierarchy / Wiki / Query tabs)
  components/     GraphView (Cytoscape.js), HierarchyView, WikiView, QueryPanel
```

Each indexed project is stored under `data/{project_id}/`:
- `project.json` — metadata
- `source/` — cloned/extracted source
- `graph.ttl` — RDF graph (Turtle)
- `wiki/` — generated Markdown pages
