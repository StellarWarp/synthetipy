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
RIGHT = r'''
b = {
    first = { }
    second = { v = 2 }
}
'''


def test_diagnose_match_for_inner_literal():
    base_doc = parse(BASE)
    right_doc = parse(RIGHT)
    base_obj = next(n for n in postorder(base_doc) if node_label(n).startswith('Object:'))
    right_obj = next(n for n in postorder(right_doc) if node_label(n).startswith('Object:'))

    base_content, base_buckets, base_unique, base_unique_to_nodes = compute_subtree_hashes(base_obj)
    right_content, right_buckets, right_unique, right_unique_to_nodes = compute_subtree_hashes(right_obj)

    # find the literal nodes for second.v
    def find_literal_for_prop(root, prop_key):
        for n in postorder(root):
            if node_label(n).startswith('Property:'+prop_key):
                # find literal child
                for c in postorder(n):
                    if node_label(c).startswith('Literal:'):
                        return c
        return None

    base_lit = find_literal_for_prop(base_obj, 'second')
    right_lit = find_literal_for_prop(right_obj, 'second')

    print('\nBASE literal id:', node_id(base_lit), 'label:', node_label(base_lit))
    print('RIGHT literal id:', node_id(right_lit), 'label:', node_label(right_lit))

    print('\nbase_content for literal:', base_content.get(node_id(base_lit)))
    print('right_content for literal:', right_content.get(node_id(right_lit)))

    print('\nbase_buckets contains hash -> nodes:')
    for h, nodes in base_buckets.items():
        if node_id(base_lit) in nodes:
            print(' base hash', h, '->', nodes)

    # run matches
    matches = match_trees(base_obj, right_obj, base_content, base_buckets, right_content, right_buckets, similarity_threshold=0.4)
    print('\nMatches (other->base):')
    for k, v in matches.items():
        print(' ', k, '->', v)

    # check whether right literal was matched to base literal
    matched_base_for_right_lit = matches.get(node_id(right_lit))
    print('\nright_lit matched to base id:', matched_base_for_right_lit)

    # also try hash-based match_by_hash
    hash_matches = match_by_hash(base_obj, right_obj, base_content, base_buckets, right_content, right_buckets)
    print('\nhash matches (other->base):', hash_matches)

    assert node_id(right_lit) in matches or node_id(right_lit) in hash_matches, 'Right literal was not matched to base literal by either method'