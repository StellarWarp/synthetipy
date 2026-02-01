# 对象定义与属性映射

Synthetipy 使用标准的 Python 类定义来映射 PDX 对象。

## 1. 顶级对象

使用装饰器标记顶级对象

```python
from synthetipy import objects

# 显式标记这个类是一个 building 对象
# ID 将直接取自类名 "building_supercomputer"
@objects.building
class building_supercomputer:
    """
    文档字符串将被转换为 PDX 注释或忽略
    """
    # 基础属性：直接赋值
    category = 'research'
    base_buildtime = 360
    # 列表属性
    prerequisites = [technology.tech_mega_engineering, technology.tech_advanced_research]
```

也可以传递参数来指定不同的 ID（如果不希望使用类名）：

```python
@objects.building(id='building_supercomputer_v2')
class MySpecialLab:
    category = 'research'
```

## 2. 嵌套结构：内联类 (Inline Classes)

对于 `resources = { ... }` 这种嵌套结构，直接使用 Python 的嵌套类语法。
不需要继承 Schema，直接定义即可。

```python
@objects.building(id='building_supercomputer_v2')
class building_supercomputer:   
    # 对应 resources = { ... }
    class resources:
        category = 'planet_buildings'
        
        # 对应 cost = { ... }
        class cost:
            minerals = 100
            exotic_gases = 2
            
        # 对应 upkeep = { ... }
        class upkeep:
            energy = 5
```

## 3. 重复键处理：魔术后缀 (Magic Suffix)

PDX 允许重复键（如多个 `triggered_planet_modifier`），但 Python 类属性不允许重名。
解决方案：使用 **双下划线后缀 (`__suffix`)**。

编译器在生成 PDX 代码时，会自动剥离 `__` 及之后的内容。

```python
class building_supercomputer:
    
    # 编译为: triggered_planet_modifier = { ... }
    # 使用类继承 + 魔术后缀，同时享受 IDE 提示和后缀去重
    class triggered_planet_modifier__gestalt:
        
        # 方法定义 - 编译器根据名字 'potential' 自动识别为 trigger
        def potential(planet: scope.Planet) -> bool:
            return planet.owner.is_gestalt
            
        class modifier:
            upkeep = 1.5

    # 编译为: triggered_planet_modifier = { ... }
    class triggered_planet_modifier__machine:
        
        # 方法定义 - 自动识别为 trigger
        def potential(planet: scope.Planet) -> bool:
            return planet.owner.is_machine_empire
            
        class modifier:
            upkeep = 3
```
## 4. 方法定义：自动类型识别

在对象类内部定义方法时，**不需要显式使用装饰器**。编译器会根据方法名自动识别类型：

```python
@objects.building
class building_supercomputer:
    category = 'research'
    
    # 根据方法名 'potential' 自动识别为 trigger 块
    # 返回类型 -> bool 说明这是一个条件判断
    def potential(planet: scope.Planet) -> bool:
        return planet.owner.is_regular_empire
    
    # 根据方法名 'on_built' 自动识别为 effect 块
    # 返回类型 -> None 说明这是一个副作用操作
    def on_built(planet: scope.Planet) -> None:
        planet.add_modifier('research_boost', years=10)
    
    # 根据方法名 'ai_weight' 自动识别为 value 块
    # 返回类型 -> float 说明这是一个数值计算
    def ai_weight() -> float:
        return 100.0
```

**识别规则**：

| 方法名模式 | 自动识别为 | 返回类型 | PDX 含义 |
|-----------|-----------|---------|----------|
| `potential`, `allow`, `destroy_trigger`, `can_*` | Trigger | `bool` | 条件判断 |
| `effect`, `on_*`, `after`, `immediate` | Effect | `None` | 游戏效果 |
| `ai_weight`, `weight`, `base` | Value | `float` | 数值计算 |

**何时需要显式装饰器**：

只有在以下情况需要显式使用 `@trigger/@effect/@value`：

1. **顶层 scripted_triggers/effects/values 文件**（不在对象类内部）
2. **方法名无法推断类型时**（例如自定义名称）

```python
# 在 common/scripted_triggers/*.txt 中，顶层函数需要装饰器
@trigger
def my_custom_condition(planet: scope.Planet) -> bool:
    return planet.num_pops >= 50

# 在对象内部，标准名称不需要装饰器
@objects.building
class my_building:
    def potential(planet) -> bool:  # ✅ 自动识别
        return True
    
    # 但如果你用了非标准名称，就需要显式标记
    @trigger
    def my_special_check(planet) -> bool:  # ⚠️ 需要装饰器
        return True
```
```
