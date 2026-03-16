import pytest
from app.parsing.rust import RustParser

def test_impl_block():
    src = "pub struct Foo;\nimpl Foo { pub fn bar(&self) {} }"
    parsed = RustParser().parse("lib.rs", src)
    assert len(parsed.classes) >= 1
    assert parsed.classes[0].name == "Foo"
    assert parsed.classes[0].methods[0].name == "bar"

def test_top_level_function():
    src = "pub fn main() { }"
    parsed = RustParser().parse("main.rs", src)
    assert any(f.name == "main" and f.is_exported for f in parsed.functions)

def test_use_statement():
    src = "use std::collections::HashMap;"
    parsed = RustParser().parse("lib.rs", src)
    assert len(parsed.imports) >= 1
