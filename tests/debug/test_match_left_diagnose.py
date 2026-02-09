from synthetipy.parser import parse
from synthetipy.script_merger.gumtree_hash import compute_subtree_hashes
from synthetipy.script_merger.matcher import match_trees, match_by_hash
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


def test_diagnose_match_left():
    base_doc = parse(BASE)
    left_doc = parse(LEFT)
    base_obj = next(n for n in postorder(base_doc) if node_label(n).startswith('Object:'))
    left_obj = next(n for n in postorder(left_doc) if node_label(n).startswith('Object:'))

    base_content, base_buckets, base_unique, base_unique_to_nodes = compute_subtree_hashes(base_obj)
    left_content, left_buckets, left_unique, left_unique_to_nodes = compute_subtree_hashes(left_obj)

    def find_literal_for_prop(root, prop_key):
        for n in postorder(root):
            if node_label(n).startswith('Property:'+prop_key):
                for c in postorder(n):
                    if node_label(c).startswith('Literal:'):
                        return c
        return None

    base_lit = find_literal_for_prop(base_obj, 'second')
    left_lit = find_literal_for_prop(left_obj, 'second')

    print('\nBASE literal id:', node_id(base_lit), 'label:', node_label(base_lit))
    print('LEFT literal id:', node_id(left_lit), 'label:', node_label(left_lit))

    matches = match_trees(base_obj, left_obj, base_content, base_buckets, left_content, left_buckets, similarity_threshold=0.4)
    print('\nMatches (left->base):')
    for k,v in matches.items():
        print(' ', k, '->', v)

    hash_matches = match_by_hash(base_obj, left_obj, base_content, base_buckets, left_content, left_buckets)
    print('\nhash matches:', hash_matches)

    assert node_id(left_lit) in matches or node_id(left_lit) in hash_matches, 'Left literal was not matched to base literal by either method'