from tree_sitter import Language, Parser
import tree_sitter_c as tsc
from .base import (
    BaseParser, ParsedFile, ClassDef, FunctionDef, FieldDef,
    ImportDef, ParameterDef, Optional,
)

C_LANG = Language(tsc.language())


class CParser(BaseParser):
    def __init__(self):
        self._parser = Parser(C_LANG)

    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        tree = self._parser.parse(source_code.encode())
        root = tree.root_node
        classes = self._extract_structs(root)
        functions = self._extract_functions(root)
        imports = self._extract_includes(root)
        return ParsedFile(
            file_path=file_path, language="c",
            classes=classes, functions=functions,
            imports=imports, constants=[], config_values=[],
        )

    def _extract_structs(self, root) -> list[ClassDef]:
        classes = []
        for node in self._walk(root, "struct_specifier"):
            name = self._child_text(node, "type_identifier") or ""
            if not name:
                continue
            fields = []
            fdl = self._find_child(node, "field_declaration_list")
            if fdl:
                for fd in fdl.children:
                    if fd.type == "field_declaration":
                        type_hint = self._child_text(fd, "primitive_type") or self._child_text(fd, "type_identifier")
                        field_name = self._child_text(fd, "field_identifier") or ""
                        if field_name:
                            fields.append(FieldDef(
                                name=field_name, type_hint=type_hint, visibility="public",
                            ))
            classes.append(ClassDef(
                name=name, qualified_name=name,
                line=node.start_point[0] + 1,
                inherits=[], implements=[],
                fields=fields, methods=[],
                is_exported=True,
            ))
        return classes

    def _extract_functions(self, root) -> list[FunctionDef]:
        functions = []
        for node in root.children:
            if node.type == "function_definition":
                is_static = False
                # Check for storage_class_specifier
                for child in node.children:
                    if child.type == "storage_class_specifier" and child.text.decode() == "static":
                        is_static = True
                decl = self._find_child(node, "function_declarator")
                if not decl:
                    continue
                name = self._child_text(decl, "identifier") or ""
                params = self._extract_params(decl)
                functions.append(FunctionDef(
                    name=name, qualified_name=name,
                    line=node.start_point[0] + 1,
                    column=node.start_point[1],
                    parameters=params,
                    visibility="private" if is_static else "public",
                    is_exported=not is_static,
                    framework_role=None, entry_point_score=0.0, calls=[],
                ))
        return functions

    def _extract_params(self, declarator_node) -> list[ParameterDef]:
        params = []
        pl = self._find_child(declarator_node, "parameter_list")
        if not pl:
            return params
        for child in pl.children:
            if child.type == "parameter_declaration":
                name = self._child_text(child, "identifier") or ""
                type_hint = self._child_text(child, "primitive_type") or self._child_text(child, "type_identifier")
                params.append(ParameterDef(name=name, type_hint=type_hint))
        return params

    def _extract_includes(self, root) -> list[ImportDef]:
        imports = []
        for node in self._walk(root, "preproc_include"):
            source = ""
            for child in node.children:
                if child.type == "system_lib_string":
                    source = child.text.decode()  # e.g. <stdio.h>
                elif child.type == "string_literal":
                    content = self._find_child(child, "string_content")
                    source = content.text.decode() if content else child.text.decode().strip('"')
            if source:
                imports.append(ImportDef(
                    source=source, resolved_file=None,
                    bindings=[], is_reexport=False,
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
