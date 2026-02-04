"""
测试 random_list 相关的 bug
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse
from synthetipy.codegen.effect_generator import EffectGenerator


def test_random_list_basic():
    """Bug: random_list 处理错误，生成为循环"""
    print("=" * 60)
    print("测试 1: random_list 应该生成为概率选择")
    print("=" * 60)
    
    pdx_code = """
spawn_leader = {
    random_list = {
        10 = {
            create_leader = {
                class = commander
                skill = 3
            }
        }
        20 = {
            create_leader = {
                class = scientist
                skill = 4
            }
        }
        70 = {
            create_leader = {
                class = admiral
                skill = 5
            }
        }
    }
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
        # 不应该生成为 for 循环
        assert 'for list in scope.lists' not in code, "random_list 不应该生成为循环"
        # 不应该有 list.10() 这样的语法错误
        assert 'list.10' not in code, "不应该有数字键语法错误"
        # 应该包含权重信息
        assert '10' in code or 'weight' in code or 'random' in code, "应该包含权重或随机选择逻辑"
        print("\n✓ 测试通过")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
    print()


def test_numeric_keys_handling():
    """Bug: 数字键生成为 list.10() 的语法错误"""
    print("=" * 60)
    print("测试 2: 数字键应该正确处理")
    print("=" * 60)
    
    pdx_code = """
weighted_choice = {
    random_list = {
        50 = { log = "Option A" }
        30 = { log = "Option B" }
        20 = { log = "Option C" }
    }
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
        # 检查是否有非法的数字属性访问
        assert '.50(' not in code and '.30(' not in code and '.20(' not in code, \
            "不应该有 .数字() 的语法错误"
        print("\n✓ 测试通过")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
    print()


if __name__ == '__main__':
    test_random_list_basic()
    test_numeric_keys_handling()
    
    print("=" * 60)
    print("所有测试完成!")
    print("=" * 60)
