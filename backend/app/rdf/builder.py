from rdflib import Graph, URIRef, Literal, RDF, XSD
from urllib.parse import quote
from .ontology import CG, load_ontology
from ..parsing.base import ParsedFile, FunctionDef, ClassDef, FieldDef, ImportDef, ConstantDef

_CLASS_KIND_TO_RDF: dict[str, URIRef] = {
    "class":          CG.Class,
    "abstract_class": CG.AbstractClass,
    "final_class":    CG.Class,       # no distinct FinalClass type; remains a Class
    "data_class":     CG.DataClass,
    "interface":      CG.Interface,
    "enum":           CG.Enum,
    "struct":         CG.Struct,
    "trait":          CG.Trait,
    "mixin":          CG.Mixin,
}

_VAR_KIND_TO_RDF: dict[str, URIRef] = {
    "constant": CG.Constant,
    "final":    CG.Constant,
    "static":   CG.Field,
    "instance": CG.Field,
    "local":    CG.LocalVariable,
}

# Constructor method name patterns per language
_CONSTRUCTOR_NAMES = {"__init__", "constructor", "initialize", "init"}


def _uri(project_id: str, kind: str, qname: str) -> URIRef:
    return URIRef(f"http://codegraph.dev/node/{project_id}/{kind}/{quote(qname, safe='')}")


class RDFBuilder:
    def build(self, project_id: str, parsed_files: list[ParsedFile]) -> Graph:
        g = load_ontology()
        # Create Package/Module nodes first (one per unique package)
        package_uris: dict[str, URIRef] = {}
        for pf in parsed_files:
            if pf.package and pf.package not in package_uris:
                pkg_uri = _uri(project_id, "module", pf.package)
                g.add((pkg_uri, RDF.type, CG.Module))
                g.add((pkg_uri, CG.name, Literal(pf.package)))
                package_uris[pf.package] = pkg_uri

        for pf in parsed_files:
            file_uri = _uri(project_id, "file", pf.file_path)
            lang = pf.language
            g.add((file_uri, RDF.type, CG.File))
            g.add((file_uri, CG.filePath, Literal(pf.file_path)))
            g.add((file_uri, CG.language, Literal(lang)))
            if pf.is_test:
                g.add((file_uri, CG.isTest, Literal(True, datatype=XSD.boolean)))
            if pf.line_count:
                g.add((file_uri, CG.lineCount, Literal(pf.line_count, datatype=XSD.integer)))
            if pf.file_size:
                g.add((file_uri, CG.fileSize, Literal(pf.file_size, datatype=XSD.integer)))
            # Connect package → file and package → class
            if pf.package and pf.package in package_uris:
                pkg_uri = package_uris[pf.package]
                g.add((pkg_uri, CG.containsFile, file_uri))
                for cls in pf.classes:
                    cls_uri = _uri(project_id, "class", cls.qualified_name)
                    g.add((pkg_uri, CG.containsClass, cls_uri))
            for cls in pf.classes:
                self._add_class(g, project_id, file_uri, cls, lang)
            for fn in pf.functions:
                self._add_function(g, project_id, file_uri, fn, lang=lang)
            for imp in pf.imports:
                self._add_import(g, project_id, file_uri, imp)
            for const in pf.constants:
                self._add_storage(g, project_id, file_uri, const, lang)
        self._add_call_edges(g, project_id, parsed_files)
        return g

    def _add_class(self, g, project_id, file_uri, cls: ClassDef, lang: str = ""):
        uri = _uri(project_id, "class", cls.qualified_name)
        rdf_type = _CLASS_KIND_TO_RDF.get(cls.class_kind, CG.Class)
        g.add((uri, RDF.type, rdf_type))
        g.add((uri, CG.name, Literal(cls.name)))
        g.add((uri, CG.qualifiedName, Literal(cls.qualified_name)))
        g.add((uri, CG.line, Literal(cls.line, datatype=XSD.integer)))
        g.add((uri, CG.isExported, Literal(cls.is_exported, datatype=XSD.boolean)))
        g.add((uri, CG.classKind, Literal(cls.class_kind)))
        if lang:
            g.add((uri, CG.language, Literal(lang)))
        g.add((file_uri, CG.contains, uri))
        for base in cls.inherits:
            g.add((uri, CG.inherits, _uri(project_id, "class", base)))
        for iface in cls.implements:
            g.add((uri, CG.implements, _uri(project_id, "class", iface)))
        for field in cls.fields:
            self._add_field(g, project_id, uri, cls.qualified_name, field, lang)
        for method in cls.methods:
            self._add_function(g, project_id, file_uri, method, owner=uri, owner_name=cls.name, lang=lang)

    def _add_field(self, g, project_id, cls_uri: URIRef, cls_qname: str, field: FieldDef, lang: str = ""):
        uri = _uri(project_id, "field", f"{cls_qname}/{field.name}")
        g.add((uri, RDF.type, CG.Field))
        g.add((uri, CG.name, Literal(field.name)))
        g.add((uri, CG.visibility, Literal(field.visibility)))
        if field.type_hint:
            g.add((uri, CG.dataType, Literal(field.type_hint)))
        if lang:
            g.add((uri, CG.language, Literal(lang)))
        g.add((cls_uri, CG.hasField, uri))

    def _add_function(self, g, project_id, file_uri, fn: FunctionDef, owner=None, owner_name: str = "", lang: str = ""):
        uri = _uri(project_id, "function", fn.qualified_name)
        if owner is not None:
            is_constructor = (
                fn.name in _CONSTRUCTOR_NAMES or
                (owner_name and fn.name == owner_name)
            )
            rdf_type = CG.Constructor if is_constructor else CG.Method
        else:
            rdf_type = CG.Function
        g.add((uri, RDF.type, rdf_type))
        g.add((uri, CG.name, Literal(fn.name)))
        g.add((uri, CG.qualifiedName, Literal(fn.qualified_name)))
        g.add((uri, CG.line, Literal(fn.line, datatype=XSD.integer)))
        g.add((uri, CG.visibility, Literal(fn.visibility)))
        g.add((uri, CG.isExported, Literal(fn.is_exported, datatype=XSD.boolean)))
        g.add((uri, CG.entryPointScore, Literal(fn.entry_point_score, datatype=XSD.float)))
        if fn.is_abstract:
            g.add((uri, CG.isAbstract, Literal(True, datatype=XSD.boolean)))
        if fn.framework_role:
            g.add((uri, CG.frameworkRole, Literal(fn.framework_role)))
        if lang:
            g.add((uri, CG.language, Literal(lang)))
        # Parameter nodes
        for i, param in enumerate(fn.parameters):
            p_uri = _uri(project_id, "parameter", f"{fn.qualified_name}/param/{i}/{param.name}")
            g.add((p_uri, RDF.type, CG.Parameter))
            g.add((p_uri, CG.name, Literal(param.name)))
            if param.type_hint:
                g.add((p_uri, CG.dataType, Literal(param.type_hint)))
            if lang:
                g.add((p_uri, CG.language, Literal(lang)))
            g.add((uri, CG.hasParameter, p_uri))
        if owner is not None:
            g.add((owner, CG.hasMethod, uri))
        else:
            g.add((file_uri, CG.defines, uri))

    def _add_storage(self, g, project_id, file_uri, const: ConstantDef, lang: str = ""):
        scope = const.owner_qname or str(file_uri)
        uri = _uri(project_id, "storage", f"{scope}/{const.name}/{const.line}")
        rdf_type = _VAR_KIND_TO_RDF.get(const.var_kind, CG.Constant)
        g.add((uri, RDF.type, rdf_type))
        g.add((uri, CG.name, Literal(const.name)))
        g.add((uri, CG.line, Literal(const.line, datatype=XSD.integer)))
        if const.value is not None:
            g.add((uri, CG.value, Literal(const.value)))
        if lang:
            g.add((uri, CG.language, Literal(lang)))
        # Link to owner: class-scoped → hasField; local → function hasParameter; file-level → defines
        if const.owner_qname and const.var_kind in ("instance", "static", "constant", "final"):
            owner_uri = _uri(project_id, "class", const.owner_qname)
            g.add((owner_uri, CG.hasField, uri))
        elif const.owner_qname and const.var_kind == "local":
            fn_uri = _uri(project_id, "function", const.owner_qname)
            g.add((fn_uri, CG.defines, uri))
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
        known_qnames = {fn.qualified_name for pf in parsed_files
                        for cls in pf.classes for fn in cls.methods}
        known_qnames |= {fn.qualified_name for pf in parsed_files for fn in pf.functions}

        # simple name → list of qualified names (for fuzzy resolution)
        name_to_qnames: dict[str, list[str]] = {}
        for qname in known_qnames:
            simple = qname.split(".")[-1]
            name_to_qnames.setdefault(simple, []).append(qname)

        for pf in parsed_files:
            all_fns = [fn for cls in pf.classes for fn in cls.methods] + pf.functions
            for fn in all_fns:
                caller = _uri(project_id, "function", fn.qualified_name)
                for callee_name in fn.calls:
                    if callee_name in known_qnames:
                        g.add((caller, CG.calls, _uri(project_id, "function", callee_name)))
                    elif callee_name in name_to_qnames:
                        for qname in name_to_qnames[callee_name]:
                            g.add((caller, CG.calls, _uri(project_id, "function", qname)))
                    else:
                        callee = _uri(project_id, "external", callee_name)
                        g.add((callee, RDF.type, CG.ExternalSymbol))
                        g.add((callee, CG.qualifiedName, Literal(callee_name)))
                        if "." in callee_name:
                            owner, method = callee_name.rsplit(".", 1)
                            g.add((callee, CG.name, Literal(method)))
                            g.add((callee, CG.filePath, Literal(owner)))
                        else:
                            g.add((callee, CG.name, Literal(callee_name)))
                        g.add((caller, CG.calls, callee))
