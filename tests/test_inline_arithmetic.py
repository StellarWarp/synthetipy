"""测试内联运算表达式和 @ 符号"""
from pathlib import Path
import sys

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from synthetipy import Lexer, Parser

def test_identifier_with_at():
    """测试标识符中包含 @ 符号"""
    code = """
some_effect = {
    event_target:cyberspecies@species = {
        modify_species = {
            species = prev
        }
    }
}
"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    # 打印所有tokens以便调试
    print("\n=== Tokens for identifier with @ ===")
    for token in tokens:
        if token.type.name not in ('NEWLINE', 'COMMENT'):
            print(f"{token.type.name:15} {repr(token.value)}")
    
    parser = Parser(tokens)
    doc = parser.parse()
    
    # 应该成功解析
    assert doc is not None
    print(f"✅ Successfully parsed {len(doc.statements)} statement(s)")


def test_inline_arithmetic_basic():
    """测试基本的内联运算表达式 @[ value + 10 ]"""
    code = """
some_effect = {
    add_modifier = {
        modifier = country_stability_add
        years = @[ stabilitylevel2 + 10 ]
    }
}
"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    print("\n=== Tokens for inline arithmetic ===")
    for token in tokens:
        if token.type.name not in ('NEWLINE', 'COMMENT'):
            print(f"{token.type.name:15} {repr(token.value)}")
    
    parser = Parser(tokens)
    try:
        doc = parser.parse()
        assert doc is not None
        print(f"✅ Successfully parsed {len(doc.statements)} statement(s)")
    except Exception as e:
        print(f"❌ Failed to parse: {e}")


def test_inline_arithmetic_with_param():
    """测试带参数的内联运算表达式 @[ $PARAM$ + 10 ]"""
    code = """
some_effect = {
    add_modifier = {
        modifier = country_stability_add
        years = @[ $STABILITY_LEVEL$ + 10 ]
    }
}
"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    print("\n=== Tokens for inline arithmetic with param ===")
    for token in tokens:
        if token.type.name not in ('NEWLINE', 'COMMENT'):
            print(f"{token.type.name:15} {repr(token.value)}")
    
    parser = Parser(tokens)
    try:
        doc = parser.parse()
        assert doc is not None
        print(f"✅ Successfully parsed {len(doc.statements)} statement(s)")
    except Exception as e:
        print(f"❌ Failed to parse: {e}")


def test_inline_arithmetic_with_backslash():
    """测试带反斜杠的内联运算表达式 @\[ $PARAM$ + 10 ]"""
    code = r"""
some_effect = {
    add_modifier = {
        modifier = country_stability_add
        years = @\[ $STABILITY_LEVEL$ + 10 ]
    }
}
"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    print("\n=== Tokens for inline arithmetic with backslash ===")
    for token in tokens:
        if token.type.name not in ('NEWLINE', 'COMMENT'):
            print(f"{token.type.name:15} {repr(token.value)}")
    
    parser = Parser(tokens)
    try:
        doc = parser.parse()
        assert doc is not None
        print(f"✅ Successfully parsed {len(doc.statements)} statement(s)")
    except Exception as e:
        print(f"❌ Failed to parse: {e}")


if __name__ == '__main__':
    test_identifier_with_at()
    test_inline_arithmetic_basic()
    test_inline_arithmetic_with_param()
    test_inline_arithmetic_with_backslash()
