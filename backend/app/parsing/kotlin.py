from tree_sitter import Language, Parser
import tree_sitter_kotlin as tskotlin
from .base import (
    BaseParser, ParsedFile, ClassDef, FunctionDef, FieldDef,
    ImportDef, ParameterDef, Optional,
)

KOTLIN_LANG = Language(tskotlin.language())


class KotlinParser(BaseParser):
    def __init__(self):
        self._parser = Parser(KOTLIN_LANG)

    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        tree = self._parser.parse(source_code.encode())
        root = tree.root_node
        package = self._extract_package(root)
        classes = self._extract_classes(root, package)
        functions = self._extract_top_level_functions(root, package)
        imports = self._extract_imports(root)
        return ParsedFile(
            file_path=file_path, language="kotlin",
            classes=classes, functions=functions,
            imports=imports, constants=[], config_values=[],
        )

    def _extract_package(self, root) -> str:
        for node in root.children:
            if node.type == "package_header":
                qi = self._find_child(node, "qualified_identifier")
                if qi:
                    return qi.text.decode()
                ident = self._child_text(node, "identifier")
                if ident:
                    return ident
        return ""

    def _extract_classes(self, root, package: str) -> list[ClassDef]:
        classes = []
        for node in self._walk(root, "class_declaration"):
            name = self._child_text(node, "identifier") or ""
            qname = f"{package}.{name}" if package else name
            modifiers = self._get_modifiers(node)
            methods = self._extract_methods(node, qname)
            # Determine class_kind from modifiers and class body presence
            if "interface" in modifiers:
                kind = "interface"
            elif "enum" in modifiers:
                kind = "enum"
            elif "data" in modifiers:
                kind = "data_class"
            elif "abstract" in modifiers:
                kind = "abstract_class"
            else:
                kind = "class"
            # Kotlin interfaces: tree-sitter uses class_declaration with "interface" keyword
            # Check if the node has "interface" as a direct keyword child
            for child in node.children:
                if not child.is_named and child.text == b"interface":
                    kind = "interface"
                    break
                if not child.is_named and child.text == b"enum":
                    kind = "enum"
                    break
            classes.append(ClassDef(
                name=name, qualified_name=qname,
                line=node.start_point[0] + 1,
                inherits=[], implements=[],
                fields=[], methods=methods,
                is_exported=True,
                class_kind=kind,
            ))
        # object_declaration → singleton class
        for node in self._walk(root, "object_declaration"):
            name = self._child_text(node, "identifier") or ""
            qname = f"{package}.{name}" if package else name
            methods = self._extract_methods(node, qname)
            classes.append(ClassDef(
                name=name, qualified_name=qname,
                line=node.start_point[0] + 1,
                inherits=[], implements=[],
                fields=[], methods=methods,
                is_exported=True,
                class_kind="class",
            ))
        return classes

    def _get_modifiers(self, node) -> list[str]:
        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                for mod in child.children:
                    modifiers.append(mod.text.decode())
        return modifiers

    def _extract_methods(self, class_node, class_qname: str) -> list[FunctionDef]:
        methods = []
        body = self._find_child(class_node, "class_body")
        if not body:
            return methods
        for node in body.children:
            if node.type == "function_declaration":
                name = self._child_text(node, "identifier") or ""
                params = self._extract_params(node)
                methods.append(FunctionDef(
                    name=name,
                    qualified_name=f"{class_qname}.{name}",
                    line=node.start_point[0] + 1,
                    column=node.start_point[1],
                    parameters=params,
                    visibility="public",
                    is_exported=True,
                    framework_role=None,
                    entry_point_score=0.0, calls=[],
                ))
        return methods

    def _extract_top_level_functions(self, root, package: str) -> list[FunctionDef]:
        functions = []
        for node in root.children:
            if node.type == "function_declaration":
                name = self._child_text(node, "identifier") or ""
                qname = f"{package}.{name}" if package else name
                params = self._extract_params(node)
                functions.append(FunctionDef(
                    name=name, qualified_name=qname,
                    line=node.start_point[0] + 1,
                    column=node.start_point[1],
                    parameters=params,
                    visibility="public",
                    is_exported=True,
                    framework_role=None,
                    entry_point_score=0.0, calls=[],
                ))
        return functions

    def _extract_imports(self, root) -> list[ImportDef]:
        imports = []
        for node in self._walk(root, "import_header"):
            qi = self._find_child(node, "qualified_identifier")
            if qi:
                source = qi.text.decode()
                imports.append(ImportDef(
                    source=source, resolved_file=None,
                    bindings=[(source.split(".")[-1], "")],
                    is_reexport=False,
                ))
        return imports

    def _extract_params(self, fn_node) -> list[ParameterDef]:
        params = []
        fp = self._find_child(fn_node, "function_value_parameters")
        if not fp:
            return params
        for child in fp.children:
            if child.type == "parameter":
                name = self._child_text(child, "identifier") or ""
                type_hint = None
                ut = self._find_child(child, "user_type")
                if ut:
                    type_hint = ut.text.decode()
                params.append(ParameterDef(name=name, type_hint=type_hint))
        return params

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
