from synthetipy.codegen.generators.macro_generator import MacroGenerator
from synthetipy.codegen.trigger_generator import TriggerGenerator
from synthetipy.ast_nodes import LiteralNode, BlockNode, PropertyNode


def test_rhs_to_fstring_handles_multiple_macros():
    gen = TriggerGenerator()
    mg = MacroGenerator(gen)
    lit = LiteralNode('building_$TYPE$_$LEVEL$', 'string')
    template, params = mg.rhs_to_fstring(lit)
    assert '{TYPE}' in template and '{LEVEL}' in template
    assert 'TYPE' in params and 'LEVEL' in params


def test_format_macro_lhs_generates_meta_pdx_lines():
    gen = TriggerGenerator()
    mg = MacroGenerator(gen)
    # create a small block: { foo = bar }
    block = BlockNode([PropertyNode('foo', LiteralNode('bar', 'identifier'))])
    lines = mg.format_macro_lhs(None, block)
    assert any('meta.pdx' in l for l in lines)