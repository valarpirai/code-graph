import pytest
from app.parsing.java import JavaParser

JAVA_SOURCE = """
package com.example;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.stereotype.Service;

public class UserService {
    private static final int MAX_USERS = 100;
    private String name;

    @GetMapping
    public void getUsers(String filter) {
        userRepo.findAll(filter);
    }
}
"""

@pytest.fixture
def parsed():
    return JavaParser().parse("src/UserService.java", JAVA_SOURCE)

def test_class_extracted(parsed):
    assert len(parsed.classes) == 1
    cls = parsed.classes[0]
    assert cls.name == "UserService"
    assert cls.qualified_name == "com.example.UserService"
    assert cls.is_exported is True

def test_method_framework_role(parsed):
    method = parsed.classes[0].methods[0]
    assert method.name == "getUsers"
    assert method.framework_role == "rest_endpoint"
    assert method.parameters[0].name == "filter"

def test_field_extracted(parsed):
    fields = parsed.classes[0].fields
    assert any(f.name == "name" for f in fields)

def test_constant_extracted(parsed):
    assert any(c.name == "MAX_USERS" and c.value == "100" for c in parsed.constants)

def test_import_extracted(parsed):
    sources = [i.source for i in parsed.imports]
    assert any("GetMapping" in s for s in sources)

def test_method_call_extracted(parsed):
    method = parsed.classes[0].methods[0]
    assert "findAll" in method.calls
