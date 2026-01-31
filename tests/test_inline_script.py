"""
测试 Inline Script 解析和展开功能
"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse, InlineScriptResolver
from synthetipy.ast_nodes import ObjectNode, PropertyNode, BlockNode

# Stellaris 游戏目录
GAME_ROOT = Path("D:/SteamLibrary/steamapps/common/Stellaris")


def test_load_inline_script():
    """测试加载 inline_script"""
    print("\n" + "=" * 60)
    print("测试 1: 加载 inline_script 文件")
    print("=" * 60)
    
    resolver = InlineScriptResolver(GAME_ROOT)
    
    # 尝试加载几个常见的 inline_script
    scripts_to_test = [
        "jobs/roboticist_add",
        "jobs/soldiers_add",
        "buildings/on_all_capital_buildings",
    ]
    
    for script_path in scripts_to_test:
        print(f"\n加载: {script_path}")
        block = resolver.load_script(script_path)
        
        if block:
            print(f"  [OK] 语句数: {len(block.statements)}")
            # 显示前几个语句
            for i, stmt in enumerate(block.statements[:3]):
                if isinstance(stmt, PropertyNode):
                    print(f"    - {stmt.key} = ...")
        else:
            print(f"  [FAIL] 加载失败")


def test_unpack_inline_script():
    """测试展开 inline_script"""
    print("\n" + "=" * 60)
    print("测试 2: 展开 inline_script")
    print("=" * 60)
    
    # 创建一个包含 inline_script 的测试代码
    code = """
building_test = {
    category = research
    
    inline_script = {
        script = jobs/roboticist_add
        AMOUNT = @b1_jobs
    }
    
    cost = {
        minerals = 400
    }
}
"""
    
    # 解析
    ast = parse(code)
    print(f"\n原始 AST:")
    print(f"  对象数: {len(ast.statements)}")
    
    if ast.statements:
        obj = ast.statements[0]
        print(f"  对象名: {obj.name}")
        print(f"  属性数: {len(obj.body.statements)}")
        
        # 显示属性
        for stmt in obj.body.statements:
            if isinstance(stmt, PropertyNode):
                print(f"    - {stmt.key}")
    
    # 展开 inline_script
    print(f"\n展开 inline_script...")
    resolver = InlineScriptResolver(GAME_ROOT)
    
    try:
        unpacked_ast = resolver.unpack_inline_scripts(ast)
        
        print(f"\n展开后的 AST:")
        print(f"  对象数: {len(unpacked_ast.statements)}")
        
        if unpacked_ast.statements:
            obj = unpacked_ast.statements[0]
            print(f"  对象名: {obj.name}")
            print(f"  属性数: {len(obj.body.statements)}")
            
            # 显示属性
            for stmt in obj.body.statements:
                if isinstance(stmt, PropertyNode):
                    print(f"    - {stmt.key}")
        
        print(f"\n[OK] 展开成功！")
        
    except Exception as e:
        print(f"\n[FAIL] 展开失败: {e}")
        import traceback
        traceback.print_exc()


def test_parameter_replacement():
    """测试参数替换"""
    print("\n" + "=" * 60)
    print("测试 3: 参数替换")
    print("=" * 60)
    
    # 创建测试代码
    code = """
test_building = {
    inline_script = {
        script = jobs/roboticist_add
        AMOUNT = 10
    }
}
"""
    
    ast = parse(code)
    resolver = InlineScriptResolver(GAME_ROOT)
    
    # 获取 inline_script 属性
    obj = ast.statements[0]
    inline_prop = None
    
    for stmt in obj.body.statements:
        if isinstance(stmt, PropertyNode) and stmt.key == 'inline_script':
            inline_prop = stmt
            break
    
    if inline_prop:
        print(f"\n找到 inline_script 属性")
        
        # 解析并展开
        expanded = resolver.resolve_inline_script_property(inline_prop)
        
        if expanded:
            print(f"[OK] 展开成功")
            print(f"  展开后语句数: {len(expanded.statements)}")
            
            # 显示展开后的内容
            for stmt in expanded.statements[:5]:
                if isinstance(stmt, PropertyNode):
                    print(f"    - {stmt.key} = {stmt.value.value if hasattr(stmt.value, 'value') else '...'}")
        else:
            print(f"[FAIL] 展开失败")
    else:
        print(f"[FAIL] 未找到 inline_script 属性")


def test_real_building():
    """测试真实建筑文件的 inline_script 展开"""
    print("\n" + "=" * 60)
    print("测试 4: 真实建筑文件")
    print("=" * 60)
    
    # 读取一个真实的建筑文件
    building_file = GAME_ROOT / "common" / "buildings" / "09_army_buildings.txt"
    
    if not building_file.exists():
        print(f"[SKIP] 文件不存在: {building_file}")
        return
    
    with open(building_file, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # 解析
    ast = parse(content)
    
    print(f"\n原始文件:")
    print(f"  对象数: {len(ast.statements)}")
    
    # 计算 inline_script 数量
    inline_count = 0
    for obj in ast.statements:
        if isinstance(obj, ObjectNode):
            for stmt in obj.body.statements:
                if isinstance(stmt, PropertyNode) and stmt.key == 'inline_script':
                    inline_count += 1
    
    print(f"  inline_script 数量: {inline_count}")
    
    # 展开
    print(f"\n展开所有 inline_script...")
    resolver = InlineScriptResolver(GAME_ROOT)
    
    try:
        unpacked_ast = resolver.unpack_inline_scripts(ast)
        
        print(f"\n展开后:")
        print(f"  对象数: {len(unpacked_ast.statements)}")
        
        # 计算展开后的 inline_script 数量（应该为 0）
        inline_count_after = 0
        total_properties = 0
        
        for obj in unpacked_ast.statements:
            if isinstance(obj, ObjectNode):
                total_properties += len(obj.body.statements)
                for stmt in obj.body.statements:
                    if isinstance(stmt, PropertyNode) and stmt.key == 'inline_script':
                        inline_count_after += 1
        
        print(f"  剩余 inline_script: {inline_count_after}")
        print(f"  总属性数: {total_properties}")
        
        if inline_count_after == 0:
            print(f"\n[OK] 所有 inline_script 已展开！")
        else:
            print(f"\n[WARN] 仍有 {inline_count_after} 个 inline_script 未展开")
        
    except Exception as e:
        print(f"\n[FAIL] 展开失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  Inline Script Resolver 测试套件")
    print("=" * 60)
    
    # 检查游戏目录
    if not GAME_ROOT.exists():
        print(f"\n错误: 游戏目录不存在: {GAME_ROOT}")
        print("请修改 GAME_ROOT 变量指向正确的 Stellaris 目录")
        return
    
    # 运行测试
    test_load_inline_script()
    test_unpack_inline_script()
    test_parameter_replacement()
    test_real_building()
    
    print("\n" + "=" * 60)
    print("  测试完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
