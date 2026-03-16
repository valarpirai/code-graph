from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from abc import ABC, abstractmethod


@dataclass
class ParameterDef:
    name: str
    type_hint: Optional[str]


@dataclass
class FieldDef:
    name: str
    type_hint: Optional[str]
    visibility: str


@dataclass
class ConstantDef:
    name: str
    value: Optional[str]
    line: int
    var_kind: str = "constant"    # constant | static | instance | final | local
    owner_qname: Optional[str] = None  # qualified name of owning class or method


@dataclass
class ConfigValue:
    key: str
    value: str
    source_file: str


@dataclass
class FunctionDef:
    name: str
    qualified_name: str
    line: int
    column: int
    parameters: list[ParameterDef]
    visibility: str
    is_exported: bool
    framework_role: Optional[str]
    entry_point_score: float
    is_abstract: bool = False
    calls: list[str] = field(default_factory=list)  # qualified names of callees


@dataclass
class ClassDef:
    name: str
    qualified_name: str
    line: int
    inherits: list[str]
    implements: list[str]
    fields: list[FieldDef]
    methods: list[FunctionDef]
    is_exported: bool
    class_kind: str = "class"
    # Valid values:
    # "class"          regular class
    # "abstract_class" abstract class (Java abstract, Python ABC subclass)
    # "final_class"    final/sealed class (Java final)
    # "data_class"     record / dataclass (Java record, Kotlin data class, Python @dataclass)
    # "interface"      interface (Java, TS, Go, Kotlin, Python Protocol)
    # "enum"           enumeration (Java, TS, Kotlin, Rust, C, Python)
    # "struct"         struct (Rust, Go, C — also C union)
    # "trait"          trait (Rust)
    # "mixin"          mixin module (Ruby)


@dataclass
class ImportDef:
    source: str                        # raw import string
    resolved_file: Optional[str]       # resolved path within repo
    bindings: list[tuple[str, str]]    # [(name, alias), ...]
    is_reexport: bool


@dataclass
class ParsedFile:
    file_path: str
    language: str
    classes: list[ClassDef]
    functions: list[FunctionDef]       # standalone (not in class)
    imports: list[ImportDef]
    constants: list[ConstantDef]
    config_values: list[ConfigValue]
    package: str = ""                  # package / namespace (e.g. "com.example.servlet")
    is_test: bool = False              # True if this is a test/spec file
    line_count: int = 0               # total lines in the file
    file_size: int = 0                # bytes


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str, source_code: str) -> ParsedFile: ...
