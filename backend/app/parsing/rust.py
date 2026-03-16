from tree_sitter import Language, Parser
import tree_sitter_rust as tsrust
from .base import (
    BaseParser, ParsedFile, ClassDef, FunctionDef, FieldDef,
    ImportDef, ParameterDef, Optional,
)

RUST_LANG = Language(tsrust.language())


class RustParser(BaseParser):
    def __init__(self):
        self._parser = Parser(RUST_LANG)

    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        tree = self._parser.parse(source_code.encode())
        root = tree.root_node
        classes = self._extract_impl_blocks(root)
        functions = self._extract_functions(root)
        imports = self._extract_imports(root)
        return ParsedFile(
            file_path=file_path, language="rust",
            classes=classes, functions=functions,
            imports=imports, constants=[], config_values=[],
        )

    def _extract_impl_blocks(self, root) -> list[ClassDef]:
        classes = []
        for node in self._walk(root, "impl_item"):
            type_name = self._child_text(node, "type_identifier") or ""
            decl_list = self._find_child(node, "declaration_list")
            methods = []
            if decl_list:
                for fn_node in decl_list.children:
                    if fn_node.type == "function_item":
                        name = self._child_text(fn_node, "identifier") or ""
                        is_pub = self._has_visibility(fn_node)
                        params = self._extract_params(fn_node)
                        methods.append(FunctionDef(
                            name=name,
                            qualified_name=f"{type_name}::{name}",
                            line=fn_node.start_point[0] + 1,
                            column=fn_node.start_point[1],
                            parameters=params,
                            visibility="public" if is_pub else "private",
                            is_exported=is_pub,
                            framework_role=None,
                            entry_point_score=0.0, calls=[],
                        ))
            classes.append(ClassDef(
                name=type_name, qualified_name=type_name,
                line=node.start_point[0] + 1,
                inherits=[], implements=[],
                fields=[], methods=methods,
                is_exported=self._has_visibility(node),
            ))
        return classes

    def _extract_functions(self, root) -> list[FunctionDef]:
        functions = []
        for node in root.children:
            if node.type == "function_item":
                name = self._child_text(node, "identifier") or ""
                is_pub = self._has_visibility(node)
                params = self._extract_params(node)
                functions.append(FunctionDef(
                    name=name, qualified_name=name,
                    line=node.start_point[0] + 1,
                    column=node.start_point[1],
                    parameters=params,
                    visibility="public" if is_pub else "private",
                    is_exported=is_pub,
                    framework_role=None, entry_point_score=0.0, calls=[],
                ))
        return functions

    def _extract_imports(self, root) -> list[ImportDef]:
        imports = []
        for node in self._walk(root, "use_declaration"):
            # Get the full use path as source
            source = ""
            for child in node.children:
                if child.type in ("scoped_identifier", "identifier", "use_list", "scoped_use_list"):
                    source = child.text.decode()
                    break
            if source:
                imports.append(ImportDef(
                    source=source, resolved_file=None,
                    bindings=[(source.split("::")[-1], "")],
                    is_reexport=False,
                ))
        return imports

    def _extract_params(self, fn_node) -> list[ParameterDef]:
        params = []
        param_list = self._find_child(fn_node, "parameters")
        if not param_list:
            return params
        for child in param_list.children:
            if child.type == "parameter":
                name = ""
                type_hint = None
                for c in child.children:
                    if c.type == "identifier":
                        name = c.text.decode()
                    elif c.type in ("type_identifier", "reference_type", "primitive_type"):
                        type_hint = c.text.decode()
                params.append(ParameterDef(name=name, type_hint=type_hint))
        return params

    def _has_visibility(self, node) -> bool:
        return self._find_child(node, "visibility_modifier") is not None

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
