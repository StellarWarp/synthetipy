"""
测试 inline_script 解析
"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse
from synthetipy.ast_nodes import InlineScriptNode, PropertyNode, BlockNode

def test_inline_script_simple():
    """测试简单形式的 inline_script"""
    print("=" * 60)
    print("测试 1: 简单形式 inline_script")
    print("=" * 60)
    
    pdx_code = """
building_test = {
    inline_script = jobs/researcher_add
}
"""
    
    ast = parse(pdx_code)
    print(f"AST: {ast}")
    print(f"Statements: {ast.statements}")
    
    # 检查是否解析为 InlineScriptNode
    building = ast.statements[0]
    print(f"Building: {building}")
    print(f"Building body statements: {building.body.statements}")
    
    inline_prop = building.body.statements[0]
    print(f"Inline property: {inline_prop}")
    print(f"Inline property key: {inline_prop.key}")
    print(f"Inline property value type: {type(inline_prop.value)}")
    print(f"Inline property value: {inline_prop.value}")
    
    if isinstance(inline_prop.value, InlineScriptNode):
        print(f"✅ 成功解析为 InlineScriptNode")
        print(f"   Script path: {inline_prop.value.script_path}")
        print(f"   Parameters: {inline_prop.value.parameters}")
    else:
        print(f"❌ 未能解析为 InlineScriptNode，而是: {type(inline_prop.value)}")
    print()


def test_inline_script_with_params():
    """测试带参数的 inline_script"""
    print("=" * 60)
    print("测试 2: 带参数的 inline_script")
    print("=" * 60)
    
    pdx_code = """
building_test = {
    inline_script = {
        script = jobs/researcher_add
        AMOUNT = 10
        TYPE = physics
    }
}
"""
    
    ast = parse(pdx_code)
    building = ast.statements[0]
    inline_prop = building.body.statements[0]
    
    print(f"Inline property value type: {type(inline_prop.value)}")
    
    if isinstance(inline_prop.value, InlineScriptNode):
        print(f"✅ 成功解析为 InlineScriptNode")
        print(f"   Script path: {inline_prop.value.script_path}")
        print(f"   Parameters: {inline_prop.value.parameters}")
    else:
        print(f"❌ 未能解析为 InlineScriptNode，而是: {type(inline_prop.value)}")
    print()


def test_inline_script_in_real_code():
    """测试真实代码中的 inline_script"""
    print("=" * 60)
    print("测试 3: 真实代码中的 inline_script")
    print("=" * 60)
    
    pdx_code = """
building_capital = {
    category = government
    
    inline_script = {
        script = buildings/on_all_capital_buildings
    }
    
    inline_script = {
        script = buildings/regular_empire_capital_jobs
        AMOUNT = 200
    }
    
    resources = {
        cost = {
            minerals = 1000
        }
    }
}
"""
    
    ast = parse(pdx_code)
    building = ast.statements[0]
    
    print(f"Building statements count: {len(building.body.statements)}")
    
    inline_count = 0
    for stmt in building.body.statements:
        if isinstance(stmt, PropertyNode) and str(stmt.key) == 'inline_script':
            inline_count += 1
            if isinstance(stmt.value, InlineScriptNode):
                print(f"✅ Inline script {inline_count}:")
                print(f"   Script: {stmt.value.script_path}")
                print(f"   Params: {stmt.value.parameters}")
            else:
                print(f"❌ Inline script {inline_count} 未正确解析")
    
    print(f"\n总共找到 {inline_count} 个 inline_script")
    print()


if __name__ == '__main__':
    test_inline_script_simple()
    test_inline_script_with_params()
    test_inline_script_in_real_code()
    
    print("=" * 60)
    print("所有测试完成!")
    print("=" * 60)
