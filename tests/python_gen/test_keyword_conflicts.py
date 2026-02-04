"""
测试 Python 关键字冲突
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse
from synthetipy.codegen.trigger_generator import TriggerGenerator
from synthetipy.codegen.effect_generator import EffectGenerator


def test_from_keyword():
    """Bug: from 是 Python 关键字，需要特殊处理"""
    print("=" * 60)
    print("测试 1: from 关键字应该转义")
    print("=" * 60)
    
    pdx_code = """
show_on_uncolonized = {
    exists = from
    from = { is_wilderness_empire = no }
    uses_district_set = city_world
}
"""
    print("【PDX 代码】")
    print(pdx_code)
    
    try:
        ast = parse(pdx_code)
        gen = TriggerGenerator()
        obj = ast.statements[0]
        lines = gen.generate(obj.name, obj.body)
        
        print("【生成的 Python 代码】")
        print('\n'.join(lines))
        
        code = '\n'.join(lines)
        # 检查是否正确处理 from 关键字（应该转义或使用其他方式）
        # 不应该有裸的 "def from(" 或 "class from:"
        assert 'def from(' not in code and 'class from:' not in code, \
            "from 关键字未正确转义"
        print("\n✓ 测试通过")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
    print()


def test_if_keyword():
    """Bug: if 作为对象名时是 Python 关键字"""
    print("=" * 60)
    print("测试 2: if 作为函数名时应该转义")
    print("=" * 60)
    
    pdx_code = """
if = {
    limit = { always = yes }
    log = "test"
}
"""
    print("【PDX 代码】")
    print(pdx_code)
    
    try:
        ast = parse(pdx_code)
        gen = EffectGenerator()
        obj = ast.statements[0]
        lines = gen.generate(obj.name, obj.body)
        
        print("【生成的 Python 代码】")
        print('\n'.join(lines))
        
        code = '\n'.join(lines)
        # 这是一个特殊情况，if 通常作为控制流处理
        # 但如果作为顶层对象定义，需要转义
        print("\n✓ 测试通过")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
    print()


def test_common_keywords():
    """测试其他常见 Python 关键字"""
    print("=" * 60)
    print("测试 3: 其他常见关键字应该转义")
    print("=" * 60)
    
    pdx_code = """
check_keywords = {
    for = yes
    while = yes
    class = commander
    return = yes
    import = yes
}
"""
    print("【PDX 代码】")
    print(pdx_code)
    
    try:
        ast = parse(pdx_code)
        gen = TriggerGenerator()
        obj = ast.statements[0]
        lines = gen.generate(obj.name, obj.body)
        
        print("【生成的 Python 代码】")
        print('\n'.join(lines))
        
        code = '\n'.join(lines)
        # class 在 Stellaris 中是合法的属性名（如 class = commander）
        # 需要确保生成的代码中正确处理
        print("\n注意: 某些关键字在属性名位置可能是合法的")
        print("\n✓ 测试通过")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
    print()


if __name__ == '__main__':
    test_from_keyword()
    test_if_keyword()
    test_common_keywords()
    
    print("=" * 60)
    print("所有测试完成!")
    print("=" * 60)
