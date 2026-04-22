# Low-Level Design: Graph Pipeline

This document explains the four-stage pipeline that turns source code into a queryable knowledge graph.

```
Source code
    │
    ▼
[1] Ontology        — schema of node types and relationships
    │
    ▼
[2] AST Parsing     — Tree-sitter produces a concrete syntax tree
    │ ParsedFile
    ▼
[3] RDF Builder     — triples written to graph.ttl
    │ graph.ttl
    ▼
[4] SPARQL Queries  — analysis, wiki, MCP tools read the graph
```

---

## 1. Ontology

**Files:** `backend/ontology.ttl`, `backend/app/rdf/ontology.py`

The ontology is an OWL/Turtle file that declares every node class, edge predicate, and datatype property used in the graph. It is loaded once at build time and merged into every `graph.ttl` so the schema travels with the data.

### Node hierarchy

```turtle
# ontology.ttl (excerpt)
cg:Callable        a owl:Class .
cg:Function        a owl:Class ; rdfs:subClassOf cg:Callable .
cg:Method          a owl:Class ; rdfs:subClassOf cg:Callable .
cg:Constructor     a owl:Class ; rdfs:subClassOf cg:Callable .

cg:TypeDefinition  a owl:Class .
cg:Class           a owl:Class ; rdfs:subClassOf cg:TypeDefinition .
cg:Interface       a owl:Class ; rdfs:subClassOf cg:TypeDefinition .
cg:Enum            a owl:Class ; rdfs:subClassOf cg:TypeDefinition .
cg:Trait           a owl:Class ; rdfs:subClassOf cg:TypeDefinition .

cg:StorageNode     a owl:Class .
cg:Field           a owl:Class ; rdfs:subClassOf cg:StorageNode .
cg:Constant        a owl:Class ; rdfs:subClassOf cg:StorageNode .

cg:File            a owl:Class .
cg:Module          a owl:Class .
cg:Import          a owl:Class .
cg:ExternalSymbol  a owl:Class .
```

### Key predicates

```turtle
# Object properties (node → node)
cg:calls        a owl:ObjectProperty .   # Function → Function/Method
cg:inherits     a owl:ObjectProperty .   # Class → Class
cg:implements   a owl:ObjectProperty .   # Class → Interface
cg:imports      a owl:ObjectProperty .   # File → Module/ExternalSymbol
cg:defines      a owl:ObjectProperty .   # File → Class/Function/…
cg:hasMethod    a owl:ObjectProperty .   # Class → Method
cg:hasField     a owl:ObjectProperty .   # Class → Field
cg:contains     a owl:ObjectProperty .   # File → Class

# Datatype properties (node → literal)
cg:name          a owl:DatatypeProperty .
cg:qualifiedName a owl:DatatypeProperty .
cg:filePath      a owl:DatatypeProperty .
cg:language      a owl:DatatypeProperty .
cg:line          a owl:DatatypeProperty .
cg:visibility    a owl:DatatypeProperty .
cg:returnType    a owl:DatatypeProperty .
cg:isAbstract    a owl:DatatypeProperty .
```

### Loading in Python

```python
# backend/app/rdf/ontology.py
from pathlib import Path
from rdflib import Graph, Namespace

CG = Namespace("http://codegraph.dev/ontology#")
_ONTOLOGY_PATH = Path(__file__).parent.parent.parent / "ontology.ttl"

def load_ontology() -> Graph:
    g = Graph()
    g.parse(str(_ONTOLOGY_PATH), format="turtle")
    return g
```

### Adding a new language to the ontology

If a new language introduces a concept that no existing class covers (e.g. Rust `trait`, Python `decorator`), add it to `ontology.ttl`:

```turtle
# Step 1 — declare the new class in ontology.ttl
cg:Decorator   a owl:Class ; rdfs:subClassOf cg:Callable .

# Step 2 — add a datatype property if needed
cg:decoratorTarget  a owl:DatatypeProperty ;
    rdfs:domain cg:Decorator ;
    rdfs:range  xsd:string .
```

Then map the new class in `builder.py`:

```python
# backend/app/rdf/builder.py
_CLASS_KIND_TO_RDF = {
    "class":          CG.Class,
    "abstract_class": CG.AbstractClass,
    "interface":      CG.Interface,
    "trait":          CG.Trait,
    "decorator":      CG.Decorator,   # ← new entry
}
```

No other files need changing — the rest of the pipeline uses this map.

---

## 2. AST Generation

**Files:** `backend/app/parsing/base.py`, `backend/app/parsing/<language>.py`, `backend/app/parsing/__init__.py`

Each language parser wraps a Tree-sitter grammar and walks the CST to produce a `ParsedFile` — a plain Python dataclass.

### Data model

```python
# backend/app/parsing/base.py (simplified)
@dataclass
class FunctionDef:
    name: str
    qualified_name: str
    line: int
    column: int
    parameters: list[ParameterDef]
    visibility: str           # "public" | "private" | "protected" | ""
    is_exported: bool
    calls: list[str]          # qualified names of callees found in the body
    return_type: str = ""
    entry_point_score: float = 0.0
    framework_role: str = ""  # "rest_endpoint", "jpa_entity", etc.

@dataclass
class ClassDef:
    name: str
    qualified_name: str
    line: int
    class_kind: str           # "class" | "interface" | "enum" | "trait" | …
    inherits: list[str]
    implements: list[str]
    fields: list[FieldDef]
    methods: list[FunctionDef]
    is_exported: bool

@dataclass
class ParsedFile:
    file_path: str
    language: str
    classes: list[ClassDef]
    functions: list[FunctionDef]   # top-level (not inside a class)
    imports: list[ImportDef]
    constants: list[ConstantDef]
    package: str = ""
    is_test: bool = False
    line_count: int = 0
    file_size: int = 0
```

### Parser base class

```python
# backend/app/parsing/base.py
class BaseParser:
    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        raise NotImplementedError

    # Shared tree-sitter helpers used by all subclasses
    def _child_text(self, node, src: bytes) -> str:
        return src[node.start_byte:node.end_byte].decode(errors="replace")

    def _find_child(self, node, *types):
        for child in node.children:
            if child.type in types:
                return child
        return None
```

### Java parser — concrete example

```python
# backend/app/parsing/java.py (simplified)
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

class JavaParser(BaseParser):
    def __init__(self):
        self._parser = Parser(Language(tsjava.language()))

    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        src = source_code.encode()
        tree = self._parser.parse(src)
        root = tree.root_node

        package = self._extract_package(root, src)
        imports = self._extract_imports(root, src)
        classes = self._extract_classes(root, src, package)

        return ParsedFile(
            file_path=file_path,
            language="java",
            package=package,
            classes=classes,
            functions=[],         # Java has no top-level functions
            imports=imports,
            constants=[],
            line_count=source_code.count("\n") + 1,
            file_size=len(source_code),
        )

    def _extract_package(self, root, src: bytes) -> str:
        for node in root.children:
            if node.type == "package_declaration":
                # package com.example.service;
                # child at index 1 is the scoped_identifier
                return self._child_text(node.children[1], src)
        return ""

    def _extract_classes(self, root, src, package) -> list[ClassDef]:
        classes = []
        for node in self._walk(root):
            if node.type == "class_declaration":
                name = self._child_text(self._find_child(node, "identifier"), src)
                qname = f"{package}.{name}" if package else name
                classes.append(ClassDef(
                    name=name,
                    qualified_name=qname,
                    line=node.start_point[0] + 1,
                    class_kind="class",
                    inherits=self._extract_superclass(node, src),
                    implements=self._extract_interfaces(node, src),
                    fields=self._extract_fields(node, src, qname),
                    methods=self._extract_methods(node, src, qname),
                    is_exported="public" in self._get_modifiers(node, src),
                ))
        return classes
```

### Parser registry

```python
# backend/app/parsing/__init__.py
from .java       import JavaParser
from .python     import PythonParser
from .typescript import TypeScriptParser
# … other languages

_EXTENSION_MAP: dict[str, type[BaseParser]] = {
    ".java":  JavaParser,
    ".py":    PythonParser,
    ".ts":    TypeScriptParser,
    ".tsx":   TypeScriptParser,
    ".js":    TypeScriptParser,
    ".rs":    RustParser,
    ".go":    GoParser,
    ".kt":    KotlinParser,
    # …
}

def get_parser(file_path: str) -> BaseParser | None:
    ext = Path(file_path).suffix.lower()
    cls = _EXTENSION_MAP.get(ext)
    return cls() if cls else None
```

### Adding a new language

```python
# 1. Install the tree-sitter grammar
#    backend/pyproject.toml
#    tree-sitter-rust = ">=0.21"

# 2. Create the parser
# backend/app/parsing/rust.py
import tree_sitter_rust as tsrust

class RustParser(BaseParser):
    def __init__(self):
        self._parser = Parser(Language(tsrust.language()))

    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        src = source_code.encode()
        tree = self._parser.parse(src)
        # … walk tree, extract structs/traits/functions
        return ParsedFile(file_path=file_path, language="rust", ...)

# 3. Register it
# backend/app/parsing/__init__.py
from .rust import RustParser
_EXTENSION_MAP[".rs"] = RustParser

# 4. Run: cd backend && uv sync
```

---

## 3. AST → TTL (RDF Builder)

**Files:** `backend/app/rdf/builder.py`, `backend/app/rdf/graph_store.py`

`RDFBuilder.build()` takes the list of `ParsedFile` objects and emits RDF triples into an `rdflib.Graph`, which is then serialised to `graph.ttl`.

### URI scheme

Every node gets a stable URI encoding its project, kind, and qualified name:

```python
# backend/app/rdf/builder.py
from urllib.parse import quote
from rdflib import URIRef

def _uri(project_id: str, kind: str, qname: str) -> URIRef:
    safe = quote(qname, safe="")
    return URIRef(f"http://codegraph.dev/node/{project_id}/{kind}/{safe}")

# Examples
# http://codegraph.dev/node/abc123/file/src/main/UserService.java
# http://codegraph.dev/node/abc123/class/com.example.UserService
# http://codegraph.dev/node/abc123/function/com.example.UserService.getUsers
# http://codegraph.dev/node/abc123/storage/com.example.UserService/id
```

### Build flow

```python
# backend/app/rdf/builder.py (simplified)
from rdflib import Graph, RDF, Literal
from app.rdf.ontology import load_ontology, CG

class RDFBuilder:
    def build(self, project_id: str, parsed_files: list[ParsedFile]) -> Graph:
        g = load_ontology()          # start with the schema

        for pf in parsed_files:
            file_uri = _uri(project_id, "file", pf.file_path)
            g.add((file_uri, RDF.type,    CG.File))
            g.add((file_uri, CG.filePath, Literal(pf.file_path)))
            g.add((file_uri, CG.language, Literal(pf.language)))

            for cls in pf.classes:
                self._add_class(g, project_id, file_uri, cls, pf.language)

            for fn in pf.functions:
                self._add_function(g, project_id, file_uri, fn, pf.language)

            for imp in pf.imports:
                self._add_import(g, project_id, file_uri, imp)

        self._add_call_edges(g, project_id, parsed_files)
        return g
```

### Adding a class node

```python
def _add_class(self, g, project_id, file_uri, cls: ClassDef, lang: str):
    cls_uri  = _uri(project_id, "class", cls.qualified_name)
    rdf_type = _CLASS_KIND_TO_RDF.get(cls.class_kind, CG.Class)

    g.add((cls_uri, RDF.type,         rdf_type))
    g.add((cls_uri, CG.name,          Literal(cls.name)))
    g.add((cls_uri, CG.qualifiedName, Literal(cls.qualified_name)))
    g.add((cls_uri, CG.language,      Literal(lang)))
    g.add((cls_uri, CG.line,          Literal(cls.line)))
    g.add((file_uri, CG.defines,      cls_uri))
    g.add((file_uri, CG.contains,     cls_uri))

    for parent in cls.inherits:
        parent_uri = _uri(project_id, "class", parent)
        g.add((cls_uri, CG.inherits, parent_uri))

    for iface in cls.implements:
        iface_uri = _uri(project_id, "class", iface)
        g.add((cls_uri, CG.implements, iface_uri))

    for method in cls.methods:
        self._add_function(g, project_id, cls_uri, method, lang, owner=cls_uri)
```

### Resolving call edges

Call targets are extracted as simple names by the parsers. The builder tries to resolve them to known qualified names before creating the edge:

```python
def _add_call_edges(self, g, project_id, parsed_files):
    # Build lookup tables from all parsed files
    all_fns: dict[str, URIRef] = {}          # qname → uri
    name_index: dict[str, list[str]] = {}    # simple_name → [qname, …]

    for pf in parsed_files:
        for fn in _all_functions(pf):
            uri = _uri(project_id, "function", fn.qualified_name)
            all_fns[fn.qualified_name] = uri
            name_index.setdefault(fn.name, []).append(fn.qualified_name)

    for pf in parsed_files:
        for fn in _all_functions(pf):
            caller = _uri(project_id, "function", fn.qualified_name)
            for callee_name in fn.calls:
                if callee_name in all_fns:
                    # Exact qualified-name match
                    g.add((caller, CG.calls, all_fns[callee_name]))
                elif callee_name in name_index:
                    # Fuzzy: match by simple name (may link to multiple targets)
                    for qname in name_index[callee_name]:
                        g.add((caller, CG.calls, all_fns[qname]))
                else:
                    # Unknown — record as external symbol
                    ext = _uri(project_id, "external", callee_name)
                    g.add((ext, RDF.type, CG.ExternalSymbol))
                    g.add((ext, CG.name, Literal(callee_name)))
                    g.add((caller, CG.calls, ext))
```

### Saving to disk

```python
# backend/app/rdf/graph_store.py
def save_graph(graph: Graph, project_id: str, data_dir: Path) -> None:
    path = data_dir / project_id / "graph.ttl"
    path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(path), format="turtle")

def load_graph(project_id: str, data_dir: Path) -> Graph:
    path = data_dir / project_id / "graph.ttl"
    g = Graph()
    g.parse(str(path), format="turtle")
    return g
```

Resulting TTL fragment:

```turtle
@prefix cg: <http://codegraph.dev/ontology#> .

<http://codegraph.dev/node/abc/class/com.example.UserService>
    a cg:Class ;
    cg:name          "UserService" ;
    cg:qualifiedName "com.example.UserService" ;
    cg:language      "java" ;
    cg:line          12 .

<http://codegraph.dev/node/abc/file/src/UserService.java>
    a cg:File ;
    cg:filePath "src/UserService.java" ;
    cg:defines  <http://codegraph.dev/node/abc/class/com.example.UserService> .

<http://codegraph.dev/node/abc/function/com.example.UserService.getUser>
    a cg:Method ;
    cg:name "getUser" ;
    cg:calls <http://codegraph.dev/node/abc/function/com.example.UserRepo.findById> .
```

---

## 4. Querying TTL (SPARQL)

**Files:** `backend/app/wiki/sparql_queries.py`, `backend/app/analysis/blast_radius.py`, `backend/app/api/analysis.py`, `backend/app/ai/nl_sparql.py`

All reads go through rdflib's built-in SPARQL 1.1 engine. The graph is loaded into memory; queries execute in-process with no separate triple store.

### Standard prefix block

Every query starts with these prefixes:

```python
# backend/app/wiki/sparql_queries.py
PREFIXES = """\
PREFIX cg:  <http://codegraph.dev/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
"""
```

### Critical rule — no subclass inference

rdflib does **not** infer subclass membership. Querying `cg:Callable` will miss `cg:Method` and `cg:Constructor`. Always enumerate concrete types with `VALUES`:

```sparql
-- WRONG: returns nothing for Methods/Constructors
SELECT ?fn WHERE { ?fn a cg:Callable }

-- CORRECT
SELECT ?fn ?name WHERE {
  VALUES ?type { cg:Function cg:Method cg:Constructor }
  ?fn a ?type ;
      cg:name ?name .
}
```

### Counting nodes by type

```python
# backend/app/wiki/sparql_queries.py
PROJECT_STATS = PREFIXES + """
SELECT
  (COUNT(DISTINCT ?f)  AS ?fileCount)
  (COUNT(DISTINCT ?fn) AS ?functionCount)
  (COUNT(DISTINCT ?cl) AS ?classCount)
WHERE {
  OPTIONAL { ?f  a cg:File . }
  OPTIONAL {
    ?fn a ?fnType .
    VALUES ?fnType { cg:Function cg:Method cg:Constructor }
  }
  OPTIONAL {
    ?cl a ?clType .
    VALUES ?clType { cg:Class cg:AbstractClass cg:DataClass
                     cg:Interface cg:Enum cg:Struct cg:Trait cg:Mixin }
  }
}
"""
```

### Executing a query

```python
from rdflib import Graph
from app.rdf.graph_store import load_graph

graph: Graph = load_graph(project_id, data_dir)

rows = graph.query(PROJECT_STATS)
for row in rows:
    print(row.fileCount, row.functionCount, row.classCount)
```

### Finding callers of a function

```sparql
PREFIX cg:  <http://codegraph.dev/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?caller ?callerName ?type WHERE {
  ?caller cg:calls <http://codegraph.dev/node/abc/function/com.example.Repo.findById> .
  ?caller cg:name  ?callerName .
  ?caller a        ?type .
}
```

### Blast radius (direct + transitive callers)

Direct callers come from SPARQL; transitive callers are computed with NetworkX:

```python
# backend/app/analysis/blast_radius.py
import networkx as nx
from rdflib import URIRef

def compute_blast_radius(graph: Graph, node_uri: str) -> dict:
    target = URIRef(node_uri)

    # 1. Direct callers via a single SPARQL triple pattern
    direct = {
        str(s)
        for s, _, _ in graph.triples((None, CG.calls, target))
    }

    # 2. Build a directed call graph and walk ancestors
    dg = nx.DiGraph()
    for s, _, o in graph.triples((None, CG.calls, None)):
        dg.add_edge(str(s), str(o))

    transitive = nx.ancestors(dg, node_uri) if node_uri in dg else set()

    return {
        "target_node":         node_uri,
        "direct_callers":      sorted(direct),
        "transitive_callers":  sorted(transitive - direct),
        "severity":            len(direct | transitive),
    }
```

### Parameterised SPARQL in the API

The `/sparql` endpoint accepts an arbitrary query string, validates it is a `SELECT`, and returns JSON-serialised bindings:

```python
# backend/app/api/analysis.py (simplified)
@router.post("/{project_id}/sparql")
async def run_sparql(project_id: str, body: SparqlRequest):
    graph = get_project_graph(project_id)
    results = graph.query(body.query)
    bindings = [
        {str(var): str(val) for var, val in row.asdict().items()}
        for row in results
    ]
    return {"results": {"bindings": bindings[:500]}}   # cap at 500 rows
```

### Natural language → SPARQL (Claude API)

The backend converts a plain-English question to SPARQL using the Claude API, then executes the generated query:

```python
# backend/app/ai/nl_sparql.py (simplified)
import anthropic

_SYSTEM_PROMPT = """
You are a SPARQL query generator for a code knowledge graph.
Ontology namespace: PREFIX cg: <http://codegraph.dev/ontology#>
Node types: cg:File, cg:Class, cg:Method, cg:Function, cg:Interface, ...
Predicates: cg:calls, cg:inherits, cg:implements, cg:defines, cg:name, ...
Always use VALUES to enumerate concrete types. Return only the SPARQL query.
"""

def nl_to_sparql(graph: Graph, question: str, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    sparql = resp.content[0].text.strip()
    results = graph.query(sparql)
    return {"query": sparql, "results": _serialize(results)}
```

---

## Summary

| Stage | Input | Output | Key file |
|---|---|---|---|
| Ontology | `ontology.ttl` | `rdflib.Namespace` (CG) | `app/rdf/ontology.py` |
| AST Parsing | Source file bytes | `ParsedFile` dataclass | `app/parsing/<lang>.py` |
| RDF Build | `list[ParsedFile]` | `graph.ttl` | `app/rdf/builder.py` |
| SPARQL Query | `graph.ttl` + query string | JSON bindings | `app/wiki/sparql_queries.py`, `app/analysis/` |

The ontology is the contract between the parser and every downstream consumer — extend it when a language introduces a concept no existing class covers.
