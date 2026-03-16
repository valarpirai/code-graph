from tree_sitter import Language, Parser
import tree_sitter_java as tsjava
from .base import (
    BaseParser, ParsedFile, ClassDef, FunctionDef, FieldDef,
    ConstantDef, ImportDef, ParameterDef, Optional,
)

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
            package=package,
        )

    def _extract_package(self, root) -> str:
        for node in root.children:
            if node.type == "package_declaration":
                for child in node.children:
                    if child.type in ("scoped_identifier", "identifier"):
                        return child.text.decode()
        return ""

    def _extract_classes(self, root, package: str) -> list[ClassDef]:
        classes = []
        # class_declaration covers regular, abstract, and final classes
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
            if "abstract" in modifiers:
                kind = "abstract_class"
            elif "final" in modifiers:
                kind = "final_class"
            else:
                kind = "class"
            classes.append(ClassDef(
                name=name, qualified_name=qname,
                line=node.start_point[0] + 1,
                inherits=[superclass] if superclass else [],
                implements=interfaces,
                fields=fields, methods=methods,
                is_exported="public" in modifiers,
                class_kind=kind,
            ))
        # interface_declaration
        for node in self._walk(root, "interface_declaration"):
            name = self._child_text(node, "identifier")
            qname = f"{package}.{name}" if package else name
            modifiers = self._get_modifiers(node)
            methods = self._extract_methods(node, qname)
            # interfaces can extend other interfaces
            extends = self._extract_extends_interfaces(node)
            classes.append(ClassDef(
                name=name, qualified_name=qname,
                line=node.start_point[0] + 1,
                inherits=extends,
                implements=[],
                fields=[], methods=methods,
                is_exported="public" in modifiers,
                class_kind="interface",
            ))
        return classes

    def _extract_extends_interfaces(self, interface_node) -> list[str]:
        """Extract interfaces that an interface extends."""
        result = []
        extends = self._find_child(interface_node, "extends_interfaces")
        if extends:
            for child in self._walk(extends, "type_identifier"):
                result.append(child.text.decode())
        return result

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
                ptype = (self._child_text(p, "type_identifier") or
                         self._child_text(p, "integral_type") or
                         self._child_text(p, "floating_point_type"))
                params.append(ParameterDef(name=pname, type_hint=ptype))
        return params

    def _extract_calls(self, method_node) -> list[str]:
        calls = []
        for node in self._walk(method_node, "method_invocation"):
            # method_invocation has structure: object . method_name argument_list
            # The method name is the identifier that comes just before argument_list
            method_name = None
            for child in node.children:
                if child.type == "identifier":
                    method_name = child.text.decode()
                elif child.type == "argument_list":
                    break
            if method_name:
                calls.append(method_name)
        return calls

    def _extract_imports(self, root) -> list[ImportDef]:
        imports = []
        for node in self._walk(root, "import_declaration"):
            src = ""
            for child in node.children:
                if child.type == "scoped_identifier":
                    src = child.text.decode()
            if src:
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
            type_name = (self._child_text(node, "type_identifier") or
                         self._child_text(node, "integral_type"))
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
        # keyword nodes like 'public', 'private', 'static', 'final' are NOT is_named
        # so we collect all children's text, skipping annotation nodes
        result = []
        for c in mods.children:
            if c.type not in ("marker_annotation", "annotation"):
                result.append(c.text.decode())
        return result

    def _get_annotations(self, node) -> list[str]:
        anns = []
        # Annotations are inside the modifiers node
        mods = self._find_child(node, "modifiers")
        if mods:
            for child in mods.children:
                if child.type == "marker_annotation":
                    name = self._child_text(child, "identifier")
                    if name:
                        anns.append(name)
        # Also check direct children for compatibility
        for child in node.children:
            if child.type == "marker_annotation":
                name = self._child_text(child, "identifier")
                if name:
                    anns.append(name)
        return anns

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
