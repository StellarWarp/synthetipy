"""
测试控制流相关的 bug
"""

import sys
from pathlib import Path

# sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from synthetipy import parse
from synthetipy.codegen.trigger_generator import TriggerGenerator
from synthetipy.codegen.effect_generator import EffectGenerator


def test_if_block_content_preserved():
    """Bug: if 块内容丢失，只生成 _result_1 = True"""
    print("=" * 60)
    print("测试 1: if 块内容应该保留")
    print("=" * 60)
    
    pdx_code = """
allow = {
    has_upgraded_capital = yes
    if = {
        limit = {
            exists = orbital_defence
        }
        orbital_defence = {
            exists = starbase
            starbase = {
                NOR = {
                    has_starbase_building = ring_noble_estates
                    is_starbase_building_building = ring_noble_estates
                }
                owner = {
                    has_flag = machine_intelligence
                }
            }
        }
    }
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
        
        # 检查是否包含 orbital_defence 和 starbase 的逻辑
        code = '\n'.join(lines)
        assert 'orbital_defence' in code, "orbital_defence 逻辑丢失"
        assert 'starbase' in code, "starbase 逻辑丢失"
        assert '_result_1 = True' not in code, "不应该生成占位符"
        print("\n✓ 测试通过")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
    print()


def test_hidden_trigger_content():
    """Bug: hidden_trigger 块内容丢失"""
    print("=" * 60)
    print("测试 2: hidden_trigger 块内容应该保留")
    print("=" * 60)
    
    pdx_code = """
is_unemployed = {
    hidden_trigger = {
        OR = {
            is_pop_category = ruler_unemployment
            is_pop_category = specialist_unemployment
            is_pop_category = worker_unemployment
        }
    }
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
        assert 'is_pop_category' in code, "hidden_trigger 内容丢失"
        assert 'ruler_unemployment' in code, "具体逻辑丢失"
        print("\n✓ 测试通过")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
    print()


def test_hidden_effect_content():
    """Bug: hidden_effect 块内容丢失"""
    print("=" * 60)
    print("测试 3: hidden_effect 块内容应该保留")
    print("=" * 60)
    
    pdx_code = """
set_first_contact = {
    custom_tooltip = start_first_contact
    hidden_effect = {
        owner = {
            set_timed_country_flag = {
                flag = recent_first_contact
                years = 20
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
        assert 'set_timed_country_flag' in code, "hidden_effect 内容丢失"
        assert 'recent_first_contact' in code, "具体逻辑丢失"
        print("\n✓ 测试通过")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
    print()


def test_switch_statement():
    """Bug: switch 语句生成 if None:"""
    print("=" * 60)
    print("测试 4: switch 语句应该正确处理")
    print("=" * 60)
    
    pdx_code = """
contact_enclave = {
    contact_country = {
        switch = {
            trigger = is_country_type
            enclave = {
                setup_first_contact_path = { TYPE = enclave }
            }
            tiyanki = {
                setup_first_contact_path = { TYPE = tiyanki }
            }
            default = {
                log_error = "Unknown type"
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
        assert 'if None:' not in code, "不应该生成 if None:"
        assert 'is_country_type' in code, "trigger 丢失"
        print("\n✓ 测试通过")
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
    print()


def test_if_with_unconvertible_limit_raises():
    pdx = """
    allow = {
        if = {
            limit = {
                unknown_block = { foo = bar }
            }
            some_flag = yes
        }
    }
    """
    ast = parse(pdx)
    gen = TriggerGenerator()

    obj = ast.statements[0]
    import pytest
    from synthetipy.codegen.exceptions import MissingConditionError
    with pytest.raises(MissingConditionError):
        gen.generate(obj.name, obj.body)


if __name__ == '__main__':
    test_if_block_content_preserved()
    test_hidden_trigger_content()
    test_hidden_effect_content()
    test_switch_statement()
    
    print("=" * 60)
    print("所有测试完成!")
    print("=" * 60)
