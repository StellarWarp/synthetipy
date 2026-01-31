"""测试复杂的内联运算表达式"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import Lexer, Parser


def test_complex_arithmetic_operators():
    """测试各种算术运算符 +, -, *, /, 括号"""
    code = """
test_effect = {
    value1 = @[ base_value + 10 ]
    value2 = @[ base_value - 5 ]
    value3 = @[ base_value * 2 ]
    value4 = @[ base_value / 3 ]
    value5 = @[ (base_value + 10) * 2 ]
    value6 = @[ base_value + modifier * 0.5 ]
}
"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    print("\n=== Complex arithmetic operators ===")
    # 只显示运算符相关的 tokens
    for token in tokens:
        if token.type.name in ('PLUS', 'MINUS', 'MULTIPLY', 'DIVIDE', 'LPAREN', 'RPAREN'):
            print(f"{token.type.name:15} {repr(token.value)}")
    
    parser = Parser(tokens)
    doc = parser.parse()
    assert doc is not None
    print(f"✅ Successfully parsed {len(doc.statements)} statement(s)")


def test_nested_expression():
    """测试嵌套表达式"""
    code = """
test_effect = {
    complex_value = @[ ((base + modifier) * multiplier - offset) / divisor ]
}
"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    print("\n=== Nested expression tokens ===")
    in_arithmetic = False
    for token in tokens:
        if token.type.name == 'VARIABLE' and token.value in ('@', '@\\'):
            in_arithmetic = True
        if in_arithmetic and token.type.name not in ('NEWLINE', 'COMMENT'):
            print(f"{token.type.name:15} {repr(token.value)}")
        if token.type.name == 'RBRACKET':
            in_arithmetic = False
    
    parser = Parser(tokens)
    doc = parser.parse()
    assert doc is not None
    print(f"✅ Successfully parsed {len(doc.statements)} statement(s)")


def test_real_game_example():
    """测试真实游戏代码示例"""
    code = """
complex_trigger_modifier = {
    trigger = count_owned_planet
    trigger_scope = owner
    parameters = {
        limit = {
            has_modifier = instability_join_revolt
            planet_stability < @[ stabilitylevel2 + 10 ]
            exists = controller
            controller = { is_same_value = root.owner }
        }
    }
    potential = {
        owner = {
            any_owned_planet = {
                has_modifier = instability_join_revolt
                planet_stability < @[ stabilitylevel2 + 10 ]
                exists = controller
                controller = { is_same_value = root.owner }
            }
        }
    }
    desc = STRING_REBELLIOUS_JOINER_PLANETS_IN_OWNER
    mode = add
    mult = 1.5
}
"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    parser = Parser(tokens)
    doc = parser.parse()
    assert doc is not None
    print(f"\n✅ Successfully parsed real game example: {len(doc.statements)} statement(s)")


if __name__ == '__main__':
    test_complex_arithmetic_operators()
    test_nested_expression()
    test_real_game_example()
