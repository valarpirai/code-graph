from tree_sitter import Language, Parser
import tree_sitter_python as tspy
from .base import (
    BaseParser, ParsedFile, ClassDef, FunctionDef,
    ConstantDef, ImportDef, ParameterDef, Optional,
)

PYTHON_LANG = Language(tspy.language())


class PythonParser(BaseParser):
    def __init__(self):
        self._parser = Parser(PYTHON_LANG)

    def parse(self, file_path: str, source_code: str) -> ParsedFile:
        tree = self._parser.parse(source_code.encode())
        root = tree.root_node
        classes, class_constants = self._extract_classes(root)
        functions = self._extract_top_level_functions(root)
        imports = self._extract_imports(root)
        # Module-level constants + class-level constants all go in ParsedFile.constants
        constants = self._extract_module_constants(root)
        constants.extend(class_constants)
        return ParsedFile(
            file_path=file_path, language="python",
            classes=classes, functions=functions,
            imports=imports, constants=constants, config_values=[],
        )

    def _extract_classes(self, root) -> tuple[list[ClassDef], list[ConstantDef]]:
        classes = []
        all_class_constants = []
        for node in root.children:
            if node.type == "class_definition":
                cls, consts = self._parse_class(node)
                classes.append(cls)
                all_class_constants.extend(consts)
        return classes, all_class_constants

    def _parse_class(self, node) -> tuple[ClassDef, list[ConstantDef]]:
        name = self._child_text(node, "identifier") or ""
        # Inheritance: argument_list directly in class_definition
        inherits = []
        arg_list = self._find_child(node, "argument_list")
        if arg_list:
            for child in arg_list.children:
                if child.type == "identifier":
                    inherits.append(child.text.decode())
        # Determine class_kind from base classes and decorators
        _ENUM_BASES = {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag"}
        _ABC_BASES = {"ABC", "ABCMeta"}
        _PROTOCOL_BASES = {"Protocol"}
        if any(b in _ENUM_BASES for b in inherits):
            kind = "enum"
        elif any(b in _ABC_BASES for b in inherits):
            kind = "abstract_class"
        elif any(b in _PROTOCOL_BASES for b in inherits):
            kind = "interface"
        elif self._has_decorator(node, "dataclass"):
            kind = "data_class"
        else:
            kind = "class"
        # Extract methods and class-level constants from the block
        block = self._find_child(node, "block")
        methods = []
        constants = []
        if block:
            methods = self._extract_methods(block, name)
            constants = self._extract_class_constants(block)
        cls = ClassDef(
            name=name,
            qualified_name=name,
            line=node.start_point[0] + 1,
            inherits=inherits,
            implements=[],
            fields=[],
            methods=methods,
            is_exported=not name.startswith("_"),
            class_kind=kind,
        )
        return cls, constants

    def _has_decorator(self, class_node, decorator_name: str) -> bool:
        """Check if a class node has a specific decorator."""
        current = class_node.prev_sibling
        while current is not None and current.type == "decorator":
            for child in current.children:
                if child.type == "identifier" and child.text.decode() == decorator_name:
                    return True
                if child.type == "call":
                    fn = child.children[0] if child.children else None
                    if fn and fn.type == "identifier" and fn.text.decode() == decorator_name:
                        return True
            current = current.prev_sibling
        return False

    def _extract_methods(self, block_node, class_name: str) -> list[FunctionDef]:
        methods = []
        for node in block_node.children:
            if node.type == "function_definition":
                methods.append(self._parse_function(node, class_name))
        return methods

    def _extract_top_level_functions(self, root) -> list[FunctionDef]:
        functions = []
        for node in root.children:
            if node.type == "function_definition":
                functions.append(self._parse_function(node, None))
        return functions

    def _parse_function(self, node, class_name: Optional[str]) -> FunctionDef:
        name = self._child_text(node, "identifier") or ""
        qname = f"{class_name}.{name}" if class_name else name
        params = self._extract_params(node)
        calls = self._extract_calls(node)
        return FunctionDef(
            name=name,
            qualified_name=qname,
            line=node.start_point[0] + 1,
            column=node.start_point[1],
            parameters=params,
            visibility="public",
            is_exported=not name.startswith("_"),
            framework_role=None,
            entry_point_score=0.0,
            calls=calls,
        )

    def _extract_params(self, func_node) -> list[ParameterDef]:
        params = []
        parameters = self._find_child(func_node, "parameters")
        if not parameters:
            return params
        for child in parameters.children:
            if child.type == "identifier":
                pname = child.text.decode()
                if pname == "self":
                    continue
                params.append(ParameterDef(name=pname, type_hint=None))
            elif child.type == "typed_parameter":
                # [identifier] [':'] [type]
                pname = None
                ptype = None
                for sub in child.children:
                    if sub.type == "identifier" and pname is None:
                        pname = sub.text.decode()
                        if pname == "self":
                            pname = None
                            break
                    elif sub.type == "type":
                        # type node contains identifier
                        ptype = sub.text.decode()
                if pname:
                    params.append(ParameterDef(name=pname, type_hint=ptype))
        return params

    def _extract_calls(self, func_node) -> list[str]:
        calls = []
        block = self._find_child(func_node, "block")
        if block:
            for call_node in self._walk(block, "call"):
                # call node: [identifier/attribute] [argument_list]
                func_child = call_node.children[0] if call_node.children else None
                if func_child and func_child.type == "identifier":
                    calls.append(func_child.text.decode())
        return calls

    def _extract_imports(self, root) -> list[ImportDef]:
        imports = []
        for node in root.children:
            if node.type == "import_statement":
                # import os  /  import os.path
                for child in node.children:
                    if child.type == "dotted_name":
                        src = child.text.decode()
                        imports.append(ImportDef(
                            source=src, resolved_file=None,
                            bindings=[(src.split(".")[-1], "")],
                            is_reexport=False,
                        ))
            elif node.type == "import_from_statement":
                imports.append(self._parse_from_import(node))
        return imports

    def _parse_from_import(self, node) -> ImportDef:
        # from pathlib import Path
        # from . import utils
        # from ..models import User
        source = ""
        bindings = []

        # Children: 'from', source (dotted_name or relative_import), 'import', names...
        children = node.children
        i = 0
        while i < len(children):
            child = children[i]
            if child.type == "dotted_name" and source == "":
                source = child.text.decode()
            elif child.type == "relative_import":
                # relative_import: import_prefix [dotted_name]
                prefix_node = self._find_child(child, "import_prefix")
                prefix = prefix_node.text.decode() if prefix_node else ""
                dotted = self._find_child(child, "dotted_name")
                module = dotted.text.decode() if dotted else ""
                source = prefix + module
            elif child.type == "dotted_name" and source != "":
                # These are the imported names after 'import'
                bindings.append((child.text.decode(), ""))
            i += 1

        return ImportDef(
            source=source, resolved_file=None,
            bindings=bindings,
            is_reexport=False,
        )

    def _extract_module_constants(self, root) -> list[ConstantDef]:
        """Extract module-level ALL_CAPS assignments as constants."""
        constants = []
        for node in root.children:
            if node.type == "expression_statement":
                assign = self._find_child(node, "assignment")
                if assign:
                    name_node = self._find_child(assign, "identifier")
                    if name_node:
                        name = name_node.text.decode()
                        if name.isupper():
                            val_node = assign.children[-1] if assign.children else None
                            value = val_node.text.decode() if val_node else None
                            constants.append(ConstantDef(
                                name=name, value=value,
                                line=node.start_point[0] + 1,
                            ))
        return constants

    def _extract_class_constants(self, block_node) -> list[ConstantDef]:
        """Extract ALL_CAPS assignments inside a class body."""
        constants = []
        for node in block_node.children:
            if node.type == "expression_statement":
                assign = self._find_child(node, "assignment")
                if assign:
                    name_node = self._find_child(assign, "identifier")
                    if name_node:
                        name = name_node.text.decode()
                        if name.isupper():
                            val_node = assign.children[-1] if assign.children else None
                            value = val_node.text.decode() if val_node else None
                            constants.append(ConstantDef(
                                name=name, value=value,
                                line=node.start_point[0] + 1,
                            ))
        return constants

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
