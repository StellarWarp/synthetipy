# Scope Types (作用域类型系统)

本文档定义 PDX 脚本中可用的作用域类型及其方法。这些定义将根据官方文档自动生成，提供完整的 IDE 类型提示支持。

## 1. 类型系统概述

Synthetipy 为每个 PDX 作用域提供 Python 类型定义，包含：
- **属性**：只读属性，可直接访问（如 `planet.num_pops`）
- **关联作用域**：导航到其他作用域对象（如 `planet.owner`）
- **Trigger 方法**：用于条件检查，返回 `bool`（如 `planet.has_building('x')`）
- **Effect 方法**：用于修改游戏状态，返回 `None`（如 `planet.add_building('x')`）

## 2. 基础作用域类型

### 2.1 Planet (行星)

```python
class Planet(Scope):
    """行星作用域"""
    
    # === 属性 (只读) ===
    num_pops: int                    # 人口数量
    size: int                        # 行星大小
    stability: float                 # 稳定度 (0-100)
    amenities: float                 # 宜居度
    crime: float                     # 犯罪度 (0-100)
    is_colonized: bool               # 是否已殖民
    is_habitable: bool               # 是否可居住
    designation: str                 # 行星类型 (col_research, col_forge, etc.)
    name: str                        # 行星名称
    
    # === 关联作用域 ===
    owner: 'Country'                 # 所有者国家
    capital: 'Planet'                # 所属首都
    pops: list['Pop']                # 所有人口
    
    # === Trigger 方法 (条件检查) ===
    def has_building(self, building: str) -> bool:
        """检查是否有指定建筑"""
        ...
    
    def has_designation(self, designation: str) -> bool:
        """检查是否有指定类型"""
        ...
    
    def has_modifier(self, modifier: str) -> bool:
        """检查是否有指定修正"""
        ...
    
    def has_upgraded_capital(self) -> bool:
        """检查是否有升级的首都建筑"""
        ...
    
    def can_build_building(self, building: str) -> bool:
        """检查是否可以建造指定建筑"""
        ...
    
    def num_buildings(self, *, type: str = None) -> int:
        """获取建筑数量，可按类型过滤"""
        ...
    
    def num_districts(self, *, type: str = None) -> int:
        """获取区划数量，可按类型过滤"""
        ...
    
    def can_build_district(self, district: str) -> bool:
        """检查是否可以建造指定区划"""
        ...
    
    # === Effect 方法 (修改操作) ===
    def add_building(self, building: str) -> None:
        """添加建筑"""
        ...
    
    def remove_building(self, building: str) -> None:
        """移除建筑"""
        ...
    
    def add_district(self, district: str) -> None:
        """添加区划"""
        ...
    
    def remove_district(self, district: str) -> None:
        """移除区划"""
        ...
    
    def add_modifier(self, modifier: str, *, days: int = None, years: int = None) -> None:
        """添加修正（可指定持续时间）"""
        ...
    
    def remove_modifier(self, modifier: str) -> None:
        """移除修正"""
        ...
    
    def set_designation(self, designation: str) -> None:
        """设置行星类型"""
        ...
    
    def optimize_buildings(self) -> None:
        """优化建筑布局"""
        ...
    
    def create_pop(self, job: str, *, count: int = 1) -> None:
        """创建人口"""
        ...
    
    def kill_pop(self, *, count: int = 1) -> None:
        """杀死人口"""
        ...
    
    def resettle_pop(self, target: 'Planet') -> None:
        """重新安置人口到目标行星"""
        ...
    
    def remove_all_buildings_of_type(self, type: str) -> None:
        """移除指定类型的所有建筑"""
        ...
```

### 2.2 Country (国家)

```python
class Country(Scope):
    """国家作用域"""
    
    # === 属性 (只读) ===
    is_ai: bool                      # 是否是 AI
    is_regular_empire: bool          # 是否是常规帝国
    is_hive_empire: bool             # 是否是蜂群意识
    is_machine_empire: bool          # 是否是机械帝国
    is_gestalt: bool                 # 是否是格式塔意识
    num_owned_planets: int           # 拥有的行星数量
    num_owned_pops: int              # 拥有的人口数量
    
    # 资源
    energy: int                      # 能量币
    minerals: int                    # 矿物
    food: int                        # 食物
    alloys: int                      # 合金
    consumer_goods: int              # 消费品
    influence: int                   # 影响力
    unity: int                       # 凝聚力
    
    # === 关联作用域 ===
    capital: 'Planet'                # 首都行星
    owned_planets: list['Planet']    # 所有拥有的行星
    owned_pops: list['Pop']          # 所有拥有的人口
    subjects: list['Country']        # 附庸国家
    overlord: 'Country'              # 宗主国
    ruler: 'Leader'                  # 统治者
    
    # === Trigger 方法 (条件检查) ===
    def has_technology(self, tech: str) -> bool:
        """检查是否拥有指定科技"""
        ...
    
    def has_civic(self, civic: str) -> bool:
        """检查是否拥有指定政体"""
        ...
    
    def has_ethic(self, ethic: str) -> bool:
        """检查是否拥有指定思潮"""
        ...
    
    def has_modifier(self, modifier: str) -> bool:
        """检查是否有指定修正"""
        ...
    
    def can_afford(self, **resources) -> bool:
        """检查是否能支付指定资源"""
        ...
    
    def has_ascension_perk(self, perk: str) -> bool:
        """检查是否拥有指定飞升天赋"""
        ...
    
    def has_tradition(self, tradition: str) -> bool:
        """检查是否拥有指定传统"""
        ...
    
    def is_at_war_with(self, country: 'Country') -> bool:
        """检查是否与指定国家处于战争状态"""
        ...
    
    def has_communications(self, country: 'Country') -> bool:
        """检查是否与指定国家建立通讯"""
        ...
    
    # === Effect 方法 (修改操作) ===
    def add_resource(self, resource: str, amount: int) -> None:
        """添加资源（负数表示扣除）"""
        ...
    
    def add_modifier(self, modifier: str, *, days: int = None, years: int = None) -> None:
        """添加修正"""
        ...
    
    def remove_modifier(self, modifier: str) -> None:
        """移除修正"""
        ...
    
    def send_message(self, text: str, *, title: str = None, type: str = None) -> None:
        """发送消息通知"""
        ...
    
    def fire_event(self, event: str, *, days: int = None) -> None:
        """触发事件"""
        ...
    
    def add_technology(self, tech: str) -> None:
        """添加科技"""
        ...
    
    def add_civic(self, civic: str) -> None:
        """添加政体"""
        ...
    
    def remove_civic(self, civic: str) -> None:
        """移除政体"""
        ...
    
    def create_fleet(self, design: str, location: 'Planet') -> None:
        """在指定位置创建舰队"""
        ...
    
    def establish_communications(self, country: 'Country') -> None:
        """与指定国家建立通讯"""
        ...
```

### 2.3 Pop (人口)

```python
class Pop(Scope):
    """人口作用域"""
    
    # === 属性 (只读) ===
    job: str                         # 职业
    is_enslaved: bool                # 是否被奴役
    is_robot: bool                   # 是否是机器人
    happiness: float                 # 幸福度 (0-100)
    species: str                     # 种族
    
    # === 关联作用域 ===
    planet: 'Planet'                 # 所在行星
    owner: 'Country'                 # 所有者国家
    
    # === Trigger 方法 ===
    def has_job(self, job: str) -> bool:
        """检查是否有指定职业"""
        ...
    
    def has_trait(self, trait: str) -> bool:
        """检查是否有指定特质"""
        ...
    
    # === Effect 方法 ===
    def set_job(self, job: str) -> None:
        """设置职业"""
        ...
    
    def kill(self) -> None:
        """杀死此人口"""
        ...
    
    def enslave(self) -> None:
        """奴役此人口"""
        ...
    
    def free(self) -> None:
        """解放此人口"""
        ...
```

### 2.4 Leader (领袖)

```python
class Leader(Scope):
    """领袖作用域"""
    
    # === 属性 (只读) ===
    name: str                        # 名称
    level: int                       # 等级
    age: int                         # 年龄
    class_name: str                  # 职业类别 (governor, scientist, admiral, general)
    
    # === 关联作用域 ===
    owner: 'Country'                 # 所有者国家
    
    # === Trigger 方法 ===
    def has_trait(self, trait: str) -> bool:
        """检查是否有指定特质"""
        ...
    
    def has_skill_level(self, level: int) -> bool:
        """检查技能等级"""
        ...
    
    # === Effect 方法 ===
    def add_trait(self, trait: str) -> None:
        """添加特质"""
        ...
    
    def remove_trait(self, trait: str) -> None:
        """移除特质"""
        ...
    
    def set_level(self, level: int) -> None:
        """设置等级"""
        ...
    
    def kill(self) -> None:
        """杀死此领袖"""
        ...
```

### 2.5 Ship (舰船)

```python
class Ship(Scope):
    """舰船作用域"""
    
    # === 属性 (只读) ===
    name: str                        # 舰船名称
    design: str                      # 设计方案
    hull_health: float               # 船体健康度 (0-1)
    shield_health: float             # 护盾健康度 (0-1)
    
    # === 关联作用域 ===
    owner: 'Country'                 # 所有者国家
    fleet: 'Fleet'                   # 所属舰队
    
    # === Trigger 方法 ===
    def has_component(self, component: str) -> bool:
        """检查是否有指定组件"""
        ...
    
    # === Effect 方法 ===
    def repair(self) -> None:
        """修复舰船"""
        ...
    
    def destroy(self) -> None:
        """摧毁舰船"""
        ...
```

### 2.6 Fleet (舰队)

```python
class Fleet(Scope):
    """舰队作用域"""
    
    # === 属性 (只读) ===
    name: str                        # 舰队名称
    fleet_power: int                 # 舰队战力
    
    # === 关联作用域 ===
    owner: 'Country'                 # 所有者国家
    ships: list['Ship']              # 所有舰船
    
    # === Trigger 方法 ===
    def is_in_combat(self) -> bool:
        """检查是否在战斗中"""
        ...
    
    # === Effect 方法 ===
    def set_location(self, location: 'Planet') -> None:
        """设置位置"""
        ...
    
    def destroy(self) -> None:
        """摧毁舰队"""
        ...
```

## 3. 类型生成说明

这些类型定义将通过以下方式自动生成：

1. **从官方文档提取**：解析 Paradox 官方 wiki、mod 文档等
2. **AST 分析**：分析现有 mod 脚本，提取常用方法
3. **类型推断**：根据使用模式推断参数和返回类型
4. **手工补充**：对于文档不全的部分，手工添加定义

生成的类型文件位置：`synthetipy/scope.py`

## 4. 使用示例

```python
from synthetipy import trigger, effect, scope

@trigger
def can_build_megastructure(country: scope.Country) -> bool:
    """检查是否可以建造巨型建筑"""
    # IDE 会提供 country 的所有方法和属性的自动完成
    return (
        country.has_technology('tech_mega_engineering') and
        country.has_ascension_perk('ap_galactic_wonders') and
        country.can_afford(minerals=10000, alloys=5000)
    )

@effect
def setup_research_planet(planet: scope.Planet) -> None:
    """设置研究行星"""
    # IDE 会提供 planet 的所有方法和属性的自动完成
    planet.set_designation('col_research')
    planet.add_building('building_research_lab_1')
    planet.add_modifier('research_focus', years=10)
    
    # 作用域切换时也有完整的类型提示
    owner = planet.owner
    owner.send_message("Research planet established!")
```

## 5. 扩展作用域

对于自定义 mod 添加的新作用域或方法，可以通过继承扩展：

```python
from synthetipy.scope import Planet, Country

class ExtendedPlanet(Planet):
    """扩展的行星作用域（自定义 mod）"""
    
    # 添加自定义属性
    custom_resource: int
    
    # 添加自定义方法
    def has_custom_building(self, building: str) -> bool: ...
    def add_custom_modifier(self, modifier: str) -> None: ...

# 使用扩展的类型
@trigger
def custom_check(planet: ExtendedPlanet) -> bool:
    return planet.custom_resource > 100
```
