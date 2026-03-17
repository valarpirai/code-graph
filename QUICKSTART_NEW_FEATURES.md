# Quick Start: Wiki + LLM Features

## What Was Fixed

✅ **Wiki generation now works** — Fixed 5 critical bugs:
- API response shape mismatches (frontend/backend)
- Wrong SPARQL property for local variables (`cg:hasLocalVar` → `cg:defines`)
- Missing type constraints in queries
- Template field mismatches

✅ **All wiki tests passing** (183/187 total backend tests pass)

---

## What's New

### 1. 🔍 Wiki Semantic Search (RAG)

Ask questions about your codebase in natural language:

```
User: "Which classes handle authentication?"
AI: "The AuthManager class in auth/manager.py handles authentication..."
```

**How to use**:
1. Generate wiki for your project (button in Wiki tab)
2. Type question in "Ask the Wiki" box
3. Press Enter or click "Ask"
4. Click source links to jump to relevant pages

### 2. 💬 Natural Language → SPARQL

Convert questions to SPARQL queries automatically:

```
User: "Show me all public methods in classes that implement EventHandler"
AI: Generates and executes SPARQL query, displays results in table
```

**How to use**:
1. Go to Query tab
2. Type question in "Ask in Natural Language" box
3. Press Enter or click "Ask"
4. Generated SPARQL appears in editor (editable)
5. Results displayed in table

---

## Setup

### 1. Install Dependencies

```bash
cd backend
uv sync
```

### 2. Configure API Key

**Option A**: Environment variable
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**Option B**: `.env` file
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > backend/.env
```

### 3. Start Backend

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`

### 4. Start Frontend

```bash
cd frontend
npm install  # if first time
npm run dev
```

Frontend runs on `http://localhost:5173`

---

## Example Workflow

1. **Index a project**:
   - Paste GitHub URL or upload ZIP on landing page
   - Wait for indexing to complete

2. **Generate wiki**:
   - Go to Wiki tab
   - Click "Generate Wiki" button
   - Wait 2-5 seconds

3. **Try semantic search**:
   - Type: "What are the main entry points?"
   - AI answers based on wiki content
   - Click source links to see full documentation

4. **Try natural language queries**:
   - Go to Query tab
   - Type: "List all functions with more than 5 parameters"
   - AI generates SPARQL, executes it, shows results

---

## API Endpoints

| Endpoint | Method | Purpose | Requires API Key |
|----------|--------|---------|------------------|
| `/projects/{id}/wiki/generate` | POST | Generate Markdown docs | No |
| `/projects/{id}/wiki` | GET | List wiki files | No |
| `/projects/{id}/wiki/{path}` | GET | Fetch single file | No |
| `/projects/{id}/wiki/search` | POST | Semantic search | **Yes** |
| `/projects/{id}/sparql` | POST | Execute SPARQL | No |
| `/projects/{id}/sparql/natural` | POST | NL → SPARQL | **Yes** |

---

## Limitations

- **RAG context**: Only top 80k chars of wiki content (ranked by keyword relevance)
- **NL SPARQL accuracy**: Works best with clear, specific questions
- **No streaming**: 1-2 second latency for LLM responses
- **No cluster support yet**: Cluster sections in wiki pages will be empty

---

## Troubleshooting

### "ANTHROPIC_API_KEY not configured"
- Check environment variable: `echo $ANTHROPIC_API_KEY`
- Check `.env` file exists in `backend/` directory
- Restart backend server after setting key

### Wiki generates but is empty
- Check backend logs for SPARQL query errors
- Try re-indexing project: click "Re-index" button in project header

### SPARQL query fails
- Check generated query in editor (might need manual adjustment)
- Some complex queries require domain expertise

### Frontend shows old data
- Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows/Linux)
- Clear browser cache

---

## Files Changed

See `IMPLEMENTATION_SUMMARY.md` for full technical details.

**Key files**:
- `backend/app/ai/wiki_search.py` — RAG search logic
- `backend/app/ai/nl_sparql.py` — NL → SPARQL generation
- `backend/app/api/wiki.py` — Wiki endpoints (fixed + search)
- `backend/app/wiki/sparql_queries.py` — Fixed FUNCTION_LOCAL_VARS
- `frontend/src/components/project/WikiView/index.tsx` — Search UI
- `frontend/src/components/project/QueryPanel/index.tsx` — NL query UI

---

## Cost Estimate

Claude Sonnet 4.6 pricing (as of 2024):
- Input: ~$3 per million tokens
- Output: ~$15 per million tokens

**Typical usage**:
- Wiki search: ~10-20k input tokens, ~200-500 output tokens per query
- NL SPARQL: ~2-5k input tokens, ~100-200 output tokens per query

**Rough cost**: $0.01-0.05 per question (varies by wiki size and question complexity)
