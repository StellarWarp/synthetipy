import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy.parser import parse
from synthetipy.ast_nodes import *

code = """
building_test = {
    category = research
    cost = 400
}
"""

ast = parse(code)
obj = ast.statements[0]

print(f'Object: {obj.name}')
print(f'Body statements: {len(obj.body.statements)}')

for stmt in obj.body.statements:
    print(f'  - {type(stmt).__name__}: {stmt}')
    if isinstance(stmt, PropertyNode):
        print(f'    key: {stmt.key}')
        print(f'    value: {stmt.value}')
