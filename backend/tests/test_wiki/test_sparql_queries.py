import pytest
from rdflib import Graph, Literal, URIRef, Namespace
from rdflib.namespace import RDF, RDFS, XSD
from app.wiki import sparql_queries as Q

CG = Namespace("http://codegraph.dev/ontology#")


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
    file1   = URIRef("http://example.org/file/myclass")
    cls1    = URIRef("http://example.org/cls/MyClass")
    parent  = URIRef("http://example.org/cls/BaseClass")
    iface   = URIRef("http://example.org/cls/Serializable")
    mixin   = URIRef("http://example.org/cls/LogMixin")
    field1  = URIRef("http://example.org/fld/name")
    method1 = URIRef("http://example.org/method/greet")
    param1  = URIRef("http://example.org/param/greeting")

    # File → defines → class
    g.add((file1, RDF.type, CG.File))
    g.add((file1, CG.filePath, Literal("src/myclass.py")))
    g.add((file1, CG.language, Literal("python")))
    g.add((file1, CG.defines, cls1))

    g.add((cls1, RDF.type, CG.Class))
    g.add((cls1, CG.name, Literal("MyClass")))
    g.add((cls1, CG.line, Literal(10, datatype=XSD.integer)))
    g.add((cls1, CG.inherits, parent))
    g.add((cls1, CG.implements, iface))
    g.add((cls1, CG.mixes, mixin))
    g.add((cls1, CG.hasField, field1))
    g.add((field1, CG.name, Literal("name")))
    g.add((field1, CG.dataType, Literal("str")))
    g.add((field1, CG.visibility, Literal("public")))
    g.add((cls1, CG.hasMethod, method1))
    g.add((method1, CG.name, Literal("greet")))
    g.add((method1, CG.returnType, Literal("str")))
    g.add((method1, CG.hasParameter, param1))
    g.add((param1, CG.name, Literal("greeting")))
    g.add((param1, CG.dataType, Literal("str")))
    return g


def make_function_graph() -> Graph:
    g = Graph()
    g.bind("cg", CG)
    file1  = URIRef("http://example.org/file/utils")
    fn1    = URIRef("http://example.org/fn/compute")
    param1 = URIRef("http://example.org/param/x")
    var1   = URIRef("http://example.org/var/result")
    callee = URIRef("http://example.org/fn/helper")

    g.add((file1, RDF.type, CG.File))
    g.add((file1, CG.filePath, Literal("src/utils.py")))
    g.add((file1, CG.language, Literal("python")))
    g.add((file1, CG.defines, fn1))

    g.add((fn1, RDF.type, CG.Function))
    g.add((fn1, CG.name, Literal("compute")))
    g.add((fn1, CG.line, Literal(5, datatype=XSD.integer)))
    g.add((fn1, CG.hasParameter, param1))
    g.add((param1, CG.name, Literal("x")))
    g.add((param1, CG.dataType, Literal("int")))
    g.add((fn1, CG.defines, var1))
    g.add((var1, RDF.type, CG.LocalVariable))
    g.add((var1, CG.name, Literal("result")))
    g.add((var1, CG.dataType, Literal("int")))
    g.add((fn1, CG.calls, callee))
    g.add((callee, CG.name, Literal("helper")))
    g.add((fn1, CG.frameworkRole, Literal("rest_endpoint")))
    g.add((fn1, CG.entryPointScore, Literal(0.9, datatype=XSD.float)))
    return g


def make_module_graph() -> Graph:
    g = Graph()
    g.bind("cg", CG)
    mod1   = URIRef("http://example.org/mod/utils")
    file1  = URIRef("http://example.org/file/utils")
    cls1   = URIRef("http://example.org/cls/Helper")
    fn1    = URIRef("http://example.org/fn/compute")
    const1 = URIRef("http://example.org/const/MAX")
    imp1   = URIRef("http://example.org/import/os")

    g.add((mod1, RDF.type, CG.Module))
    g.add((mod1, CG.name, Literal("utils")))
    g.add((mod1, CG.containsFile, file1))

    g.add((file1, RDF.type, CG.File))
    g.add((file1, CG.filePath, Literal("src/utils.py")))
    g.add((file1, CG.defines, cls1))
    g.add((file1, CG.defines, fn1))
    g.add((file1, CG.defines, const1))
    g.add((file1, CG.imports, imp1))

    g.add((cls1, RDF.type, CG.Class))
    g.add((cls1, CG.name, Literal("Helper")))

    g.add((fn1, RDF.type, CG.Function))
    g.add((fn1, CG.name, Literal("compute")))

    g.add((const1, RDF.type, CG.Constant))
    g.add((const1, CG.name, Literal("MAX")))
    g.add((const1, CG.value, Literal("100")))

    g.add((imp1, RDF.type, CG.Import))
    g.add((imp1, CG.name, Literal("os")))
    return g


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
        # constType is the RDF type URI — verify it's a known storage type
        assert "codegraph.dev/ontology#Constant" in str(row.constType)


class TestModuleImportsQuery:
    def test_returns_import(self):
        g = make_module_graph()
        results = list(g.query(Q.MODULE_IMPORTS))
        assert len(results) == 1
        assert str(results[0].importTarget) == "http://example.org/import/os"
