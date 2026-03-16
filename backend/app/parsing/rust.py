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
        type_defs = self._extract_type_defs(root)
        classes = self._merge_impl_blocks(root, type_defs)
        functions = self._extract_functions(root)
        imports = self._extract_imports(root)
        return ParsedFile(
            file_path=file_path, language="rust",
            classes=classes, functions=functions,
            imports=imports, constants=[], config_values=[],
        )

    def _extract_type_defs(self, root) -> dict[str, ClassDef]:
        """Extract struct_item, trait_item, enum_item as ClassDef entries."""
        type_defs: dict[str, ClassDef] = {}
        for node in root.children:
            if node.type == "struct_item":
                name = self._child_text(node, "type_identifier") or ""
                if name:
                    fields = self._extract_struct_fields(node)
                    type_defs[name] = ClassDef(
                        name=name, qualified_name=name,
                        line=node.start_point[0] + 1,
                        inherits=[], implements=[],
                        fields=fields, methods=[],
                        is_exported=self._has_visibility(node),
                        class_kind="struct",
                    )
            elif node.type == "trait_item":
                name = self._child_text(node, "type_identifier") or ""
                if name:
                    methods = self._extract_trait_methods(node, name)
                    type_defs[name] = ClassDef(
                        name=name, qualified_name=name,
                        line=node.start_point[0] + 1,
                        inherits=[], implements=[],
                        fields=[], methods=methods,
                        is_exported=self._has_visibility(node),
                        class_kind="trait",
                    )
            elif node.type == "enum_item":
                name = self._child_text(node, "type_identifier") or ""
                if name:
                    type_defs[name] = ClassDef(
                        name=name, qualified_name=name,
                        line=node.start_point[0] + 1,
                        inherits=[], implements=[],
                        fields=[], methods=[],
                        is_exported=self._has_visibility(node),
                        class_kind="enum",
                    )
        return type_defs

    def _extract_struct_fields(self, struct_node) -> list[FieldDef]:
        fields = []
        fl = self._find_child(struct_node, "field_declaration_list")
        if not fl:
            return fields
        for field in fl.children:
            if field.type == "field_declaration":
                name = self._child_text(field, "field_identifier") or ""
                type_hint = None
                for child in field.children:
                    if child.type in ("type_identifier", "primitive_type", "reference_type"):
                        type_hint = child.text.decode()
                        break
                is_pub = self._find_child(field, "visibility_modifier") is not None
                if name:
                    fields.append(FieldDef(
                        name=name, type_hint=type_hint,
                        visibility="public" if is_pub else "private",
                    ))
        return fields

    def _extract_trait_methods(self, trait_node, trait_name: str) -> list[FunctionDef]:
        methods = []
        decl_list = self._find_child(trait_node, "declaration_list")
        if not decl_list:
            return methods
        for fn_node in decl_list.children:
            if fn_node.type in ("function_item", "function_signature_item"):
                name = self._child_text(fn_node, "identifier") or ""
                params = self._extract_params(fn_node)
                methods.append(FunctionDef(
                    name=name,
                    qualified_name=f"{trait_name}::{name}",
                    line=fn_node.start_point[0] + 1,
                    column=fn_node.start_point[1],
                    parameters=params,
                    visibility="public",
                    is_exported=True,
                    is_abstract=fn_node.type == "function_signature_item",
                    framework_role=None,
                    entry_point_score=0.0, calls=[],
                ))
        return methods

    def _merge_impl_blocks(self, root, type_defs: dict[str, ClassDef]) -> list[ClassDef]:
        """Merge impl block methods into type_defs; create stubs for unknown types."""
        for node in self._walk(root, "impl_item"):
            type_name = self._child_text(node, "type_identifier") or ""
            if not type_name:
                continue
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
            if type_name in type_defs:
                type_defs[type_name].methods.extend(methods)
            else:
                type_defs[type_name] = ClassDef(
                    name=type_name, qualified_name=type_name,
                    line=node.start_point[0] + 1,
                    inherits=[], implements=[],
                    fields=[], methods=methods,
                    is_exported=self._has_visibility(node),
                    class_kind="struct",
                )
        return list(type_defs.values())

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
