from tree_sitter import Language, Parser
import tree_sitter_go as tsgo
from .base import (
    BaseParser, ParsedFile, ClassDef, FunctionDef, FieldDef,
    ImportDef, ParameterDef, Optional,
)

GO_LANG = Language(tsgo.language())


class GoParser(BaseParser):
    def __init__(self):
        self._parser = Parser(GO_LANG)

    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        tree = self._parser.parse(source_code.encode())
        root = tree.root_node
        functions, receiver_methods = self._extract_functions(root)
        classes = self._build_classes(receiver_methods)
        imports = self._extract_imports(root)
        return ParsedFile(
            file_path=file_path, language="go",
            classes=classes, functions=functions,
            imports=imports, constants=[], config_values=[],
        )

    def _extract_functions(self, root) -> tuple[list[FunctionDef], dict[str, list[FunctionDef]]]:
        functions = []
        receiver_methods: dict[str, list[FunctionDef]] = {}

        for node in root.children:
            if node.type == "function_declaration":
                name = self._child_text(node, "identifier") or ""
                is_exported = name[:1].isupper() if name else False
                params = self._extract_params(node)
                functions.append(FunctionDef(
                    name=name, qualified_name=name,
                    line=node.start_point[0] + 1,
                    column=node.start_point[1],
                    parameters=params, visibility="public" if is_exported else "private",
                    is_exported=is_exported,
                    framework_role=None, entry_point_score=0.0, calls=[],
                ))
            elif node.type == "method_declaration":
                name = self._child_text(node, "field_identifier") or ""
                is_exported = name[:1].isupper() if name else False
                params = self._extract_params(node)
                # Extract receiver type
                recv_type = self._extract_receiver_type(node)
                fn = FunctionDef(
                    name=name, qualified_name=f"{recv_type}.{name}" if recv_type else name,
                    line=node.start_point[0] + 1,
                    column=node.start_point[1],
                    parameters=params, visibility="public" if is_exported else "private",
                    is_exported=is_exported,
                    framework_role=None, entry_point_score=0.0, calls=[],
                )
                if recv_type:
                    receiver_methods.setdefault(recv_type, []).append(fn)

        return functions, receiver_methods

    def _extract_receiver_type(self, method_node) -> str:
        # First parameter_list is the receiver
        param_lists = [c for c in method_node.children if c.type == "parameter_list"]
        if not param_lists:
            return ""
        recv_list = param_lists[0]
        for pd in self._walk(recv_list, "parameter_declaration"):
            # Look for type_identifier in pointer_type or directly
            for child in pd.children:
                if child.type == "pointer_type":
                    ti = self._child_text(child, "type_identifier")
                    if ti:
                        return ti
                elif child.type == "type_identifier":
                    return child.text.decode()
        return ""

    def _extract_params(self, fn_node) -> list[ParameterDef]:
        params = []
        # For method_declaration, the second parameter_list has the actual params
        # For function_declaration, the first (and possibly only) parameter_list
        param_lists = [c for c in fn_node.children if c.type == "parameter_list"]
        if not param_lists:
            return params
        # For method_declaration: param_lists[0] is receiver, param_lists[1] is params
        # For function_declaration: param_lists[0] is params
        if fn_node.type == "method_declaration" and len(param_lists) >= 2:
            pl = param_lists[1]
        else:
            pl = param_lists[0]
        for pd in self._walk(pl, "parameter_declaration"):
            name = self._child_text(pd, "identifier") or ""
            type_hint = self._child_text(pd, "type_identifier")
            params.append(ParameterDef(name=name, type_hint=type_hint))
        return params

    def _build_classes(self, receiver_methods: dict[str, list[FunctionDef]]) -> list[ClassDef]:
        classes = []
        for type_name, methods in receiver_methods.items():
            line = methods[0].line if methods else 0
            classes.append(ClassDef(
                name=type_name, qualified_name=type_name,
                line=line, inherits=[], implements=[],
                fields=[], methods=methods,
                is_exported=type_name[:1].isupper(),
            ))
        return classes

    def _extract_imports(self, root) -> list[ImportDef]:
        imports = []
        for node in self._walk(root, "import_declaration"):
            for spec in self._walk(node, "import_spec"):
                source = ""
                alias = ""
                for child in spec.children:
                    if child.type == "interpreted_string_literal":
                        content = self._find_child(child, "interpreted_string_literal_content")
                        source = content.text.decode() if content else child.text.decode().strip('"')
                    elif child.type == "package_identifier":
                        alias = child.text.decode()
                    elif child.type == "dot":
                        alias = "."
                if source:
                    name = source.rsplit("/", 1)[-1]
                    imports.append(ImportDef(
                        source=source, resolved_file=None,
                        bindings=[(name, alias)],
                        is_reexport=False,
                    ))
        return imports

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
