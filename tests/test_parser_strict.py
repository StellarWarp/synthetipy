"""测试修改后的 parser"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse, ScriptedVariableNode, ObjectNode

# 测试 1: Scripted variables
print("=== 测试 1: Scripted Variables ===")
code1 = """
@buildings_t1 = 240
@b1_time = 360
@stabilitylevel2 = 40

building_lab = {
    buildtime = @b1_time
    cost = 400
}
"""

doc1 = parse(code1)
print(f"解析了 {len(doc1.statements)} 个语句")
for stmt in doc1.statements:
    if isinstance(stmt, ScriptedVariableNode):
        print(f"  ✅ ScriptedVariable: {stmt.name} = {stmt.value}")
    elif isinstance(stmt, ObjectNode):
        print(f"  ✅ Object: {stmt.name}")

# 测试 2: 严格模式 - 应该抛出异常
print("\n=== 测试 2: 严格模式（错误检测）===")
code2 = """
building_bad = {
    invalid_syntax_here
    cost = 400
}
"""

try:
    doc2 = parse(code2)
    print(f"❌ 应该抛出异常但没有！")
except Exception as e:
    print(f"✅ 正确捕获错误：{e}")

print("\n=== 所有测试完成 ===")
