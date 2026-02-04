"""
测试特殊语法相关的 bug (trigger:, modifier:, event_target:)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse
from synthetipy.codegen.value_generator import ValueGenerator
from synthetipy.codegen.effect_generator import EffectGenerator


def test_trigger_colon_syntax():
    """Bug: trigger: 语法没有转换为函数调用"""
    print("=" * 60)
    print("测试 1: trigger: 语法应该转换为函数调用")
    print("=" * 60)
    
    pdx_code = """
leader_election_mult = {
    base = 2
    add = trigger:num_candidate_supported
    mult = 0.5
}
"""
    print("【PDX 代码】")
    print(pdx_code)
    
    try:
        ast = parse(pdx_code)
        gen = ValueGenerator()
        obj = ast.statements[0]
        lines = gen.generate(obj.name, obj.body)
        
        print("【生成的 Python 代码】")
        print('\n'.join(lines))
        
        code = '\n'.join(lines)
        # 应该生成 scope.num_candidate_supported()
        assert 'trigger:num_candidate_supported' not in code, "trigger: 语法未转换"
        assert 'num_candidate_supported()' in code, "应该生成函数调用"
        print("\n✓ 测试通过")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
    print()


def test_modifier_colon_syntax():
    """Bug: modifier: 语法没有转换为函数调用"""
    print("=" * 60)
    print("测试 2: modifier: 语法应该转换为函数调用")
    print("=" * 60)
    
    pdx_code = """
leader_traits_modified = {
    add = this.leader_traits_unmodified
    if = {
        limit = { exists = owner }
        add = owner.modifier:negative_traits_country
    }
}
"""
    print("【PDX 代码】")
    print(pdx_code)
    
    try:
        ast = parse(pdx_code)
        gen = ValueGenerator()
        obj = ast.statements[0]
        lines = gen.generate(obj.name, obj.body)
        
        print("【生成的 Python 代码】")
        print('\n'.join(lines))
        
        code = '\n'.join(lines)
        # 应该生成 scope.owner.negative_traits_country()
        assert 'modifier:negative_traits_country' not in code, "modifier: 语法未转换"
        assert 'negative_traits_country()' in code, "应该生成函数调用"
        print("\n✓ 测试通过")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
    print()


def test_event_target_colon_syntax():
    """Bug: event_target: 语法没有转换"""
    print("=" * 60)
    print("测试 3: event_target: 语法应该转换")
    print("=" * 60)
    
    pdx_code = """
contact_system = {
    event_target:formless_system = {
        every_fleet_in_system = {
            limit = {
                owner = {
                    is_same_value = event_target:the_seal_owner
                }
            }
            add_modifier = {
                modifier = some_modifier
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
        # 应该正确处理 event_target
        assert 'event_target:formless_system' not in code or 'get_event_target' in code, "event_target 语法未正确转换"
        print("\n✓ 测试通过")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
    print()


if __name__ == '__main__':
    test_trigger_colon_syntax()
    test_modifier_colon_syntax()
    test_event_target_colon_syntax()
    
    print("=" * 60)
    print("所有测试完成!")
    print("=" * 60)
