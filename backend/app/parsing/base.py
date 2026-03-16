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
    class_kind: str = "class"   # "class" | "abstract_class" | "final_class" | "interface"


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


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str, source_code: str) -> ParsedFile: ...
