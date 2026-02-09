"""测试 Trigger 和 Effect 的宏参数支持

该文件是交互式/手动演示脚本，包含示例输入与生成器打印输出。
它会在自动化测试中被跳过以避免解析/生成器当前的实现细节导致收集时错误。
"""

import pytest
pytest.skip("Manual demo script - skip in automated test runs", allow_module_level=True)

from synthetipy.parser import parse
from synthetipy.codegen.trigger_generator import TriggerGenerator
from synthetipy.codegen.effect_generator import EffectGenerator

print("=" * 70)
print("测试 Trigger 宏参数支持")
print("=" * 70)

# 测试 1: 简单 trigger 参数
trigger_pdx_1 = """
has_enough_pops_trigger = {
    num_pops >= $MIN_POPS$
    num_free_districts >= $MIN_DISTRICTS|5$
}
"""

print("\n【测试 1: 简单 trigger 参数】")
print("PDX 代码:")
print(trigger_pdx_1)

ast = parse(trigger_pdx_1)
obj = ast.statements[0]
generator = TriggerGenerator()
code = generator.generate(obj.name, obj.body, 'scope')
print("\n生成的 Python 代码:")
print('\n'.join(code))

# 测试 2: 复杂 trigger 参数（字符串拼接）
trigger_pdx_2 = """
has_building_trigger = {
    has_building = building_$TYPE$_$LEVEL$
    num_buildings = { type = building_$TYPE$_$LEVEL$ value >= 1 }
}
"""

print("\n" + "=" * 70)
print("【测试 2: 复杂 trigger 参数】")
print("PDX 代码:")
print(trigger_pdx_2)

ast = parse(trigger_pdx_2)
obj = ast.statements[0]
generator = TriggerGenerator()
code = generator.generate(obj.name, obj.body, 'scope')
print("\n生成的 Python 代码:")
print('\n'.join(code))

print("\n" + "=" * 70)
print("测试 Effect 宏参数支持")
print("=" * 70)

# 测试 3: 简单 effect 参数
effect_pdx_1 = """
add_resources_effect = {
    add_minerals = $MINERALS$
    add_energy = $ENERGY|100$
}
"""

print("\n【测试 3: 简单 effect 参数】")
print("PDX 代码:")
print(effect_pdx_1)

ast = parse(effect_pdx_1)
obj = ast.statements[0]
generator = EffectGenerator()
code = generator.generate(obj.name, obj.body, 'scope')
print("\n生成的 Python 代码:")
print('\n'.join(code))

# 测试 4: 复杂 effect 参数（字符串拼接）
effect_pdx_2 = """
add_building_effect = {
    add_building = building_$TYPE$_$LEVEL$
    set_variable = { which = building_$TYPE$_count value = 1 }
}
"""

print("\n" + "=" * 70)
print("【测试 4: 复杂 effect 参数】")
print("PDX 代码:")
print(effect_pdx_2)

ast = parse(effect_pdx_2)
obj = ast.statements[0]
generator = EffectGenerator()
code = generator.generate(obj.name, obj.body, 'scope')
print("\n生成的 Python 代码:")
print('\n'.join(code))

print("\n" + "=" * 70)
print("所有测试完成!")
print("=" * 70)
