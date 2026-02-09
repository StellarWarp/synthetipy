from synthetipy.parser import parse
from synthetipy.script_merger.gumtree_hash import compute_subtree_hashes
from synthetipy.script_merger.utils import postorder, node_label, node_id
from synthetipy.script_merger.matcher import match_by_hash


BUILDING_TEXT = r'''
building_colony_shelter = {
	capital = yes
	can_build = no
	can_demolish = no
	can_be_ruined = no
	can_be_disabled = no
	position_priority = 0
	capital_tier = 1

	category = government

	building_sets = {
		government
	}

	potential = {
		exists = owner
		owner = {
			is_regular_empire = yes
			is_fallen_empire = no
		}
		NOR = {
			has_modifier = resort_colony
			has_modifier = slave_colony
			uses_habitat_capitals = yes
			uses_district_set = cosmogenesis_world
		}
	}

	convert_to = {
		building_hive_capital
		building_deployment_post
		building_resort_capital
		building_slave_capital
		building_ancient_control_center
		building_ancient_palace
		building_colony_shelter_wilderness
	}

	planet_modifier = {
		planet_housing_add = 300
		planet_amenities_add = 300
	}

	inline_script = {
		script = shroud/jobs/colonist_add
		AMOUNT = 200
	}

	inline_script = {
		script = buildings/on_all_capital_buildings
	}

	triggered_planet_modifier = {
		potential = {
			exists = owner
			owner = { has_valid_civic = civic_dystopian_society }
		}
		job_enforcer_add = 100
		job_colonist_add = -100
		job_spe_colonist_add = -100
	}

	triggered_planet_modifier = {
		potential = {
			exists = owner
			owner = { is_regular_empire = yes }
			has_modifier = penal_colony
		}
		job_colonist_add = -100
		job_spe_colonist_add = -100
	}

	triggered_planet_modifier = {
		potential = {
			exists = owner
			owner = {
				is_individual_machine = yes
			}
		}
		job_roboticist_add = 100
		job_colonist_add = -100
		job_spe_colonist_add = -100
	}

	triggered_planet_modifier = {
		potential = {
			exists = owner
			owner = { has_active_tradition = tr_synthetics_prefabricated_components }
		}
		job_roboticist_add = 100
		job_colonist_add = -100
		job_spe_colonist_add = -100
	}

	resources = {
		category = planet_buildings
		upkeep = {
			energy = 1
		}
	}

	upgrades = {
		building_capital
	}
}
'''

# slightly modified variant for comparison
BUILDING_TEXT_MODIFIED = r'''
building_colony_shelter = {
	capital = yes
	can_build = no
	can_demolish = no
	can_be_ruined = no
	can_be_disabled = no
	position_priority = 1  # modified
	capital_tier = 1

	category = government

	building_sets = {
		government
	}

	potential = {
		exists = owner
		owner = {
			is_regular_empire = yes
			is_fallen_empire = no
		}
		NOR = {
			has_modifier = resort_colony
			has_modifier = slave_colony
			uses_habitat_capitals = yes
			uses_district_set = cosmogenesis_world
		}
	}

	planet_modifier = {
		planet_housing_add = 350  # modified
		planet_amenities_add = 300
	}

	inline_script = {
		script = shroud/jobs/colonist_add
		AMOUNT = 200
	}
}
'''


def test_large_building_parsed_and_hashed():
    doc = parse(BUILDING_TEXT)

    # Expect some top-level object nodes (building_colony_shelter, building_capital)
    top_objects = doc.statements
        
    assert len(top_objects) >= 2

    any_disambiguated = False
    for obj in top_objects:
        content_map, content_buckets, unique_map, unique_buckets = compute_subtree_hashes(obj)

        # Basic sanity: every node encountered under object has both content and unique hashes
        for n in postorder(obj):
            nid = node_id(n)
            assert nid in content_map
            assert nid in unique_map

        # Ensure disambiguation: if any parent has multiple children with same content hash, unique hashes differ
        from collections import defaultdict
        for parent in postorder(obj):
            from synthetipy.script_merger.utils import astnode_children
            chs = astnode_children(parent)
            seen = {}
            for c in chs:
                ch_content = content_map[node_id(c)]
                seen.setdefault(ch_content, []).append(c)
            for content_h, entries in seen.items():
                if len(entries) > 1:
                    # check their unique hashes differ
                    uniqs = {unique_map[node_id(e)] for e in entries}
                    if len(uniqs) > 1:
                        any_disambiguated = True
                        break
            if any_disambiguated:
                break
        if any_disambiguated:
            break
    assert any_disambiguated


def test_building_variant_hash_match():
    base_doc = parse(BUILDING_TEXT)
    mod_doc = parse(BUILDING_TEXT_MODIFIED)

    # pick the first object in each doc
    base_obj = base_doc.statements[0]
    mod_obj = mod_doc.statements[0]
	

    base_content, base_buckets, base_unique, base_ub = compute_subtree_hashes(base_obj)
    mod_content, mod_buckets, mod_unique, mod_ub = compute_subtree_hashes(mod_obj)

	# match_by_hash returns a mapping: other_node_id -> base_node_id
	matches = match_by_hash(base_obj, mod_obj, base_content, base_buckets, mod_content, mod_buckets)

	# Build id->node maps for pretty printing
	from synthetipy.script_merger.utils import postorder, node_label, node_id
	base_map = {node_id(n): n for n in postorder(base_obj)}
	mod_map = {node_id(n): n for n in postorder(mod_obj)}

	# Helper to format a node concisely: short id, object-local path, and brief content
	def fmt(n):
		if n is None:
			return '<missing>'
		nid = node_id(n)
		short_id = f"{nid & 0xFFFFF:05x}"
		lab = node_label(n)

		# build a brief path up to the enclosing object (Object:name)
		parts = []
		cur = n
		while cur is not None:
			lbl = node_label(cur)
			if lbl.startswith('Object:'):
				parts.append(lbl)
				break
			if lbl.startswith('Property:') and hasattr(cur, 'key'):
				parts.append(str(cur.key))
			else:
				parts.append(lbl.split(':')[0])
			cur = getattr(cur, 'parent', None)
		path = ' > '.join(reversed(parts)) if parts else ''

		# short content: prefer str() for value-like nodes, otherwise repr()
		content = ''
		try:
			content = str(n)
		except Exception:
			content = repr(n)
		# compress long reprs
		if len(content) > 60:
			content = content[:57] + '...'

		return f"{lab} @{short_id} | {path} | {content}"

	# Print unmatched nodes for readability: other-side unmatched and base-side unmatched
	from pprint import pprint
	unmatched_other = [oid for oid in mod_map.keys() if oid not in matches]
	unmatched_base = [bid for bid in base_map.keys() if bid not in set(matches.values())]

	printable_other = [fmt(mod_map[oid]) for oid in unmatched_other]
	printable_base = [fmt(base_map[bid]) for bid in unmatched_base]

	print('\n-- unmatched nodes in other (mod) --')
	pprint(printable_other)
	print('\n-- unmatched nodes in base --')
	pprint(printable_base)

    # Expect many matches but at least one differing node for the modified properties
    assert len(matches) > 5

    # find property nodes for 'position_priority' and 'planet_housing_add'
    from synthetipy.script_merger.utils import astnode_children

    def find_prop(node, key_name):
        # recursive search for PropertyNode with given key_name
        from synthetipy.script_merger.utils import astnode_children
        def _rec(n):
            if node_label(n).startswith('Property:') and str(n.key) == key_name:
                return n
            for ch in astnode_children(n):
                found = _rec(ch)
                if found is not None:
                    return found
            return None
        return _rec(node)

    pos_base = find_prop(base_obj, 'position_priority')
    pos_mod = find_prop(mod_obj, 'position_priority')
    assert pos_base is not None and pos_mod is not None

    # their content hashes should differ due to the modified value
    assert base_content[node_id(pos_base)] != mod_content[node_id(pos_mod)]

    # planet_housing_add changed in variant
    ph_base = find_prop(base_obj, 'planet_housing_add')
    ph_mod = find_prop(mod_obj, 'planet_housing_add')
    assert ph_base is not None and ph_mod is not None
    assert base_content[node_id(ph_base)] != mod_content[node_id(ph_mod)]

    # nodes other than modified ones should match via content hash
    # find a known static property, e.g., 'capital'
    cap_base = find_prop(base_obj, 'capital')
    cap_mod = find_prop(mod_obj, 'capital')
    assert cap_base is not None and cap_mod is not None
    assert base_content[node_id(cap_base)] == mod_content[node_id(cap_mod)]

