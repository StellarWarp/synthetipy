# Scripted Values (脚本数值计算)

Scripted Values 用于定义可复用的数值计算逻辑。在 Synthetipy 中返回 `float` 或 `int` 类型。

## 1. 基础定义

使用 `@value` 装饰器标记函数为数值计算。

```python
from synthetipy import value, scope

@value
def colony_base_score(planet: scope.Planet) -> float:
    """殖民地基础分数"""
    return planet.num_pops * 10.0
```

编译为：
```pdx
colony_base_score = {
    base = 0
    modifier = {
        add = num_pops
        multiply = 10
    }
}
```

## 2. 算术运算

支持标准的算术表达式，编译器会自动转换为 PDX 的 modifier 链。

```python
@value
def colony_development_score(planet: scope.Planet) -> float:
    """殖民地发展分数"""
    
    base_score = planet.num_pops * 10.0
    building_bonus = planet.num_buildings() * 5.0
    district_bonus = planet.num_districts() * 3.0
    
    return base_score + building_bonus + district_bonus
```

编译为：
```pdx
colony_development_score = {
    base = 0
    
    # base_score = num_pops * 10
    modifier = {
        add = num_pops
        multiply = 10
    }
    
    # building_bonus
    modifier = {
        add = num_buildings
        multiply = 5
    }
    
    # district_bonus
    modifier = {
        add = num_districts
        multiply = 3
    }
}
```

## 3. 条件分支（自动拆分）

⚠️ **PDX 的 scripted_value 不支持 if 分支**。编译器会自动将分支拆分为多个独立的 modifier。

```python
@value
def designation_multiplier(planet: scope.Planet) -> float:
    """根据星球类型计算乘数"""
    
    if planet.designation == 'col_research':
        return 1.5
    elif planet.designation == 'col_forge':
        return 1.3
    elif planet.designation == 'col_factory':
        return 1.2
    else:
        return 1.0
```

编译器自动生成：
```pdx
designation_multiplier = {
    base = 0
    
    modifier = {
        has_designation = col_research
        add = 1.5
    }
    
    modifier = {
        has_designation = col_forge
        add = 1.3
    }
    
    modifier = {
        has_designation = col_factory
        add = 1.2
    }
    
    modifier = {
        NOR = {
            has_designation = col_research
            has_designation = col_forge
            has_designation = col_factory
        }
        add = 1.0
    }
}
```

## 4. 复杂计算（自动拆分为辅助 value）

当计算过于复杂时，编译器会生成辅助的 scripted_value。

```python
@value
def colony_value_rating(planet: scope.Planet) -> float:
    """殖民地综合价值评级"""
    
    # 基础分数
    base = planet.num_pops * 10.0
    
    # 类型乘数（会被拆分）
    if planet.designation == 'col_research':
        type_mult = 1.5
    elif planet.designation == 'col_forge':
        type_mult = 1.3
    else:
        type_mult = 1.0
    
    # 稳定度修正（会被拆分）
    if planet.stability >= 80:
        stability_mult = 1.2
    elif planet.stability >= 60:
        stability_mult = 1.1
    elif planet.stability < 30:
        stability_mult = 0.8
    else:
        stability_mult = 1.0
    
    # 基础设施
    infrastructure = planet.num_buildings() * 5.0 + planet.num_districts() * 3.0
    
    # 最终计算
    return (base + infrastructure) * type_mult * stability_mult
```

编译器自动生成：
```pdx
# 主 value
colony_value_rating = {
    base = value:colony_value_rating_base
    
    modifier = {
        multiply = value:colony_value_rating_type_mult
    }
    
    modifier = {
        multiply = value:colony_value_rating_stability_mult
    }
}

# 辅助 value 1: 基础分数和基础设施
colony_value_rating_base = {
    base = 0
    
    # base = num_pops * 10
    modifier = {
        add = num_pops
        multiply = 10
    }
    
    # infrastructure: buildings
    modifier = {
        add = num_buildings
        multiply = 5
    }
    
    # infrastructure: districts
    modifier = {
        add = num_districts
        multiply = 3
    }
}

# 辅助 value 2: 类型乘数
colony_value_rating_type_mult = {
    base = 1.0
    
    modifier = {
        has_designation = col_research
        set = 1.5
    }
    
    modifier = {
        has_designation = col_forge
        set = 1.3
    }
}

# 辅助 value 3: 稳定度乘数
colony_value_rating_stability_mult = {
    base = 1.0
    
    modifier = {
        stability >= 80
        set = 1.2
    }
    
    modifier = {
        stability >= 60
        stability < 80
        set = 1.1
    }
    
    modifier = {
        stability < 30
        set = 0.8
    }
}
```

## 5. 数学函数

支持常见的数学函数，编译器会映射到 PDX 的对应操作。

```python
import math

@value
def population_growth_rate(planet: scope.Planet) -> float:
    """人口增长率"""
    
    base_growth = 3.0
    
    # min/max 函数
    pop_factor = min(planet.num_pops / 100.0, 2.0)
    
    # clamp
    stability_factor = max(0.5, min(planet.stability / 100.0, 1.5))
    
    # 三元运算符
    housing_factor = 1.0 if planet.free_housing > 0 else 0.5
    
    growth = base_growth * pop_factor * stability_factor * housing_factor
    
    # 向下取整
    return math.floor(growth)
```

## 6. 参数化 Value

```python
@value(params=['resource_type'])
def resource_production(planet: scope.Planet, resource_type: str) -> float:
    """计算指定资源的产出"""
    
    # 动态访问（编译时展开）
    base = planet.resources.produces[resource_type]
    efficiency = planet.get_modifier(f'{resource_type}_production_add')
    
    return base * (1.0 + efficiency)
```

## 7. 作用域支持

与 trigger 类似，value 也支持作用域切换。

```python
@value
def empire_research_output(country: scope.Country) -> float:
    """帝国研究产出"""
    
    total = 0.0
    
    # 遍历所有行星
    for planet in country.owned_planets:
        if planet.has_designation('col_research'):
            total += planet.num_researchers() * 5.0
    
    return total
```

编译为：
```pdx
empire_research_output = {
    base = 0
    
    # 使用 export_trigger_value_to_variable
    every_owned_planet = {
        limit = { has_designation = col_research }
        
        # 累加研究人员产出
        owner = {
            change_variable = {
                which = empire_research_output_temp
                value = num_researchers
            }
            multiply_variable = {
                which = empire_research_output_temp
                value = 5
            }
        }
    }
}
```

## 8. 完整示例

```python
from synthetipy import value, scope

@value
def planet_priority_score(planet: scope.Planet) -> float:
    """计算行星优先级（用于 AI 决策）"""
    
    # 基础分数
    base = planet.num_pops * 1.0
    
    # 根据类型调整
    if planet.designation == 'col_research':
        base *= 1.5
    elif planet.designation == 'col_forge':
        base *= 1.3
    
    # 建筑加成
    building_count = planet.num_buildings()
    base += building_count * 2.0
    
    # 稳定度惩罚
    if planet.stability < 50:
        base *= 0.7
    
    # 所有者科技水平加成
    owner = planet.owner
    if owner.has_technology('tech_planetary_unification'):
        base *= 1.1
    
    return base

@value
def fleet_power_rating(fleet: scope.Fleet) -> float:
    """舰队战力评级"""
    
    base_power = fleet.fleet_power
    
    # 数量因子（开方）
    size_factor = (fleet.num_ships / 100.0) ** 0.5
    
    # 提督加成
    if fleet.has_admiral:
        admiral_bonus = 1.0 + (fleet.admiral.skill / 10.0)
    else:
        admiral_bonus = 1.0
    
    # 科技水平
    tech_level = fleet.owner.tech_level
    tech_multiplier = 1.0 + (tech_level - 1) * 0.1
    
    return base_power * size_factor * admiral_bonus * tech_multiplier
```
