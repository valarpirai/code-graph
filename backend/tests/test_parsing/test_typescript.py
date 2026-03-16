import pytest
from app.parsing.typescript import TypeScriptParser

def test_exported_arrow_function():
    src = 'export const greet = (name: string): string => `Hello ${name}`;'
    parsed = TypeScriptParser().parse("greet.ts", src)
    assert len(parsed.functions) >= 1
    fn = parsed.functions[0]
    assert fn.name == "greet"
    assert fn.is_exported is True

def test_class_extracted():
    src = """
export class UserService {
  private name: string;
  constructor(name: string) { this.name = name; }
  getName(): string { return this.name; }
}
"""
    parsed = TypeScriptParser().parse("user.ts", src)
    assert len(parsed.classes) >= 1
    assert parsed.classes[0].name == "UserService"
    assert parsed.classes[0].is_exported is True

def test_import_extracted():
    src = 'import { useState, useEffect } from "react";'
    parsed = TypeScriptParser().parse("app.ts", src)
    assert len(parsed.imports) >= 1
    assert parsed.imports[0].source == "react"
