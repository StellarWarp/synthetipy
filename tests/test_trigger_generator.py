"""
测试 Trigger 生成器

测试将 PDX trigger 块转换为 Python 布尔表达式的功能
"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy.parsing.lexer import Lexer
from synthetipy import Parser
from synthetipy.codegen.trigger_generator import TriggerGenerator

MAX_LINES = 8  # 最多打印的代码行数


def print_lines(lines: list[str], max_lines: int = MAX_LINES):
    """打印代码行，限制最大行数"""
    for i, line in enumerate(lines[:max_lines]):
        print(line)
    if len(lines) > max_lines:
        print(f"    ... (省略 {len(lines) - max_lines} 行，共 {len(lines)} 行)")


def parse_pdx_trigger(pdx_code: str):
    """解析 PDX 代码并返回 AST"""
    lexer = Lexer(pdx_code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()


def test_simple_trigger():
    """测试简单的 trigger"""
    print("\n" + "=" * 60)
    print("测试 1: 简单 Trigger")
    print("=" * 60)
    
    pdx_code = """
can_build = {
    is_ai = yes
    num_pops >= 10
}
"""
    
    print("PDX 代码:")
    print(pdx_code)
    
    ast = parse_pdx_trigger(pdx_code)
    
    if ast.statements:
        obj = ast.statements[0]
        generator = TriggerGenerator()
        lines = generator.generate("can_build", obj.body, "planet")
        
        print("\n生成的 Python 代码:")
        print_lines(lines)


def test_logic_blocks():
    """测试逻辑块 (AND/OR/NOT)"""
    print("\n" + "=" * 60)
    print("测试 2: 逻辑块")
    print("=" * 60)
    
    pdx_code = """
is_valid = {
    OR = {
        is_ai = yes
        has_technology = tech_advanced
    }
    NOT = {
        has_modifier = primitive
    }
}
"""
    
    print("PDX 代码:")
    print(pdx_code)
    
    ast = parse_pdx_trigger(pdx_code)
    
    if ast.statements:
        obj = ast.statements[0]
        generator = TriggerGenerator()
        lines = generator.generate("is_valid", obj.body, "country")
        
        print("\n生成的 Python 代码:")
        print_lines(lines)


def test_control_flow():
    """测试控制流 (if/else)"""
    print("\n" + "=" * 60)
    print("测试 3: 控制流 (if/else)")
    print("=" * 60)
    
    pdx_code = """
check_colony_type = {
    if = {
        limit = {
            num_pops >= 100
        }
        has_building = building_capital
    }
    else = {
        num_districts >= 10
    }
}
"""
    
    print("PDX 代码:")
    print(pdx_code)
    
    ast = parse_pdx_trigger(pdx_code)
    
    if ast.statements:
        obj = ast.statements[0]
        generator = TriggerGenerator()
        lines = generator.generate("check_colony_type", obj.body, "planet")
        
        print("\n生成的 Python 代码:")
        print_lines(lines)


def test_special_calls():
    """测试特殊调用 (check_variable_arithmetic)"""
    print("\n" + "=" * 60)
    print("测试 4: 特殊调用")
    print("=" * 60)
    
    pdx_code = """
has_enough_resources = {
    check_variable_arithmetic = {
        which = value:calculate_resources
        add = 100
        value >= 1000
    }
}
"""
    
    print("PDX 代码:")
    print(pdx_code)
    
    ast = parse_pdx_trigger(pdx_code)
    
    if ast.statements:
        obj = ast.statements[0]
        generator = TriggerGenerator()
        lines = generator.generate("has_enough_resources", obj.body, "country")
        
        print("\n生成的 Python 代码:")
        print_lines(lines)


def test_method_calls():
    """测试方法调用"""
    print("\n" + "=" * 60)
    print("测试 5: 方法调用")
    print("=" * 60)
    
    pdx_code = """
has_free_jobs = {
    free_jobs_of_type = {
        category = ruler
        value > 0
    }
}
"""
    
    print("PDX 代码:")
    print(pdx_code)
    
    ast = parse_pdx_trigger(pdx_code)
    
    if ast.statements:
        obj = ast.statements[0]
        generator = TriggerGenerator()
        lines = generator.generate("has_free_jobs", obj.body, "planet")
        
        print("\n生成的 Python 代码:")
        print_lines(lines)


def test_complex_nested_trigger():
    """测试复杂的嵌套 trigger (用户提供的示例)"""
    print("\n" + "=" * 60)
    print("测试 6: 复杂嵌套 Trigger (真实案例)")
    print("=" * 60)
    
    pdx_code = """
auto_resettle_planet_has_free_jobs = {
	if = {
		limit = {
			owner = {
				is_gestalt = no
			}
		}
		OR = {
			free_jobs_of_type = {
				category = ruler
				value > 0
			}
			# For tooltip.
			if = {
				limit = {
					free_jobs_of_type = {
						category = specialist
						value > 0
					}
				}
				free_jobs_of_type = {
					category = specialist
					value > 0
				}
			}
			else = {
				free_jobs_of_type = {
					category = dystopian_specialist
					value > 0
				}
			}
			free_jobs_of_type = {
				category = worker
				value > 0
			}
		}
		custom_tooltip = {
			text = auto_resettle_has_free_jobs_100_regular
			check_variable_arithmetic = {
				which = value:auto_resettle_count_available_jobs_regular
				value >= 100
			}
		}
	}
	else = {
		OR = {
			AND = {
				OR = {
					free_jobs_of_type = {
						category = complex_drone
						value > 0
					}
					free_jobs_of_type = {
						category = simple_drone
						value > 0
					}
				}
				custom_tooltip = {
					text = auto_resettle_has_free_jobs_100_gestalt_drone
					check_variable_arithmetic = {
						which = value:auto_resettle_count_available_jobs_gestalt_drone
						value >= 100
					}
				}
			}
			free_jobs_of_type = {
				category = bio_trophy
				value >= 100
			}
		}
	}
}
"""
    
    print("PDX 代码:")
    print(pdx_code)
    
    try:
        ast = parse_pdx_trigger(pdx_code)
        
        if ast.statements:
            obj = ast.statements[0]
            generator = TriggerGenerator()
            lines = generator.generate("auto_resettle_planet_has_free_jobs", obj.body, "planet")
            
            print("\n生成的 Python 代码:")
            print("-" * 60)
            print_lines(lines, 10000)
            print("-" * 60)
            
            # 验证生成的代码是否包含关键结构
            code_text = '\n'.join(lines)
            
            print("\n验证生成的代码结构:")
            checks = [
                ("包含函数定义", "def auto_resettle_planet_has_free_jobs" in code_text),
                ("包含 if 语句", "if " in code_text),
                ("包含 else 语句", "else:" in code_text),
                ("包含 OR 逻辑", "logic.OR" in code_text or " or " in code_text),
                ("包含 AND 逻辑", "logic.AND" in code_text or " and " in code_text),
                ("包含方法调用", "free_jobs_of_type" in code_text),
                ("包含函数调用", "auto_resettle_count_available_jobs" in code_text),
                ("包含作用域访问", "planet.owner" in code_text),
                ("包含 not 操作", "not " in code_text),
            ]
            
            for check_name, result in checks:
                status = "✓" if result else "✗"
                print(f"  {status} {check_name}")
            
            # 统计代码行数
            code_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
            print(f"\n生成代码行数: {len(code_lines)}")
            print(f"缩进层级: {max(len(line) - len(line.lstrip()) for line in lines if line.strip()) // 4}")
            
    except Exception as e:
        print(f"\n❌ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def test_scope_nesting():
    """测试作用域嵌套"""
    print("\n" + "=" * 60)
    print("测试 7: 作用域嵌套")
    print("=" * 60)
    
    pdx_code = """
is_capital_valid = {
    owner = {
        is_regular_empire = yes
        capital = {
            num_pops >= 50
        }
    }
}
"""
    
    print("PDX 代码:")
    print(pdx_code)
    
    ast = parse_pdx_trigger(pdx_code)
    
    if ast.statements:
        obj = ast.statements[0]
        generator = TriggerGenerator()
        lines = generator.generate("is_capital_valid", obj.body, "planet")
        
        print("\n生成的 Python 代码:")
        print_lines(lines)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print(" " * 20 + "TRIGGER 生成器测试套件")
    print("=" * 70)
    
    tests = [
        # test_simple_trigger,
        # test_logic_blocks,
        # test_control_flow,
        # test_special_calls,
        # test_method_calls,
        # test_scope_nesting,
        test_complex_nested_trigger,  # 最复杂的放在最后
    ]
    
    for i, test_func in enumerate(tests, 1):
        try:
            test_func()
            print(f"\n✓ 测试 {i} 完成")
        except Exception as e:
            print(f"\n✗ 测试 {i} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)


if __name__ == '__main__':
    run_all_tests()
