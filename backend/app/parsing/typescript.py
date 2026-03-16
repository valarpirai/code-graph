from tree_sitter import Language, Parser
import tree_sitter_typescript as tsts
from .base import (
    BaseParser, ParsedFile, ClassDef, FunctionDef, FieldDef,
    ImportDef, ParameterDef, Optional,
)

TS_LANG = Language(tsts.language_typescript())


class TypeScriptParser(BaseParser):
    def __init__(self):
        self._parser = Parser(TS_LANG)

    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        tree = self._parser.parse(source_code.encode())
        root = tree.root_node
        classes = self._extract_classes(root)
        functions = self._extract_functions(root)
        imports = self._extract_imports(root)
        return ParsedFile(
            file_path=file_path, language="typescript",
            classes=classes, functions=functions,
            imports=imports, constants=[], config_values=[],
        )

    def _extract_classes(self, root) -> list[ClassDef]:
        classes = []
        for node in self._walk(root, "class_declaration"):
            name = self._child_text(node, "type_identifier") or ""
            is_exported = self._is_exported(node)
            fields = self._extract_fields(node)
            methods = self._extract_methods(node, name)
            inherits = []
            # heritage: extends
            hc = self._find_child(node, "class_heritage")
            if hc:
                for ext in self._walk(hc, "extends_clause"):
                    tid = self._child_text(ext, "type_identifier") or self._child_text(ext, "identifier")
                    if tid:
                        inherits.append(tid)
            classes.append(ClassDef(
                name=name, qualified_name=name,
                line=node.start_point[0] + 1,
                inherits=inherits, implements=[],
                fields=fields, methods=methods,
                is_exported=is_exported,
            ))
        return classes

    def _extract_fields(self, class_node) -> list[FieldDef]:
        fields = []
        body = self._find_child(class_node, "class_body")
        if not body:
            return fields
        for node in body.children:
            if node.type == "public_field_definition":
                name = self._child_text(node, "property_identifier") or ""
                vis = "public"
                acc = self._find_child(node, "accessibility_modifier")
                if acc:
                    vis = acc.text.decode()
                ta = self._find_child(node, "type_annotation")
                type_hint = None
                if ta:
                    for c in ta.children:
                        if c.type not in (":", ):
                            type_hint = c.text.decode()
                            break
                fields.append(FieldDef(name=name, type_hint=type_hint, visibility=vis))
        return fields

    def _extract_methods(self, class_node, class_name: str) -> list[FunctionDef]:
        methods = []
        body = self._find_child(class_node, "class_body")
        if not body:
            return methods
        for node in body.children:
            if node.type == "method_definition":
                name = self._child_text(node, "property_identifier") or ""
                params = self._extract_params(node)
                methods.append(FunctionDef(
                    name=name,
                    qualified_name=f"{class_name}.{name}",
                    line=node.start_point[0] + 1,
                    column=node.start_point[1],
                    parameters=params,
                    visibility="public",
                    is_exported=False,
                    framework_role=None,
                    entry_point_score=0.0,
                    calls=[],
                ))
        return methods

    def _extract_functions(self, root) -> list[FunctionDef]:
        functions = []
        for node in root.children:
            is_exported = False
            target = node
            if node.type == "export_statement":
                is_exported = True
                # The actual declaration is a child
                for child in node.children:
                    if child.type in ("function_declaration", "lexical_declaration", "variable_declaration"):
                        target = child
                        break
                else:
                    continue

            if target.type == "function_declaration":
                name = self._child_text(target, "identifier") or ""
                params = self._extract_params(target)
                functions.append(FunctionDef(
                    name=name, qualified_name=name,
                    line=target.start_point[0] + 1,
                    column=target.start_point[1],
                    parameters=params, visibility="public",
                    is_exported=is_exported,
                    framework_role=None, entry_point_score=0.0, calls=[],
                ))
            elif target.type in ("lexical_declaration", "variable_declaration"):
                for decl in self._walk(target, "variable_declarator"):
                    name_node = self._find_child(decl, "identifier")
                    if not name_node:
                        continue
                    # Check if value is arrow_function or function
                    for child in decl.children:
                        if child.type in ("arrow_function", "function"):
                            params = self._extract_params(child)
                            functions.append(FunctionDef(
                                name=name_node.text.decode(),
                                qualified_name=name_node.text.decode(),
                                line=decl.start_point[0] + 1,
                                column=decl.start_point[1],
                                parameters=params, visibility="public",
                                is_exported=is_exported,
                                framework_role=None, entry_point_score=0.0, calls=[],
                            ))
        return functions

    def _extract_imports(self, root) -> list[ImportDef]:
        imports = []
        for node in self._walk(root, "import_statement"):
            source = ""
            bindings = []
            for child in node.children:
                if child.type == "string":
                    source = self._get_string_content(child)
                elif child.type == "import_clause":
                    for ic_child in child.children:
                        if ic_child.type == "named_imports":
                            for spec in self._walk(ic_child, "import_specifier"):
                                name = self._child_text(spec, "identifier") or ""
                                alias = ""
                                ids = [c for c in spec.children if c.type == "identifier"]
                                if len(ids) >= 2:
                                    name = ids[0].text.decode()
                                    alias = ids[1].text.decode()
                                elif len(ids) == 1:
                                    name = ids[0].text.decode()
                                bindings.append((name, alias))
                        elif ic_child.type == "identifier":
                            bindings.append((ic_child.text.decode(), ""))
            if source:
                imports.append(ImportDef(
                    source=source, resolved_file=None,
                    bindings=bindings, is_reexport=False,
                ))
        # Handle re-exports: export { X } from "..."
        for node in self._walk(root, "export_statement"):
            source = ""
            bindings = []
            has_from = False
            for child in node.children:
                if child.type == "string":
                    source = self._get_string_content(child)
                    has_from = True
                elif child.type == "export_clause":
                    for spec in self._walk(child, "export_specifier"):
                        name = self._child_text(spec, "identifier") or ""
                        bindings.append((name, ""))
            if has_from and source:
                imports.append(ImportDef(
                    source=source, resolved_file=None,
                    bindings=bindings, is_reexport=True,
                ))
        return imports

    def _extract_params(self, fn_node) -> list[ParameterDef]:
        params = []
        fp = self._find_child(fn_node, "formal_parameters")
        if not fp:
            return params
        for child in fp.children:
            if child.type in ("required_parameter", "optional_parameter"):
                name = self._child_text(child, "identifier") or ""
                ta = self._find_child(child, "type_annotation")
                type_hint = None
                if ta:
                    for c in ta.children:
                        if c.type != ":":
                            type_hint = c.text.decode()
                            break
                params.append(ParameterDef(name=name, type_hint=type_hint))
        return params

    def _get_string_content(self, string_node) -> str:
        frag = self._find_child(string_node, "string_fragment")
        if frag:
            return frag.text.decode()
        return string_node.text.decode().strip("'\"")

    def _is_exported(self, node) -> bool:
        if node.parent and node.parent.type == "export_statement":
            return True
        return False

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
