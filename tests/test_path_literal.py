import pytest
from synthetipy.parsing.lexer import Lexer
from synthetipy.parser import Parser
from synthetipy.ast_nodes import LiteralNode, PropertyNode, ListNode, DocumentNode


def parse_src(src: str):
    lexer = Lexer(src)
    tokens = lexer.tokenize()
    parser = Parser(tokens, source_text=src)
    return parser.parse()


def test_path_as_property_value():
    src = "script = jobs/miners_add"
    doc = parse_src(src)
    assert isinstance(doc, DocumentNode)
    assert len(doc.statements) == 1
    prop = doc.statements[0]
    assert isinstance(prop, PropertyNode)
    assert isinstance(prop.value, LiteralNode)
    assert prop.value.value == 'jobs/miners_add'
    assert prop.value.value_type == 'path'


def test_path_in_list():
    src = 'list = { jobs/miners_add other_job }'
    doc = parse_src(src)
    prop = doc.statements[0]
    assert isinstance(prop.value, ListNode)
    items = prop.value.items
    # first item should be path literal
    assert isinstance(items[0], LiteralNode)
    assert items[0].value == 'jobs/miners_add'
    assert items[0].value_type == 'path'


def test_path_after_dot_is_error():
    # owner.jobs/miners_add is invalid syntax according to decision
    src = 'owner = { child = { owner.jobs/miners_add = yes } }'
    with pytest.raises(Exception):
        parse_src(src)
