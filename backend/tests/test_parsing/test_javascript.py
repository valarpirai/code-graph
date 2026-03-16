import pytest
from app.parsing.javascript import JavaScriptParser

def test_commonjs_require():
    src = 'const db = require("./db");'
    parsed = JavaScriptParser().parse("app.js", src)
    assert len(parsed.imports) >= 1
    assert parsed.imports[0].source == "./db"

def test_exported_function():
    src = "export function greet(name) { return 'Hello ' + name; }"
    parsed = JavaScriptParser().parse("app.js", src)
    assert any(f.name == "greet" and f.is_exported for f in parsed.functions)

def test_arrow_function():
    src = "const add = (a, b) => a + b;"
    parsed = JavaScriptParser().parse("utils.js", src)
    assert any(f.name == "add" for f in parsed.functions)
