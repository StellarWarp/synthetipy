from synthetipy.parser import parse
from synthetipy.script_merger.matcher import match_trees
from synthetipy.script_merger.gumtree_hash import compute_subtree_hashes
from synthetipy.script_merger.utils import postorder, node_label, node_id

# A slightly more complex base and modified variant to exercise matching and moves
BASE = r'''
building_x = {
	capital = yes
	position_priority = 0
	planet_modifier = { planet_housing_add = 300 planet_amenities_add = 300 }
	inline_script = { script = shroud/jobs/colonist_add AMOUNT = 200 }
	triggered_planet_modifier = { potential = { exists = owner } job_colonist_add = -100 }
}
'''

MOD = r'''
building_x = {
	capital = yes
	position_priority = 1  # changed
	planet_modifier = { planet_housing_add = 350 planet_amenities_add = 300 }
	# inline_script moved below triggered modifier
	triggered_planet_modifier = { potential = { exists = owner } job_colonist_add = -100 }
	inline_script = { script = shroud/jobs/colonist_add AMOUNT = 200 }
	new_property = yes
}
'''


def test_print_base_node_matches_debug():
    base_doc = parse(BASE)
    mod_doc = parse(MOD)

    base_obj = next(n for n in postorder(base_doc) if node_label(n).startswith('Object:'))
    mod_obj = next(n for n in postorder(mod_doc) if node_label(n).startswith('Object:'))

    base_content, base_buckets, base_unique, base_ub = compute_subtree_hashes(base_obj)
    mod_content, mod_buckets, mod_unique, mod_ub = compute_subtree_hashes(mod_obj)

    matches = match_trees(base_obj, mod_obj, base_content, base_buckets, mod_content, mod_buckets, similarity_threshold=0.4)

    # invert mapping to base_id -> other_id for easy lookup
    inv_matches = {v: k for k, v in matches.items()}

    # build id->node maps for printing
    def id_map(root):
        m = {}
        for n in postorder(root):
            m[node_id(n)] = n
        return m

    base_map = id_map(base_obj)
    mod_map = id_map(mod_obj)

    print('\n=== MATCHING REPORT (base -> mod) ===')
    matched_count = 0
    for n in postorder(base_obj):
        nid = node_id(n)
        label = node_label(n)
        content_h = base_content.get(nid, '<no>')
        unique_h = base_unique.get(nid, '<no>')
        other_id = inv_matches.get(nid)
        if other_id is not None:
            matched_count += 1
            other_node = mod_map.get(other_id)
            print(f'BASE {label} id={nid} content={content_h[:8]} unique={unique_h[:8]} --> MATCHED TO {node_label(other_node)} id={other_id} content={mod_content.get(other_id)[:8]} unique={mod_unique.get(other_id)[:8]}')
        else:
            print(f'BASE {label} id={nid} content={str(content_h)[:8]} unique={str(unique_h)[:8]} --> UNMATCHED')

    print(f'\nTotal base nodes: {len(base_map)}, matched: {matched_count}, matches returned: {len(matches)}')

    # Basic assertion to keep this a test
    assert matched_count >= 3

# Note: run pytest with -s to see the printed report (e.g., `python -m pytest -q -s tests/test_matcher_debug_print.py`)
