"""
测试 Value 生成器
"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse
from synthetipy.codegen.value_generator import ValueGenerator


def test_simple_value():
    """测试简单 value"""
    print("=" * 60)
    print("测试 1: 简单 value (base + multiply)")
    print("=" * 60)
    
    pdx_code = """
bca_production_inc_mult_from_urban_resource = {
    base = 0.2
    multiply = value:bca_resource_designation_num_city_districts
}
"""
    print("【PDX 代码】")
    print(pdx_code)
    
    ast = parse(pdx_code)
    gen = ValueGenerator()
    
    # 获取第一个对象的 body
    obj = ast.statements[0]
    lines = gen.generate(obj.name, obj.body)
    
    print("【生成的 Python 代码】")
    print('\n'.join(lines))
    print()


def test_complex_trigger_modifier():
    """测试 complex_trigger_modifier"""
    print("=" * 60)
    print("测试 2: complex_trigger_modifier")
    print("=" * 60)
    
    pdx_code = """
bca_resource_designation_num_city_districts = {
    complex_trigger_modifier = {
        trigger = num_districts
        parameters = {
            type = district_city
        }
        mode = add
    }
    complex_trigger_modifier = {
        trigger = num_districts
        parameters = {
            type = district_hive
        }
        mode = add
    }
}
"""
    print("【PDX 代码】")
    print(pdx_code)
    
    ast = parse(pdx_code)
    gen = ValueGenerator()
    
    obj = ast.statements[0]
    lines = gen.generate(obj.name, obj.body)
    
    print("【生成的 Python 代码】")
    print('\n'.join(lines))
    print()


def test_modifier_with_conditions():
    """测试带条件的 modifier"""
    print("=" * 60)
    print("测试 3: modifier 带条件")
    print("=" * 60)
    
    pdx_code = """
bca_planet_energy_job_add_estimate = {
    set = value:bca_planet_energy_job_add
    modifier = {
        add = 2
        NOT = {has_building = building_energy_nexus}
    }
}
"""
    print("【PDX 代码】")
    print(pdx_code)
    
    ast = parse(pdx_code)
    gen = ValueGenerator()
    
    obj = ast.statements[0]
    lines = gen.generate(obj.name, obj.body)
    
    print("【生成的 Python 代码】")
    print('\n'.join(lines))
    print()


def test_value_with_params():
    """测试带参数的 value 引用"""
    print("=" * 60)
    print("测试 4: 带参数的 value 引用")
    print("=" * 60)
    
    pdx_code = """
bca_potential_standard_energy_production_estimate = {
    set = $NUM_R_DST$
    multiply = 300
    divide = 100
    mult = value:bca_planet_energy_job_add_estimate
    mult = value:bca_planet_energy_job_mult_estimate|num_district_city|$NUM_C_DST$|
}
"""
    print("【PDX 代码】")
    print(pdx_code)
    
    ast = parse(pdx_code)
    gen = ValueGenerator()
    
    obj = ast.statements[0]
    lines = gen.generate(obj.name, obj.body)
    
    print("【生成的 Python 代码】")
    print('\n'.join(lines))
    print()


def test_complex_value():
    """测试复杂 value"""
    print("=" * 60)
    print("测试 5: 复杂 value (多个 modifier)")
    print("=" * 60)
    
    pdx_code = """
bca_potential_energy_district_max_inc = {
    modifier = {
        has_building = building_generator_districts_1
        subtract = @b1_max_districts_add
    }
    modifier = {
        has_building = building_generator_districts_2
        subtract = @b2_max_districts_add
    }
    modifier = {
        has_building = building_generator_districts_3
        subtract = @b3_max_districts_add
    }
    add = @b4_max_districts_add
}
"""
    print("【PDX 代码】")
    print(pdx_code)
    
    ast = parse(pdx_code)
    gen = ValueGenerator()
    
    obj = ast.statements[0]
    lines = gen.generate(obj.name, obj.body)
    
    print("【生成的 Python 代码】")
    print('\n'.join(lines))
    print()


def test_modifier_reference():
    """测试 modifier: 引用"""
    print("=" * 60)
    print("测试 6: modifier: 引用")
    print("=" * 60)
    
    pdx_code = """
bca_potential_district_generator_max_add = {
    add = modifier:district_generator_max_add
    add = value:bca_potential_energy_district_max_inc
}
"""
    print("【PDX 代码】")
    print(pdx_code)
    
    ast = parse(pdx_code)
    gen = ValueGenerator()
    
    obj = ast.statements[0]
    lines = gen.generate(obj.name, obj.body)
    
    print("【生成的 Python 代码】")
    print('\n'.join(lines))
    print()


if __name__ == '__main__':
    test_simple_value()
    test_complex_trigger_modifier()
    test_modifier_with_conditions()
    test_value_with_params()
    test_complex_value()
    test_modifier_reference()
    
    print("=" * 60)
    print("所有测试完成!")
    print("=" * 60)
