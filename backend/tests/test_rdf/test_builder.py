from rdflib import RDF, Literal
from app.rdf.builder import RDFBuilder, _uri
from app.rdf.ontology import CG
from app.parsing.base import (
    ParsedFile, ClassDef, FunctionDef, ImportDef, ParameterDef
)


def make_parsed_file(file_path="src/Foo.java", language="java") -> ParsedFile:
    method = FunctionDef(
        name="bar", qualified_name="com.example.Foo.bar",
        line=5, column=2, parameters=[],
        visibility="public", is_exported=True,
        framework_role=None, entry_point_score=0.1,
        calls=["externalHelper"],
    )
    cls = ClassDef(
        name="Foo", qualified_name="com.example.Foo",
        line=3, inherits=[], implements=[],
        fields=[], methods=[method], is_exported=True,
    )
    imp = ImportDef(source="com.example.Other", resolved_file=None, bindings=[], is_reexport=False)
    return ParsedFile(
        file_path=file_path, language=language,
        classes=[cls], functions=[], imports=[imp], constants=[], config_values=[],
    )


def test_file_triple_added():
    g = RDFBuilder().build("proj1", [make_parsed_file()])
    file_uri = _uri("proj1", "file", "src/Foo.java")
    assert (file_uri, RDF.type, CG.File) in g
    assert (file_uri, CG.language, Literal("java")) in g


def test_class_triple_added():
    g = RDFBuilder().build("proj1", [make_parsed_file()])
    cls_uri = _uri("proj1", "class", "com.example.Foo")
    assert (cls_uri, RDF.type, CG.Class) in g
    assert (cls_uri, CG.name, Literal("Foo")) in g


def test_function_triple_added():
    g = RDFBuilder().build("proj1", [make_parsed_file()])
    fn_uri = _uri("proj1", "function", "com.example.Foo.bar")
    # bar is a method owned by Foo → CG.Method, not CG.Function
    assert (fn_uri, RDF.type, CG.Method) in g


def test_call_edge_to_external():
    g = RDFBuilder().build("proj1", [make_parsed_file()])
    caller = _uri("proj1", "function", "com.example.Foo.bar")
    callee = _uri("proj1", "external", "externalHelper")
    assert (caller, CG.calls, callee) in g
    assert (callee, RDF.type, CG.ExternalSymbol) in g


def test_import_triple_added():
    g = RDFBuilder().build("proj1", [make_parsed_file()])
    file_uri = _uri("proj1", "file", "src/Foo.java")
    imp_uri = _uri("proj1", "import", "com.example.Other")
    assert (imp_uri, RDF.type, CG.Import) in g
    assert (file_uri, CG.imports, imp_uri) in g


def test_call_edge_between_known_functions():
    caller_fn = FunctionDef(
        name="main", qualified_name="pkg.main",
        line=1, column=0, parameters=[],
        visibility="public", is_exported=True,
        framework_role=None, entry_point_score=0.5,
        calls=["pkg.helper"],
    )
    callee_fn = FunctionDef(
        name="helper", qualified_name="pkg.helper",
        line=10, column=0, parameters=[],
        visibility="public", is_exported=True,
        framework_role=None, entry_point_score=0.0,
        calls=[],
    )
    pf = ParsedFile(
        file_path="main.go", language="go",
        classes=[], functions=[caller_fn, callee_fn],
        imports=[], constants=[], config_values=[],
    )
    g = RDFBuilder().build("proj1", [pf])
    caller_uri = _uri("proj1", "function", "pkg.main")
    callee_uri = _uri("proj1", "function", "pkg.helper")
    assert (caller_uri, CG.calls, callee_uri) in g
