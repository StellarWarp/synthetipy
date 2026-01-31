"""
测试 Parser 功能
"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy.parser import parse
from synthetipy.ast_nodes import *


def test_simple_object():
    """测试简单对象解析"""
    code = """
building_test = {
    category = research
    cost = 400
}
"""
    ast = parse(code)
    
    assert len(ast.statements) == 1
    obj = ast.statements[0]
    assert isinstance(obj, ObjectNode)
    assert obj.name == "building_test"
    
    # 检查属性
    assert len(obj.body.statements) == 2
    
    category = obj.body.get_property('category')
    assert category is not None
    assert isinstance(category.value, ValueNode)
    assert category.value.value == 'research'
    
    cost = obj.body.get_property('cost')
    assert cost is not None
    assert isinstance(cost.value, ValueNode)
    
    print("✅ 测试简单对象 - 通过")


def test_nested_block():
    """测试嵌套代码块"""
    code = """
building_test = {
    cost = {
        minerals = 400
        energy = 200
    }
}
"""
    ast = parse(code)
    
    obj = ast.statements[0]
    cost = obj.body.get_property('cost')
    
    assert isinstance(cost.value, BlockNode)
    assert len(cost.value.statements) == 2
    
    minerals = cost.value.get_property('minerals')
    assert minerals is not None
    assert minerals.value.value == 400
    
    print("✅ 测试嵌套代码块 - 通过")


def test_condition():
    """测试逻辑条件"""
    code = """
building_test = {
    destroy_trigger = {
        OR = {
            has_modifier = slave_colony
            owner = { is_ai = no }
        }
    }
}
"""
    ast = parse(code)
    
    obj = ast.statements[0]
    destroy_trigger = obj.body.get_property('destroy_trigger')
    
    assert isinstance(destroy_trigger.value, BlockNode)
    
    # 找到 OR 条件
    or_condition = None
    for stmt in destroy_trigger.value.statements:
        if isinstance(stmt, ConditionNode):
            or_condition = stmt
            break
    
    assert or_condition is not None
    assert or_condition.operator == 'OR'
    assert isinstance(or_condition.body, BlockNode)
    assert len(or_condition.body.statements) >= 2
    
    print("✅ 测试逻辑条件 - 通过")


def test_comparison():
    """测试比较表达式"""
    code = """
building_test = {
    destroy_trigger = {
        OR = {
            num_pops >= 50
            minerals > 1000
        }
    }
}
"""
    ast = parse(code)
    
    obj = ast.statements[0]
    destroy_trigger = obj.body.get_property('destroy_trigger')
    or_condition = destroy_trigger.value.statements[0]
    
    # 检查比较表达式
    comparisons = [s for s in or_condition.body.statements if isinstance(s, ComparisonNode)]
    assert len(comparisons) == 2
    
    comp1 = comparisons[0]
    assert comp1.left == 'num_pops'
    assert comp1.operator == '>='
    assert comp1.right.value == 50
    
    print("✅ 测试比较表达式 - 通过")


def test_complex_structure():
    """测试复杂结构"""
    code = """
building_research_lab_1 = {
    category = research
    cost = {
        minerals = 400
    }
    
    potential = {
        NOT = { has_modifier = slave_colony }
    }
    
    destroy_trigger = {
        OR = {
            owner = { is_ai = no }
            has_modifier = slave_colony
            num_pops >= 50
        }
    }
    
    produces = {
        physics_research = 10
        society_research = 10
    }
}
"""
    ast = parse(code)
    
    assert len(ast.statements) == 1
    obj = ast.statements[0]
    assert obj.name == "building_research_lab_1"
    
    # 验证所有主要属性存在
    assert obj.body.get_property('category') is not None
    assert obj.body.get_property('cost') is not None
    assert obj.body.get_property('potential') is not None
    assert obj.body.get_property('destroy_trigger') is not None
    assert obj.body.get_property('produces') is not None
    
    print("✅ 测试复杂结构 - 通过")


def test_multiple_objects():
    """测试多个对象"""
    code = """
building_lab_1 = {
    category = research
}

building_lab_2 = {
    category = research
}

building_lab_3 = {
    category = research
}
"""
    ast = parse(code)
    
    assert len(ast.statements) == 3
    
    for i, obj in enumerate(ast.statements):
        assert isinstance(obj, ObjectNode)
        assert obj.name == f"building_lab_{i+1}"
    
    print("✅ 测试多个对象 - 通过")


def test_list():
    """测试列表"""
    code = """
building_test = {
    tags = { tag1 tag2 tag3 }
    values = { 100 200 300 }
}
"""
    ast = parse(code)
    
    obj = ast.statements[0]
    
    tags = obj.body.get_property('tags')
    assert isinstance(tags.value, ListNode)
    assert len(tags.value.items) == 3
    
    values = obj.body.get_property('values')
    assert isinstance(values.value, ListNode)
    assert len(values.value.items) == 3
    
    print("✅ 测试列表 - 通过")


def test_variable_reference():
    """测试变量引用"""
    code = """
building_test = {
    base_buildtime = @b1_time
    cost = @standard_cost
}
"""
    ast = parse(code)
    
    obj = ast.statements[0]
    
    buildtime = obj.body.get_property('base_buildtime')
    assert isinstance(buildtime.value, ValueNode)
    assert buildtime.value.value_type == 'variable'
    assert buildtime.value.value == '@b1_time'
    
    print("✅ 测试变量引用 - 通过")


if __name__ == '__main__':
    print("=" * 60)
    print("运行 Parser 测试套件")
    print("=" * 60)
    print()
    
    test_simple_object()
    test_nested_block()
    test_condition()
    test_comparison()
    test_complex_structure()
    test_multiple_objects()
    test_list()
    test_variable_reference()
    
    print()
    print("=" * 60)
    print("🎉 所有测试通过！")
    print("=" * 60)
