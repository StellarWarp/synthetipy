# 宏参数系统 (Macro Parameters)

Paradox 脚本的宏参数系统基于字符串替换，这带来了独特的挑战和设计权衡。

## 1. 问题概述

### 1.1 PDX 的字符串替换机制

PDX 脚本中的参数是纯文本替换，发生在脚本解析之前：

```pdx
# 定义
my_effect = {
    add_modifier = {
        modifier = $MODIFIER_TYPE$
        days = $DURATION|30$
    }
}

# 调用
inline_script = {
    script = my_effect
    MODIFIER_TYPE = "planet_stability_add"
    DURATION = 60
}

# 实际等价于（字符串替换后）
add_modifier = {
    modifier = planet_stability_add
    days = 60
}
```

### 1.2 复杂性来源

**简单参数**（直接使用）：
```pdx
add_resource = { 
    minerals = $AMOUNT$  # 直接替换为数值
}
```

**字符串拼接**（与其他文本混合）：
```pdx
set_country_flag = flag_$EVENT_ID$_triggered  # 拼接为标识符
add_modifier = { modifier = modifier_$TIER$_$TYPE$ }  # 多段拼接
has_building = building_$BUILDING_TYPE$_$LEVEL$  # 构建建筑ID
```

**条件拼接**（参数决定语义）：
```pdx
# 参数值决定是标识符还是作用域
$TARGET$ = { add_minerals = 100 }  

# 可能是：
# event_target:my_planet = { ... }  # 作用域切换
# capital = { ... }  # 作用域切换
# minerals = 100  # 资源赋值（如果 TARGET=minerals）
```

### 11.7 简化方案：二分法策略（推荐）

经过分析，动态识别各种复杂模式（value 调用、字符串拼接、动态作用域等）难度很高且容易出错。
**采用二分法**：简单情况直接生成，复杂情况保留原始 PDX。

#### 判断标准

**简单情况**（直接生成 Python）：
- ✅ 参数直接用作数值：`add = $AMOUNT$`
- ✅ 参数作为函数参数：`has_building('$BUILDING$')`
- ✅ 参数转发（无拼接）：`value:some_func|PARAM|$MY_VAR$|`
  - 关键：`$MY_VAR$` 独立出现，没有和其他文本拼接
  - 示例：`value:bca_energy_job|num_district|$NUM_C_DST$|` ✅ 简单
- ✅ 无字符串拼接
- ✅ 无动态调用

**复杂情况**（使用 `meta.pdx()`）：
- ⚠️ 字符串拼接：`building_$TYPE$_$LEVEL$`
  - 参数与其他文本混合，构成新标识符
- ⚠️ 动态函数名：`value:$FUNC_NAME$` 或 `value:prefix_$TYPE$`
  - 函数名本身包含参数
- ⚠️ 动态作用域：`$TARGET$ = { ... }`
  - 作用域名称由参数决定
- ⚠️ 参数作为键：`$RESOURCE$ = 100`
  - 属性键由参数决定

#### 代码示例

```python
# === 简单情况：直接生成 ===
@meta.value
def simple_calculation(scope, BASE: float, MULT: float) -> float:
    result = 0.0
    result += BASE      # 直接使用参数
    result *= MULT      # 直接使用参数
    return result

# PDX:
# simple_calculation = {
#     base = 0
#     add = $BASE$
#     multiply = $MULT$
# }

# === 复杂情况：保留原始 PDX ===
@meta.value
def building_production(scope, TYPE: str, LEVEL: int) -> float:
    # 字符串拼接 → 复杂情况
    return meta.pdx("""
        base = 0
        complex_trigger_modifier = {
            trigger = num_buildings
            parameters = { type = building_$TYPE$_$LEVEL$ }
            mode = add
        }
        multiply = value:building_$TYPE$_base_output
    """, TYPE=TYPE, LEVEL=LEVEL)

# 运行时：
# 1. 替换参数：TYPE='research', LEVEL=2
# 2. 解析 PDX：building_research_2
# 3. 动态执行
```

#### 实现机制

```python
class MetaPDX:
    """meta.pdx() 实现"""
    
    @staticmethod
    def evaluate(pdx_template: str, scope, **params) -> Any:
        """
        运行时评估 PDX 代码块
        
        Args:
            pdx_template: PDX 代码模板（带 $PARAM$ 占位符）
            scope: 作用域对象
            **params: 参数值
        
        Returns:
            执行结果（value 返回 float，trigger 返回 bool）
        """
        # 1. 参数替换
        pdx_code = pdx_template
        for key, value in params.items():
            pdx_code = pdx_code.replace(f"${key}$", str(value))
        
        # 2. 动态解析
        from ..parser import PDXParser
        parser = PDXParser()
        ast = parser.parse(pdx_code)
        
        # 3. 动态执行
        from ..interpreter import PDXInterpreter
        interpreter = PDXInterpreter()
        return interpreter.evaluate(ast, scope)
```

#### inline_script 类比

这个方案与 `inline_script` 处理完全一致：

```python
# inline_script 当前实现
inline_1 = Meta.inline_script(
    script='common/inline_scripts/my_script.txt',
    PARAM1=value1,
    PARAM2=value2
)

# meta.pdx() 新方案
result = meta.pdx("""
    complex_trigger_modifier = {
        trigger = num_buildings
        parameters = { type = building_$TYPE$_$LEVEL$ }
    }
""", TYPE=type_val, LEVEL=level_val)
```

都是：**保留原始 PDX → 运行时替换参数 → 动态解析执行**

### 11.8 二分法实现策略

#### 阶段 1：基础框架（立即实现）

1. ✅ **参数识别**：扫描 AST，收集所有 `$PARAM$`
2. ⚠️ **简单性判断**：
   ```python
   def is_simple_param_usage(param_node) -> bool:
       """判断参数是否为简单使用"""
       # 检查父节点类型
       parent = param_node.parent
       
       # 简单情况 1：作为属性值、算术操作数
       if isinstance(parent, PropertyNode) and parent.value == param_node:
           return True
       
       # 简单情况 2：参数转发（在 value/trigger 调用参数中）
       # 例如：value:func|PARAM|$VAR$| - $VAR$ 独立出现，无拼接
       if isinstance(param_node, LiteralNode):
           val = str(param_node.value)
           # 检查是否只有单个参数（没有拼接其他文本）
           if val.strip() == val and val.startswith('$') and val.endswith('$'):
               # 检查前后没有其他字符
               return True
           # 如果有其他字符 → 拼接 → 复杂
           if '$' in val and len(val) > len('$X$'):
               # building_$TYPE$_$LEVEL$ 这种情况
               return False
       
       # 简单情况 3：在 IdentifierExpressionNode.parsed 中作为参数值
       # 例如：value:func|PARAM|$VAR$| 解析后的 arguments 列表
       if isinstance(parent, IdentifierExpressionNode):
           if hasattr(parent, 'parsed') and parent.parsed:
               # 检查是否在参数列表中
               if param_node in parent.parsed.arguments:
                   return True
       
       return False
   
   def has_complex_params(node: ASTNode) -> bool:
       """检查节点树是否包含复杂参数使用"""
       # 遍历节点树
       for child in walk_tree(node):
           if is_macro_param(child):
               if not is_simple_param_usage(child):
                   return True
       return False
   ```

3. ⚠️ **代码生成分支**：
   ```python
   class ValueGenerator:
       def _generate_value_statement(self, prop: PropertyNode):
           # 检查是否包含复杂参数
           if self._has_complex_params(prop):
               # 生成 meta.pdx() 调用
               self._generate_pdx_block(prop)
           else:
               # 常规生成
               self._generate_arithmetic_op(...)
   ```

#### 阶段 2：meta.pdx() 运行时（后续）

4. ⬜ 实现 `MetaPDX.evaluate()` - 动态解析执行
5. ⬜ 集成到 value/trigger/effect 运行时
6. ⬜ 参数替换优化

#### 阶段 3：Python → PDX 反向编译（可选）

7. ⬜ 识别 `meta.pdx()` 调用
8. ⬜ 提取原始 PDX 模板
9. ⬜ 还原参数占位符

### 11.9 优势分析

| 特性 | 传统方案 | 二分法方案 |
|------|----------|------------|
| **实现复杂度** | 高（需要识别各种模式） | 低（简单判断） |
| **正确性** | 易出错（遗漏边界情况） | 高（复杂情况原样保留） |
| **性能** | 好（全编译） | 中（复杂部分运行时解析） |
| **可维护性** | 低（复杂逻辑） | 高（清晰二分） |
| **Python 代码可读性** | 好 | 中（meta.pdx 部分不透明） |

### 11.10 完整示例对比

```python
# === 示例 1：简单 value（直接生成） ===
@meta.value
def simple_bonus(scope, BASE: float, MULT: float) -> float:
    result = 0.0
    result += BASE
    result *= MULT
    return result

# 编译为 PDX:
"""
simple_bonus = {
    base = 0
    add = $BASE$
    multiply = $MULT$
}
"""

# === 示例 2：简单参数转发（直接生成） ===
@meta.value
def energy_production_estimate(scope, NUM_C_DST: int, NUM_R_DST: int) -> float:
    result = 0.0
    # 参数转发，无拼接 → 简单情况
    result *= bca_planet_energy_job_mult_estimate(
        scope, 
        num_district_city=NUM_C_DST  # $NUM_C_DST$ 独立传递
    )
    result += bca_planet_energy_job_add_estimate(
        scope,
        num_resource_district=NUM_R_DST  # $NUM_R_DST$ 独立传递
    )
    return result

# 编译为 PDX:
"""
energy_production_estimate = {
    base = 0
    multiply = value:bca_planet_energy_job_mult_estimate|num_district_city|$NUM_C_DST$|
    add = value:bca_planet_energy_job_add_estimate|num_resource_district|$NUM_R_DST$|
}
"""

# === 示例 3：复杂拼接（meta.pdx） ===
@meta.value
def complex_bonus(scope, TYPE: str, TIER: int, RESOURCE: str) -> float:
    return meta.pdx("""
        base = 0
        
        # 字符串拼接 - 复杂
        complex_trigger_modifier = {
            trigger = num_buildings
            parameters = { type = building_$TYPE$_$TIER$ }
            mode = add
        }
        
        # 动态函数名 - 复杂
        multiply = value:$RESOURCE$_production_multiplier
        
        # 动态 modifier 引用 - 复杂
        add = modifier:$TYPE$_$TIER$_bonus
    """, TYPE=TYPE, TIER=TIER, RESOURCE=RESOURCE)

# 编译为 PDX（直接保留）:
"""
complex_bonus = {
    base = 0
    complex_trigger_modifier = {
        trigger = num_buildings
        parameters = { type = building_$TYPE$_$TIER$ }
        mode = add
    }
    multiply = value:$RESOURCE$_production_multiplier
    add = modifier:$TYPE$_$TIER$_bonus
}
"""

# === 示例 4：混合模式 ===
@meta.value
def mixed_calculation(scope, SIMPLE: float, COMPLEX_TYPE: str) -> float:
    result = 0.0
    result += SIMPLE  # 简单参数，直接使用
    
    # 复杂部分用 meta.pdx
    complex_part = meta.pdx("""
        complex_trigger_modifier = {
            trigger = count_pops
            parameters = { type = pop_$COMPLEX_TYPE$ }
        }
    """, COMPLEX_TYPE=COMPLEX_TYPE)
    
    result += complex_part
    return result
```

### 11.11 实现优先级（最终版）

**立即实现**（第一阶段）：
1. ✅ 参数识别器（AST 遍历）
2. ⚠️ 简单性判断器（`is_simple_usage()`）
3. ⚠️ 函数签名生成（带参数）
4. ⚠️ 简单参数直接替换
5. ⚠️ 复杂情况生成 `meta.pdx()` 调用

**后续实现**（第二阶段）：
6. ⬜ `MetaPDX.evaluate()` 运行时
7. ⬜ 动态解析器集成
8. ⬜ 性能优化（缓存解析结果）

**可选实现**（第三阶段）：
9. ⬜ Python → PDX 反向编译
10. ⬜ meta.pdx 块的静态分析
11. ⬜ 类型推断（基于 PDX 模板）

### 11.8 代码示例

```python
# 实际使用示例
from synthetipy import meta, scope

@meta.value
def get_building_output(planet: scope.Planet, TYPE: str, LEVEL: int) -> float:
    """获取指定建筑的产出"""
    
    # 方案 1: meta.macro() - 推荐
    building_id = meta.macro(f"building_{TYPE}_{LEVEL}")
    count = planet.num_buildings(type=building_id)
    
    # 方案 2: meta.value_call() - 动态函数名
    base_output = meta.value_call(f"building_{TYPE}_base_output")
    
    return count * base_output(planet)

# 编译为 PDX:
"""
get_building_output = {
    base = 0
    
    # meta.macro 生成
    complex_trigger_modifier = {
        trigger = num_buildings
        parameters = { type = building_$TYPE$_$LEVEL$ }
        mode = add
    }
    
    # meta.value_call 生成
    multiply = value:building_$TYPE$_base_output
}
"""
```

### 11.9 实现优先级更新

**立即实现**（第一阶段基础）：
1. ✅ 参数收集器（识别 `$PARAM$`）
2. ⚠️ 函数签名生成（带参数）
3. ⚠️ `meta.macro()` 基础实现
4. ⚠️ 简单反向编译（模式识别）

**后续迭代**：
5. ⬜ `meta.value_call()` 动态调用
6. ⬜ 元数据追踪系统
7. ⬜ 完整反向编译器
