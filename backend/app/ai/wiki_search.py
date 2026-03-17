"""RAG-based semantic search over generated wiki files."""
from pathlib import Path

import anthropic

_MODEL = "claude-sonnet-4-6"
_MAX_CONTEXT_CHARS = 80_000


def _rank_files(files: list[Path], question: str) -> list[Path]:
    """Return files sorted by keyword relevance to the question (descending)."""
    words = set(question.lower().split())
    def score(f: Path) -> int:
        text = f.read_text(encoding="utf-8").lower()
        return sum(1 for w in words if w in text)
    return sorted(files, key=score, reverse=True)


def search_wiki(wiki_dir: Path, question: str, api_key: str) -> dict:
    """Answer a question by searching the wiki files using Claude."""
    files = sorted(wiki_dir.rglob("*.md"))
    if not files:
        return {"answer": "No wiki content found. Generate the wiki first.", "sources": []}

    ranked = _rank_files(files, question)

    context_parts: list[str] = []
    total = 0
    sources: list[str] = []
    for f in ranked:
        content = f.read_text(encoding="utf-8")
        chunk = f"### {f.stem}\n{content}"
        if total + len(chunk) > _MAX_CONTEXT_CHARS:
            break
        context_parts.append(chunk)
        sources.append(str(f.relative_to(wiki_dir)))
        total += len(chunk)

    context = "\n\n---\n\n".join(context_parts)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=(
            "You are a helpful code documentation assistant. "
            "Answer the user's question based only on the provided wiki documentation. "
            "Be concise and reference specific classes, functions, or modules when relevant."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Wiki documentation:\n\n{context}\n\n"
                    f"---\n\nQuestion: {question}"
                ),
            }
        ],
    )

    return {
        "answer": message.content[0].text,
        "sources": sources,
    }
