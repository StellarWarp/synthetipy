from synthetipy.script_merger.edits import roundtrip_apply_and_compare, generate_edit_script
from synthetipy.script_merger.gumtree_hash import compute_subtree_hashes
from synthetipy.script_merger.matcher import match_trees
from synthetipy.script_merger.utils import postorder, node_label, node_id
from synthetipy.parser import parse

BASE = """
b = {
    first = { }
    second = { v = 1 }
}
"""
LEFT = """
b = {
    second = { v = 1 }
    first = { }
}
"""
RIGHT = """
b = {
    first = { }
    second = { v = 2 }
}
"""


def test_print_ops_for_failing_case():
    base = parse(BASE)
    left = parse(LEFT)
    right = parse(RIGHT)

    # precompute
    base_obj = next(n for n in postorder(base) if n.__class__.__name__.startswith('Object'))
    right_obj = next(n for n in postorder(right) if n.__class__.__name__.startswith('Object'))

    base_content, base_buckets, base_unique, base_unique_to_nodes = compute_subtree_hashes(base_obj)
    right_content, right_buckets, right_unique, right_unique_to_nodes = compute_subtree_hashes(right_obj)

    matches = match_trees(base_obj, right_obj, base_content, base_buckets, right_content, right_buckets)

    theirs_ops = generate_edit_script(base_obj, right_obj, matches, base_content, base_buckets, right_content, right_buckets, base_unique, right_unique)

    # also compute ours ops (base->left)
    left_obj = next(n for n in postorder(left) if n.__class__.__name__.startswith('Object'))
    base_content2, base_buckets2, base_unique2, base_unique_to_nodes2 = compute_subtree_hashes(base_obj)
    left_content, left_buckets, left_unique, left_unique_to_nodes = compute_subtree_hashes(left_obj)
    ours_matches = match_trees(base_obj, left_obj, base_content2, base_buckets2, left_content, left_buckets)
    ours_ops = generate_edit_script(base_obj, left_obj, ours_matches, base_content2, base_buckets2, left_content, left_buckets, base_unique2, left_unique)

    print('\nOurs matches (other->base):')
    for k,v in ours_matches.items():
        print(' ', k, '->', v)

    print('\nOurs ops:')
    for op in ours_ops:
        print(' ', type(op).__name__, op)
        if hasattr(op, 'node'):
            from synthetipy.script_merger.utils import postorder as _post, node_label
            print('  subtree annotations:')
            for n in _post(op.node):
                print('   ', node_label(n), 'base_uid:', getattr(n, '_base_uid', None))
        # print label of target id if available
        from synthetipy.script_merger.utils import node_id, node_label
        try:
            print('  target label in base (if exists):', node_label(next(n for n in postorder(base_obj) if node_id(n) == op.target)))
        except Exception:
            pass

    # find literal nodes for second.v in base/left/right
    def find_literal_for_prop(root, prop_key):
        for n in postorder(root):
            if node_label(n).startswith('Property:'+prop_key):
                for c in postorder(n):
                    if node_label(c).startswith('Literal:'):
                        return c
        return None

    base_lit = find_literal_for_prop(base_obj, 'second')
    left_lit = find_literal_for_prop(left_obj, 'second')
    right_lit = find_literal_for_prop(right_obj, 'second')

    from synthetipy.script_merger.utils import node_id
    print('\nbase literal id:', node_id(base_lit), 'label:', node_label(base_lit))
    print('left literal id:', node_id(left_lit), 'label:', node_label(left_lit))
    print('right literal id:', node_id(right_lit), 'label:', node_label(right_lit))

    print('\nDoes ours_matches include left literal?', node_id(left_lit) in ours_matches)
    print('Does theirs_matches include right literal?', node_id(right_lit) in matches)

    print('\nTheirs ops:')
    for op in theirs_ops:
        print(' ', type(op).__name__, op)
        # if Insert/Replace show subtree annotations
        from synthetipy.script_merger.utils import postorder as _post, node_id, node_label
        if hasattr(op, 'node'):
            print('  subtree annotations:')
            for n in _post(op.node):
                print('   ', node_label(n), 'base_uid:', getattr(n, '_base_uid', None))

    # also run roundtrip to show apply results
    eq, ops2 = roundtrip_apply_and_compare(base_obj, right_obj)
    print('\nRoundtrip equal?', eq)
    for op in ops2:
        print(' ', type(op).__name__, op)