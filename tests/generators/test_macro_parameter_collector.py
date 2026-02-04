from synthetipy.codegen.macro_parameter_utils import MacroParameterCollector
from synthetipy.ast_nodes_basic import BlockNode, PropertyNode, LiteralNode


def test_macro_left_collection_simple_block():
    # tech_$AREA$_1 = { cost = 100 }
    inner_block = BlockNode([PropertyNode('cost', LiteralNode(100))])
    prop = PropertyNode('tech_$AREA$_1', inner_block)
    block = BlockNode([prop])

    collector = MacroParameterCollector()
    params = collector.collect(block)

    # 全局参数包含 AREA
    assert 'AREA' in params

    # macro_lefts 包含该 PropertyNode
    assert prop in collector.macro_lefts
    macro = collector.macro_lefts[prop]

    # 局部 macro 参数也包含 AREA
    assert 'AREA' in macro.parameters

    # pdx 模板包含 key 与内部属性
    assert 'tech_$AREA$_1' in macro.pdx_template
    assert 'cost' in macro.pdx_template

    # meta_lines 为 meta.pdx(...) 调用（不含 return）
    assert macro.meta_lines
    assert macro.meta_lines[0].strip().startswith('meta.pdx(')
