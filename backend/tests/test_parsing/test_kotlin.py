import pytest
from app.parsing.kotlin import KotlinParser

def test_top_level_function():
    src = 'package app\nfun main() { println("hi") }'
    parsed = KotlinParser().parse("Main.kt", src)
    assert any(f.name == "main" for f in parsed.functions)

def test_class_extracted():
    src = "class UserService {\n  fun getUser(id: Int): String { return \"user\" }\n}"
    parsed = KotlinParser().parse("UserService.kt", src)
    assert len(parsed.classes) >= 1
    assert parsed.classes[0].name == "UserService"
