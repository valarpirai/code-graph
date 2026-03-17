# Implementation Summary: Wiki Fixes + LLM Features

## Bugs Fixed

### 1. Wiki Generation Not Working (5 critical bugs)

#### Bug #1: Frontend/Backend API Mismatch
- **Issue**: `list_wiki` returned `list[dict]` but frontend expected `{files: [...]}`
- **Fix**: Changed return type to `{"files": [...]}` wrapper object
- **Files**: `backend/app/api/wiki.py:47-61`

#### Bug #2: Wiki Content Response Type Mismatch
- **Issue**: `fetch_wiki_file` returned `PlainTextResponse` but frontend called `.json()`
- **Fix**: Changed to return `{"content": "...", "name": "..."}` JSON object
- **Files**: `backend/app/api/wiki.py:64-84`

#### Bug #3: Wrong SPARQL Property for Local Variables
- **Issue**: `FUNCTION_LOCAL_VARS` query used non-existent `cg:hasLocalVar` property
- **Reality**: RDFBuilder uses `cg:defines` + `rdf:type cg:LocalVariable`
- **Fix**: Changed query to `?fn cg:defines ?var . ?var a cg:LocalVariable`
- **Files**: `backend/app/wiki/sparql_queries.py:201-210`

#### Bug #4: Template Field Mismatch (Mutability)
- **Issue**: Templates referenced `f.mutability` and `v.mutability` but SPARQL queries don't return it
- **Fix**: Removed "Mutability" columns from class and function templates
- **Files**:
  - `backend/app/wiki/templates/class.md.j2:35-38`
  - `backend/app/wiki/templates/function.md.j2:24-27`

#### Bug #5: Test Fixtures Using Wrong RDF Structure
- **Issue**: Test graphs used `cg:hasLocalVar` (doesn't exist in ontology)
- **Fix**: Updated test fixtures to use `cg:defines` + `rdf:type cg:LocalVariable`
- **Files**:
  - `backend/tests/test_wiki/test_sparql_queries.py:82-84`
  - `backend/tests/test_wiki/test_generator.py:59-61`

**Test Results**: 183 passed (was 181), 4 failed (was 6) — wiki tests now 100% passing

---

## New Features Added

### 1. Wiki Semantic Search (RAG-powered)

**Backend**:
- New module: `backend/app/ai/wiki_search.py`
- Ranks wiki files by keyword relevance to user question
- Loads top-ranked files into Claude context (up to 80k chars)
- Returns natural language answer + source file paths
- Model: `claude-sonnet-4-6`

**API**:
- `POST /api/v1/projects/{id}/wiki/search`
- Request: `{"question": "What does the render method do?"}`
- Response: `{"answer": "...", "sources": ["classes/Component.md", ...]}`

**Frontend**:
- Added search input box at top of Wiki tab
- Live "Ask the Wiki" semantic search with Enter key support
- Answer displayed in Markdown with syntax highlighting
- Source links are clickable → jumps to that wiki page
- Files: `frontend/src/components/project/WikiView/index.tsx`

**Example Use**:
```
User: "Which classes handle authentication?"
Claude: "The AuthManager class in auth/manager.py handles authentication.
        It inherits from BaseAuth and implements OAuth2Provider..."
Sources: [classes/AuthManager.md, modules/auth.md]
```

---

### 2. Natural Language → SPARQL Query

**Backend**:
- New module: `backend/app/ai/nl_sparql.py`
- Converts natural language to SPARQL SELECT queries
- System prompt includes full ontology schema (node types, properties, relations)
- Automatically executes generated query against project graph
- Returns both the SPARQL query AND results
- Model: `claude-sonnet-4-6`

**API**:
- `POST /api/v1/projects/{id}/sparql/natural`
- Request: `{"question": "Which functions call the render method?"}`
- Response: `{"query": "PREFIX cg:...", "variables": [...], "results": {"bindings": [...]}}`

**Frontend**:
- Added NL input field at top of Query tab
- Generated SPARQL populates the editor below (user can inspect/edit)
- Results displayed in same table as manual SPARQL queries
- "Ask" button with loading state
- Files: `frontend/src/components/project/QueryPanel/index.tsx`

**Example Use**:
```
User: "Show me all public methods in classes that implement EventHandler"

Generated SPARQL:
PREFIX cg: <http://codegraph.dev/ontology#>
SELECT ?cls ?method WHERE {
  ?cls a ?clsType ;
       cg:implements <...EventHandler> ;
       cg:hasMethod ?method .
  ?method cg:visibility "public" .
  VALUES ?clsType { cg:Class cg:AbstractClass }
}
LIMIT 50

Results displayed in table.
```

---

## Configuration Required

Add to `.env` file:
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

Or set environment variable:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Both features return HTTP 503 if API key is not configured (graceful degradation).

---

## Dependencies Added

**Backend**:
- `anthropic>=0.40.0` (added to `pyproject.toml`)

**Frontend**:
- No new dependencies (existing React Query + fetch)

**Installation**:
```bash
cd backend
uv sync
```

---

## Architecture Notes

### RAG Search Flow
1. User submits question via frontend
2. Backend ranks all `.md` files by keyword overlap
3. Top files loaded into context (up to 80k chars)
4. Claude generates answer based only on wiki content
5. Returns answer + source file paths
6. Frontend renders Markdown, makes sources clickable

### NL→SPARQL Flow
1. User submits question via frontend
2. Backend sends question + full ontology schema to Claude
3. Claude generates SPARQL SELECT query
4. Backend executes query against rdflib Graph
5. Returns both query text AND results
6. Frontend populates SPARQL editor + displays results table
7. User can edit generated query and re-run manually

### Why Separate Endpoints?
- Wiki search: document-oriented, natural language answers
- NL SPARQL: structured queries, tabular results
- Different use cases: exploration vs. precise data extraction

---

## API Summary

| Endpoint | Method | Purpose | LLM |
|----------|--------|---------|-----|
| `/projects/{id}/wiki/generate` | POST | Generate Markdown docs from graph | No |
| `/projects/{id}/wiki` | GET | List all wiki files | No |
| `/projects/{id}/wiki/{path}` | GET | Fetch single wiki file | No |
| `/projects/{id}/wiki/search` | POST | Semantic search over wiki | **Yes** |
| `/projects/{id}/sparql` | POST | Execute raw SPARQL query | No |
| `/projects/{id}/sparql/natural` | POST | NL → SPARQL + execute | **Yes** |

---

## Testing

**Backend Tests**:
- All 19 wiki endpoint tests pass
- 183/187 total tests pass (4 pre-existing failures unrelated to this work)

**Manual Testing Required**:
1. Generate wiki for a project
2. Try semantic search: "What are the main entry points?"
3. Try NL SPARQL: "List all functions with more than 5 parameters"
4. Verify source links in wiki search jump to correct page
5. Verify generated SPARQL appears in editor and is editable

---

## Files Modified

**Backend** (12 files):
- `app/api/wiki.py` — fixed response shapes, added search endpoint
- `app/api/analysis.py` — added NL SPARQL endpoint
- `app/config.py` — added `anthropic_api_key` setting
- `app/wiki/sparql_queries.py` — fixed `FUNCTION_LOCAL_VARS` query
- `app/wiki/templates/class.md.j2` — removed mutability column
- `app/wiki/templates/function.md.j2` — removed mutability column
- `pyproject.toml` — added `anthropic>=0.40.0`
- `tests/test_api/test_wiki_endpoints.py` — updated for new response shapes
- `tests/test_wiki/test_sparql_queries.py` — fixed local var test fixture
- `tests/test_wiki/test_generator.py` — fixed local var test fixture

**Backend** (2 new files):
- `app/ai/__init__.py`
- `app/ai/wiki_search.py` — RAG search implementation
- `app/ai/nl_sparql.py` — NL→SPARQL implementation

**Frontend** (5 files):
- `src/api/types.ts` — added `WikiSearchResponse`, `NLSparqlResponse`
- `src/api/client.ts` — added `searchWiki()`, `runNLSparql()`
- `src/components/project/WikiView/index.tsx` — added search UI
- `src/components/project/WikiView/WikiSidebar.tsx` — fixed path vs name bug
- `src/components/project/QueryPanel/index.tsx` — added NL input UI

---

## Known Limitations

1. **No Cluster Support Yet**: `cg:Cluster`, `cg:cohesionScore`, `cg:hasNode` properties mentioned in SPARQL queries but not in ontology — cluster sections in wiki pages will be empty
2. **No Subclass Inference**: rdflib SPARQL doesn't support OWL reasoning — all queries must enumerate concrete types with VALUES clauses
3. **RAG Context Limit**: Only top 80k chars of wiki content loaded (ranked by keyword relevance)
4. **NL SPARQL Accuracy**: Depends on question clarity and schema complexity — complex joins may require manual refinement
5. **No Streaming**: Both LLM features use non-streaming responses (1-2 second latency typical)

---

## Next Steps (Future Work)

1. Add cluster generation to ontology + RDF builder
2. Implement wiki full-text search index (e.g., with sqlite FTS5)
3. Add conversation history to wiki search (multi-turn RAG)
4. Add SPARQL query history/favorites
5. Add "Explain this query" button (SPARQL → natural language)
6. Add embeddings-based semantic similarity (vs keyword ranking)
