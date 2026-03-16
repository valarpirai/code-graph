import pytest
from app.parsing.python import PythonParser

CLASS_SOURCE = '''
class UserService:
    MAX_USERS = 100

    def __init__(self, name: str):
        self.name = name

    def get_user(self, user_id: int) -> str:
        return self.name
'''

FUNCTION_SOURCE = '''
def main():
    result = helper()
    return result

def helper():
    pass
'''

IMPORT_SOURCE = '''
import os
import sys
from pathlib import Path
from typing import Optional, List
from . import utils
from ..models import User
'''

@pytest.fixture
def parsed_class():
    return PythonParser().parse("services/user.py", CLASS_SOURCE)

@pytest.fixture
def parsed_functions():
    return PythonParser().parse("main.py", FUNCTION_SOURCE)

@pytest.fixture
def parsed_imports():
    return PythonParser().parse("app.py", IMPORT_SOURCE)

def test_class_extracted(parsed_class):
    assert len(parsed_class.classes) == 1
    cls = parsed_class.classes[0]
    assert cls.name == "UserService"
    assert cls.qualified_name == "UserService"

def test_methods_extracted(parsed_class):
    cls = parsed_class.classes[0]
    method_names = [m.name for m in cls.methods]
    assert "__init__" in method_names
    assert "get_user" in method_names

def test_method_parameters(parsed_class):
    cls = parsed_class.classes[0]
    get_user = next(m for m in cls.methods if m.name == "get_user")
    param_names = [p.name for p in get_user.parameters]
    assert "user_id" in param_names

def test_constant_extracted(parsed_class):
    assert any(c.name == "MAX_USERS" for c in parsed_class.constants)

def test_top_level_functions(parsed_functions):
    names = [f.name for f in parsed_functions.functions]
    assert "main" in names
    assert "helper" in names

def test_function_calls(parsed_functions):
    main_fn = next(f for f in parsed_functions.functions if f.name == "main")
    assert "helper" in main_fn.calls

def test_imports_extracted(parsed_imports):
    sources = [i.source for i in parsed_imports.imports]
    assert "os" in sources
    assert "sys" in sources
    assert "pathlib" in sources

def test_from_import(parsed_imports):
    assert any(i.source == "pathlib" for i in parsed_imports.imports)

def test_relative_import(parsed_imports):
    assert any(i.source.startswith(".") for i in parsed_imports.imports)
