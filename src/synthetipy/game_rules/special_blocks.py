"""
PDXLang 特殊块规则

此文件由 tools/generate_python_rules.py 自动生成
"""

# control_flow
CONTROL_FLOW_BLOCKS = {
    'effect:else_if', 'effect:if', 'effect:switch', 'trigger:else_if', 'trigger:if', 
    'trigger:switch',
}

# hidden
HIDDEN_BLOCKS = {'effect:hidden_effect', 'trigger:hidden_trigger'}

# random
RANDOM_BLOCKS = {'effect:locked_random_list', 'effect:random', 'effect:random_list'}

# scope_change
SCOPE_CHANGE_BLOCKS = {
    'alliance', 'archaeological_site', 'army_leader', 'assembling_species', 'associated_federation', 
    'astral_rift', 'attacker', 'aura_owner', 'background_planet', 'branch_office_owner', 
    'built_species', 'capital_scope', 'capital_star', 'contact_country', 'controller', 'creator', 
    'declining_species', 'defender', 'design', 'envoy_location_country', 'excavator_fleet', 
    'explorer', 'federation', 'federation_leader', 'fleet', 'founder_species', 'from', 'fromfrom', 
    'fromfromfrom', 'fromfromfromfrom', 'galactic_custodian', 'galactic_emperor', 'growing_species', 
    'heir', 'home_planet', 'instigator', 'last_added_deposit', 'last_created_ambient_object', 
    'last_created_army', 'last_created_cosmic_storm', 'last_created_cosmic_storm_influence_field', 
    'last_created_country', 'last_created_design', 'last_created_fleet', 'last_created_leader', 
    'last_created_pop_faction', 'last_created_ship', 'last_created_species', 'last_created_system', 
    'leader', 'lock_country', 'mining_station', 'no_scope', 'observation_outpost', 
    'observation_outpost_owner', 'orbit', 'orbital_defence', 'orbital_station', 'overlord', 'owner', 
    'owner_main_species', 'owner_or_space_owner', 'owner_species', 'planet', 'planet_owner', 
    'pop_faction', 'prev', 'prevprev', 'prevprevprev', 'prevprevprevprev', 'research_station', 
    'reverse_first_contact', 'root', 'ruler', 'sector', 'sector_capital', 'ship_growth_stage', 
    'solar_system', 'space_owner', 'spawner_planet', 'species', 'spynetwork', 'star', 'starbase', 
    'storm_influence_field', 'system_star', 'target', 'target_system', 'this', 'unhappiest_pop',
}

# wrapper
WRAPPER_BLOCKS = {'effect:custom_tooltip', 'effect:tooltip', 'trigger:custom_tooltip'}
