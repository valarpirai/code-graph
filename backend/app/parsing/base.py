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


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str, source_code: str) -> ParsedFile: ...
