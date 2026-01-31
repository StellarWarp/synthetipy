"""测试双方括号参数语法 [[PARAM] ... ]"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import Lexer, Parser


def test_double_bracket_param():
    """测试双方括号参数语法"""
    code = """
test_effect = {
    any_owned_pop_group = {
        [[SPIRITUALIST]
            is_spiritualist = yes
        ]
        [[!SPIRITUALIST]
            is_spiritualist = no
        ]
    }
}
"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    print("\n=== Tokens for double bracket param ===")
    for token in tokens:
        if token.type.name not in ('NEWLINE', 'COMMENT'):
            print(f"{token.type.name:15} {repr(token.value)}")
    
    try:
        parser = Parser(tokens)
        doc = parser.parse()
        assert doc is not None
        print(f"\n✅ Successfully parsed {len(doc.statements)} statement(s)")
        
        # 打印 AST 结构
        print("\n=== AST Structure ===")
        for stmt in doc.statements:
            print(f"  {stmt}")
            if hasattr(stmt, 'body') and hasattr(stmt.body, 'statements'):
                for s in stmt.body.statements:
                    print(f"    {s}")
                    if hasattr(s, 'body') and isinstance(s.body, list):
                        for b in s.body:
                            print(f"      {b}")
    except Exception as e:
        import traceback
        print(f"\n❌ Failed to parse: {e}")
        traceback.print_exc()


if __name__ == '__main__':
    test_double_bracket_param()
