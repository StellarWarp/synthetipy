# Scripted Triggers (脚本触发器)

Scripted Triggers 用于定义可复用的条件判断逻辑。在 Synthetipy 中，使用装饰器和标准 Python 语法来定义。

> **通用语法参考**：关于 if/else、for 循环、作用域切换等控制流语法，请参考 [03_logic_and_scopes.md](./03_logic_and_scopes.md)。  
> **作用域类型参考**：关于可用的作用域类型、属性和方法，请参考 [04_scope_types.md](./04_scope_types.md)。  
> 本文档专注于 trigger 特有的特性。

## 1. 基础定义

使用 `@trigger` 装饰器标记函数为触发器。函数必须返回 `bool` 类型。

```python
from synthetipy import trigger, scope

@trigger
def can_build_research_facility(planet: scope.Planet) -> bool:
    """检查是否可以建造研究设施"""
    return (
        planet.owner.is_regular_empire and
        not planet.has_modifier('slave_colony') and
        planet.num_pops >= 10
    )
```

编译为：
```pdx
can_build_research_facility = {
    owner = { is_regular_empire = yes }
    NOT = { has_modifier = slave_colony }
    num_pops >= 10
}
```

## 2. 在对象定义中使用

在 building、technology 等对象中，某些字段（如 `potential`、`allow`）会自动识别为 trigger 块。

```python
from synthetipy import objects, scope

@objects.building
class building_supercomputer:
    # 根据方法名自动识别为 trigger 块，不需要 @trigger 装饰器
    def potential(planet: scope.Planet) -> bool:
        return (
            planet.owner.is_regular_empire and
            not planet.has_modifier('slave_colony')
        )
    
    def allow(planet: scope.Planet) -> bool:
        return planet.num_pops >= 10
```

## 3. 参数化触发器

使用 `params` 参数声明需要传入的参数。

```python
@trigger(params=['tech_name'])
def has_technology_param(country: scope.Country, tech_name: str) -> bool:
    """检查是否拥有指定技术（参数化）"""
    return country.has_technology(tech_name)

@trigger(params=['building_type', 'min_count'])
def has_enough_buildings(planet: scope.Planet, building_type: str, min_count: str) -> bool:
    """检查是否有足够数量的建筑"""
    # ⚠️ 参数都是字符串，在编译时内联展开
    return planet.num_buildings(type=building_type) >= int(min_count)
```

调用时会内联展开：
```python
@trigger
def is_research_hub(planet: scope.Planet) -> bool:
    return planet.has_enough_buildings('research', '5')

# 编译时展开为：
# num_buildings = { type = research value >= 5 }
```

## 4. 完整示例

```python
from synthetipy import trigger, scope

@trigger
def can_remove_research_building(planet: scope.Planet) -> bool:
    """BCA Mod: 检查是否可以移除研究建筑"""
    return (
        planet.has_designation('col_bca_research') or
        (
            planet.num_buildings(type='research') > 1 and
            planet.owner.is_ai
        )
    )

@trigger
def is_advanced_research_colony(planet: scope.Planet) -> bool:
    """判断是否是高级研究殖民地"""
    
    # 基础检查 - Early Return 模式（详见 03_logic_and_scopes.md）
    if not planet.has_designation('col_research'):
        return False
    
    if planet.num_pops < 50:
        return False
    
    # 建筑要求
    has_institute = planet.has_building('building_institute')
    has_complex = planet.has_building('building_research_complex')
    
    if not (has_institute or has_complex):
        return False
    
    # 所有者检查 - 作用域变量
    owner = planet.owner
    return owner.has_technology('tech_advanced_research')

@trigger
def all_planets_stable(country: scope.Country) -> bool:
    """检查所有行星是否稳定"""
    # For 循环检查（详见 03_logic_and_scopes.md）
    for planet in country.owned_planets:
        if planet.stability < 50:
            return False
    return True

@trigger
def has_any_research_planet(country: scope.Country) -> bool:
    """是否有研究行星"""
    # For 循环 + break 模式
    _found = False
    for planet in country.owned_planets:
        if planet.has_designation('col_research'):
            _found = True
            break
    return _found
```

## 5. 最佳实践

### 5.1 保持简单

Trigger 应该是纯粹的条件检查，避免复杂的计算逻辑：

```python
# ✅ 好：简单清晰
@trigger
def is_valid_target(planet: scope.Planet) -> bool:
    return (
        planet.is_colonized and
        planet.num_pops >= 10 and
        not planet.has_modifier('quarantine')
    )

# ❌ 差：逻辑过于复杂
@trigger
def complex_check(planet: scope.Planet) -> bool:
    total = 0
    for pop in planet.pops:
        if pop.job == 'researcher':
            total += 1
    threshold = planet.num_pops * 0.3
    return total >= threshold
```

### 5.2 使用 Early Return

Early return 模式可以让代码更清晰，避免深层嵌套：

```python
@trigger
def is_valid_colonization_target(planet: scope.Planet) -> bool:
    # 逐步排除不符合的情况
    if planet.is_colonized:
        return False
    
    if not planet.is_habitable:
        return False
    
    if planet.has_modifier('primitive_civilization'):
        return False
    
    # 最后的正向检查
    return planet.size >= 15
```

### 5.3 合理使用局部变量

提取复杂表达式到局部变量可以提高可读性：

```python
@trigger
def can_build_megastructure(country: scope.Country) -> bool:
    # 提取复杂条件
    has_tech = country.has_technology('tech_mega_engineering')
    has_resources = country.minerals >= 10000 and country.alloys >= 5000
    has_ascension = country.has_ascension_perk('ap_galactic_wonders')
    
    # 清晰的逻辑组合
    return has_tech and has_resources and has_ascension
```
