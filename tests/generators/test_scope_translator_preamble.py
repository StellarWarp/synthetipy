from synthetipy.codegen.generators.scope_translator import ScopeTranslator
from synthetipy.codegen.trigger_generator import TriggerGenerator
from synthetipy.ast_nodes import ScopeNode, ScopeObjectNode, IdentifierNode, LiteralNode


def test_is_scope_lhs_true_for_scope_node():
    gen = TriggerGenerator()
    st = ScopeTranslator(gen)

    # Build a fake IdentifierExpressionNode-like with scope
    class FakeId:
        def __init__(self):
            self.is_macro_expression = False
            self.call_info = None
            self.scope = ScopeNode([ScopeObjectNode('orbital_defence')])
    node = FakeId()
    assert st.is_scope_lhs(node)


def test_prepare_scope_preamble_hoists_root():
    gen = TriggerGenerator()
    st = ScopeTranslator(gen)
    class FakeId:
        def __init__(self):
            self.scope = ScopeNode([ScopeObjectNode('orbital_defence')])
    node = FakeId()
    pre_lines, mapping = st.prepare_scope_preamble(node)
    assert any('orbital_defence' in l for l in pre_lines)
    assert 'orbital_defence' in mapping


def test_format_macro_rhs_fstring_extracts_params():
    gen = TriggerGenerator()
    st = ScopeTranslator(gen)
    lit = LiteralNode('building_$TYPE$_$LEVEL$', 'string')
    from synthetipy.codegen.generators.macro_generator import MacroGenerator
    mg = MacroGenerator(gen)
    template, params = mg.rhs_to_fstring(lit)
    assert '{TYPE}' in template and '{LEVEL}' in template
    assert 'TYPE' in params and 'LEVEL' in params
