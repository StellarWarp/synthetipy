# 逻辑与作用域系统

Synthetipy 使用 Python 的标准控制流语句来表达 PDX 的逻辑和作用域操作。这些语法在 trigger 和 effect 中通用。

## 1. 条件控制流

### if/elif/else 语句

Python 的条件语句会被转换为 PDX 的 `if = { limit = {...} ... }` 结构。

**在 Trigger 中（返回 bool）：**
```python
def potential(planet: scope.Planet) -> bool:
    if planet.num_pops >= 100:
        return planet.has_building('building_capital')
    elif planet.num_pops >= 50:
        return planet.num_buildings() >= 10
    else:
        return planet.num_districts() >= 5
```

编译为：
```pdx
potential = {
    if = {
        limit = { num_pops >= 100 }
        has_building = building_capital
    }
    else_if = {
        limit = { num_pops >= 50 }
        num_buildings >= 10
    }
    else = {
        num_districts >= 5
    }
}
```

**在 Effect 中（执行操作）：**
```python
def on_built(planet: scope.Planet) -> None:
    if planet.designation == 'col_research':
        planet.add_building('building_institute')
        planet.add_modifier('research_bonus', years=10)
    elif planet.designation == 'col_forge':
        planet.add_building('building_foundry_2')
    else:
        planet.optimize_buildings()
```

编译为：
```pdx
on_built = {
    if = {
        limit = { has_designation = col_research }
        add_building = building_institute
        add_modifier = { modifier = research_bonus years = 10 }
    }
    else_if = {
        limit = { has_designation = col_forge }
        add_building = building_foundry_2
    }
    else = {
        optimize_buildings = yes
    }
}
```

### Early Return 模式

提前返回用于简化多个排他性检查。

**Trigger 中的 Early Return（返回 False）：**
```python
def allow(planet: scope.Planet) -> bool:
    # 不满足条件时提前返回 False
    if planet.is_colonized:
        return False
    
    if not planet.is_habitable:
        return False
    
    if planet.has_modifier('primitive_civilization'):
        return False
    
    # 所有检查通过
    return planet.size >= 15
```

编译为：
```pdx
allow = {
    NOR = { is_colonized = yes }
    is_habitable = yes
    NOT = { has_modifier = primitive_civilization }
    planet_size >= 15
}
```

**Effect 中的 Early Return（提前退出）：**
```python
def on_destroy(planet: scope.Planet) -> None:
    # 不满足条件时提前退出
    if not planet.has_designation('col_research'):
        return
    
    if planet.num_pops < 50:
        planet.owner.send_message("Population too low")
        return
    
    # 满足条件才执行
    planet.add_building('building_institute')
    planet.owner.send_message("Research facility built")
```

编译为：
```pdx
on_destroy = {
    if = {
        limit = {
            has_designation = col_research
            num_pops >= 50
        }
        add_building = building_institute
        owner = { send_message = { text = "Research facility built" } }
    }
    else_if = {
        limit = {
            has_designation = col_research
            num_pops < 50
        }
        owner = { send_message = { text = "Population too low" } }
    }
}
```

## 2. 作用域切换 (Scope Switching)

PDX 的核心特性是作用域切换（如 `owner = { ... }`）。Synthetipy 提供两种 Pythonic 写法。

### 方式 A: with 语句（推荐）

最清晰地表达"进入某个作用域执行逻辑"的语义。

**PDX 原文：**
```pdx
potential = {
    owner = {
        is_ai = yes
        capital = {
            is_planet_class = pc_ocean
        }
    }
    num_pops >= 10
}
```

**Synthetipy：**
```python
def potential(planet: scope.Planet) -> bool:
    # 切换到 owner 作用域
    with planet.owner as owner:
        if not owner.is_ai:
            return False
        
        # 嵌套切换到 capital 作用域
        with owner.capital as capital:
            if not capital.is_planet_class('pc_ocean'):
                return False
    
    # 回到 planet 作用域
    return planet.num_pops >= 10
```

### 方式 B: 变量赋值（简化写法）

对于简单的作用域链访问，可以通过变量赋值简化。

**Synthetipy：**
```python
def potential(planet: scope.Planet) -> bool:
    owner = planet.owner  # 不立即展开，保存引用
    
    return (
        owner.is_regular_empire and  # 编译时展开为 owner = { is_regular_empire = yes }
        owner.has_technology('tech_mega_engineering') and
        planet.num_pops >= 20
    )
```

编译为：
```pdx
potential = {
    owner = {
        is_regular_empire = yes
        has_technology = tech_mega_engineering
    }
    num_pops >= 20
}
```

## 3. 循环与迭代

### For 循环遍历作用域列表

用于处理集合中的每个元素（如所有行星）。

**Trigger 中的 any_ 检查：**
```python
def allow(country: scope.Country) -> bool:
    # 检查是否存在满足条件的行星
    _found = False
    for planet in country.owned_planets:
        if planet.has_designation('col_research') and planet.num_pops >= 50:
            _found = True
            break
    
    if not _found:
        return False
    
    return country.has_technology('tech_advanced_research')
```

编译为：
```pdx
allow = {
    any_owned_planet = {
        has_designation = col_research
        num_pops >= 50
    }
    has_technology = tech_advanced_research
}
```

**Effect 中的 every_ 操作：**
```python
def on_action(country: scope.Country) -> None:
    # 对每个满足条件的行星执行操作
    for planet in country.owned_planets:
        if not planet.has_designation('col_research'):
            continue  # limit 过滤
        
        planet.add_building('building_institute')
        planet.add_modifier('research_focus', years=20)
```

编译为：
```pdx
on_action = {
    every_owned_planet = {
        limit = { has_designation = col_research }
        add_building = building_institute
        add_modifier = { modifier = research_focus years = 20 }
    }
}
```

### 常见的迭代作用域

| Python 属性 | PDX 语法 | 说明 |
|------------|---------|------|
| `country.owned_planets` | `any_owned_planet`, `every_owned_planet` | 所有拥有的行星 |
| `country.owned_pops` | `any_owned_pop`, `every_owned_pop` | 所有拥有的人口 |
| `planet.pops` | `any_pop`, `every_pop` | 行星上的人口 |
| `country.subjects` | `any_subject`, `every_subject` | 所有附庸国 |
| `galaxy.countries` | `any_country`, `every_country` | 所有国家 |

### 嵌套循环

```python
def complex_check(country: scope.Country) -> None:
    for planet in country.owned_planets:
        if planet.designation != 'col_research':
            continue
        
        # 嵌套循环
        for pop in planet.pops:
            if pop.job == 'researcher':
                pop.add_modifier('research_boost', years=5)
```

编译为：
```pdx
complex_check = {
    every_owned_planet = {
        limit = { has_designation = col_research }
        
        every_pop = {
            limit = { has_job = researcher }
            add_modifier = { modifier = research_boost years = 5 }
        }
    }
}
```

## 4. 布尔逻辑

### 基础布尔运算

**AND（所有条件都满足）：**
```python
return (
    planet.is_habitable and
    planet.num_pops >= 10 and
    not planet.has_modifier('slave_colony')
)
```
→ 所有条件平铺在同一层

**OR（任一条件满足）：**
```python
return (
    planet.has_building('building_capital') or
    planet.has_building('building_major_capital')
)
```
→
```pdx
OR = {
    has_building = building_capital
    has_building = building_major_capital
}
```

**NOT（条件不满足）：**
```python
return not planet.has_modifier('resort_colony')
```
→
```pdx
NOT = { has_modifier = resort_colony }
```

### 复杂逻辑组合

```python
def potential(planet: scope.Planet) -> bool:
    # 复杂的布尔表达式
    basic_check = planet.is_colonized and planet.num_pops >= 20
    
    owner_check = (
        planet.owner.is_regular_empire or
        planet.owner.is_hive_empire
    )
    
    no_restrictions = not (
        planet.has_modifier('resort_colony') or
        planet.has_modifier('slave_colony')
    )
    
    return basic_check and owner_check and no_restrictions
```

编译为：
```pdx
potential = {
    is_colonized = yes
    num_pops >= 20
    
    OR = {
        owner = { is_regular_empire = yes }
        owner = { is_hive_empire = yes }
    }
    
    NOR = {
        has_modifier = resort_colony
        has_modifier = slave_colony
    }
}
```

## 5. 变量与临时值

### 局部变量

在函数内使用局部变量提高可读性：

```python
def potential(planet: scope.Planet) -> bool:
    # 计算中间值
    has_capital = planet.has_building('building_capital')
    has_upgraded = planet.has_building('building_major_capital')
    
    # 使用中间值
    has_any_capital = has_capital or has_upgraded
    
    return has_any_capital and planet.num_pops >= 50
```

编译时会内联展开这些逻辑。

### 作用域变量

保存作用域引用以简化访问：

```python
def potential(planet: scope.Planet) -> bool:
    owner = planet.owner
    capital = owner.capital
    
    return (
        owner.has_technology('tech_advanced') and
        capital.num_pops >= 100 and
        planet.num_pops >= 50
    )
```

## 6. 完整示例

**综合运用所有特性：**
```python
def validate_and_upgrade(planet: scope.Planet) -> None:
    """验证行星并执行升级（effect 示例）"""
    
    # Early return：基础检查
    if not planet.is_colonized:
        return
    
    if planet.num_pops < 20:
        planet.owner.send_message("Population too low")
        return
    
    # 作用域切换
    with planet.owner as owner:
        if not owner.has_technology('tech_advanced_research'):
            owner.send_message("Missing required technology")
            return
    
    # 条件执行
    if planet.designation == 'col_research':
        # 遍历行星上的人口
        for pop in planet.pops:
            if pop.job == 'researcher':
                pop.add_modifier('research_excellence', years=10)
        
        planet.add_building('building_institute')
    
    elif planet.designation == 'col_forge':
        planet.add_district('district_industrial')
    
    # 无条件执行
    planet.add_modifier('planet_upgraded', years=20)
```

## 总结

| 特性 | Trigger 用法 | Effect 用法 |
|-----|------------|------------|
| **if/else** | 返回不同的 bool 值 | 执行不同的操作 |
| **Early return** | `return False` 跳过检查 | `return` 提前退出 |
| **with 语句** | 作用域切换检查条件 | 作用域切换执行操作 |
| **for 循环** | `any_*` 检查（用 break） | `every_*` 操作（用 continue 过滤） |
| **布尔逻辑** | 组合多个检查条件 | 用于 if 的 limit 部分 |
