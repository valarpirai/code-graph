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
    file1   = URIRef("http://example.org/file/main")
    cls1    = URIRef("http://example.org/cls/Widget")
    fn1     = URIRef("http://example.org/fn/build")
    imp1    = URIRef("http://example.org/import/os")
    field1  = URIRef("http://example.org/fld/size")
    method1 = URIRef("http://example.org/method/render")
    param1  = URIRef("http://example.org/param/color")
    var1    = URIRef("http://example.org/var/tmp")
    cluster = URIRef("http://example.org/cluster/c1")

    # Module + File structure
    g.add((mod1, RDF.type, CG.Module))
    g.add((mod1, CG.name, Literal("mymodule")))
    g.add((mod1, CG.containsFile, file1))

    g.add((file1, RDF.type, CG.File))
    g.add((file1, CG.filePath, Literal("src/mymodule.py")))
    g.add((file1, CG.language, Literal("python")))
    g.add((file1, CG.defines, cls1))
    g.add((file1, CG.defines, fn1))
    g.add((file1, CG.imports, imp1))

    g.add((imp1, RDF.type, CG.Import))
    g.add((imp1, CG.name, Literal("os")))

    # Class
    g.add((cls1, RDF.type, CG.Class))
    g.add((cls1, CG.name, Literal("Widget")))
    g.add((cls1, CG.line, Literal(5, datatype=XSD.integer)))
    g.add((cls1, CG.hasField, field1))
    g.add((field1, CG.name, Literal("size")))
    g.add((field1, CG.dataType, Literal("int")))
    g.add((field1, CG.visibility, Literal("public")))
    g.add((cls1, CG.hasMethod, method1))
    g.add((method1, CG.name, Literal("render")))
    g.add((method1, CG.returnType, Literal("str")))
    g.add((method1, CG.hasParameter, param1))
    g.add((param1, CG.name, Literal("color")))
    g.add((param1, CG.dataType, Literal("str")))

    # Standalone function
    g.add((fn1, RDF.type, CG.Function))
    g.add((fn1, CG.name, Literal("build")))
    g.add((fn1, CG.line, Literal(20, datatype=XSD.integer)))
    g.add((fn1, CG.defines, var1))
    g.add((var1, RDF.type, CG.LocalVariable))
    g.add((var1, CG.name, Literal("tmp")))
    g.add((var1, CG.dataType, Literal("str")))
    g.add((fn1, CG.frameworkRole, Literal("utility")))
    g.add((fn1, CG.entryPointScore, Literal(0.5, datatype=XSD.float)))

    # Cluster
    g.add((cluster, RDF.type, CG.Cluster))
    g.add((cluster, CG.cohesionScore, Literal(0.85, datatype=XSD.float)))
    g.add((cluster, CG.hasNode, cls1))
    g.add((cluster, CG.hasNode, fn1))

    return g


class FakeProject:
    name = "TestProject"
    source = "https://github.com/example/test"
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
        # importTarget is the import URI which contains "os" in the path
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
