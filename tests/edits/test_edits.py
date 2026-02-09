from synthetipy.parser import parse
from synthetipy.script_merger.edits import generate_edit_script, apply_edit_script, roundtrip_apply_and_compare
from synthetipy.script_merger.utils import postorder, node_label, node_id, structural_equal


def test_update_property_value():
    BASE = r"""
b = {
	prop = { x = 0 }
}
"""
    MOD = r"""
b = {
	prop = { x = 1 }
}
"""
    base_doc = parse(BASE)
    mod_doc = parse(MOD)
    base_obj = next(n for n in postorder(base_doc) if node_label(n).startswith('Object:'))
    mod_obj = next(n for n in postorder(mod_doc) if node_label(n).startswith('Object:'))

    eq, ops = roundtrip_apply_and_compare(base_obj, mod_obj)
    assert eq, f'Roundtrip failed, ops: {ops}'


def test_insert_and_delete_property():
    BASE = r"""
b = {
	prop = { a = 1 }
}
"""
    MOD = r"""
b = {
	prop = { a = 1 b = 2 }
}
"""
    base_doc = parse(BASE)
    mod_doc = parse(MOD)
    base_obj = next(n for n in postorder(base_doc) if node_label(n).startswith('Object:'))
    mod_obj = next(n for n in postorder(mod_doc) if node_label(n).startswith('Object:'))

    eq, ops = roundtrip_apply_and_compare(base_obj, mod_obj)
    assert eq, f'Roundtrip failed, ops: {ops}'


def test_move_child_order():
    BASE = r"""
b = {
	prop1 = { }
	prop2 = { }
}
"""
    MOD = r"""
b = {
	prop2 = { }
	prop1 = { }
}
"""
    base_doc = parse(BASE)
    mod_doc = parse(MOD)
    base_obj = next(n for n in postorder(base_doc) if node_label(n).startswith('Object:'))
    mod_obj = next(n for n in postorder(mod_doc) if node_label(n).startswith('Object:'))

    eq, ops = roundtrip_apply_and_compare(base_obj, mod_obj)
    assert eq, f'Roundtrip failed, ops: {ops}'
