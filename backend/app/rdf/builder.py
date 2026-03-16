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
