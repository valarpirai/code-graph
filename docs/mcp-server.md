# Code Graph MCP Server

An MCP (Model Context Protocol) server that exposes the Code Graph backend as tools callable by Claude and other MCP-compatible clients.

## Overview

The MCP server is a standalone Python process (`backend/mcp_server.py`) built with `fastmcp`. It talks to the running Code Graph FastAPI backend via HTTP — the backend must be running before the MCP server is started.

```
Claude / MCP Client
       │  MCP protocol (stdio)
       ▼
  mcp_server.py
       │  HTTP (httpx)
       ▼
  FastAPI backend  :8000
       │
       ▼
  graph.ttl / wiki/ on disk
```

## Who Is It For

**Developers working on a large or unfamiliar codebase** — the MCP server is most useful when you need structural facts mid-task: "what calls this?", "what does this module depend on?", "is it safe to change this signature?"

**Teams doing code review or onboarding** — reviewers and new joiners can ask architecture questions grounded in the actual code rather than reading every file.

### When to use

- Refactoring — ask Claude to check blast radius before changing a shared function
- Code review — verify call chains and dependencies for changed files
- Onboarding — ask "how does X work?" and get answers from generated wiki pages
- Debugging — trace execution flow to understand what runs before/after a failure point

### When NOT to use

- **Codebase < 5k lines** — just point Claude at the files directly
- **You need implementation logic** — the graph captures structure, not behavior; read the source for line-by-line understanding
- **The graph is stale** — if code has changed significantly since last indexing, re-index first
- **One-off question on a repo you won't revisit** — indexing overhead isn't worth it

## How It Changes the Workflow

Without the MCP server, exploring structure requires manual steps:

```
You:    "What functions call processPayment?"
You:    manually run SPARQL / grep / read code
You:    paste results back into chat
Claude: answers based on what you pasted
```

With the MCP server, you can ask Claude to query the graph directly:

```
You:    "What functions call processPayment?"
Claude: [calls get_blast_radius]
Claude: "Three callers: checkout(), retryPayment(), adminRefund().
         retryPayment() has the highest risk — 14 transitive callers."
```

The biggest gain is **accuracy**: Claude queries structural facts instead of guessing from pattern-matching. That matters most for cross-cutting changes (rename a field, change an interface) where missing one callsite breaks things.

**What it doesn't replace:** the graph shows *where* things are and *how* they connect. Claude still needs to read source to understand *what* the code does.

| Codebase size | Value |
|---|---|
| < 5k lines   | Low — Claude can read the files directly |
| 5k–50k lines | High — graph navigation beats grepping |
| 50k+ lines   | Very high — too large for context; graph is essential |

## Tech Stack

| Layer | Technology |
|---|---|
| MCP framework | `fastmcp` 2.x (Python) |
| Transport | stdio — MCP standard, no network socket |
| HTTP client (to backend) | `httpx` (sync) |
| Runtime | Python 3.11+, `uv` package manager |
| Backend API | FastAPI + uvicorn |
| Graph storage | RDF/Turtle files on disk (`rdflib`) |
| Query language | SPARQL 1.1 (via rdflib) |
| AI features | Anthropic Claude API (`anthropic` SDK, `claude-sonnet-4-6`) |
| Configuration | `pydantic-settings` — reads from env vars or `.env` file |

## Security

### What is protected

| Threat | Control |
|---|---|
| Zip-slip attack | `resolve()` path check rejects any member escaping the dest directory |
| Oversized ZIP upload | Hard 200 MB cap enforced before extraction begins |
| Invalid GitHub URLs | Strict regex — only `github.com/{owner}/{repo}` accepted |
| Private repo access | GitHub API called to confirm public visibility before cloning |
| Wiki path traversal | `resolve()` check in the wiki endpoint rejects `../` escapes |
| SPARQL data mutation | Backend exposes SELECT queries only — no UPDATE/INSERT/DELETE endpoints |
| API key exposure | `ANTHROPIC_API_KEY` read from env var or `.env`; never hardcoded |
| MCP network exposure | stdio transport — the server process is only accessible to the local OS user |
| Frontend CSRF | CORS restricted to `localhost:5173`, `localhost`, `localhost:80` |

### Known gaps (designed for local/trusted use)

**No authentication on the backend API** — any process on localhost can call `http://localhost:8000` directly. There is no token, session, or API key protecting the REST endpoints.

**HTTP only between MCP server and backend** — if `CODE_GRAPH_URL` is pointed at a remote host, traffic is unencrypted. Only use remote backends over a trusted network or a TLS-terminating proxy.

**No rate limiting** — MCP tool calls are not throttled. A misbehaving client can saturate the backend.

**SPARQL gives full read access** — `run_sparql` and `natural_language_query` can read everything in the graph. This is intentional (it's a query interface), but be aware if the graph contains sensitive source code.

The system is designed for a local development workflow where the OS user boundary is the trust boundary. Do not expose the backend port to the internet without adding authentication.

---

## Tools

### Project Management

| Tool | Description |
|------|-------------|
| `list_projects` | List all indexed projects (id, name, status, languages) |
| `get_project` | Get full metadata for a project by ID |
| `index_github_repo` | Start indexing a public GitHub repo — returns immediately |
| `wait_for_indexing` | Poll until indexing completes; returns final state + progress log |
| `reindex_project` | Trigger re-indexing of an existing project |
| `delete_project` | Delete a project and all its data |

### Graph & Queries

| Tool | Description |
|------|-------------|
| `get_graph_summary` | Node and edge counts grouped by type |
| `run_sparql` | Execute a SPARQL SELECT query (capped at 500 rows) |
| `natural_language_query` | Convert plain-English to SPARQL and execute (requires `ANTHROPIC_API_KEY`) |

### Analysis

| Tool | Description |
|------|-------------|
| `get_blast_radius` | All callers (direct + transitive) of a node, with severity |

## Running

```bash
cd backend
uv sync                                              # install deps including fastmcp
uv run python mcp_server.py                          # stdio (default)
uv run python mcp_server.py --transport sse          # HTTP/SSE on :8001
uv run python mcp_server.py --transport sse --port 9000
```

The FastAPI backend must already be running on `:8000` before starting the MCP server.

## Connecting an AI Coding Assistant

### Prerequisites

1. Start the backend: `cd backend && uv run uvicorn app.main:app --reload`
2. Index a project via the UI or API so there is graph data to query
3. Register the MCP server in your AI client (steps below)

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (create if absent):

```json
{
  "mcpServers": {
    "code-graph": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/code-graph/backend",
        "run", "python", "mcp_server.py"
      ],
      "env": {
        "CODE_GRAPH_URL": "http://localhost:8000"
      }
    }
  }
}
```

Restart Claude Desktop. The tool list (`list_projects`, `run_sparql`, etc.) will appear in the tools panel.

### Claude Code (CLI / IDE extension)

Add to `.claude/mcp.json` in any project where you want access:

```json
{
  "mcpServers": {
    "code-graph": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/code-graph/backend",
        "run", "python", "mcp_server.py"
      ]
    }
  }
}
```

Or register globally: `claude mcp add code-graph -- uv --directory /path/to/backend run python mcp_server.py`

### Remote / team setup (SSE transport)

Run the MCP server in SSE mode on a shared host:

```bash
uv run python mcp_server.py --transport sse --host 0.0.0.0 --port 8001
```

Then point each client at `http://<host>:8001/sse` instead of using a local command. Note the [security gaps](#known-gaps-designed-for-localtrustd-use) — add authentication before exposing this to a network.

### Verifying the connection

Once registered, ask the AI:

> "List all code-graph projects"

It should call `list_projects` and return project names. If the tool list is empty or the call fails, check that the backend is reachable at `CODE_GRAPH_URL`.

### Configuration

| Variable         | Default                 | Description                     |
|------------------|-------------------------|---------------------------------|
| `CODE_GRAPH_URL` | `http://localhost:8000` | Base URL of the FastAPI backend |

## Design Decisions

- **Standalone HTTP client** — the MCP server does not import backend app code. All calls go through the REST API, avoiding coupling to internal state.
- **Sync tools** — `fastmcp` tools are synchronous; HTTP calls use `httpx` in sync mode.
- **Error surfacing** — HTTP errors from the backend are raised as `ValueError` with a structured message; fastmcp converts these to MCP error responses.
- **No streaming** — all tools return complete results; SPARQL results are capped at 500 rows.
