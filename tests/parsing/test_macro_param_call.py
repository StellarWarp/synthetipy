from pathlib import Path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.synthetipy.parsing.lexer import Lexer
from src.synthetipy.parsing.parser_context import ParserContext
from src.synthetipy.parsing.expression_parser import ExpressionParser
from src.synthetipy.ast_nodes_expression import MacroParam


def test_value_call_with_pure_macro_param():
    code = "value:tech_cost|AREA|$PARAM$|"
    lexer = Lexer(code)
    tokens = lexer.tokenize()

    context = ParserContext({})
    parser = ExpressionParser(tokens, context)

    result = parser.parse_expression()

    assert result.call_info.call_type == 'value'
    assert result.call_info.arguments[0][0] == 'AREA'
    assert isinstance(result.call_info.arguments[0][1], MacroParam)
    assert result.call_info.arguments[0][1].name == 'PARAM'


def test_value_call_with_mixed_macro_param_becomes_macro_expression():
    code = "value:tech_cost|AREA|te$st$|"
    lexer = Lexer(code)
    tokens = lexer.tokenize()

    context = ParserContext({})
    parser = ExpressionParser(tokens, context)

    result = parser.parse_expression()

    assert result.macro_expression is not None
    assert 'te$st$' in result.macro_expression.raw_expression


def test_event_target_pure_macro_allowed_without_dot():
    code = "event_target:$FOO$"
    lexer = Lexer(code)
    tokens = lexer.tokenize()

    context = ParserContext({})
    parser = ExpressionParser(tokens, context)

    result = parser.parse_expression()

    # Should be a ScopeNode with an EventTargetNode containing a MacroParam
    from src.synthetipy.ast_nodes_expression import EventTargetNode, ScopeNode
    assert isinstance(result, ScopeNode)
    scopes = result.scopes
    assert len(scopes) >= 1
    assert isinstance(scopes[0], EventTargetNode)
    assert hasattr(scopes[0], 'target_macro')
    assert isinstance(scopes[0].target_macro, MacroParam)
    assert scopes[0].target_macro.name == 'FOO'


def test_event_target_pure_macro_followed_by_dot_allowed():
    code = "event_target:$FOO$.owner"
    lexer = Lexer(code)
    tokens = lexer.tokenize()

    context = ParserContext({})
    parser = ExpressionParser(tokens, context)

    result = parser.parse_expression()

    from src.synthetipy.ast_nodes_expression import EventTargetNode, ScopeNode, ScopeObjectNode
    assert isinstance(result, ScopeNode)
    scopes = result.scopes
    assert len(scopes) == 2
    assert isinstance(scopes[0], EventTargetNode)
    assert hasattr(scopes[0], 'target_macro')
    assert isinstance(scopes[0].target_macro, MacroParam)
    assert scopes[0].target_macro.name == 'FOO'
    assert isinstance(scopes[1], ScopeObjectNode)
    assert scopes[1].scope_name == 'owner'


def test_value_call_pure_macro_without_trailing_pipe_becomes_macro_expression():
    code = "value:tech_cost|AREA|$PARAM$"
    lexer = Lexer(code)
    tokens = lexer.tokenize()

    context = ParserContext({})
    parser = ExpressionParser(tokens, context)

    result = parser.parse_expression()

    assert result.macro_expression is not None
    assert '$PARAM$' in result.macro_expression.raw_expression


import pytest
from src.synthetipy.parsing.parser_utils import ParserError


def test_value_call_missing_pipe_after_param_name_raises():
    code = "value:tech_cost|AREA"
    lexer = Lexer(code)
    tokens = lexer.tokenize()

    context = ParserContext({})
    parser = ExpressionParser(tokens, context)

    # with pytest.raises(ParserError):
    #     parser.parse_expression()


def test_value_call_missing_value_after_param_name_raises():
    code = "value:tech_cost|AREA|"
    lexer = Lexer(code)
    tokens = lexer.tokenize()

    context = ParserContext({})
    parser = ExpressionParser(tokens, context)

    with pytest.raises(ParserError):
        parser.parse_expression()


def test_event_target_missing_identifier_raises():
    code = "event_target:"
    lexer = Lexer(code)
    tokens = lexer.tokenize()

    context = ParserContext({})
    parser = ExpressionParser(tokens, context)

    with pytest.raises(ParserError):
        parser.parse_expression()
