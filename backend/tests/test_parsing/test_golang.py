import pytest
from app.parsing.golang import GoParser

def test_receiver_method():
    src = "package svc\nfunc (s *Server) Start() error { return nil }"
    parsed = GoParser().parse("server.go", src)
    assert len(parsed.classes) >= 1
    assert parsed.classes[0].name == "Server"
    assert parsed.classes[0].methods[0].name == "Start"

def test_top_level_function():
    src = "package main\nfunc main() { }"
    parsed = GoParser().parse("main.go", src)
    assert any(f.name == "main" for f in parsed.functions)

def test_import_extracted():
    src = 'package main\nimport "fmt"\nfunc main() { fmt.Println("hi") }'
    parsed = GoParser().parse("main.go", src)
    assert len(parsed.imports) >= 1
