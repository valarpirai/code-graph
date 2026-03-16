from .base import BaseParser, ParsedFile
from .java import JavaParser
from .typescript import TypeScriptParser
from .javascript import JavaScriptParser
from .golang import GoParser
from .rust import RustParser
from .kotlin import KotlinParser
from .ruby import RubyParser
from .c import CParser
from .python import PythonParser
from .markup import GenericXmlParser, GenericJsonParser, MarkdownParser, YamlParser, HtmlParser

_EXTENSION_MAP: dict[str, type] = {
    # Code
    ".java": JavaParser,
    ".ts": TypeScriptParser,
    ".tsx": TypeScriptParser,
    ".js": JavaScriptParser,
    ".jsx": JavaScriptParser,
    ".go": GoParser,
    ".rs": RustParser,
    ".kt": KotlinParser,
    ".rb": RubyParser,
    ".c": CParser,
    ".h": CParser,
    ".py": PythonParser,
    # Markup / config
    ".xml": GenericXmlParser,
    ".json": GenericJsonParser,
    ".md": MarkdownParser,
    ".markdown": MarkdownParser,
    ".yml": YamlParser,
    ".yaml": YamlParser,
    ".html": HtmlParser,
    ".htm": HtmlParser,
}


def get_parser(extension: str) -> BaseParser | None:
    cls = _EXTENSION_MAP.get(extension)
    return cls() if cls else None
