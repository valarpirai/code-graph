# Wiki Generation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate structured markdown wiki files from the project's RDF graph by running SPARQL queries through Jinja2 templates, exposed via a FastAPI router and triggered manually from the UI.

**Architecture:** A `WikiGenerator` class orchestrates everything: it runs named SPARQL queries (defined in `sparql_queries.py`) against the project's `graph.ttl`, feeds the results into Jinja2 templates, and writes `.md` files under `/data/{project-id}/wiki/`. Three FastAPI endpoints (generate, list, fetch) are added to a new `api/wiki.py` router that is registered in `main.py`.

**Tech Stack:** Python 3.11+, FastAPI, rdflib (SPARQL), Jinja2, pytest, tmp_path fixture

---

## File Map

```
backend/
  app/
    wiki/
      __init__.py
      generator.py              # WikiGenerator: queries → templates → .md files
      sparql_queries.py         # named SPARQL query strings
      templates/
        index.md.j2
        class.md.j2
        module.md.j2
        function.md.j2
    api/
      wiki.py                   # FastAPI router: generate, list, fetch
  tests/
    test_wiki/
      __init__.py
      test_sparql_queries.py
      test_generator.py
    test_api/
      test_wiki_endpoints.py
```

---

## Chunk 1: Jinja2 Templates + SPARQL Queries + Query Tests

### Task 1.1: Create the wiki package skeleton

**Files:**
- Create: `backend/app/wiki/__init__.py`
- Create: `backend/app/wiki/templates/` (directory)
- Create: `backend/tests/test_wiki/__init__.py`

- [ ] **Step 1: Create package init files**

`backend/app/wiki/__init__.py` — empty file to mark the package.

`backend/tests/test_wiki/__init__.py` — empty file.

```bash
# Run from backend/
touch app/wiki/__init__.py
mkdir -p app/wiki/templates
touch tests/test_wiki/__init__.py
```

---

### Task 1.2: Write SPARQL queries module

**File:** `backend/app/wiki/sparql_queries.py`

This module contains all named SPARQL query strings used during wiki generation. Prefixes match the ontology defined in Plan 2 (`cg:`, `rdfs:`, `xsd:`).

- [ ] **Step 1: Write the file**

```python
# backend/app/wiki/sparql_queries.py

PREFIXES = """
PREFIX cg: <http://codegraph.dev/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

# --- Index page queries ---

PROJECT_STATS = PREFIXES + """
SELECT
  (COUNT(DISTINCT ?f) AS ?fileCount)
  (COUNT(DISTINCT ?fn) AS ?functionCount)
  (COUNT(DISTINCT ?cl) AS ?classCount)
  (COUNT(DISTINCT ?fd) AS ?fieldCount)
WHERE {
  OPTIONAL { ?f a cg:File . }
  OPTIONAL { ?fn a cg:Function . }
  OPTIONAL { ?cl a cg:Class . }
  OPTIONAL { ?fd a cg:Field . }
}
"""

PROJECT_LANGUAGES = PREFIXES + """
SELECT DISTINCT ?language
WHERE {
  ?f a cg:File ;
     cg:language ?language .
}
ORDER BY ?language
"""

TOP_LEVEL_MODULES = PREFIXES + """
SELECT ?module ?filePath
WHERE {
  ?module a cg:Module ;
          cg:filePath ?filePath .
}
ORDER BY ?filePath
"""

CLUSTER_SUMMARY = PREFIXES + """
SELECT ?cluster ?cohesionScore ?topNode
WHERE {
  ?cluster a cg:Cluster ;
           cg:cohesionScore ?cohesionScore .
  OPTIONAL {
    ?cluster cg:hasNode ?topNode .
  }
}
ORDER BY DESC(?cohesionScore)
"""

# --- Class page queries ---

CLASS_DETAILS = PREFIXES + """
SELECT ?cls ?name ?filePath ?language ?lineNumber
WHERE {
  ?cls a cg:Class ;
       cg:name ?name ;
       cg:filePath ?filePath .
  OPTIONAL { ?cls cg:language ?language . }
  OPTIONAL { ?cls cg:lineNumber ?lineNumber . }
}
ORDER BY ?name
"""

CLASS_INHERITANCE = PREFIXES + """
SELECT ?cls ?parent
WHERE {
  ?cls a cg:Class ;
       cg:inherits ?parent .
}
"""

CLASS_INTERFACES = PREFIXES + """
SELECT ?cls ?iface
WHERE {
  ?cls a cg:Class ;
       cg:implements ?iface .
}
"""

CLASS_MIXINS = PREFIXES + """
SELECT ?cls ?mixin
WHERE {
  ?cls a cg:Class ;
       cg:mixes ?mixin .
}
"""

CLASS_FIELDS = PREFIXES + """
SELECT ?cls ?fieldName ?fieldType ?visibility ?mutability ?defaultValue
WHERE {
  ?cls a cg:Class ;
       cg:hasField ?field .
  ?field cg:name ?fieldName .
  OPTIONAL { ?field cg:type ?fieldType . }
  OPTIONAL { ?field cg:visibility ?visibility . }
  OPTIONAL { ?field cg:mutability ?mutability . }
  OPTIONAL { ?field cg:defaultValue ?defaultValue . }
}
ORDER BY ?cls ?fieldName
"""

CLASS_METHODS = PREFIXES + """
SELECT ?cls ?methodName ?returnType ?lineNumber
WHERE {
  ?cls a cg:Class ;
       cg:hasMethod ?method .
  ?method cg:name ?methodName .
  OPTIONAL { ?method cg:returnType ?returnType . }
  OPTIONAL { ?method cg:lineNumber ?lineNumber . }
}
ORDER BY ?cls ?methodName
"""

METHOD_PARAMETERS = PREFIXES + """
SELECT ?method ?paramName ?paramType
WHERE {
  ?method cg:hasParameter ?param .
  ?param cg:name ?paramName .
  OPTIONAL { ?param cg:type ?paramType . }
}
ORDER BY ?method ?paramName
"""

CLASS_CALLERS = PREFIXES + """
SELECT ?caller ?callerName ?callerType
WHERE {
  ?caller cg:calls ?method .
  ?method cg:belongsTo ?cls .
  ?cls a cg:Class ;
       cg:name ?clsName .
  FILTER(?clsName = ?targetName)
  ?caller cg:name ?callerName .
  ?caller a ?callerType .
}
"""

CLASS_DEPENDENCIES = PREFIXES + """
SELECT DISTINCT ?cls ?dep ?depName
WHERE {
  ?cls a cg:Class .
  ?cls cg:hasMethod ?method .
  ?method cg:calls ?depNode .
  ?depNode cg:belongsTo ?dep .
  ?dep a cg:Class ;
       cg:name ?depName .
  FILTER(?dep != ?cls)
}
ORDER BY ?cls ?depName
"""

CLASS_CLUSTER = PREFIXES + """
SELECT ?cls ?cluster ?cohesionScore
WHERE {
  ?cluster a cg:Cluster ;
           cg:hasNode ?cls ;
           cg:cohesionScore ?cohesionScore .
}
"""

# --- Function page queries ---

STANDALONE_FUNCTIONS = PREFIXES + """
SELECT ?fn ?name ?filePath ?language ?lineNumber ?module
WHERE {
  ?fn a cg:Function ;
      cg:name ?name ;
      cg:filePath ?filePath .
  OPTIONAL { ?fn cg:language ?language . }
  OPTIONAL { ?fn cg:lineNumber ?lineNumber . }
  OPTIONAL { ?fn cg:belongsTo ?module . }
  FILTER NOT EXISTS { ?cls a cg:Class ; cg:hasMethod ?fn . }
}
ORDER BY ?name
"""

FUNCTION_PARAMETERS = PREFIXES + """
SELECT ?fn ?paramName ?paramType
WHERE {
  ?fn a cg:Function ;
      cg:hasParameter ?param .
  ?param cg:name ?paramName .
  OPTIONAL { ?param cg:type ?paramType . }
}
ORDER BY ?fn ?paramName
"""

FUNCTION_LOCAL_VARS = PREFIXES + """
SELECT ?fn ?varName ?varType ?mutability
WHERE {
  ?fn a cg:Function ;
      cg:hasLocalVar ?var .
  ?var cg:name ?varName .
  OPTIONAL { ?var cg:type ?varType . }
  OPTIONAL { ?var cg:mutability ?mutability . }
}
ORDER BY ?fn ?varName
"""

FUNCTION_CALLERS = PREFIXES + """
SELECT ?fn ?caller ?callerName
WHERE {
  ?caller cg:calls ?fn .
  ?caller cg:name ?callerName .
}
"""

FUNCTION_CALLEES = PREFIXES + """
SELECT ?fn ?callee ?calleeName
WHERE {
  ?fn cg:calls ?callee .
  ?callee cg:name ?calleeName .
}
ORDER BY ?fn ?calleeName
"""

FUNCTION_FRAMEWORK_ROLE = PREFIXES + """
SELECT ?fn ?role ?entryPointScore
WHERE {
  ?fn a cg:Function .
  OPTIONAL { ?fn cg:frameworkRole ?role . }
  OPTIONAL { ?fn cg:entryPointScore ?entryPointScore . }
}
"""

FUNCTION_CLUSTER = PREFIXES + """
SELECT ?fn ?cluster ?cohesionScore
WHERE {
  ?cluster a cg:Cluster ;
           cg:hasNode ?fn ;
           cg:cohesionScore ?cohesionScore .
}
"""

# --- Module page queries ---

MODULE_DETAILS = PREFIXES + """
SELECT ?module ?name ?filePath
WHERE {
  ?module a cg:Module ;
          cg:name ?name ;
          cg:filePath ?filePath .
}
ORDER BY ?name
"""

MODULE_CLASSES = PREFIXES + """
SELECT ?module ?cls ?clsName
WHERE {
  ?cls a cg:Class ;
       cg:name ?clsName ;
       cg:belongsTo ?module .
}
ORDER BY ?module ?clsName
"""

MODULE_FUNCTIONS = PREFIXES + """
SELECT ?module ?fn ?fnName
WHERE {
  ?fn a cg:Function ;
      cg:name ?fnName ;
      cg:belongsTo ?module .
  FILTER NOT EXISTS { ?cls a cg:Class ; cg:hasMethod ?fn . }
}
ORDER BY ?module ?fnName
"""

MODULE_CONSTANTS = PREFIXES + """
SELECT ?module ?constName ?constValue ?constType
WHERE {
  ?module a cg:Module .
  ?const a cg:Constant ;
         cg:name ?constName ;
         cg:belongsTo ?module .
  OPTIONAL { ?const cg:value ?constValue . }
  OPTIONAL { ?const cg:type ?constType . }
}
ORDER BY ?module ?constName
"""

MODULE_IMPORTS = PREFIXES + """
SELECT ?module ?importTarget
WHERE {
  ?module a cg:Module ;
          cg:imports ?importTarget .
}
ORDER BY ?module ?importTarget
"""
```

---

### Task 1.3: Write Jinja2 templates

**Files:**
- `backend/app/wiki/templates/index.md.j2`
- `backend/app/wiki/templates/class.md.j2`
- `backend/app/wiki/templates/module.md.j2`
- `backend/app/wiki/templates/function.md.j2`

- [ ] **Step 1: index.md.j2**

`backend/app/wiki/templates/index.md.j2`:

```jinja
# {{ project.name }}

**Source URL:** {{ project.source_url }}
**Last Indexed:** {{ project.last_indexed }}

---

## Languages

{% for lang in languages -%}
- {{ lang }}
{% endfor %}

---

## Statistics

| Metric | Count |
|--------|-------|
| Files | {{ stats.fileCount }} |
| Functions | {{ stats.functionCount }} |
| Classes | {{ stats.classCount }} |
| Fields | {{ stats.fieldCount }} |

---

## Modules

{% for mod in modules -%}
- [{{ mod.name }}](modules/{{ mod.name }}.md) — `{{ mod.filePath }}`
{% endfor %}

---

## Functional Clusters

| Cluster | Cohesion Score | Top Node |
|---------|---------------|----------|
{% for c in clusters -%}
| {{ c.cluster }} | {{ c.cohesionScore }} | {{ c.topNode or '' }} |
{% endfor %}
```

- [ ] **Step 2: class.md.j2**

`backend/app/wiki/templates/class.md.j2`:

```jinja
# Class: {{ cls.name }}

**File:** `{{ cls.filePath }}`
**Language:** {{ cls.language or 'unknown' }}
**Line:** {{ cls.lineNumber or 'N/A' }}

---

{% if inheritance %}
## Inheritance

{% for parent in inheritance -%}
- `{{ parent }}`
{% endfor %}
{% endif %}

{% if interfaces %}
## Implements

{% for iface in interfaces -%}
- `{{ iface }}`
{% endfor %}
{% endif %}

{% if mixins %}
## Mixins

{% for mixin in mixins -%}
- `{{ mixin }}`
{% endfor %}
{% endif %}

## Fields

| Name | Type | Visibility | Mutability | Default |
|------|------|------------|------------|---------|
{% for f in fields -%}
| {{ f.fieldName }} | {{ f.fieldType or '' }} | {{ f.visibility or '' }} | {{ f.mutability or '' }} | {{ f.defaultValue or '' }} |
{% endfor %}

## Methods

| Name | Return Type | Line |
|------|-------------|------|
{% for m in methods -%}
| {{ m.methodName }} | {{ m.returnType or '' }} | {{ m.lineNumber or '' }} |
{% endfor %}

---

## Callers

{% if callers %}
{% for c in callers -%}
- `{{ c.callerName }}` ({{ c.callerType }})
{% endfor %}
{% else %}
_No callers found._
{% endif %}

## Dependencies

{% if dependencies %}
{% for d in dependencies -%}
- [{{ d.depName }}]({{ d.depName }}.md)
{% endfor %}
{% else %}
_No outgoing class dependencies._
{% endif %}

---

## Cluster

{% if cluster %}
**Cluster ID:** {{ cluster.cluster }}
**Cohesion Score:** {{ cluster.cohesionScore }}
{% else %}
_Not assigned to a cluster._
{% endif %}
```

- [ ] **Step 3: module.md.j2**

`backend/app/wiki/templates/module.md.j2`:

```jinja
# Module: {{ module.name }}

**File:** `{{ module.filePath }}`

---

## Classes

{% if classes %}
{% for c in classes -%}
- [{{ c.clsName }}](../classes/{{ c.clsName }}.md)
{% endfor %}
{% else %}
_No classes in this module._
{% endif %}

## Standalone Functions

{% if functions %}
{% for f in functions -%}
- [{{ f.fnName }}](../functions/{{ module.name }}_{{ f.fnName }}.md)
{% endfor %}
{% else %}
_No standalone functions in this module._
{% endif %}

## Constants

{% if constants %}
| Name | Type | Value |
|------|------|-------|
{% for c in constants -%}
| {{ c.constName }} | {{ c.constType or '' }} | {{ c.constValue or '' }} |
{% endfor %}
{% else %}
_No constants in this module._
{% endif %}

## Import Dependencies

{% if imports %}
{% for i in imports -%}
- `{{ i.importTarget }}`
{% endfor %}
{% else %}
_No imports recorded._
{% endif %}
```

- [ ] **Step 4: function.md.j2**

`backend/app/wiki/templates/function.md.j2`:

```jinja
# Function: {{ fn.name }}

**File:** `{{ fn.filePath }}`
**Language:** {{ fn.language or 'unknown' }}
**Line:** {{ fn.lineNumber or 'N/A' }}

---

## Parameters

{% if parameters %}
| Name | Type |
|------|------|
{% for p in parameters -%}
| {{ p.paramName }} | {{ p.paramType or '' }} |
{% endfor %}
{% else %}
_No parameters._
{% endif %}

## Local Variables

{% if local_vars %}
| Name | Type | Mutability |
|------|------|------------|
{% for v in local_vars -%}
| {{ v.varName }} | {{ v.varType or '' }} | {{ v.mutability or '' }} |
{% endfor %}
{% else %}
_No local variables recorded._
{% endif %}

---

## Callers

{% if callers %}
{% for c in callers -%}
- `{{ c.callerName }}`
{% endfor %}
{% else %}
_No callers found._
{% endif %}

## Callees

{% if callees %}
{% for c in callees -%}
- `{{ c.calleeName }}`
{% endfor %}
{% else %}
_No callees found._
{% endif %}

---

## Framework Role

{% if framework_role %}
**Role:** {{ framework_role.role or 'N/A' }}
**Entry Point Score:** {{ framework_role.entryPointScore or '0' }}
{% else %}
_No framework role assigned._
{% endif %}

## Cluster

{% if cluster %}
**Cluster ID:** {{ cluster.cluster }}
**Cohesion Score:** {{ cluster.cohesionScore }}
{% else %}
_Not assigned to a cluster._
{% endif %}
```

---

### Task 1.4: Write SPARQL query tests

**File:** `backend/tests/test_wiki/test_sparql_queries.py`

Tests build small inline RDF graphs using rdflib and run SPARQL queries from `sparql_queries.py` against them, checking the returned rows match the fixture data.

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_wiki/test_sparql_queries.py

import pytest
from rdflib import Graph, Literal, URIRef, Namespace
from rdflib.namespace import RDF, RDFS, XSD
from app.wiki import sparql_queries as Q

CG = Namespace("http://codegraph.dev/ontology#")

# -----------------------------------------------------------------------
# Fixture graph builders
# -----------------------------------------------------------------------

def make_stats_graph() -> Graph:
    g = Graph()
    g.bind("cg", CG)
    file1 = URIRef("http://example.org/file1")
    fn1   = URIRef("http://example.org/fn1")
    fn2   = URIRef("http://example.org/fn2")
    cls1  = URIRef("http://example.org/cls1")
    fld1  = URIRef("http://example.org/fld1")
    g.add((file1, RDF.type, CG.File))
    g.add((fn1,   RDF.type, CG.Function))
    g.add((fn2,   RDF.type, CG.Function))
    g.add((cls1,  RDF.type, CG.Class))
    g.add((fld1,  RDF.type, CG.Field))
    return g


def make_class_graph() -> Graph:
    g = Graph()
    g.bind("cg", CG)
    cls1   = URIRef("http://example.org/cls/MyClass")
    parent = URIRef("http://example.org/cls/BaseClass")
    iface  = URIRef("http://example.org/cls/Serializable")
    mixin  = URIRef("http://example.org/cls/LogMixin")
    field1 = URIRef("http://example.org/fld/name")
    method1 = URIRef("http://example.org/method/greet")
    param1  = URIRef("http://example.org/param/greeting")

    g.add((cls1, RDF.type, CG.Class))
    g.add((cls1, CG.name, Literal("MyClass")))
    g.add((cls1, CG.filePath, Literal("src/myclass.py")))
    g.add((cls1, CG.language, Literal("python")))
    g.add((cls1, CG.lineNumber, Literal(10, datatype=XSD.integer)))
    g.add((cls1, CG.inherits, parent))
    g.add((cls1, CG.implements, iface))
    g.add((cls1, CG.mixes, mixin))
    g.add((cls1, CG.hasField, field1))
    g.add((field1, CG.name, Literal("name")))
    g.add((field1, CG.type, Literal("str")))
    g.add((field1, CG.visibility, Literal("public")))
    g.add((cls1, CG.hasMethod, method1))
    g.add((method1, CG.name, Literal("greet")))
    g.add((method1, CG.returnType, Literal("str")))
    g.add((method1, CG.hasParameter, param1))
    g.add((param1, CG.name, Literal("greeting")))
    g.add((param1, CG.type, Literal("str")))
    return g


def make_function_graph() -> Graph:
    g = Graph()
    g.bind("cg", CG)
    fn1    = URIRef("http://example.org/fn/compute")
    param1 = URIRef("http://example.org/param/x")
    var1   = URIRef("http://example.org/var/result")
    callee = URIRef("http://example.org/fn/helper")
    mod1   = URIRef("http://example.org/mod/utils")

    g.add((fn1, RDF.type, CG.Function))
    g.add((fn1, CG.name, Literal("compute")))
    g.add((fn1, CG.filePath, Literal("src/utils.py")))
    g.add((fn1, CG.language, Literal("python")))
    g.add((fn1, CG.lineNumber, Literal(5, datatype=XSD.integer)))
    g.add((fn1, CG.belongsTo, mod1))
    g.add((fn1, CG.hasParameter, param1))
    g.add((param1, CG.name, Literal("x")))
    g.add((param1, CG.type, Literal("int")))
    g.add((fn1, CG.hasLocalVar, var1))
    g.add((var1, CG.name, Literal("result")))
    g.add((var1, CG.type, Literal("int")))
    g.add((fn1, CG.calls, callee))
    g.add((callee, CG.name, Literal("helper")))
    g.add((fn1, CG.frameworkRole, Literal("rest_endpoint")))
    g.add((fn1, CG.entryPointScore, Literal(0.9, datatype=XSD.float)))
    return g


def make_module_graph() -> Graph:
    g = Graph()
    g.bind("cg", CG)
    mod1   = URIRef("http://example.org/mod/utils")
    cls1   = URIRef("http://example.org/cls/Helper")
    fn1    = URIRef("http://example.org/fn/compute")
    const1 = URIRef("http://example.org/const/MAX")

    g.add((mod1, RDF.type, CG.Module))
    g.add((mod1, CG.name, Literal("utils")))
    g.add((mod1, CG.filePath, Literal("src/utils.py")))
    g.add((cls1, RDF.type, CG.Class))
    g.add((cls1, CG.name, Literal("Helper")))
    g.add((cls1, CG.belongsTo, mod1))
    g.add((fn1, RDF.type, CG.Function))
    g.add((fn1, CG.name, Literal("compute")))
    g.add((fn1, CG.belongsTo, mod1))
    g.add((const1, RDF.type, CG.Constant))
    g.add((const1, CG.name, Literal("MAX")))
    g.add((const1, CG.value, Literal("100")))
    g.add((const1, CG.type, Literal("int")))
    g.add((const1, CG.belongsTo, mod1))
    g.add((mod1, CG.imports, Literal("os")))
    return g


# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------

class TestProjectStatsQuery:
    def test_counts_entities_correctly(self):
        g = make_stats_graph()
        results = list(g.query(Q.PROJECT_STATS))
        assert len(results) == 1
        row = results[0]
        assert int(row.fileCount) == 1
        assert int(row.functionCount) == 2
        assert int(row.classCount) == 1
        assert int(row.fieldCount) == 1


class TestProjectLanguagesQuery:
    def test_returns_distinct_languages(self):
        g = Graph()
        g.bind("cg", CG)
        f1 = URIRef("http://example.org/f1")
        f2 = URIRef("http://example.org/f2")
        f3 = URIRef("http://example.org/f3")
        g.add((f1, RDF.type, CG.File))
        g.add((f1, CG.language, Literal("python")))
        g.add((f2, RDF.type, CG.File))
        g.add((f2, CG.language, Literal("python")))
        g.add((f3, RDF.type, CG.File))
        g.add((f3, CG.language, Literal("javascript")))

        results = list(g.query(Q.PROJECT_LANGUAGES))
        langs = [str(r.language) for r in results]
        assert sorted(langs) == ["javascript", "python"]


class TestClassDetailsQuery:
    def test_returns_class_with_all_fields(self):
        g = make_class_graph()
        results = list(g.query(Q.CLASS_DETAILS))
        assert len(results) == 1
        row = results[0]
        assert str(row.name) == "MyClass"
        assert str(row.filePath) == "src/myclass.py"
        assert str(row.language) == "python"
        assert int(row.lineNumber) == 10


class TestClassInheritanceQuery:
    def test_returns_parent_class(self):
        g = make_class_graph()
        results = list(g.query(Q.CLASS_INHERITANCE))
        assert len(results) == 1
        assert str(results[0].parent) == "http://example.org/cls/BaseClass"


class TestClassInterfacesQuery:
    def test_returns_interface(self):
        g = make_class_graph()
        results = list(g.query(Q.CLASS_INTERFACES))
        assert len(results) == 1
        assert str(results[0].iface) == "http://example.org/cls/Serializable"


class TestClassMixinsQuery:
    def test_returns_mixin(self):
        g = make_class_graph()
        results = list(g.query(Q.CLASS_MIXINS))
        assert len(results) == 1
        assert str(results[0].mixin) == "http://example.org/cls/LogMixin"


class TestClassFieldsQuery:
    def test_returns_field_with_type_and_visibility(self):
        g = make_class_graph()
        results = list(g.query(Q.CLASS_FIELDS))
        assert len(results) == 1
        row = results[0]
        assert str(row.fieldName) == "name"
        assert str(row.fieldType) == "str"
        assert str(row.visibility) == "public"


class TestClassMethodsQuery:
    def test_returns_method_with_return_type(self):
        g = make_class_graph()
        results = list(g.query(Q.CLASS_METHODS))
        assert len(results) == 1
        row = results[0]
        assert str(row.methodName) == "greet"
        assert str(row.returnType) == "str"


class TestMethodParametersQuery:
    def test_returns_parameter_for_method(self):
        g = make_class_graph()
        results = list(g.query(Q.METHOD_PARAMETERS))
        assert len(results) == 1
        row = results[0]
        assert str(row.paramName) == "greeting"
        assert str(row.paramType) == "str"


class TestStandaloneFunctionsQuery:
    def test_returns_function_not_belonging_to_class(self):
        g = make_function_graph()
        results = list(g.query(Q.STANDALONE_FUNCTIONS))
        names = [str(r.name) for r in results]
        assert "compute" in names

    def test_excludes_class_methods(self):
        g = make_class_graph()
        # method1 belongs to cls1 via cg:hasMethod — should not appear
        results = list(g.query(Q.STANDALONE_FUNCTIONS))
        names = [str(r.name) for r in results]
        assert "greet" not in names


class TestFunctionParametersQuery:
    def test_returns_parameter(self):
        g = make_function_graph()
        results = list(g.query(Q.FUNCTION_PARAMETERS))
        assert len(results) == 1
        assert str(results[0].paramName) == "x"
        assert str(results[0].paramType) == "int"


class TestFunctionLocalVarsQuery:
    def test_returns_local_var(self):
        g = make_function_graph()
        results = list(g.query(Q.FUNCTION_LOCAL_VARS))
        assert len(results) == 1
        assert str(results[0].varName) == "result"


class TestFunctionCalleesQuery:
    def test_returns_callee(self):
        g = make_function_graph()
        results = list(g.query(Q.FUNCTION_CALLEES))
        assert len(results) == 1
        assert str(results[0].calleeName) == "helper"


class TestModuleDetailsQuery:
    def test_returns_module(self):
        g = make_module_graph()
        results = list(g.query(Q.MODULE_DETAILS))
        assert len(results) == 1
        row = results[0]
        assert str(row.name) == "utils"
        assert str(row.filePath) == "src/utils.py"


class TestModuleClassesQuery:
    def test_returns_class_in_module(self):
        g = make_module_graph()
        results = list(g.query(Q.MODULE_CLASSES))
        assert len(results) == 1
        assert str(results[0].clsName) == "Helper"


class TestModuleFunctionsQuery:
    def test_returns_standalone_function_in_module(self):
        g = make_module_graph()
        results = list(g.query(Q.MODULE_FUNCTIONS))
        names = [str(r.fnName) for r in results]
        assert "compute" in names


class TestModuleConstantsQuery:
    def test_returns_constant(self):
        g = make_module_graph()
        results = list(g.query(Q.MODULE_CONSTANTS))
        assert len(results) == 1
        row = results[0]
        assert str(row.constName) == "MAX"
        assert str(row.constValue) == "100"
        assert str(row.constType) == "int"


class TestModuleImportsQuery:
    def test_returns_import(self):
        g = make_module_graph()
        results = list(g.query(Q.MODULE_IMPORTS))
        assert len(results) == 1
        assert str(results[0].importTarget) == "os"
```

- [ ] **Step 2: Run failing tests**

```bash
cd backend
pytest tests/test_wiki/test_sparql_queries.py -v 2>&1 | head -30
```

Expected output (before implementation):
```
ERRORS or ImportError: No module named 'app.wiki.sparql_queries'
```

- [ ] **Step 3: Implement `sparql_queries.py`** (done in Task 1.2 above)

- [ ] **Step 4: Run tests — expect all green**

```bash
cd backend
pytest tests/test_wiki/test_sparql_queries.py -v
```

Expected output:
```
tests/test_wiki/test_sparql_queries.py::TestProjectStatsQuery::test_counts_entities_correctly PASSED
tests/test_wiki/test_sparql_queries.py::TestProjectLanguagesQuery::test_returns_distinct_languages PASSED
tests/test_wiki/test_sparql_queries.py::TestClassDetailsQuery::test_returns_class_with_all_fields PASSED
...
PASSED (all 17 tests)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/wiki/ backend/tests/test_wiki/
git commit -m "feat(wiki): add SPARQL query strings, Jinja2 templates, and query tests (Chunk 1)"
```

---

## Chunk 2: WikiGenerator Class + File Generation Tests

### Task 2.1: Write `generator.py`

**File:** `backend/app/wiki/generator.py`

The `WikiGenerator` class:
1. Accepts a project data directory path and an rdflib `Graph`.
2. Clears existing `wiki/` output directory.
3. Runs SPARQL queries to collect data.
4. Renders Jinja2 templates.
5. Writes `.md` files to `wiki/` subdirectories.

- [ ] **Step 1: Write the failing test first**

`backend/tests/test_wiki/test_generator.py`:

```python
# backend/tests/test_wiki/test_generator.py

import pytest
from pathlib import Path
from rdflib import Graph, Literal, URIRef, Namespace
from rdflib.namespace import RDF, XSD

CG = Namespace("http://codegraph.dev/ontology#")


def make_full_fixture_graph() -> Graph:
    """Fixture graph with one module, one class, one standalone function."""
    g = Graph()
    g.bind("cg", CG)

    mod1    = URIRef("http://example.org/mod/mymodule")
    cls1    = URIRef("http://example.org/cls/Widget")
    fn1     = URIRef("http://example.org/fn/build")
    field1  = URIRef("http://example.org/fld/size")
    method1 = URIRef("http://example.org/method/render")
    param1  = URIRef("http://example.org/param/color")
    var1    = URIRef("http://example.org/var/tmp")
    file1   = URIRef("http://example.org/file/main")
    cluster = URIRef("http://example.org/cluster/c1")

    # Module
    g.add((mod1, RDF.type, CG.Module))
    g.add((mod1, CG.name, Literal("mymodule")))
    g.add((mod1, CG.filePath, Literal("src/mymodule.py")))
    g.add((mod1, CG.imports, Literal("os")))

    # Class
    g.add((cls1, RDF.type, CG.Class))
    g.add((cls1, CG.name, Literal("Widget")))
    g.add((cls1, CG.filePath, Literal("src/mymodule.py")))
    g.add((cls1, CG.language, Literal("python")))
    g.add((cls1, CG.lineNumber, Literal(5, datatype=XSD.integer)))
    g.add((cls1, CG.belongsTo, mod1))
    g.add((cls1, CG.hasField, field1))
    g.add((field1, CG.name, Literal("size")))
    g.add((field1, CG.type, Literal("int")))
    g.add((field1, CG.visibility, Literal("public")))
    g.add((cls1, CG.hasMethod, method1))
    g.add((method1, CG.name, Literal("render")))
    g.add((method1, CG.returnType, Literal("str")))
    g.add((method1, CG.hasParameter, param1))
    g.add((param1, CG.name, Literal("color")))
    g.add((param1, CG.type, Literal("str")))

    # Standalone function
    g.add((fn1, RDF.type, CG.Function))
    g.add((fn1, CG.name, Literal("build")))
    g.add((fn1, CG.filePath, Literal("src/mymodule.py")))
    g.add((fn1, CG.language, Literal("python")))
    g.add((fn1, CG.lineNumber, Literal(20, datatype=XSD.integer)))
    g.add((fn1, CG.belongsTo, mod1))
    g.add((fn1, CG.hasLocalVar, var1))
    g.add((var1, CG.name, Literal("tmp")))
    g.add((var1, CG.type, Literal("str")))
    g.add((fn1, CG.frameworkRole, Literal("utility")))
    g.add((fn1, CG.entryPointScore, Literal(0.5, datatype=XSD.float)))

    # Cluster
    g.add((cluster, RDF.type, CG.Cluster))
    g.add((cluster, CG.cohesionScore, Literal(0.85, datatype=XSD.float)))
    g.add((cluster, CG.hasNode, cls1))
    g.add((cluster, CG.hasNode, fn1))

    # File + stats
    g.add((file1, RDF.type, CG.File))
    g.add((file1, CG.language, Literal("python")))

    return g


class FakeProject:
    name = "TestProject"
    source_url = "https://github.com/example/test"
    last_indexed = "2026-03-16T00:00:00Z"


class TestWikiGenerator:
    @pytest.fixture
    def wiki_dir(self, tmp_path):
        from app.wiki.generator import WikiGenerator
        g = make_full_fixture_graph()
        gen = WikiGenerator(project=FakeProject(), graph=g, output_dir=tmp_path)
        gen.generate()
        return tmp_path

    def test_index_md_created(self, wiki_dir):
        assert (wiki_dir / "index.md").exists()

    def test_index_md_contains_project_name(self, wiki_dir):
        content = (wiki_dir / "index.md").read_text()
        assert "TestProject" in content

    def test_index_md_contains_language(self, wiki_dir):
        content = (wiki_dir / "index.md").read_text()
        assert "python" in content

    def test_index_md_contains_stats(self, wiki_dir):
        content = (wiki_dir / "index.md").read_text()
        assert "Files" in content
        assert "Functions" in content

    def test_class_file_created(self, wiki_dir):
        assert (wiki_dir / "classes" / "Widget.md").exists()

    def test_class_md_contains_class_name(self, wiki_dir):
        content = (wiki_dir / "classes" / "Widget.md").read_text()
        assert "Widget" in content

    def test_class_md_contains_field(self, wiki_dir):
        content = (wiki_dir / "classes" / "Widget.md").read_text()
        assert "size" in content

    def test_class_md_contains_method(self, wiki_dir):
        content = (wiki_dir / "classes" / "Widget.md").read_text()
        assert "render" in content

    def test_class_md_contains_cluster(self, wiki_dir):
        content = (wiki_dir / "classes" / "Widget.md").read_text()
        assert "0.85" in content

    def test_function_file_created(self, wiki_dir):
        assert (wiki_dir / "functions" / "mymodule_build.md").exists()

    def test_function_md_contains_function_name(self, wiki_dir):
        content = (wiki_dir / "functions" / "mymodule_build.md").read_text()
        assert "build" in content

    def test_function_md_contains_local_var(self, wiki_dir):
        content = (wiki_dir / "functions" / "mymodule_build.md").read_text()
        assert "tmp" in content

    def test_function_md_contains_framework_role(self, wiki_dir):
        content = (wiki_dir / "functions" / "mymodule_build.md").read_text()
        assert "utility" in content

    def test_module_file_created(self, wiki_dir):
        assert (wiki_dir / "modules" / "mymodule.md").exists()

    def test_module_md_contains_module_name(self, wiki_dir):
        content = (wiki_dir / "modules" / "mymodule.md").read_text()
        assert "mymodule" in content

    def test_module_md_lists_class(self, wiki_dir):
        content = (wiki_dir / "modules" / "mymodule.md").read_text()
        assert "Widget" in content

    def test_module_md_lists_function(self, wiki_dir):
        content = (wiki_dir / "modules" / "mymodule.md").read_text()
        assert "build" in content

    def test_module_md_lists_import(self, wiki_dir):
        content = (wiki_dir / "modules" / "mymodule.md").read_text()
        assert "os" in content

    def test_regenerate_clears_old_files(self, tmp_path):
        from app.wiki.generator import WikiGenerator
        g = make_full_fixture_graph()
        gen = WikiGenerator(project=FakeProject(), graph=g, output_dir=tmp_path)
        gen.generate()
        # plant a stale file
        stale = tmp_path / "classes" / "OldClass.md"
        stale.write_text("stale")
        gen.generate()
        assert not stale.exists(), "Stale wiki file should be removed on re-generation"
```

- [ ] **Step 2: Run failing tests**

```bash
cd backend
pytest tests/test_wiki/test_generator.py -v 2>&1 | head -20
```

Expected:
```
ImportError: No module named 'app.wiki.generator'
```

- [ ] **Step 3: Implement `generator.py`**

`backend/app/wiki/generator.py`:

```python
# backend/app/wiki/generator.py

import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape
from rdflib import Graph

from app.wiki import sparql_queries as Q


def _rows_to_dicts(result) -> list[dict]:
    """Convert SPARQL ResultRow objects to plain dicts keyed by variable name."""
    return [
        {str(var): (str(row[var]) if row[var] is not None else None) for var in row.labels}
        for row in result
    ]


class WikiGenerator:
    def __init__(self, project: Any, graph: Graph, output_dir: Path):
        self.project = project
        self.graph = graph
        self.output_dir = Path(output_dir)
        self._env = Environment(
            loader=PackageLoader("app.wiki", "templates"),
            autoescape=select_autoescape([]),
            keep_trailing_newline=True,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> None:
        """Clear output dir, then write all wiki files."""
        self._clear_output_dir()
        self._write_index()
        self._write_classes()
        self._write_functions()
        self._write_modules()

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def _clear_output_dir(self) -> None:
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "classes").mkdir()
        (self.output_dir / "functions").mkdir()
        (self.output_dir / "modules").mkdir()

    def _render(self, template_name: str, **context: Any) -> str:
        tmpl = self._env.get_template(template_name)
        return tmpl.render(**context)

    def _write(self, rel_path: str, content: str) -> None:
        dest = self.output_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Page writers
    # ------------------------------------------------------------------

    def _write_index(self) -> None:
        stats_rows  = _rows_to_dicts(self.graph.query(Q.PROJECT_STATS))
        stats = stats_rows[0] if stats_rows else {}

        lang_rows   = _rows_to_dicts(self.graph.query(Q.PROJECT_LANGUAGES))
        languages   = [r["language"] for r in lang_rows]

        module_rows = _rows_to_dicts(self.graph.query(Q.TOP_LEVEL_MODULES))
        # Derive short name from URI if no cg:name predicate was used
        modules = []
        for r in module_rows:
            name = r.get("name") or r.get("module", "").rsplit("/", 1)[-1]
            modules.append({"name": name, "filePath": r.get("filePath", "")})

        cluster_rows = _rows_to_dicts(self.graph.query(Q.CLUSTER_SUMMARY))

        content = self._render(
            "index.md.j2",
            project=self.project,
            stats=stats,
            languages=languages,
            modules=modules,
            clusters=cluster_rows,
        )
        self._write("index.md", content)

    def _write_classes(self) -> None:
        class_rows     = _rows_to_dicts(self.graph.query(Q.CLASS_DETAILS))
        inherit_rows   = _rows_to_dicts(self.graph.query(Q.CLASS_INHERITANCE))
        iface_rows     = _rows_to_dicts(self.graph.query(Q.CLASS_INTERFACES))
        mixin_rows     = _rows_to_dicts(self.graph.query(Q.CLASS_MIXINS))
        field_rows     = _rows_to_dicts(self.graph.query(Q.CLASS_FIELDS))
        method_rows    = _rows_to_dicts(self.graph.query(Q.CLASS_METHODS))
        dep_rows       = _rows_to_dicts(self.graph.query(Q.CLASS_DEPENDENCIES))
        cluster_rows   = _rows_to_dicts(self.graph.query(Q.CLASS_CLUSTER))

        for cls in class_rows:
            cls_uri = cls.get("cls", "")
            name    = cls.get("name", "UnknownClass")

            inheritance = [r["parent"] for r in inherit_rows if r.get("cls") == cls_uri]
            interfaces  = [r["iface"]  for r in iface_rows   if r.get("cls") == cls_uri]
            mixins      = [r["mixin"]  for r in mixin_rows    if r.get("cls") == cls_uri]
            fields      = [r for r in field_rows  if r.get("cls") == cls_uri]
            methods     = [r for r in method_rows if r.get("cls") == cls_uri]
            deps        = [r for r in dep_rows    if r.get("cls") == cls_uri]
            cluster_hit = next((r for r in cluster_rows if r.get("cls") == cls_uri), None)

            content = self._render(
                "class.md.j2",
                cls=cls,
                inheritance=inheritance,
                interfaces=interfaces,
                mixins=mixins,
                fields=fields,
                methods=methods,
                callers=[],
                dependencies=deps,
                cluster=cluster_hit,
            )
            self._write(f"classes/{name}.md", content)

    def _write_functions(self) -> None:
        fn_rows       = _rows_to_dicts(self.graph.query(Q.STANDALONE_FUNCTIONS))
        param_rows    = _rows_to_dicts(self.graph.query(Q.FUNCTION_PARAMETERS))
        var_rows      = _rows_to_dicts(self.graph.query(Q.FUNCTION_LOCAL_VARS))
        callee_rows   = _rows_to_dicts(self.graph.query(Q.FUNCTION_CALLEES))
        role_rows     = _rows_to_dicts(self.graph.query(Q.FUNCTION_FRAMEWORK_ROLE))
        cluster_rows  = _rows_to_dicts(self.graph.query(Q.FUNCTION_CLUSTER))

        for fn in fn_rows:
            fn_uri  = fn.get("fn", "")
            name    = fn.get("name", "unknown")
            mod_uri = fn.get("module", "")
            mod_name = mod_uri.rsplit("/", 1)[-1] if mod_uri else "nomodule"

            params       = [r for r in param_rows   if r.get("fn") == fn_uri]
            local_vars   = [r for r in var_rows      if r.get("fn") == fn_uri]
            callees      = [r for r in callee_rows   if r.get("fn") == fn_uri]
            role_hit     = next((r for r in role_rows    if r.get("fn") == fn_uri), None)
            cluster_hit  = next((r for r in cluster_rows if r.get("fn") == fn_uri), None)

            content = self._render(
                "function.md.j2",
                fn=fn,
                parameters=params,
                local_vars=local_vars,
                callers=[],
                callees=callees,
                framework_role=role_hit,
                cluster=cluster_hit,
            )
            self._write(f"functions/{mod_name}_{name}.md", content)

    def _write_modules(self) -> None:
        module_rows   = _rows_to_dicts(self.graph.query(Q.MODULE_DETAILS))
        class_rows    = _rows_to_dicts(self.graph.query(Q.MODULE_CLASSES))
        fn_rows       = _rows_to_dicts(self.graph.query(Q.MODULE_FUNCTIONS))
        const_rows    = _rows_to_dicts(self.graph.query(Q.MODULE_CONSTANTS))
        import_rows   = _rows_to_dicts(self.graph.query(Q.MODULE_IMPORTS))

        for mod in module_rows:
            mod_uri = mod.get("module", "")
            name    = mod.get("name", "unknown")

            classes   = [r for r in class_rows  if r.get("module") == mod_uri]
            functions = [r for r in fn_rows      if r.get("module") == mod_uri]
            constants = [r for r in const_rows   if r.get("module") == mod_uri]
            imports   = [r for r in import_rows  if r.get("module") == mod_uri]

            content = self._render(
                "module.md.j2",
                module=mod,
                classes=classes,
                functions=functions,
                constants=constants,
                imports=imports,
            )
            self._write(f"modules/{name}.md", content)
```

- [ ] **Step 4: Run tests — expect all green**

```bash
cd backend
pytest tests/test_wiki/test_generator.py -v
```

Expected output:
```
tests/test_wiki/test_generator.py::TestWikiGenerator::test_index_md_created PASSED
tests/test_wiki/test_generator.py::TestWikiGenerator::test_index_md_contains_project_name PASSED
...
tests/test_wiki/test_generator.py::TestWikiGenerator::test_regenerate_clears_old_files PASSED
PASSED (20 tests)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/wiki/generator.py backend/tests/test_wiki/test_generator.py
git commit -m "feat(wiki): add WikiGenerator class with template rendering and file output tests (Chunk 2)"
```

---

## Chunk 3: FastAPI Wiki Router + HTTP Tests + Register in main.py

### Task 3.1: Write wiki API router

**File:** `backend/app/api/wiki.py`

Three endpoints:
- `POST /api/v1/projects/{id}/wiki/generate` — load graph.ttl, run `WikiGenerator.generate()`, return summary.
- `GET /api/v1/projects/{id}/wiki` — list `.md` files in `wiki/`, return `{path, type, name}` list.
- `GET /api/v1/projects/{id}/wiki/{file_path:path}` — return raw markdown of a specific wiki file.

- [ ] **Step 1: Write failing HTTP tests first**

`backend/tests/test_api/test_wiki_endpoints.py`:

```python
# backend/tests/test_api/test_wiki_endpoints.py

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

PROJECT_ID = "test-wiki-project-001"


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    """Create a minimal project directory with project.json and a stub graph.ttl."""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "data_dir", str(tmp_path))

    proj_dir = tmp_path / PROJECT_ID
    proj_dir.mkdir()

    project_meta = {
        "id": PROJECT_ID,
        "name": "Wiki Test Project",
        "source_url": "https://github.com/example/repo",
        "status": "indexed",
        "last_indexed": "2026-03-16T00:00:00Z",
    }
    (proj_dir / "project.json").write_text(json.dumps(project_meta))

    # Minimal valid Turtle graph
    ttl_content = """
@prefix cg: <http://codegraph.dev/ontology#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://example.org/file1> a cg:File ;
    cg:language "python" .
"""
    (proj_dir / "graph.ttl").write_text(ttl_content)
    return proj_dir


@pytest.fixture
def client():
    return TestClient(app)


class TestGenerateWikiEndpoint:
    def test_returns_200_on_success(self, client, project_dir):
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        assert response.status_code == 200

    def test_response_body_has_message(self, client, project_dir):
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        body = response.json()
        assert "message" in body

    def test_response_body_has_file_count(self, client, project_dir):
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        body = response.json()
        assert "files_generated" in body
        assert isinstance(body["files_generated"], int)

    def test_wiki_dir_created_on_disk(self, client, project_dir):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        assert (project_dir / "wiki").exists()

    def test_index_md_created_on_disk(self, client, project_dir):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        assert (project_dir / "wiki" / "index.md").exists()

    def test_returns_404_for_missing_project(self, client, tmp_path, monkeypatch):
        import app.config as cfg
        monkeypatch.setattr(cfg.settings, "data_dir", str(tmp_path))
        response = client.post("/api/v1/projects/nonexistent-id/wiki/generate")
        assert response.status_code == 404

    def test_returns_400_if_graph_ttl_missing(self, client, project_dir):
        (project_dir / "graph.ttl").unlink()
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        assert response.status_code == 400


class TestListWikiEndpoint:
    def test_returns_200(self, client, project_dir):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki")
        assert response.status_code == 200

    def test_returns_list(self, client, project_dir):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki")
        assert isinstance(response.json(), list)

    def test_index_entry_present(self, client, project_dir):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki")
        paths = [entry["path"] for entry in response.json()]
        assert any("index.md" in p for p in paths)

    def test_entry_has_required_keys(self, client, project_dir):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki")
        entries = response.json()
        assert len(entries) > 0
        entry = entries[0]
        assert "path" in entry
        assert "type" in entry
        assert "name" in entry

    def test_returns_empty_list_if_wiki_not_generated(self, client, project_dir):
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_404_for_missing_project(self, client, tmp_path, monkeypatch):
        import app.config as cfg
        monkeypatch.setattr(cfg.settings, "data_dir", str(tmp_path))
        response = client.get("/api/v1/projects/nonexistent-id/wiki")
        assert response.status_code == 404


class TestFetchWikiFileEndpoint:
    def test_returns_markdown_content(self, client, project_dir):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki/index.md")
        assert response.status_code == 200
        assert "Wiki Test Project" in response.text

    def test_content_type_is_text(self, client, project_dir):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki/index.md")
        assert "text" in response.headers["content-type"]

    def test_nested_file_path_works(self, client, project_dir):
        # Plant a dummy class file to test nested path routing
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        wiki_dir = project_dir / "wiki" / "classes"
        # If any class file was generated, fetch it
        class_files = list(wiki_dir.glob("*.md"))
        if class_files:
            rel = "classes/" + class_files[0].name
            response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki/{rel}")
            assert response.status_code == 200

    def test_returns_404_for_missing_file(self, client, project_dir):
        client.post(f"/api/v1/projects/{PROJECT_ID}/wiki/generate")
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/wiki/classes/Nonexistent.md")
        assert response.status_code == 404

    def test_returns_404_for_missing_project(self, client, tmp_path, monkeypatch):
        import app.config as cfg
        monkeypatch.setattr(cfg.settings, "data_dir", str(tmp_path))
        response = client.get("/api/v1/projects/nonexistent-id/wiki/index.md")
        assert response.status_code == 404
```

- [ ] **Step 2: Run failing tests**

```bash
cd backend
pytest tests/test_api/test_wiki_endpoints.py -v 2>&1 | head -20
```

Expected:
```
ImportError or 404s — router not yet registered
```

- [ ] **Step 3: Implement `app/api/wiki.py`**

`backend/app/api/wiki.py`:

```python
# backend/app/api/wiki.py

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from rdflib import Graph

from app.config import settings
from app.storage.project_store import ProjectStore
from app.wiki.generator import WikiGenerator

router = APIRouter(prefix="/api/v1/projects", tags=["wiki"])

store = ProjectStore()


def _get_project_or_404(project_id: str) -> Any:
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return project


def _get_graph_or_400(project_id: str) -> Graph:
    graph_path = Path(settings.data_dir) / project_id / "graph.ttl"
    if not graph_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"graph.ttl not found for project '{project_id}'. Run indexing first.",
        )
    g = Graph()
    g.parse(str(graph_path), format="turtle")
    return g


@router.post("/{project_id}/wiki/generate")
def generate_wiki(project_id: str) -> dict:
    project = _get_project_or_404(project_id)
    graph = _get_graph_or_400(project_id)

    output_dir = Path(settings.data_dir) / project_id / "wiki"
    gen = WikiGenerator(project=project, graph=graph, output_dir=output_dir)
    gen.generate()

    md_files = list(output_dir.rglob("*.md"))
    return {
        "message": "Wiki generated successfully",
        "files_generated": len(md_files),
    }


@router.get("/{project_id}/wiki")
def list_wiki(project_id: str) -> list[dict]:
    _get_project_or_404(project_id)

    wiki_dir = Path(settings.data_dir) / project_id / "wiki"
    if not wiki_dir.exists():
        return []

    entries = []
    for md_file in sorted(wiki_dir.rglob("*.md")):
        rel = md_file.relative_to(wiki_dir)
        parts = rel.parts
        if len(parts) == 1:
            file_type = "index"
        else:
            file_type = parts[0]  # "classes", "functions", "modules"
        entries.append({
            "path": str(rel),
            "type": file_type,
            "name": md_file.stem,
        })
    return entries


@router.get("/{project_id}/wiki/{file_path:path}", response_class=PlainTextResponse)
def fetch_wiki_file(project_id: str, file_path: str) -> str:
    _get_project_or_404(project_id)

    wiki_dir = Path(settings.data_dir) / project_id / "wiki"
    target = (wiki_dir / file_path).resolve()

    # Guard against path traversal
    try:
        target.relative_to(wiki_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Wiki file '{file_path}' not found")

    return target.read_text(encoding="utf-8")
```

- [ ] **Step 4: Register router in `main.py`**

In `backend/app/main.py`, add the import and include:

```python
from app.api.wiki import router as wiki_router

# inside create_app() or at module level where other routers are included:
app.include_router(wiki_router)
```

- [ ] **Step 5: Handle wiki deletion on re-index**

In the existing indexing logic (Plan 1's project re-index path), add wiki cleanup. Locate the re-index handler in `backend/app/api/` and add:

```python
# When re-indexing a project, delete existing wiki if present
wiki_dir = Path(settings.data_dir) / project_id / "wiki"
if wiki_dir.exists():
    shutil.rmtree(wiki_dir)
```

- [ ] **Step 6: Run all wiki tests — expect all green**

```bash
cd backend
pytest tests/test_wiki/ tests/test_api/test_wiki_endpoints.py -v
```

Expected output:
```
tests/test_wiki/test_sparql_queries.py::... PASSED (17 tests)
tests/test_wiki/test_generator.py::... PASSED (20 tests)
tests/test_api/test_wiki_endpoints.py::... PASSED (16 tests)
```

- [ ] **Step 7: Run full test suite to confirm no regressions**

```bash
cd backend
pytest --tb=short -q
```

Expected: all tests green, no regressions from Plans 1–4.

- [ ] **Step 8: Final commit**

```bash
git add backend/app/api/wiki.py \
        backend/app/main.py \
        backend/tests/test_api/test_wiki_endpoints.py
git commit -m "feat(wiki): add wiki FastAPI router, HTTP tests, and register in main.py (Chunk 3)"
```

---

## Summary

| Chunk | Files Created | Tests |
|-------|--------------|-------|
| 1 | `sparql_queries.py`, 4 Jinja2 templates | 17 SPARQL query tests |
| 2 | `generator.py` | 20 file-generation tests using `tmp_path` |
| 3 | `api/wiki.py`, `main.py` update | 16 HTTP-level endpoint tests |

**Behavior notes:**
- Wiki generation is always synchronous and manual — no background task.
- Re-indexing deletes `wiki/` but does NOT regenerate it.
- Path traversal is guarded in the fetch endpoint.
- All SPARQL queries use the `cg:` ontology namespace defined in Plan 2.
