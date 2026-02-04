from synthetipy.codegen.formatters import Formatter
from synthetipy.ast_nodes_expression import MacroExpression, IdentifierExpressionNode, CallInfo
from synthetipy.ast_nodes_expression import ScopeNode, ScopeObjectNode
from synthetipy.ast_nodes import BlockNode, PropertyNode, LiteralNode
from synthetipy import parse

def test_identifier_to_value_call_simple():
    # owner.value:tech_cost|AREA|physics|
    scope = ScopeNode([ScopeObjectNode('owner')])
    call = CallInfo('value', 'tech_cost', [('AREA', 'physics')])
    node = IdentifierExpressionNode()
    node.scope = scope
    node.call_info = call

    out = Formatter.identifier_to_call(node, scope_var='scope')
    print("identifier_to_call output:", out)
    assert out == "tech_cost(scope.owner, AREA='physics')"


def test_package_macro_lhs_and_statement():
    # LHS macro: tech_$AREA$_1
    macro = MacroExpression('tech_$AREA$_1')
    id_node = IdentifierExpressionNode()
    id_node.macro_expression = macro

    lhs = Formatter.package_macro_lhs(id_node)
    assert lhs == 'tech_{AREA}_1'

    # RHS block
    inner = BlockNode([PropertyNode('TECH', LiteralNode(10))])
    prop = PropertyNode(id_node, inner)
    lines = Formatter.package_macro_statement_pdx(prop, scope_var='scope')
    print("package_macro_statement output lines:")
    for l in lines:
        print(l)
    # generate_pdx_block returns multiple lines (meta.pdx template)
    assert len(lines) == 5
    assert lines[0].strip().startswith('meta.pdx')
    assert 'tech_$AREA$_1 = {' in '\n'.join(lines[1:4])
    # body lines should be indented inside the triple-quoted block
    assert any(l.strip().startswith('TECH = 10') for l in lines)
    # one of the body lines must have leading indentation (pdx_inner_indent)
    assert any(l.startswith('    ') and 'TECH = 10' in l for l in lines)
    assert lines[-1].strip().startswith('"""')


def test_package_macro_value_macro():
    # RHS macro as value -> meta.pdx_macro(f"tech_{AREA}_1")
    macro = MacroExpression('tech_$AREA$_1')
    val_node = IdentifierExpressionNode()
    val_node.macro_expression = macro

    lines = Formatter.package_macro_value_macro(val_node)
    print('package_macro_value_macro output lines:')
    for l in lines:
        print(l)
    assert len(lines) == 1
    assert 'meta.pdx_macro' in lines[0]
    assert 'tech_{AREA}_1' in lines[0]
