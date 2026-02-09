from synthetipy.parser import parse
from synthetipy.script_merger.gumtree_hash import compute_subtree_hashes
from synthetipy.script_merger.matcher import match_trees
from synthetipy.script_merger.edits import generate_edit_script
from synthetipy.script_merger.utils import postorder, node_label, node_id

BASE = r'''
b = {
    first = { }
    second = { v = 1 }
}
'''
LEFT = r'''
b = {
    second = { v = 1 }
    first = { }
}
'''


def test_print_replace_annotations():
    base_doc = parse(BASE)
    left_doc = parse(LEFT)
    base = next(n for n in postorder(base_doc) if node_label(n).startswith('Object:'))
    left = next(n for n in postorder(left_doc) if node_label(n).startswith('Object:'))

    base_content, base_buckets, base_unique, base_unique_to_nodes = compute_subtree_hashes(base)
    left_content, left_buckets, left_unique, left_unique_to_nodes = compute_subtree_hashes(left)

    matches = match_trees(base, left, base_content, base_buckets, left_content, left_buckets)
    ops = generate_edit_script(base, left, matches, base_content, base_buckets, left_content, left_buckets, base_unique, left_unique)

    print('\n--- Replace ops and their node annotations ---')
    for op in ops:
        if op.__class__.__name__ == 'Replace':
            print('Replace target_uid:', op.target_uid)
            for n in postorder(op.node):
                print(' ', node_label(n), 'base_uid:', getattr(n, '_base_uid', None))
    assert True
