from pathlib import Path
from .parsing import get_parser
from .parsing.base import ParsedFile
from .parsing.config_parsers import parse_config_file
from .parsing.entry_point_scorer import score_entry_point
from .ingestion.language_detector import EXTENSION_MAP
from .rdf.builder import RDFBuilder
from .rdf.graph_store import save_graph


# Directories that should never be indexed
_SKIP_DIRS = {
    ".git", "node_modules", ".gradle", ".mvn", "target", "build",
    "dist", "out", "__pycache__", ".idea", ".vscode", "vendor",
    "bin", "obj", ".cache", "coverage",
}

# Extensions that are always binary / unreadable
_BINARY_EXTENSIONS = {
    ".class", ".jar", ".war", ".ear", ".zip", ".gz", ".tar",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".exe", ".dll", ".so", ".dylib", ".o", ".a",
    ".ttf", ".woff", ".woff2", ".eot",
    ".pack", ".idx", ".rev",
}


def _is_test_path(file_path: str) -> bool:
    p = file_path.replace("\\", "/").lower()
    stem = p.rsplit("/", 1)[-1]
    return (
        "/test/" in p or "/tests/" in p or "/test_" in p
        or stem.startswith("test_") or stem.endswith("test.java")
        or stem.endswith("tests.java") or stem.endswith("spec.java")
        or stem.endswith("it.java")
    )


def _should_skip(path: Path, source_dir: Path) -> bool:
    """Return True if this path is inside a skip-dir or has a binary extension."""
    try:
        rel = path.relative_to(source_dir)
    except ValueError:
        return True
    if any(part in _SKIP_DIRS for part in rel.parts):
        return True
    if path.suffix.lower() in _BINARY_EXTENSIONS:
        return True
    return False


def _detect_language(path: Path) -> str:
    # Check full filename first (e.g. "Dockerfile", "Makefile")
    name_map = {"dockerfile": "docker", "makefile": "make", "gemfile": "ruby"}
    lang = name_map.get(path.name.lower(), "")
    if lang:
        return lang
    return EXTENSION_MAP.get(path.suffix.lower(), path.suffix.lstrip(".") or "unknown")


class Indexer:
    async def run(
        self,
        project_id: str,
        source_dir: Path,
        data_dir: Path,
        notifier=None,
        include_languages: set[str] | None = None,
    ):
        parsed_files: list[ParsedFile] = []
        paths = [p for p in source_dir.rglob("*") if p.is_file() and not _should_skip(p, source_dir)]

        if include_languages:
            paths = [p for p in paths if _detect_language(p) in include_languages]

        for i, path in enumerate(paths):
            rel_path = str(path.relative_to(source_dir))
            language = _detect_language(path)

            try:
                source = path.read_text(errors="replace")
            except Exception:
                if notifier:
                    await notifier({"type": "progress", "current": i + 1, "total": len(paths), "file": rel_path})
                continue

            line_count = source.count("\n") + 1
            file_size  = path.stat().st_size

            parser = get_parser(path.suffix.lower())
            # Also check by filename for special files
            if parser is None:
                from .parsing.markup import PackageJsonParser, PomXmlParser, YamlParser
                fname = path.name
                if fname == "package.json":
                    parser = PackageJsonParser()
                elif fname == "pom.xml":
                    parser = PomXmlParser()
                elif fname in ("docker-compose.yml", "docker-compose.yaml",
                               "application.yml", "application.yaml"):
                    parser = YamlParser()

            if parser is not None:
                try:
                    pf = parser.parse(rel_path, source)
                except Exception:
                    pf = ParsedFile(
                        file_path=rel_path, language=language,
                        classes=[], functions=[], imports=[], constants=[], config_values=[],
                    )
            else:
                # Stub: create a plain File node with no code entities
                pf = ParsedFile(
                    file_path=rel_path, language=language,
                    classes=[], functions=[], imports=[], constants=[], config_values=[],
                )

            pf.language   = language          # normalise: parser may leave it wrong
            pf.line_count = line_count
            pf.file_size  = file_size
            pf.is_test    = _is_test_path(rel_path)
            parsed_files.append(pf)

            # also attempt config parsing
            try:
                config_vals = parse_config_file(rel_path, source)
                if config_vals:
                    pf.config_values.extend(config_vals)
            except Exception:
                pass

            if notifier:
                await notifier({"type": "progress", "current": i + 1, "total": len(paths), "file": rel_path})

        # score entry points
        call_targets = {
            c
            for pf in parsed_files
            for fn in (list(pf.functions) + [m for cls in pf.classes for m in cls.methods])
            for c in fn.calls
        }
        for pf in parsed_files:
            for fn in pf.functions + [m for cls in pf.classes for m in cls.methods]:
                fn.entry_point_score = score_entry_point(fn, Path(pf.file_path).stem, fn.qualified_name in call_targets)

        g = RDFBuilder().build(project_id, parsed_files)
        save_graph(g, project_id, data_dir)

        if notifier:
            await notifier({"type": "done", "triples": len(g)})
