import pytest
from app.parsing.ruby import RubyParser

def test_module_class_nesting():
    src = "module Api\n  class UsersController\n    def index; end\n  end\nend"
    parsed = RubyParser().parse("users_controller.rb", src)
    assert len(parsed.classes) >= 1
    assert parsed.classes[0].qualified_name == "Api::UsersController"

def test_method_extracted():
    src = "class Foo\n  def bar; end\nend"
    parsed = RubyParser().parse("foo.rb", src)
    assert parsed.classes[0].methods[0].name == "bar"

def test_require_extracted():
    src = 'require "json"\nrequire_relative "./helper"'
    parsed = RubyParser().parse("app.rb", src)
    assert len(parsed.imports) >= 2
