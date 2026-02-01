"""
PDX 语言常量定义

集中管理 PDX 脚本语言的关键字、操作符、作用域等常量
避免在各个模块中重复定义
"""

# ============================================
# 逻辑操作符
# ============================================

LOGIC_OPERATORS = frozenset({'AND', 'OR', 'NOT', 'NOR', 'NAND'})


# ============================================
# 比较操作符映射 (PDX -> Python)
# ============================================

COMPARISON_OPS = {
    '=': '==',
    '>': '>',
    '<': '<',
    '>=': '>=',
    '<=': '<=',
    '==': '==',
    '!=': '!='
}


# ============================================
# 作用域切换关键字
# ============================================

# 简单作用域切换（属性访问）
SCOPE_SWITCHES = frozenset({
    'owner', 'capital', 'overlord', 'ruler', 'planet', 
    'country', 'leader', 'pop', 'fleet', 'ship', 'starbase',
    'from', 'root', 'prev', 'this', 'solar_system', 'sector',
    'species', 'army',
})

# 迭代作用域映射 {关键字: (迭代变量, 集合属性)}
ITERATION_SCOPES = {
    'any_owned_planet': ('planet', 'owned_planets'),
    'every_owned_planet': ('planet', 'owned_planets'),
    'any_owned_pop': ('pop', 'owned_pops'),
    'every_owned_pop': ('pop', 'owned_pops'),
    'any_planet': ('planet', 'planets'),
    'every_planet': ('planet', 'planets'),
    'any_pop': ('pop', 'pops'),
    'every_pop': ('pop', 'pops'),
    'any_country': ('country', 'countries'),
    'every_country': ('country', 'countries'),
    'any_owned_fleet': ('fleet', 'owned_fleets'),
    'every_owned_fleet': ('fleet', 'owned_fleets'),
}


# ============================================
# 方法调用识别
# ============================================

# 方法前缀（这些前缀的关键字应被识别为方法调用）
METHOD_PREFIXES = frozenset({
    'has_', 'can_', 'is_', 'num_', 'any_', 'every_', 
    'free_', 'count_', 'check_',
})

# 循环关键字前缀
LOOP_PREFIXES = frozenset({'every_', 'random_', 'ordered_'})

# 循环类型映射 {后缀: (迭代变量, 集合属性)}
LOOP_MAPPINGS = {
    'owned_planet': ('planet', 'owned_planets'),
    'owned_pop': ('pop', 'owned_pops'),
    'owned_ship': ('ship', 'owned_ships'),
    'owned_fleet': ('fleet', 'owned_fleets'),
    'owned_leader': ('leader', 'owned_leaders'),
    'pop': ('pop', 'pops'),
    'planet': ('planet', 'planets'),
    'system': ('system', 'systems'),
    'country': ('country', 'countries'),
    'neighbor_country': ('neighbor', 'neighbor_countries'),
    'owned_army': ('army', 'owned_armies'),
    'owned_starbase': ('starbase', 'owned_starbases'),
    'megastructure': ('mega', 'megastructures'),
}


# ============================================
# 变量和标记操作
# ============================================

VARIABLE_OPS = frozenset({
    'set_variable', 'add_variable', 'subtract_variable', 
    'multiply_variable', 'divide_variable', 'clear_variable',
    'change_variable',
})

FLAG_OPS = frozenset({
    'set_planet_flag', 'remove_planet_flag',
    'set_country_flag', 'remove_country_flag',
    'set_global_flag', 'remove_global_flag',
    'set_star_flag', 'remove_star_flag',
    'set_fleet_flag', 'remove_fleet_flag',
    'set_ship_flag', 'remove_ship_flag',
    'set_pop_flag', 'remove_pop_flag',
    'set_leader_flag', 'remove_leader_flag',
})


# ============================================
# Effect 相关
# ============================================

# 带参数块的效果
BLOCK_EFFECTS = frozenset({
    'add_modifier', 'remove_modifier',
    'add_building', 'remove_building',
    'add_district', 'remove_district',
    'add_resource', 'fire_event', 'send_message',
    'create_pop', 'kill_pop',
    'create_fleet', 'create_ship',
    'create_army', 'create_leader',
    'set_owner', 'set_controller',
    'add_deposit', 'remove_deposit',
    'add_trait', 'remove_trait',
})

# 主参数键（作为第一个位置参数）
PRIMARY_KEYS = frozenset({
    'modifier', 'building', 'district', 'id', 'job',
    'deposit', 'trait', 'species', 'leader_class',
})

# 特殊调用关键字
SPECIAL_CALLS = frozenset({
    'check_variable_arithmetic',
    'check_variable',
    'custom_tooltip',
    'custom_tooltip_with_fail_root',
    'hidden_tooltip',
})


# ============================================
# 资源类型
# ============================================

RESOURCE_KEYS = frozenset({
    # 基础资源
    'minerals', 'energy', 'food', 'alloys', 
    'consumer_goods', 'influence', 'unity',
    # 研究
    'physics_research', 'society_research', 'engineering_research',
    # 战略资源
    'exotic_gases', 'rare_crystals', 'volatile_motes',
    'sr_zro', 'sr_dark_matter', 'sr_living_metal',
})


# ============================================
# 作用域类型
# ============================================

SCOPE_TYPES = {
    'country': {'owner', 'from', 'root', 'prev', 'controller', 'overlord'},
    'planet': {'capital', 'home_planet', 'capital_planet'},
    'pop': {'pop', 'species'},
    'leader': {'ruler', 'leader'},
    'fleet': {'fleet'},
    'ship': {'ship'},
    'system': {'solar_system'},
    'sector': {'sector'},
}


# ============================================
# 词法分析关键字
# ============================================

LEXER_KEYWORDS = {
    'OR', 'AND', 'NOT', 'NAND', 'NOR',
}
