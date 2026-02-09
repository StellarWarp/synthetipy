from synthetipy.parser import parse
from synthetipy.script_merger.edits import generate_edit_script
from synthetipy.script_merger.ops import Update, Replace, Move, Delete
from synthetipy.script_merger.utils import postorder, node_label, node_id


def test_update_and_replace_have_uids():
    base = next(n for n in postorder(parse('b = { a = { x = 1 } }')) if node_label(n).startswith('Object:'))
    mod_update = next(n for n in postorder(parse('b = { a = { x = 2 } }')) if node_label(n).startswith('Object:'))
    b_content, b_buckets, b_unique, b_ub = compute_subtree_hashes(base)
    m_content, m_buckets, m_unique, m_ub = compute_subtree_hashes(mod_update)
    matches = match_trees(base, mod_update, b_content, b_buckets, m_content, m_buckets)
    ops = generate_edit_script(base, mod_update, matches, b_content, b_buckets, m_content, m_buckets, b_unique, m_unique)
    assert any(isinstance(op, Update) and getattr(op, 'target_uid', None) is not None for op in ops), 'Expected Update with target_uid'

    mod_replace = next(n for n in postorder(parse('b = { a = { y = 1 } }')) if node_label(n).startswith('Object:'))
    b_content, b_buckets, b_unique, b_ub = compute_subtree_hashes(base)
    m2_content, m2_buckets, m2_unique, m2_ub = compute_subtree_hashes(mod_replace)
    matches2 = match_trees(base, mod_replace, b_content, b_buckets, m2_content, m2_buckets)
    ops2 = generate_edit_script(base, mod_replace, matches2, b_content, b_buckets, m2_content, m2_buckets, b_unique, m2_unique)
    # key changed: accept either Replace with target_uid, OR Delete+Insert with uids
    has_replace = any(isinstance(op, Replace) and getattr(op, 'target_uid', None) is not None for op in ops2)
    has_delete_insert = any(isinstance(op, Delete) and getattr(op, 'target_uid', None) is not None for op in ops2) and any(op.__class__.__name__ == 'Insert' and getattr(op, 'parent_uid', None) is not None for op in ops2)
    assert has_replace or has_delete_insert, 'Expected Replace with target_uid OR Delete+Insert with uids'


def test_move_contains_uids():
    base = next(n for n in postorder(parse('b = { prop1 = { } prop2 = { } }')) if node_label(n).startswith('Object:'))
    mod = next(n for n in postorder(parse('b = { prop2 = { } prop1 = { } }')) if node_label(n).startswith('Object:'))
    b_content, b_buckets, b_unique, b_ub = compute_subtree_hashes(base)
    m3_content, m3_buckets, m3_unique, m3_ub = compute_subtree_hashes(mod)
    matches3 = match_trees(base, mod, b_content, b_buckets, m3_content, m3_buckets)
    ops = generate_edit_script(base, mod, matches3, b_content, b_buckets, m3_content, m3_buckets, b_unique, m3_unique)
    moves = [op for op in ops if isinstance(op, Move)]
    assert moves, 'Expected Move ops'
    assert all(getattr(m, 'target_uid', None) is not None for m in moves), 'Each Move should include target_uid'
    assert all(getattr(m, 'parent_uid', None) is not None for m in moves), 'Each Move should include parent_uid'
