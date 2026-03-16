from pathlib import Path

EXTENSION_MAP: dict[str, str] = {
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
}

def detect_languages(root: Path) -> list[str]:
    """Return deduplicated sorted list of detected language names under root."""
    found: set[str] = set()
    for path in root.rglob("*"):
        if path.is_file():
            lang = EXTENSION_MAP.get(path.suffix.lower())
            if lang:
                found.add(lang)
    return sorted(found)
