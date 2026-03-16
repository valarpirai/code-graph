import pytest
from app.parsing.c import CParser

def test_struct_as_class():
    src = "struct Point { int x; int y; };"
    parsed = CParser().parse("point.h", src)
    assert len(parsed.classes) >= 1
    assert parsed.classes[0].name == "Point"
    assert len(parsed.classes[0].fields) >= 2

def test_function_extracted():
    src = "int add(int a, int b) { return a + b; }"
    parsed = CParser().parse("math.c", src)
    assert any(f.name == "add" for f in parsed.functions)

def test_include_extracted():
    src = '#include <stdio.h>\n#include "myheader.h"'
    parsed = CParser().parse("main.c", src)
    assert len(parsed.imports) >= 2
