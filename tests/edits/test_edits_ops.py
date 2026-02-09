from synthetipy.parser import parse
from synthetipy.script_merger.edits import generate_edit_script, roundtrip_apply_and_compare
from synthetipy.script_merger.utils import postorder, node_label


def test_minimal_ops_for_swap():
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

    b_content, b_buckets, b_unique, b_ub = compute_subtree_hashes(base_obj)
    m_content, m_buckets, m_unique, m_ub = compute_subtree_hashes(mod_obj)
    matches = match_trees(base_obj, mod_obj, b_content, b_buckets, m_content, m_buckets)
    ops = generate_edit_script(base_obj, mod_obj, matches, b_content, b_buckets, m_content, m_buckets, b_unique, m_unique)
    # Expect at least one move op and no replace ops
    has_move = any(getattr(op, 'op', None) == 'move' for op in ops)
    has_replace = any(getattr(op, 'op', None) == 'replace' for op in ops)
    assert has_move and not has_replace, f'Expected move(s) and no replace; got ops={ops}'


def test_roundtrip_after_lcs():
    BASE = r"""
b = {
	prop = { a = 1 }
}
"""
    MOD = r"""
b = {
	prop = { a = 2 }
}
"""
    base_doc = parse(BASE)
    mod_doc = parse(MOD)
    base_obj = next(n for n in postorder(base_doc) if node_label(n).startswith('Object:'))
    mod_obj = next(n for n in postorder(mod_doc) if node_label(n).startswith('Object:'))

    eq, ops = roundtrip_apply_and_compare(base_obj, mod_obj)
    assert eq, f'Roundtrip failed after LCS mathcing; ops={ops}'
