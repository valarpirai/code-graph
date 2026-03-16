from tree_sitter import Language, Parser
import tree_sitter_ruby as tsruby
from .base import (
    BaseParser, ParsedFile, ClassDef, FunctionDef, FieldDef,
    ImportDef, ParameterDef, Optional,
)

RUBY_LANG = Language(tsruby.language())


class RubyParser(BaseParser):
    def __init__(self):
        self._parser = Parser(RUBY_LANG)

    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        tree = self._parser.parse(source_code.encode())
        root = tree.root_node
        classes: list[ClassDef] = []
        functions: list[FunctionDef] = []
        self._extract_classes(root, [], classes, functions)
        imports = self._extract_imports(root)
        return ParsedFile(
            file_path=file_path, language="ruby",
            classes=classes, functions=functions,
            imports=imports, constants=[], config_values=[],
        )

    def _extract_classes(self, node, namespace: list[str],
                         classes: list[ClassDef], functions: list[FunctionDef]):
        for child in node.children:
            if child.type == "module":
                mod_name = self._child_text(child, "constant") or ""
                new_ns = namespace + [mod_name]
                body = self._find_child(child, "body_statement")
                if body:
                    self._extract_classes(body, new_ns, classes, functions)
            elif child.type == "class":
                cls_name = self._child_text(child, "constant") or ""
                new_ns = namespace + [cls_name]
                qname = "::".join(new_ns)
                methods = []
                body = self._find_child(child, "body_statement")
                if body:
                    methods = self._extract_methods(body, qname)
                    # Recurse for nested classes
                    self._extract_classes(body, new_ns, classes, functions)
                inherits = []
                sup = self._find_child(child, "superclass")
                if sup:
                    sc = self._child_text(sup, "constant") or self._child_text(sup, "scope_resolution")
                    if sc:
                        inherits.append(sc)
                classes.append(ClassDef(
                    name=cls_name, qualified_name=qname,
                    line=child.start_point[0] + 1,
                    inherits=inherits, implements=[],
                    fields=[], methods=methods,
                    is_exported=True,
                ))
            elif child.type == "method":
                name = self._child_text(child, "identifier") or ""
                qname = "::".join(namespace + [name]) if namespace else name
                params = self._extract_params(child)
                functions.append(FunctionDef(
                    name=name, qualified_name=qname,
                    line=child.start_point[0] + 1,
                    column=child.start_point[1],
                    parameters=params, visibility="public",
                    is_exported=True, framework_role=None,
                    entry_point_score=0.0, calls=[],
                ))

    def _extract_methods(self, body_node, class_qname: str) -> list[FunctionDef]:
        methods = []
        for child in body_node.children:
            if child.type == "method":
                name = self._child_text(child, "identifier") or ""
                params = self._extract_params(child)
                methods.append(FunctionDef(
                    name=name,
                    qualified_name=f"{class_qname}#{name}",
                    line=child.start_point[0] + 1,
                    column=child.start_point[1],
                    parameters=params, visibility="public",
                    is_exported=True, framework_role=None,
                    entry_point_score=0.0, calls=[],
                ))
        return methods

    def _extract_params(self, method_node) -> list[ParameterDef]:
        params = []
        mp = self._find_child(method_node, "method_parameters")
        if not mp:
            return params
        for child in mp.children:
            if child.type == "identifier":
                params.append(ParameterDef(name=child.text.decode(), type_hint=None))
        return params

    def _extract_imports(self, root) -> list[ImportDef]:
        imports = []
        for node in self._walk(root, "call"):
            fn_name = self._child_text(node, "identifier")
            if fn_name in ("require", "require_relative"):
                args = self._find_child(node, "argument_list")
                if args:
                    for child in args.children:
                        if child.type == "string":
                            content = self._find_child(child, "string_content")
                            source = content.text.decode() if content else child.text.decode().strip("'\"")
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
