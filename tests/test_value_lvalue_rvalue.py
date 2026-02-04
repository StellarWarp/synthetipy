import pytest
from synthetipy.parsing.lexer import Lexer
from synthetipy.parser import Parser
from synthetipy.ast_nodes import LiteralNode, IdentifierExpressionNode, IdentifierNode


def parse_src(src: str):
    lexer = Lexer(src)
    tokens = lexer.tokenize()
    parser = Parser(tokens, source_text=src)
    return parser.parse()


def test_lhs_numeric_key_allowed():
    src = '0 = { nested = 1 }'
    doc = parse_src(src)
    # should parse as object? in top-level this becomes PropertyNode with key 0
    assert len(doc.statements) == 1


def test_lhs_constant_allowed():
    src = '@MYCONST = 5'
    doc = parse_src(src)
    assert len(doc.statements) == 1


def test_rvalue_identifier_expr():
    src = 'check = owner.variable_name@prev'
    doc = parse_src(src)
    prop = doc.statements[0]
    # RHS should be an IdentifierExpressionNode
    assert isinstance(prop.value, IdentifierExpressionNode)


def test_lhs_path_error_nested():
    src = 'owner = { child = { owner.jobs/miners_add = yes } }'
    with pytest.raises(Exception):
        parse_src(src)
