from synthetipy.ast_nodes_basic import ObjectNode, DocumentNode
from synthetipy.parser import parse
from synthetipy.script_merger.gumtree_hash import compute_subtree_hashes
from synthetipy.script_merger.matcher import gumtree_match
from synthetipy.script_merger.utils import postorder, node_label

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

BUILDING_TEXT_MOD = r'''
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
            always = yes # here
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
            owner = { has_active_tradition = xxx } # and here
            
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


def test_similarity_matches_modified_properties():
    base_doc = parse(BUILDING_TEXT)
    mod_doc = parse(BUILDING_TEXT_MOD)
    
    base_obj = base_doc.statements[0]
    mod_obj = mod_doc.statements[0]

    base_content, base_buckets = compute_subtree_hashes(base_obj)
    mod_content, mod_buckets = compute_subtree_hashes(mod_obj)
    matches,_ = gumtree_match(base_obj, mod_obj,
                            base_content, base_buckets,
                            mod_content, mod_buckets, 
                            similarity_threshold=0.4)

    # ensure the majority of nodes are matched
    assert len(matches) >= 3

    # Build id->node maps and pretty-print matches for readability
    base_map = {n: n for n in postorder(base_obj)}
    mod_map = {n: n for n in postorder(mod_obj)}

    def fmt(n):
        if n is None:
            return '<missing>'
        short_id = f"{id(n) & 0xFFFFF:05x}"
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
        if len(content) > 60:
            content = content[:57] + '...'

        return f"{lab} @{short_id} | {path} | {content}"

    unmatched_other = [oid for oid in mod_map.keys() if oid not in matches]
    unmatched_base = [bid for bid in base_map.keys() if bid not in set(matches.values())]

    printable_other = [fmt(mod_map[oid]) for oid in unmatched_other]
    printable_base = [fmt(base_map[bid]) for bid in unmatched_base]

    print('\n-- unmatched nodes in other (mod) --')
    for line in printable_other:
        print(line)
    print('\n-- unmatched nodes in base --')
    for line in printable_base:
        print(line)
        
    print('\n\n')
    print(base_content[base_obj])
    print(mod_content[mod_obj])

test_similarity_matches_modified_properties()