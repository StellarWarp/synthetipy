"""调试双方括号解析"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import Lexer
from synthetipy.parser import Parser

code = """
test_effect = {
    any_owned_pop_group = {
        [[SPIRITUALIST]
            is_spiritualist = yes
        ]
    }
}
"""

lexer = Lexer(code)
tokens = lexer.tokenize()

print("=== Tokens ===")
for i, token in enumerate(tokens):
    if token.type.name not in ('NEWLINE', 'COMMENT'):
        print(f"{i:3}: {token.type.name:15} {repr(token.value)}")

print("\n=== Parsing ===")
parser = Parser(tokens)

print(f"Total tokens: {len(tokens)}")
print(f"Filtered tokens: {len(parser.filtered_tokens)}")
print("\nFiltered tokens:")
for i, t in enumerate(parser.filtered_tokens):
    print(f"  {i}: {t.type.name:15} {repr(t.value)}")

# 打开 parser 的调试模式（如果有）
try:
    doc = parser.parse()
    print(f"\nParsed {len(doc.statements)} statements")
    if doc.statements:
        for stmt in doc.statements:
            print(f"  - {stmt}")
except Exception as e:
    import traceback
    print(f"\nFailed: {e}")
    traceback.print_exc()
