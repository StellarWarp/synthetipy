from synthetipy.codegen.generators.scope_translator import ScopeTranslator
from synthetipy.codegen.trigger_generator import TriggerGenerator


def test_iteration_info_only_explicit():
    gen = TriggerGenerator()
    st = ScopeTranslator(gen)

    assert st.iteration_info('every_owned_planet') == ('planet', 'owned_planets')
    
    # Test is_iteration_scope with string keys
    assert st.is_iteration_scope('every_owned_planet') is True
    
    # prefix-only entry should not be accepted
    assert st.iteration_info('every_foo') is None
    assert st.is_iteration_scope('every_foo') is False
    
    # Test is_loop method
    assert st.is_iteration_scope('every_owned_planet') is True
    assert st.is_iteration_scope('every_foo') is False


def test_enter_exit_iteration_loop_emits_for_and_pushes_context():
    gen = TriggerGenerator()
    st = ScopeTranslator(gen)

    # ensure no lines yet
    assert gen.lines == []
    loop_var = st.enter_iteration_loop('every_owned_planet')
    assert any('for' in line and 'every_owned_planet' in line for line in gen.lines)
    assert gen.context.current_scope_var == loop_var
    st.exit_iteration_loop()
    assert gen.context.current_scope_var != loop_var
