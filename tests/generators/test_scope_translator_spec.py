from synthetipy.codegen.generators.scope_translator import ScopeTranslator
from synthetipy.codegen.trigger_generator import TriggerGenerator
from synthetipy.codegen.generators.expression_builder import ExpressionBuilder
from synthetipy.codegen.generators.control_flow import ControlFlowGenerator

from synthetipy.ast_nodes import LiteralNode, IdentifierNode


def test_dotted_string_and_exists():
    gen = TriggerGenerator()
    st = ScopeTranslator(gen)

    dotted = st.dotted('owner')
    assert dotted == "scope.owner"

    lit = LiteralNode('orbital_defence', 'identifier')
    exists = st.exists_expr(lit)
    assert "scope.exists('orbital_defence')" == exists


def test_enter_exit_scope_block_emits_with_and_pushes_context():
    gen = TriggerGenerator()
    st = ScopeTranslator(gen)

    # no lines before
    assert gen.lines == []
    scope_var = st.enter_scope_block('owner')

    # last added line should be with ... as <var>:
    assert any('with scope.owner as' in line for line in gen.lines)
    # context should have new current_scope_var
    assert gen.context.current_scope_var == scope_var

    # exit should restore
    st.exit_scope_block()
    assert gen.context.current_scope_var != scope_var
