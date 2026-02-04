"""
检查解析后 inline_script 的 AST 结构
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse
from synthetipy.ast_nodes import *


def print_ast(node, indent=0):
    """打印 AST 结构"""
    prefix = "  " * indent
    
    if isinstance(node, PropertyNode):
        print(f"{prefix}PropertyNode(key='{node.key}')")
        print(f"{prefix}  value:")
        print_ast(node.value, indent + 2)
    elif isinstance(node, ObjectNode):
        print(f"{prefix}ObjectNode(name='{node.name}')")
        print(f"{prefix}  body:")
        print_ast(node.body, indent + 2)
    elif isinstance(node, BlockNode):
        print(f"{prefix}BlockNode(statements={len(node.statements)})")
        for i, stmt in enumerate(node.statements):
            print(f"{prefix}  [{i}]:")
            print_ast(stmt, indent + 2)
    elif isinstance(node, LiteralNode):
        print(f"{prefix}LiteralNode(value={repr(node.value)})")
    elif isinstance(node, IdentifierExpressionNode):
        print(f"{prefix}IdentifierExpressionNode(expression={repr(node.expression)})")
    else:
        print(f"{prefix}{type(node).__name__}")


def main():
    # 测试三种 inline_script 格式
    code = """
test1 = {
    inline_script = jobs/wranglers_or_variant_add
}

test2 = {
    inline_script = {
        script = jobs/politician_add
        AMOUNT = 10
    }
}

test3 = {
    cost = 100
    inline_script = jobs/test
    resources = 50
}
"""
    
    print("=" * 60)
    print("解析 inline_script AST 结构")
    print("=" * 60)
    
    ast = parse(code)
    
    print("\nAST 结构:")
    for i, obj in enumerate(ast.statements):
        print(f"\n对象 {i+1}:")
        print_ast(obj)
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
