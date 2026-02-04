"""
测试 Python 代码生成器
"""

import sys
from pathlib import Path

# 添加 src 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from synthetipy import parse
from synthetipy.codegen import generate_python_code

def test_real_cases():
    """测试真实文件案例"""
    print("=" * 60)
    print("测试 5: 真实文件案例")
    print("=" * 60)
    
    pdx_code = """
# Planetary Administration
building_capital = {
	base_buildtime = @b2_time
	capital = yes
	can_build = no
	can_demolish = no
	can_be_ruined = no
	can_be_disabled = no
	position_priority = 0
	capital_tier = 2

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
			is_planet_class = pc_cosmogenesis_world
		}
	}

	convert_to = {
		building_hive_capital
		building_machine_capital
		building_resort_capital
		building_slave_capital
		building_ancient_control_center
		building_ancient_palace
		building_capital_wilderness
	}

	allow = {
		sapient_pop_amount >= 1000
	}

	upgrades = {
		"building_major_capital"
	}

	prerequisites = {
		"tech_planetary_government"
	}

	show_tech_unlock_if = {
		is_regular_empire = yes
	}

	planet_modifier = {
		job_enforcer_add = 100
		planet_housing_add = 1000
		planet_amenities_add = 1000
		planet_max_branch_office_buildings_add = 1
		planet_defense_armies_add = @tier_2_capital_defense_armies
	}

	inline_script = {
		script = buildings/on_all_capital_buildings
	}

	inline_script = {
		script = buildings/regular_empire_capital_jobs
		AMOUNT = 200
	}

	triggered_planet_modifier = {
		potential = {
			exists = owner
			owner = {
				has_active_tradition = tr_domination_imperious_architecture
			}
		}
		modifier = {
			planet_housing_add = 100
		}
	}

	triggered_planet_modifier = {
		potential = {
			exists = owner
			owner = { has_technology = tech_capital_productivity_1 }
		}
		pop_bonus_workforce_mult = 0.1
	}

	resources = {
		category = planet_buildings
		cost = {
			minerals = @b2_minerals
		}
		upkeep = {
			energy = @b2_upkeep
		}
	}

	additional_ai_weight = 100
}
"""
    print("输入 PDX 代码:")
    print(pdx_code)
    
    # 解析
    ast = parse(pdx_code)
    
    # 生成 Python 代码
    python_code = generate_python_code(ast, "common/buildings/test.txt")
    
    print("\n生成的 Python 代码:")
    print(python_code)
    print()



if __name__ == '__main__':
    test_real_cases()
    
    print("=" * 60)
    print("所有测试完成!")
    print("=" * 60)
