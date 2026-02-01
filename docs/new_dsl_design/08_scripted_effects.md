# Scripted Effects (脚本效果)

Scripted Effects 用于定义可复用的游戏效果逻辑。在 Synthetipy 中使用命令式语法，返回 `None`。

> **通用语法参考**：关于 if/else、for 循环、作用域切换等控制流语法，请参考 [03_logic_and_scopes.md](./03_logic_and_scopes.md)。  
> **作用域类型参考**：关于可用的作用域类型、属性和方法，请参考 [04_scope_types.md](./04_scope_types.md)。  
> 本文档专注于 effect 特有的操作。

## 1. 基础定义

使用 `@effect` 装饰器标记函数为效果脚本。

```python
from synthetipy import effect, scope

@effect
def grant_research_bonus(planet: scope.Planet) -> None:
    """授予研究加成"""
    planet.add_modifier('research_bonus', years=10)
```

编译为：
```pdx
grant_research_bonus = {
    add_modifier = {
        modifier = research_bonus
        years = 10
    }
}
```

## 2. 在对象定义中使用

在 building、technology、event 等对象中，某些字段（如 `on_built`、`on_destroy`）会自动识别为 effect 块。

```python
from synthetipy import objects, scope

@objects.building
class building_research_lab:
    def on_built(planet: scope.Planet) -> None:
        planet.add_modifier('research_bonus', years=10)
        planet.owner.add_resource('physics_research', 100)
    
    def on_destroy(planet: scope.Planet) -> None:
        planet.remove_modifier('research_bonus')
```

## 3. 资源操作

Effect 中最常用的操作是资源管理。

```python
@effect
def grant_resources(country: scope.Country) -> None:
    """授予资源"""
    country.add_resource('minerals', 1000)
    country.add_resource('energy', 500)
    country.add_resource('influence', 100)

@effect
def deduct_resources(country: scope.Country) -> None:
    """扣除资源"""
    country.add_resource('minerals', -500)  # 负数表示扣除
```

编译为：
```pdx
grant_resources = {
    add_resource = { minerals = 1000 }
    add_resource = { energy = 500 }
    add_resource = { influence = 100 }
}

deduct_resources = {
    add_resource = { minerals = -500 }
}
```

## 4. 修正（Modifier）操作

```python
@effect
def apply_modifiers(planet: scope.Planet) -> None:
    """应用修正"""
    # 添加有时限的修正
    planet.add_modifier('stability_boost', years=10)
    planet.add_modifier('crime_reduction', days=3600)
    
    # 添加永久修正
    planet.add_modifier('permanent_bonus')  # 无时限参数
    
    # 移除修正
    planet.remove_modifier('old_modifier')
```

## 5. 建筑和区划操作

```python
@effect
def upgrade_infrastructure(planet: scope.Planet) -> None:
    """升级基础设施"""
    # 添加建筑
    planet.add_building('building_institute')
    planet.add_building('building_research_lab_2')
    
    # 移除建筑
    planet.remove_building('building_research_lab_1')
    
    # 添加区划
    planet.add_district('district_city')
    planet.add_district('district_industrial')
    
    # 移除指定类型的所有建筑
    planet.remove_all_buildings_of_type('basic_research')
```

## 6. 人口操作

```python
@effect
def manage_pops(planet: scope.Planet) -> None:
    """管理人口"""
    # 创建人口
    planet.create_pop('researcher')
    planet.create_pop('worker', count=5)
    
    # 杀死人口
    planet.kill_pop()
    
    # 重新安置人口
    planet.resettle_pop(target=planet.owner.capital)
```

## 7. 事件和消息

```python
@effect
def trigger_events(country: scope.Country) -> None:
    """触发事件"""
    # 发送消息
    country.send_message(
        title="Research Breakthrough!",
        text="Your scientists have made a major discovery.",
        type="positive"
    )
    
    # 触发事件
    country.fire_event('research.breakthrough.100')
    
    # 延迟触发
    country.fire_event('delayed.event.200', days=30)
```

## 8. 参数化效果

使用 `params` 参数声明需要传入的参数。

```python
@effect(params=['building_type', 'count'])
def add_multiple_buildings(planet: scope.Planet, building_type: str, count: str) -> None:
    """添加多个相同建筑"""
    # 编译时会展开为循环
    for _ in range(int(count)):
        if planet.can_build_building(building_type):
            planet.add_building(building_type)

# 使用
@effect
def setup_research_planet(planet: scope.Planet) -> None:
    planet.add_multiple_buildings('building_research_lab_1', '3')
```

## 9. 完整示例

```python
from synthetipy import effect, scope

@effect
def initialize_research_colony(planet: scope.Planet) -> None:
    """初始化研究殖民地（完整流程）"""
    
    # 1. 验证条件 - Early Return 模式（详见 03_logic_and_scopes.md）
    if planet.is_colonized:
        return
    
    if not planet.owner.has_technology('tech_advanced_research'):
        planet.owner.send_message("需要高级研究科技")
        return
    
    # 2. 设置类型
    planet.set_designation('col_research')
    
    # 3. 添加基础建筑
    planet.add_building('building_capital')
    planet.add_building('building_research_lab_1')
    planet.add_building('building_research_lab_1')
    
    # 4. 添加初始人口
    for _ in range(10):
        planet.create_pop('researcher')
    
    # 5. 添加修正
    planet.add_modifier('new_research_colony', years=20)
    
    # 6. 通知所有者 - 作用域切换（详见 03_logic_and_scopes.md）
    owner = planet.owner
    owner.send_message(
        title="研究殖民地已建立",
        text=f"{planet.name} 已成功建立为研究殖民地",
        type="positive"
    )
    
    # 7. 触发事件（可选）
    owner.fire_event('research_colony.established', days=30)

@effect
def smart_planet_optimization(planet: scope.Planet) -> None:
    """智能行星优化（使用条件控制）"""
    
    # Early return 检查
    if planet.num_pops < 20:
        return
    
    # 条件执行 - if/elif/else（详见 03_logic_and_scopes.md）
    if planet.designation == 'col_research':
        if planet.num_buildings(type='research') < 3:
            planet.add_building('building_research_lab_1')
        
        if planet.stability < 50:
            planet.add_modifier('stability_initiative', years=10)
    
    elif planet.designation == 'col_forge':
        if planet.num_districts(type='industrial') < 5:
            planet.add_district('district_industrial')
        
        owner = planet.owner
        if owner.energy < 1000:
            owner.add_resource('energy', 500)
    
    # 通用优化
    if planet.crime > 20:
        planet.add_building('building_precinct_house')
    
    if planet.amenities < 0:
        planet.add_building('building_holo_theatres')

@effect
def upgrade_all_research_buildings(country: scope.Country) -> None:
    """升级所有研究建筑（使用 for 循环）"""
    
    # For 循环遍历 - every_* 模式（详见 03_logic_and_scopes.md）
    for planet in country.owned_planets:
        if not planet.has_designation('col_research'):
            continue  # limit 过滤
        
        planet.remove_building('building_research_lab_1')
        planet.add_building('building_institute')
```

## 10. 最佳实践

### 10.1 合理使用 Early Return

在 effect 中，early return 表示"不满足条件时提前退出"：

```python
@effect
def try_build_facility(planet: scope.Planet) -> None:
    # 逐步检查条件
    if not planet.has_designation('col_research'):
        return
    
    if planet.num_pops < 50:
        planet.owner.send_message("Population too low")
        return
    
    if not planet.owner.can_afford(minerals=1000):
        planet.owner.send_message("Not enough minerals")
        return
    
    # 满足所有条件才执行
    planet.add_building('building_institute')
    planet.owner.add_resource('minerals', -1000)
    planet.owner.send_message("Research facility built")
```

### 10.2 使用有意义的变量名

```python
@effect
def complex_upgrade(planet: scope.Planet) -> None:
    # ✅ 好：使用清晰的变量名
    owner = planet.owner
    has_tech = owner.has_technology('tech_mega_engineering')
    can_afford = owner.minerals >= 10000
    
    if has_tech and can_afford:
        planet.add_building('building_megastructure')
        owner.add_resource('minerals', -10000)
```

### 10.3 组织复杂的操作流程

将复杂的 effect 分解为多个阶段：

```python
@effect
def complete_planet_transformation(planet: scope.Planet) -> None:
    """完整的行星改造流程"""
    
    # 阶段 1: 验证
    if not _validate_transformation(planet):
        return
    
    # 阶段 2: 清理旧设施
    _cleanup_old_facilities(planet)
    
    # 阶段 3: 建设新设施
    _build_new_facilities(planet)
    
    # 阶段 4: 应用修正
    _apply_transformation_modifiers(planet)
    
    # 阶段 5: 通知
    planet.owner.send_message("Planet transformation complete!")
```
