"""
测试 ValueGenerator 的宏参数处理
"""

import sys
sys.path.insert(0, 'C:/Users/Estelle/source/repos/pdxlang_patcher/src')

from synthetipy.parsing.lexer import Lexer
from synthetipy import Parser
from synthetipy.codegen.value_generator import ValueGenerator


def parse_pdx(code: str):
    """辅助函数：解析 PDX 代码"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()


def test_simple_params():
    """测试简单宏参数"""
    pdx_code = """
bca_test_simple = {
    base = 0
    add = $BASE_AMOUNT$
    multiply = $MULTIPLIER$
}
"""
    
    ast = parse_pdx(pdx_code)
    
    obj = ast.statements[0]
    generator = ValueGenerator()
    code = generator.generate(obj.name, obj.body)
    
    print("=" * 60)
    print("测试 1: 简单宏参数")
    print("=" * 60)
    print("【PDX 代码】")
    print(pdx_code)
    print("【生成的 Python 代码】")
    print('\n'.join(code))
    print()


def test_param_forwarding():
    """测试参数转发（无拼接）"""
    pdx_code = """
bca_energy_estimate = {
    base = 0
    multiply = value:bca_planet_energy_job_mult|num_district_city|$NUM_C_DST$|
    add = value:bca_planet_energy_job_add|num_resource|$NUM_R_DST$|
}
"""
    
    ast = parse_pdx(pdx_code)
    
    obj = ast.statements[0]
    generator = ValueGenerator()
    code = generator.generate(obj.name, obj.body)
    
    # 调试信息
    print("=" * 60)
    print("测试 2: 参数转发（简单）")
    print("=" * 60)
    print(f"【参数收集】")
    for name, param in generator.parameters.items():
        print(f"  {name}: type={param.inferred_type}, usages={param.usages}")
    print()
    print("【PDX 代码】")
    print(pdx_code)
    print("【生成的 Python 代码】")
    print('\n'.join(code))
    print()


def test_complex_concat():
    """测试复杂字符串拼接"""
    pdx_code = """
bca_building_value = {
    base = 0
    complex_trigger_modifier = {
        trigger = num_buildings
        parameters = { type = building_$TYPE$_$LEVEL$ }
        mode = add
    }
    multiply = value:building_$TYPE$_base_output
}
"""
    
    ast = parse_pdx(pdx_code)
    
    obj = ast.statements[0]
    generator = ValueGenerator()
    code = generator.generate(obj.name, obj.body)
    
    print("=" * 60)
    print("测试 3: 复杂拼接（meta.pdx）")
    print("=" * 60)
    print("【PDX 代码】")
    print(pdx_code)
    print("【生成的 Python 代码】")
    print('\n'.join(code))
    print()


def test_mixed_params():
    """测试混合参数（简单+复杂）"""
    pdx_code = """
bca_mixed_calculation = {
    base = $BASE$
    add = 100
    complex_trigger_modifier = {
        trigger = count_pops
        parameters = { type = pop_$POP_TYPE$ }
        mode = add
    }
}
"""
    
    ast = parse_pdx(pdx_code)
    
    obj = ast.statements[0]
    generator = ValueGenerator()
    code = generator.generate(obj.name, obj.body)
    
    # 调试信息
    print("=" * 60)
    print("测试 4: 混合参数")
    print("=" * 60)
    print(f"【参数收集】")
    for name, param in generator.parameters.items():
        print(f"  {name}: type={param.inferred_type}, usages={param.usages}")
    print()
    print("【PDX 代码】")
    print(pdx_code)
    print("【生成的 Python 代码】")
    print('\n'.join(code))
    print()


if __name__ == '__main__':
    test_simple_params()
    test_param_forwarding()
    test_complex_concat()
    test_mixed_params()
    
    print("=" * 60)
    print("所有测试完成!")
    print("=" * 60)
