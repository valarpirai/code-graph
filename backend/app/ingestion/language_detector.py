from pathlib import Path

EXTENSION_MAP: dict[str, str] = {
    # Code
    ".java": "java",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".rb": "ruby",
    ".c": "c",
    ".h": "c",
    ".py": "python",
    # Markup / config
    ".xml": "xml",
    ".json": "json",
    ".md": "markdown",
    ".markdown": "markdown",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".toml": "toml",
    ".properties": "properties",
}

_PROGRAMMING_LANGUAGES = {
    "java", "typescript", "javascript", "go", "rust",
    "kotlin", "ruby", "c", "python",
}

def detect_languages(root: Path) -> list[str]:
    """Return deduplicated sorted list of programming languages found under root."""
    found: set[str] = set()
    for path in root.rglob("*"):
        if path.is_file():
            lang = EXTENSION_MAP.get(path.suffix.lower())
            if lang and lang in _PROGRAMMING_LANGUAGES:
                found.add(lang)
    return sorted(found)
