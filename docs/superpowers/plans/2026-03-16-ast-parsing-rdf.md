# AST Parsing & RDF Graph Building Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse source files for 8 languages using Tree-sitter, build an OWL/RDF knowledge graph, and expose a graph API endpoint.

**Architecture:** A BaseParser abstract class defines the extraction contract; one concrete parser per language extracts constructs into dataclasses; the RDF Builder converts these into rdflib triples; the Indexer orchestrates the full pipeline and serializes to graph.ttl.

**Tech Stack:** tree-sitter + language grammars, rdflib, owlrl, Python 3.11+, FastAPI, pytest

---

## Chunk 1: OWL Ontology + RDF Infrastructure

- [ ] **1.1** Write `backend/ontology.ttl` replacing the placeholder.

  Required classes: `cg:File`, `cg:Class`, `cg:Function`, `cg:Import`, `cg:Constant`, `cg:ConfigValue`, `cg:ExternalSymbol`.

  Required object properties: `cg:defines`, `cg:calls`, `cg:imports`, `cg:inherits`, `cg:implements`, `cg:hasField`, `cg:hasMethod`, `cg:dependsOn`.

  Required datatype properties: `cg:name`, `cg:qualifiedName`, `cg:language`, `cg:filePath`, `cg:line`, `cg:column`, `cg:visibility`, `cg:isExported`, `cg:frameworkRole`, `cg:entryPointScore`.

- [ ] **1.2** `backend/app/rdf/ontology.py`

  ```python
  from rdflib import Graph, Namespace
  CG = Namespace("http://codegraph.dev/ontology#")
  def load_ontology() -> Graph:
      g = Graph()
      g.parse("backend/ontology.ttl", format="turtle")
      return g
  ```

- [ ] **1.3** `backend/app/rdf/graph_store.py`

  ```python
  def load_graph(project_id: str, data_dir: Path) -> Graph:
      g = load_ontology()
      ttl = data_dir / project_id / "graph.ttl"
      if ttl.exists():
          g.parse(ttl, format="turtle")
      return g

  def save_graph(g: Graph, project_id: str, data_dir: Path) -> None:
      out = data_dir / project_id / "graph.ttl"
      out.parent.mkdir(parents=True, exist_ok=True)
      g.serialize(destination=str(out), format="turtle")
  ```

- [ ] **1.4** Tests: `tests/test_rdf/test_ontology.py` — assert `CG.Function` and `CG.calls` resolve; `test_graph_store.py` — save then load a single triple, assert round-trip equality.

- [ ] **1.5** Commit: `feat: OWL ontology and RDF graph store`

---

## Chunk 2: BaseParser + Java Parser (Full Detail)

- [ ] **2.1** `backend/app/parsing/base.py`

  ```python
  from __future__ import annotations
  from dataclasses import dataclass, field
  from typing import Optional
  from abc import ABC, abstractmethod

  @dataclass
  class ParameterDef:
      name: str
      type_hint: Optional[str]

  @dataclass
  class FieldDef:
      name: str
      type_hint: Optional[str]
      visibility: str

  @dataclass
  class ConstantDef:
      name: str
      value: Optional[str]
      line: int

  @dataclass
  class ConfigValue:
      key: str
      value: str
      source_file: str

  @dataclass
  class FunctionDef:
      name: str
      qualified_name: str
      line: int
      column: int
      parameters: list[ParameterDef]
      visibility: str
      is_exported: bool
      framework_role: Optional[str]
      entry_point_score: float
      calls: list[str] = field(default_factory=list)  # qualified names of callees

  @dataclass
  class ClassDef:
      name: str
      qualified_name: str
      line: int
      inherits: list[str]
      implements: list[str]
      fields: list[FieldDef]
      methods: list[FunctionDef]
      is_exported: bool

  @dataclass
  class ImportDef:
      source: str                        # raw import string
      resolved_file: Optional[str]       # resolved path within repo
      bindings: list[tuple[str, str]]    # [(name, alias), ...]
      is_reexport: bool

  @dataclass
  class ParsedFile:
      file_path: str
      language: str
      classes: list[ClassDef]
      functions: list[FunctionDef]       # standalone (not in class)
      imports: list[ImportDef]
      constants: list[ConstantDef]
      config_values: list[ConfigValue]

  class BaseParser(ABC):
      @abstractmethod
      def parse(self, file_path: str, source_code: str) -> ParsedFile: ...
  ```

- [ ] **2.2** `backend/app/parsing/java.py` — full implementation.

  ```python
  from tree_sitter import Language, Parser
  import tree_sitter_java as tsjava
  from .base import *

  JAVA_LANG = Language(tsjava.language())

  FRAMEWORK_ANNOTATIONS = {
      "Test": "test", "Entity": "jpa_entity",
      "GetMapping": "rest_endpoint", "PostMapping": "rest_endpoint",
      "PutMapping": "rest_endpoint", "DeleteMapping": "rest_endpoint",
      "RestController": "rest_controller", "Service": "service",
      "Repository": "repository",
  }

  class JavaParser(BaseParser):
      def __init__(self):
          self._parser = Parser(JAVA_LANG)

      def parse(self, file_path: str, source_code: str) -> ParsedFile:
          tree = self._parser.parse(source_code.encode())
          root = tree.root_node
          package = self._extract_package(root)
          classes = self._extract_classes(root, package)
          functions = self._extract_top_level_functions(root, package)
          imports = self._extract_imports(root)
          constants = self._extract_constants(root, package)
          return ParsedFile(
              file_path=file_path, language="java",
              classes=classes, functions=functions,
              imports=imports, constants=constants, config_values=[],
          )

      def _extract_package(self, root) -> str:
          for node in root.children:
              if node.type == "package_declaration":
                  # package_declaration: "package" scoped_identifier ";"
                  for child in node.children:
                      if child.type in ("scoped_identifier", "identifier"):
                          return child.text.decode()
          return ""

      def _extract_classes(self, root, package: str) -> list[ClassDef]:
          classes = []
          for node in self._walk(root, "class_declaration"):
              name = self._child_text(node, "identifier")
              qname = f"{package}.{name}" if package else name
              modifiers = self._get_modifiers(node)
              superclass = self._child_text(
                  self._find_child(node, "superclass"), "type_identifier"
              ) or ""
              interfaces = self._extract_interface_list(node)
              fields = self._extract_fields(node)
              methods = self._extract_methods(node, qname)
              classes.append(ClassDef(
                  name=name, qualified_name=qname,
                  line=node.start_point[0] + 1,
                  inherits=[superclass] if superclass else [],
                  implements=interfaces,
                  fields=fields, methods=methods,
                  is_exported="public" in modifiers,
              ))
          return classes

      def _extract_methods(self, class_node, class_qname: str) -> list[FunctionDef]:
          methods = []
          for node in self._walk(class_node, "method_declaration"):
              name = self._child_text(node, "identifier")
              modifiers = self._get_modifiers(node)
              annotations = self._get_annotations(node)
              framework_role = next(
                  (FRAMEWORK_ANNOTATIONS[a] for a in annotations if a in FRAMEWORK_ANNOTATIONS),
                  None,
              )
              params = self._extract_params(node)
              calls = self._extract_calls(node)
              methods.append(FunctionDef(
                  name=name,
                  qualified_name=f"{class_qname}.{name}",
                  line=node.start_point[0] + 1,
                  column=node.start_point[1],
                  parameters=params,
                  visibility="public" if "public" in modifiers else
                             "protected" if "protected" in modifiers else "private",
                  is_exported="public" in modifiers,
                  framework_role=framework_role,
                  entry_point_score=0.0,
                  calls=calls,
              ))
          return methods

      def _extract_params(self, method_node) -> list[ParameterDef]:
          params = []
          fp = self._find_child(method_node, "formal_parameters")
          if fp:
              for p in self._walk(fp, "formal_parameter"):
                  pname = self._child_text(p, "identifier")
                  ptype = self._child_text(p, "type_identifier") or \
                          self._child_text(p, "integral_type") or \
                          self._child_text(p, "floating_point_type")
                  params.append(ParameterDef(name=pname, type_hint=ptype))
          return params

      def _extract_calls(self, method_node) -> list[str]:
          calls = []
          for node in self._walk(method_node, "method_invocation"):
              method_name = self._child_text(node, "identifier")
              obj = self._child_text(node, "identifier")  # simplified; full resolution requires type inference
              if method_name:
                  calls.append(method_name)
          return calls

      def _extract_imports(self, root) -> list[ImportDef]:
          imports = []
          for node in self._walk(root, "import_declaration"):
              src = ""
              for child in node.children:
                  if child.type in ("scoped_identifier",):
                      src = child.text.decode()
              imports.append(ImportDef(
                  source=src, resolved_file=None,
                  bindings=[(src.split(".")[-1], "")],
                  is_reexport=False,
              ))
          return imports

      def _extract_fields(self, class_node) -> list[FieldDef]:
          fields = []
          for node in self._walk(class_node, "field_declaration"):
              modifiers = self._get_modifiers(node)
              type_name = self._child_text(node, "type_identifier") or \
                          self._child_text(node, "integral_type")
              for decl in self._walk(node, "variable_declarator"):
                  fname = self._child_text(decl, "identifier")
                  fields.append(FieldDef(
                      name=fname, type_hint=type_name,
                      visibility="public" if "public" in modifiers else
                                 "protected" if "protected" in modifiers else "private",
                  ))
          return fields

      def _extract_constants(self, root, package: str) -> list[ConstantDef]:
          constants = []
          for node in self._walk(root, "field_declaration"):
              modifiers = self._get_modifiers(node)
              if "static" in modifiers and "final" in modifiers:
                  for decl in self._walk(node, "variable_declarator"):
                      name = self._child_text(decl, "identifier")
                      val_node = decl.child_by_field_name("value")
                      constants.append(ConstantDef(
                          name=name,
                          value=val_node.text.decode() if val_node else None,
                          line=node.start_point[0] + 1,
                      ))
          return constants

      def _extract_top_level_functions(self, root, package: str) -> list[FunctionDef]:
          # Java has no top-level functions; return empty
          return []

      def _extract_interface_list(self, class_node) -> list[str]:
          result = []
          si = self._find_child(class_node, "super_interfaces")
          if si:
              for t in self._walk(si, "type_identifier"):
                  result.append(t.text.decode())
          return result

      def _get_modifiers(self, node) -> list[str]:
          mods = self._find_child(node, "modifiers")
          if not mods:
              return []
          return [c.text.decode() for c in mods.children if c.is_named]

      def _get_annotations(self, node) -> list[str]:
          anns = []
          for child in node.children:
              if child.type == "marker_annotation":
                  name = self._child_text(child, "identifier")
                  if name:
                      anns.append(name)
          return anns

      # --- tree-sitter helpers ---

      def _walk(self, node, node_type: str):
          if node.type == node_type:
              yield node
          for child in node.children:
              yield from self._walk(child, node_type)

      def _find_child(self, node, child_type: str):
          if node is None:
              return None
          for child in node.children:
              if child.type == child_type:
                  return child
          return None

      def _child_text(self, node, child_type: str) -> Optional[str]:
          child = self._find_child(node, child_type)
          return child.text.decode() if child else None
  ```

- [ ] **2.3** `tests/test_parsing/test_java.py`

  ```python
  import pytest
  from backend.app.parsing.java import JavaParser

  JAVA_SOURCE = """
  package com.example;

  import org.springframework.web.bind.annotation.GetMapping;
  import org.springframework.stereotype.Service;

  public class UserService {
      private static final int MAX_USERS = 100;
      private String name;

      @GetMapping("/users")
      public List<User> getUsers(String filter) {
          return userRepo.findAll(filter);
      }
  }
  """

  @pytest.fixture
  def parsed():
      return JavaParser().parse("src/UserService.java", JAVA_SOURCE)

  def test_class_extracted(parsed):
      assert len(parsed.classes) == 1
      cls = parsed.classes[0]
      assert cls.name == "UserService"
      assert cls.qualified_name == "com.example.UserService"
      assert cls.is_exported is True

  def test_method_framework_role(parsed):
      method = parsed.classes[0].methods[0]
      assert method.name == "getUsers"
      assert method.framework_role == "rest_endpoint"
      assert method.parameters[0].name == "filter"

  def test_field_extracted(parsed):
      fields = parsed.classes[0].fields
      assert any(f.name == "name" for f in fields)

  def test_constant_extracted(parsed):
      assert any(c.name == "MAX_USERS" and c.value == "100" for c in parsed.constants)

  def test_import_extracted(parsed):
      sources = [i.source for i in parsed.imports]
      assert any("GetMapping" in s for s in sources)

  def test_method_call_extracted(parsed):
      method = parsed.classes[0].methods[0]
      assert "findAll" in method.calls
  ```

- [ ] **2.4** Commit: `feat: BaseParser dataclasses and Java tree-sitter parser`

---

## Chunk 3: Remaining 7 Language Parsers (Brief)

All parsers follow the same pattern as JavaParser: subclass BaseParser, init tree-sitter Language, implement `parse()` using `_walk` / `_find_child` helpers.

- [ ] **3.1** `backend/app/parsing/typescript.py` — handles `.ts` and `.tsx`.

  Key differences from Java: `export` keyword on functions/classes maps to `is_exported`; extract `interface` declarations as ClassDef (no methods); JSX component functions detected by PascalCase name + JSX return; `import ... from "..."` maps to ImportDef; `re-export` via `export { X } from "..."`.

  Failing test (`tests/test_parsing/test_typescript.py`):
  ```python
  def test_exported_arrow_function():
      src = 'export const greet = (name: string): string => `Hello ${name}`;'
      parsed = TypeScriptParser().parse("greet.ts", src)
      fn = parsed.functions[0]
      assert fn.name == "greet"
      assert fn.is_exported is True
  ```

- [ ] **3.2** `backend/app/parsing/javascript.py` — handles `.js` and `.jsx`.

  Key differences: same grammar as TypeScript but no type annotations; `module.exports = ...` counts as export; CommonJS `require("./x")` becomes ImportDef with `resolved_file` hint.

  Failing test:
  ```python
  def test_commonjs_require():
      src = 'const db = require("./db");'
      parsed = JavaScriptParser().parse("app.js", src)
      assert parsed.imports[0].source == "./db"
  ```

- [ ] **3.3** `backend/app/parsing/golang.py` — handles `.go`.

  Key differences: no classes; `func (r *Receiver) Method()` → method stored under ClassDef named after receiver type; package-level `func` → standalone FunctionDef; `import` block → ImportDef with alias support; exported if name starts with uppercase.

  Failing test:
  ```python
  def test_receiver_method():
      src = "package svc\nfunc (s *Server) Start() error { return nil }"
      parsed = GoParser().parse("server.go", src)
      assert parsed.classes[0].name == "Server"
      assert parsed.classes[0].methods[0].name == "Start"
  ```

- [ ] **3.4** `backend/app/parsing/rust.py` — handles `.rs`.

  Key differences: `impl TypeName { fn method() }` → ClassDef; `pub fn` → is_exported; `use` statements → ImportDef; `#[test]` → framework_role="test"; `#[get("...")]` (actix-web) → framework_role="rest_endpoint".

  Failing test:
  ```python
  def test_impl_block():
      src = "pub struct Foo;\nimpl Foo { pub fn bar(&self) {} }"
      parsed = RustParser().parse("lib.rs", src)
      assert parsed.classes[0].name == "Foo"
      assert parsed.classes[0].methods[0].name == "bar"
  ```

- [ ] **3.5** `backend/app/parsing/kotlin.py` — handles `.kt`.

  Key differences: similar to Java; `data class` and `object` declarations → ClassDef; top-level functions (Kotlin allows them) → standalone FunctionDef; `@Test`, `@Get`, `@Post` annotations → framework_role.

  Failing test:
  ```python
  def test_top_level_function():
      src = "package app\nfun main() { println(\"hi\") }"
      parsed = KotlinParser().parse("Main.kt", src)
      assert parsed.functions[0].name == "main"
  ```

- [ ] **3.6** `backend/app/parsing/ruby.py` — handles `.rb`.

  Key differences: `module M; class C` nesting → qualified_name = "M::C"; `def method` inside class → method; standalone `def` → FunctionDef; `require` / `require_relative` → ImportDef; no explicit visibility keyword — `private :name` changes prior method's visibility (best-effort).

  Failing test:
  ```python
  def test_module_class_nesting():
      src = "module Api\n  class UsersController\n    def index; end\n  end\nend"
      parsed = RubyParser().parse("users_controller.rb", src)
      assert parsed.classes[0].qualified_name == "Api::UsersController"
  ```

- [ ] **3.7** `backend/app/parsing/c.py` — handles `.c` and `.h`.

  Key differences: no classes; `struct` declarations → ClassDef with fields only; top-level function definitions → FunctionDef; `#include` → ImportDef; `static` → not exported; no inheritance/interfaces.

  Failing test:
  ```python
  def test_struct_as_class():
      src = "struct Point { int x; int y; };"
      parsed = CParser().parse("point.h", src)
      assert parsed.classes[0].name == "Point"
      assert len(parsed.classes[0].fields) == 2
  ```

- [ ] **3.8** `backend/app/parsing/config_parsers.py` — extract project-level config into `list[ConfigValue]`.

  | File | Extracted keys |
  |---|---|
  | `tsconfig.json` | `compilerOptions.baseUrl`, `compilerOptions.paths.*` |
  | `go.mod` | `module` name |
  | `Cargo.toml` | `[package].name`, `[package].version` |
  | `build.gradle` | `group`, `version`, `dependencies` block (artifact ids) |
  | `Gemfile` | `gem "name"` entries |

  Each returns `list[ConfigValue]` with `source_file` set to the config file path.

- [ ] **3.9** `backend/app/parsing/framework_detector.py`

  ```python
  def detect_framework_role(node_name: str, annotations: list[str], imports: list[str]) -> Optional[str]:
      # Spring
      if any(a in annotations for a in ["GetMapping","PostMapping","PutMapping","DeleteMapping"]):
          return "rest_endpoint"
      if "RestController" in annotations: return "rest_controller"
      if "Service" in annotations: return "service"
      if "Repository" in annotations: return "repository"
      # Express / Gin / FastAPI patterns via import heuristics
      if any("express" in i for i in imports) and node_name in ("app","router"): return "express_router"
      if any("gin" in i for i in imports) and node_name in ("r","router","engine"): return "gin_router"
      if any("fastapi" in i for i in imports): return "fastapi_route"
      # Test frameworks
      if any(a in annotations for a in ["Test","test","it","describe"]): return "test"
      # ORM
      if "Entity" in annotations or any("ActiveRecord" in i for i in imports): return "entity"
      return None
  ```

- [ ] **3.10** `backend/app/parsing/entry_point_scorer.py`

  ```python
  ENTRY_NAMES = {"main", "run", "start", "handle", "handler", "execute"}
  ENTRY_FILES = {"main", "index", "app", "server", "entrypoint"}

  def score_entry_point(fn: FunctionDef, file_stem: str, has_incoming_calls: bool) -> float:
      score = 0.0
      if fn.name.lower() in ENTRY_NAMES: score += 0.3
      if not has_incoming_calls:          score += 0.2
      if fn.is_exported:                  score += 0.1
      if fn.framework_role == "rest_endpoint": score += 0.3
      if file_stem.lower() in ENTRY_FILES: score += 0.1
      return min(score, 1.0)
  ```

- [ ] **3.11** `backend/app/parsing/__init__.py` — parser registry.

  ```python
  from .java import JavaParser
  from .typescript import TypeScriptParser
  from .javascript import JavaScriptParser
  from .golang import GoParser
  from .rust import RustParser
  from .kotlin import KotlinParser
  from .ruby import RubyParser
  from .c import CParser

  EXTENSION_MAP: dict[str, type] = {
      ".java": JavaParser, ".ts": TypeScriptParser, ".tsx": TypeScriptParser,
      ".js": JavaScriptParser, ".jsx": JavaScriptParser,
      ".go": GoParser, ".rs": RustParser,
      ".kt": KotlinParser, ".rb": RubyParser,
      ".c": CParser, ".h": CParser,
  }

  def get_parser(extension: str) -> BaseParser | None:
      cls = EXTENSION_MAP.get(extension)
      return cls() if cls else None
  ```

- [ ] **3.12** Commit: `feat: language parsers for TS/JS/Go/Rust/Kotlin/Ruby/C plus config and scoring`

---

## Chunk 4: RDF Builder + Indexer + Graph API

- [ ] **4.1** `backend/app/rdf/builder.py`

  Node URI scheme: `http://codegraph.dev/node/{project_id}/{kind}/{quoted_qualified_name}`

  ```python
  from rdflib import Graph, URIRef, Literal, RDF, XSD
  from urllib.parse import quote
  from .ontology import CG, load_ontology
  from ..parsing.base import ParsedFile, FunctionDef, ClassDef, ImportDef

  def _uri(project_id: str, kind: str, qname: str) -> URIRef:
      return URIRef(f"http://codegraph.dev/node/{project_id}/{kind}/{quote(qname, safe='')}")

  class RDFBuilder:
      def build(self, project_id: str, parsed_files: list[ParsedFile]) -> Graph:
          g = load_ontology()
          for pf in parsed_files:
              file_uri = _uri(project_id, "file", pf.file_path)
              g.add((file_uri, RDF.type, CG.File))
              g.add((file_uri, CG.filePath, Literal(pf.file_path)))
              g.add((file_uri, CG.language, Literal(pf.language)))
              for cls in pf.classes:
                  self._add_class(g, project_id, file_uri, cls)
              for fn in pf.functions:
                  self._add_function(g, project_id, file_uri, fn)
              for imp in pf.imports:
                  self._add_import(g, project_id, file_uri, imp)
          # second pass: wire cg:calls edges (callees may be external)
          self._add_call_edges(g, project_id, parsed_files)
          return g

      def _add_class(self, g, project_id, file_uri, cls: ClassDef):
          uri = _uri(project_id, "class", cls.qualified_name)
          g.add((uri, RDF.type, CG.Class))
          g.add((uri, CG.name, Literal(cls.name)))
          g.add((uri, CG.qualifiedName, Literal(cls.qualified_name)))
          g.add((uri, CG.line, Literal(cls.line, datatype=XSD.integer)))
          g.add((uri, CG.isExported, Literal(cls.is_exported, datatype=XSD.boolean)))
          g.add((file_uri, CG.defines, uri))
          for base in cls.inherits:
              g.add((uri, CG.inherits, _uri(project_id, "class", base)))
          for iface in cls.implements:
              g.add((uri, CG.implements, _uri(project_id, "class", iface)))
          for method in cls.methods:
              self._add_function(g, project_id, file_uri, method, owner=uri)

      def _add_function(self, g, project_id, file_uri, fn: FunctionDef, owner=None):
          uri = _uri(project_id, "function", fn.qualified_name)
          g.add((uri, RDF.type, CG.Function))
          g.add((uri, CG.name, Literal(fn.name)))
          g.add((uri, CG.qualifiedName, Literal(fn.qualified_name)))
          g.add((uri, CG.line, Literal(fn.line, datatype=XSD.integer)))
          g.add((uri, CG.visibility, Literal(fn.visibility)))
          g.add((uri, CG.isExported, Literal(fn.is_exported, datatype=XSD.boolean)))
          g.add((uri, CG.entryPointScore, Literal(fn.entry_point_score, datatype=XSD.float)))
          if fn.framework_role:
              g.add((uri, CG.frameworkRole, Literal(fn.framework_role)))
          if owner:
              g.add((owner, CG.hasMethod, uri))
          else:
              g.add((file_uri, CG.defines, uri))

      def _add_import(self, g, project_id, file_uri, imp: ImportDef):
          uri = _uri(project_id, "import", imp.source)
          g.add((uri, RDF.type, CG.Import))
          g.add((uri, CG.name, Literal(imp.source)))
          if imp.resolved_file:
              g.add((uri, CG.filePath, Literal(imp.resolved_file)))
          g.add((file_uri, CG.imports, uri))

      def _add_call_edges(self, g, project_id, parsed_files: list[ParsedFile]):
          known = {fn.qualified_name for pf in parsed_files
                   for cls in pf.classes for fn in cls.methods}
          known |= {fn.qualified_name for pf in parsed_files for fn in pf.functions}
          for pf in parsed_files:
              all_fns = [fn for cls in pf.classes for fn in cls.methods] + pf.functions
              for fn in all_fns:
                  caller = _uri(project_id, "function", fn.qualified_name)
                  for callee_name in fn.calls:
                      if callee_name in known:
                          callee = _uri(project_id, "function", callee_name)
                      else:
                          callee = _uri(project_id, "external", callee_name)
                          g.add((callee, RDF.type, CG.ExternalSymbol))
                          g.add((callee, CG.name, Literal(callee_name)))
                      g.add((caller, CG.calls, callee))
  ```

- [ ] **4.2** `backend/app/indexer.py`

  ```python
  import asyncio
  from pathlib import Path
  from .parsing import get_parser
  from .parsing.entry_point_scorer import score_entry_point
  from .rdf.builder import RDFBuilder
  from .rdf.graph_store import save_graph

  class Indexer:
      async def run(self, project_id: str, source_dir: Path, data_dir: Path, notifier=None):
          parsed_files = []
          paths = list(source_dir.rglob("*"))
          for i, path in enumerate(paths):
              if not path.is_file():
                  continue
              parser = get_parser(path.suffix)
              if parser is None:
                  continue
              source = path.read_text(errors="replace")
              pf = parser.parse(str(path), source)
              # score entry points
              call_targets = {c for pf2 in parsed_files
                              for fn in (list(pf2.functions) + [m for cls in pf2.classes for m in cls.methods])
                              for c in fn.calls}
              for fn in pf.functions + [m for cls in pf.classes for m in cls.methods]:
                  fn.entry_point_score = score_entry_point(fn, path.stem, fn.qualified_name in call_targets)
              parsed_files.append(pf)
              if notifier:
                  await notifier({"type": "progress", "current": i + 1, "total": len(paths), "file": str(path)})
          g = RDFBuilder().build(project_id, parsed_files)
          save_graph(g, project_id, data_dir)
          if notifier:
              await notifier({"type": "done", "triples": len(g)})
  ```

- [ ] **4.3** Wire reindex endpoint in `backend/app/api/projects.py`.

  ```python
  @router.post("/{project_id}/reindex", status_code=202)
  async def reindex(project_id: str, background_tasks: BackgroundTasks, db=Depends(get_db)):
      project = get_project_or_404(db, project_id)
      background_tasks.add_task(Indexer().run, project_id,
                                Path(project.source_dir), Path(settings.DATA_DIR))
      return {"status": "indexing_started"}
  ```

- [ ] **4.4** `backend/app/api/graph.py`

  ```python
  from fastapi import APIRouter, Depends, HTTPException
  from ..rdf.graph_store import load_graph
  from ..rdf.ontology import CG
  from rdflib import RDF
  from rdflib.namespace import RDFS

  router = APIRouter(prefix="/api/v1/projects", tags=["graph"])

  @router.get("/{project_id}/graph")
  def get_graph(project_id: str, data_dir: str = Depends(get_data_dir)):
      g = load_graph(project_id, Path(data_dir))
      nodes, edges = [], []
      for s, _, o in g.triples((None, RDF.type, None)):
          label = str(g.value(s, CG.name) or s)
          nodes.append({"data": {
              "id": str(s), "label": label,
              "type": str(o).split("#")[-1],
              "language": str(g.value(s, CG.language) or ""),
              "file": str(g.value(s, CG.filePath) or ""),
              "line": int(g.value(s, CG.line) or 0),
          }})
      for s, p, o in g:
          if p in (CG.calls, CG.inherits, CG.implements, CG.imports, CG.defines, CG.hasMethod):
              edges.append({"data": {
                  "source": str(s), "target": str(o),
                  "relation": str(p).split("#")[-1],
              }})
      return {"nodes": nodes, "edges": edges}
  ```

- [ ] **4.5** Tests: `tests/test_rdf/test_builder.py` — build graph from two ParsedFile fixtures (one with a call edge), assert triples for function URI, `cg:calls` edge, ExternalSymbol node exist. `tests/test_api/test_graph.py` — mock `load_graph`, GET `/api/v1/projects/test/graph`, assert response has `nodes` and `edges` lists.

- [ ] **4.6** Register router in `backend/app/main.py`.

  ```python
  from .api.graph import router as graph_router
  app.include_router(graph_router)
  ```

- [ ] **4.7** Commit: `feat: RDF builder, indexer pipeline, and graph API endpoint`
