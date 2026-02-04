"""
测试 Effect 生成器

测试将 PDX effect 块转换为 Python 命令式代码的功能
"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy.parsing.lexer import Lexer
from synthetipy import Parser
from synthetipy.codegen.effect_generator import EffectGenerator


def parse_pdx_effect(pdx_code: str):
    """解析 PDX 代码并返回 AST"""
    lexer = Lexer(pdx_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()


# ============================================================
# Effect 测试用例 - 涵盖所有主要特性
# ============================================================

# 测试 1: 简单效果 (变量操作、标记设置)
SIMPLE_EFFECT = """
initialize_planet = {
    set_variable = {
        which = counter
        value = 0
    }
    set_planet_flag = initialized
    add_modifier = {
        modifier = growth_bonus
        years = 10
    }
}
"""

# 测试 2: 条件分支 (if/else)
CONDITIONAL_EFFECT = """
smart_build = {
    if = {
        limit = {
            free_building_slots > 0
        }
        add_building = building_factory
    }
    else = {
        remove_building = building_old
        add_building = building_factory
    }
}
"""

# 测试 3: 嵌套条件 (if/else_if/else)
NESTED_CONDITIONAL = """
optimize_planet = {
    if = {
        limit = {
            has_designation = col_research
        }
        add_building = building_research_lab
    }
    else_if = {
        limit = {
            has_designation = col_forge
        }
        add_building = building_foundry
    }
    else = {
        add_building = building_basic
    }
}
"""

# 测试 4: 循环遍历 (every_*)
LOOP_EFFECT = """
upgrade_all_planets = {
    every_owned_planet = {
        limit = {
            num_pops >= 10
        }
        add_modifier = {
            modifier = developed_world
            years = 5
        }
        set_planet_flag = upgraded
    }
}
"""

# 测试 5: 作用域切换
SCOPE_SWITCH = """
notify_owner = {
    owner = {
        add_resource = {
            minerals = 1000
        }
        send_message = {
            title = "Planet Developed"
            text = "Your planet has been upgraded."
        }
    }
}
"""

# 测试 6: 变量算术操作
VARIABLE_ARITHMETIC = """
update_counters = {
    add_variable = {
        which = build_counter
        value = 1
    }
    subtract_variable = {
        which = resource_spent
        value = 100
    }
    if = {
        limit = {
            check_variable = {
                which = build_counter
                value >= 10
            }
        }
        set_variable = {
            which = build_counter
            value = 0
        }
    }
}
"""

# 测试 7: 复杂嵌套 (来自真实示例)
COMPLEX_EFFECT = """
bca_monthly_planet_check = {
    every_owned_planet = {
        limit = {
            has_building_construction = no
        }
        if = {
            limit = {
                free_district_slots = 0
            }
            if = {
                limit = {
                    has_planet_flag = bca_pf_district_balanced
                }
                add_variable = {
                    which = bca_district_balanced_test_counter
                    value = 1
                }
                if = {
                    limit = {
                        check_variable = {
                            which = bca_district_balanced_test_counter
                            value >= 12
                        }
                    }
                    bca_test_district_to_replace_entry = yes
                    set_variable = {
                        which = bca_district_balanced_test_counter
                        value = 0
                    }
                }
            }
            else = {
                if = {
                    limit = {
                        NOT = { has_planet_flag = bca_pf_has_district_remove_plan }
                    }
                    set_planet_flag = bca_pf_previous_has_district_remove_plan_clear
                }
                bca_test_district_to_replace_entry = yes
                if = {
                    limit = {
                        has_planet_flag = bca_pf_previous_has_district_remove_plan_clear
                        NOT = { has_planet_flag = bca_pf_has_district_remove_plan }
                    }
                    set_planet_flag = bca_pf_district_balanced
                }
                remove_planet_flag = bca_pf_previous_has_district_remove_plan_clear
            }
        }
        else = {
            remove_planet_flag = bca_pf_district_balanced
        }
    }
}
"""

# 测试 8: 事件触发和消息
EVENT_EFFECT = """
trigger_research_event = {
    fire_event = {
        id = research.100
        days = 30
    }
    owner = {
        send_message = {
            title = "Research Breakthrough"
            text = "Scientists have made a discovery!"
            type = positive
        }
    }
}
"""

# 测试 9: 内联脚本和脚本调用
SCRIPT_CALLS = """
run_optimization = {
    set_variable = {
        which = bca_selected_index
        value = -1
    }
    if = {
        limit = {
            free_jobs > 0
        }
        set_variable = {
            which = bca_non_job_provider_priority_shift
            value = 100
        }
    }
    else = {
        set_variable = {
            which = bca_non_job_provider_priority_shift
            value = 0
        }
    }
    inline_script = bca_test_list
    if = {
        limit = {
            check_variable = {
                which = bca_selected_index
                value != -1
            }
        }
        inline_script = bca_execute_selection
    }
}
"""


# ============================================================
# 预期生成的 Python 代码结构
# ============================================================

EXPECTED_SIMPLE = """
def initialize_planet(planet) -> None:
    planet.set_variable('counter', 0)
    planet.set_flag('initialized')
    planet.add_modifier('growth_bonus', years=10)
"""

EXPECTED_CONDITIONAL = """
def smart_build(planet) -> None:
    if planet.free_building_slots > 0:
        planet.add_building('building_factory')
    else:
        planet.remove_building('building_old')
        planet.add_building('building_factory')
"""

EXPECTED_LOOP = """
def upgrade_all_planets(country) -> None:
    for planet in country.owned_planets:
        if planet.num_pops < 10:
            continue
        planet.add_modifier('developed_world', years=5)
        planet.set_flag('upgraded')
"""

EXPECTED_SCOPE_SWITCH = """
def notify_owner(planet) -> None:
    owner = planet.owner
    owner.add_resource('minerals', 1000)
    owner.send_message(
        title="Planet Developed",
        text="Your planet has been upgraded.",
    )
"""

EXPECTED_COMPLEX = """
def bca_monthly_planet_check(country) -> None:
    for planet in country.owned_planets:
        if planet.has_building_construction():
            continue
        
        if planet.free_district_slots == 0:
            if planet.has_flag('bca_pf_district_balanced'):
                planet.add_variable('bca_district_balanced_test_counter', 1)
                if planet.check_variable('bca_district_balanced_test_counter') >= 12:
                    bca_test_district_to_replace_entry(planet)
                    planet.set_variable('bca_district_balanced_test_counter', 0)
            else:
                if not planet.has_flag('bca_pf_has_district_remove_plan'):
                    planet.set_flag('bca_pf_previous_has_district_remove_plan_clear')
                
                bca_test_district_to_replace_entry(planet)
                
                if (planet.has_flag('bca_pf_previous_has_district_remove_plan_clear') 
                    and not planet.has_flag('bca_pf_has_district_remove_plan')):
                    planet.set_flag('bca_pf_district_balanced')
                
                planet.remove_flag('bca_pf_previous_has_district_remove_plan_clear')
        else:
            planet.remove_flag('bca_pf_district_balanced')
"""


def print_test_case(name: str, pdx_code: str, expected: str = None):
    """打印测试用例"""
    print("\n" + "=" * 60)
    print(f"测试: {name}")
    print("=" * 60)
    
    print("\n【PDX 代码】")
    print(pdx_code.strip())
    
    if expected:
        print("\n【预期 Python 代码】")
        print(expected.strip())
    
    # 解析 AST
    try:
        ast = parse_pdx_effect(pdx_code)
        if ast.statements:
            print("\n【AST 解析成功】")
            obj = ast.statements[0]
            print(f"  定义名称: {obj.name}")
            print(f"  语句数量: {len(obj.body.statements)}")
            
            # 调用 EffectGenerator 生成代码
            generator = EffectGenerator()
            # 根据效果类型推断 scope 参数
            scope_param = 'scope'  # 默认 scope
            # 如果是 every_owned_planet 这类顶层循环，使用 country
            for stmt in obj.body.statements:
                if hasattr(stmt, 'key') and str(stmt.key).startswith('every_'):
                    scope_param = 'country'
                    break
            
            lines = generator.generate(obj.name, obj.body, scope_param)
            
            print("\n【生成的 Python 代码】")
            print('\n'.join(lines))
    except Exception as e:
        import traceback
        print(f"\n【处理失败】: {e}")
        traceback.print_exc()


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print(" " * 20 + "EFFECT 生成器测试套件")
    print("=" * 70)
    
    test_cases = [
        ("简单效果", SIMPLE_EFFECT, EXPECTED_SIMPLE),
        ("条件分支", CONDITIONAL_EFFECT, EXPECTED_CONDITIONAL),
        ("嵌套条件", NESTED_CONDITIONAL, None),
        ("循环遍历", LOOP_EFFECT, EXPECTED_LOOP),
        ("作用域切换", SCOPE_SWITCH, EXPECTED_SCOPE_SWITCH),
        ("变量算术", VARIABLE_ARITHMETIC, None),
        ("复杂嵌套", COMPLEX_EFFECT, EXPECTED_COMPLEX),
        ("事件触发", EVENT_EFFECT, None),
        ("脚本调用", SCRIPT_CALLS, None),
    ]
    
    for name, pdx_code, expected in test_cases:
        print_test_case(name, pdx_code, expected)
    
    print("\n" + "=" * 70)
    print("Effect 特性清单:")
    print("=" * 70)
    print("""
  ☐ 变量操作 (set_variable, add_variable, subtract_variable)
  ☐ 标记操作 (set_planet_flag, remove_planet_flag, has_planet_flag)
  ☐ 修正操作 (add_modifier, remove_modifier)
  ☐ 建筑操作 (add_building, remove_building)
  ☐ 资源操作 (add_resource)
  ☐ 条件分支 (if/else/else_if + limit)
  ☐ 循环遍历 (every_owned_planet, every_pop, etc.)
  ☐ 作用域切换 (owner, capital, overlord, etc.)
  ☐ 脚本调用 (scripted_effect = yes, inline_script)
  ☐ 事件触发 (fire_event)
  ☐ 消息发送 (send_message)
  ☐ 逻辑块 (NOT, AND, OR) 在 limit 中
  ☐ 变量检查 (check_variable) 在 limit 中
""")


if __name__ == '__main__':
    run_all_tests()
