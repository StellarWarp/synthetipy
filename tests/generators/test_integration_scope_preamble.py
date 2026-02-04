

from synthetipy import parse
from synthetipy.codegen.trigger_generator import TriggerGenerator
from synthetipy.codegen.effect_generator import EffectGenerator
import traceback


def test_if_block_generates_starbase_hoist():
    pdx = '''
allow = {
    has_upgraded_capital = yes
    if = {
        limit = {
            exists = orbital_defence
        }
        orbital_defence = {
            exists = starbase
            starbase = {
                NOR = {
                    has_starbase_building = ring_noble_estates
                    is_starbase_building_building = ring_noble_estates
                }
            }
        }
    }
}
'''
    ast = parse(pdx)
    obj = ast.statements[0]
    gen = TriggerGenerator()
    lines = gen.generate(obj.name, obj.body)
    code = '\n'.join(lines)
    assert 'orbital_defence' in code
    assert 'starbase' in code
    assert '_result_' not in code


def test_hidden_trigger_generates_body():
    pdx = '''
is_unemployed = {
    hidden_trigger = {
        OR = {
            is_pop_category = ruler_unemployment
            is_pop_category = specialist_unemployment
            is_pop_category = worker_unemployment
        }
    }
}
'''
    ast = parse(pdx)
    obj = ast.statements[0]
    gen = TriggerGenerator()
    lines = gen.generate(obj.name, obj.body)
    code = '\n'.join(lines)
    assert 'is_pop_category' in code
    assert 'ruler_unemployment' in code
    assert '_result_' not in code


def test_hidden_effect_generates_body():
    pdx = '''
set_first_contact = {
    custom_tooltip = start_first_contact
    hidden_effect = {
        owner = {
            set_timed_country_flag = {
                flag = recent_first_contact
                years = 20
            }
        }
    }
}
'''
    ast = parse(pdx)
    obj = ast.statements[0]
    gen = EffectGenerator()
    lines = gen.generate(obj.name, obj.body)
    code = '\n'.join(lines)
    assert 'set_timed_country_flag' in code
    assert 'recent_first_contact' in code
    assert '_result_' not in code


if __name__ == '__main__':
    tests = [
        test_if_block_generates_starbase_hoist,
        test_hidden_trigger_generates_body,
        test_hidden_effect_generates_body,
    ]
    for t in tests:
        t()
