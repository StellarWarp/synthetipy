# AST → Python 代码生成策略

从 PDXLang AST 生成 Python DSL 代码的实现策略和技术细节。

## 1. 核心困难

### 1.1 块类型识别问题

**问题**：如何区分不同类型的代码块？

```pdx
building_research_lab = {
    category = research                    # 简单属性
    
    cost = {                               # 嵌套对象 → 生成内联类
        minerals = 400
    }
    
    potential = {                          # Trigger 块 → 生成 @staticmethod
        owner = { is_regular_empire = yes }
    }
    
    triggered_planet_modifier = {          # 嵌套对象（不是 trigger）
        potential = {                      # 嵌套的 Trigger 块
            ...
        }
        modifier = {                       # 嵌套对象
            ...
        }
    }
}
```

**期望的 Python 输出**：

```python
@objects.building
class building_research_lab:
    category = 'research'
    
    class cost:  # 内联类
        minerals = 400
    
    @staticmethod  # trigger 函数
    def potential() -> bool:
        return scope.owner.is_regular_empire
    
    class triggered_planet_modifier:  # 内联类
        @staticmethod  # 嵌套 trigger
        def potential() -> bool:
            ...
        
        class modifier:  # 嵌套对象
            ...
```

### 1.2 上下文相关性

同样的键名在不同上下文中有不同的含义：

| 键名 | 在 building 中 | 在 triggered_modifier 中 | 在 script_values 中 |
|------|---------------|-------------------------|---------------------|
| `potential` | Trigger 块 | Trigger 块 | ❌ 不存在 |
| `effect` | Effect 块 | ❌ 不存在 | ❌ 不存在 |
| `modifier` | 嵌套对象（条件+加成） | 嵌套对象（纯加成） | 算术操作块 |

### 1.3 文件路径依赖

顶层对象的类型依赖于文件路径：

- `common/scripted_triggers/*.txt` → 所有顶层对象是 `@trigger` 函数
- `common/scripted_effects/*.txt` → 所有顶层对象是 `@effect` 函数
- `common/script_values/*.txt` → 所有顶层对象是 `@value` 函数
- `common/buildings/*.txt` → 顶层对象是 `@objects.building` 类

## 2. 解决方案：分层识别策略

### 2.1 第一层：文件路径规则

根据文件路径确定顶层对象的默认类型。

```python
# codegen/file_rules.py
FILE_TYPE_RULES = {
    'common/scripted_triggers': 'trigger',
    'common/scripted_effects': 'effect',
    'common/script_values': 'value',
    'common/buildings': 'object',
    'common/districts': 'object',
    'common/technology': 'object',
    'common/edicts': 'object',
    # ... 更多规则
}

def get_file_type(file_path: str) -> str:
    """根据文件路径获取类型"""
    for pattern, obj_type in FILE_TYPE_RULES.items():
        if pattern in file_path:
            return obj_type
    return 'object'  # 默认
```

### 2.2 第二层：键名知识库

维护一个知识库，记录哪些键对应哪种类型的块。

```python
# codegen/block_type_registry.py

# Trigger 块的键名（返回 bool）
TRIGGER_KEYS = {
    # 通用 trigger
    'potential', 'allow', 'can_build', 'destroy_trigger',
    'abort_trigger', 'completion_trigger',
    
    # 条件检查
    'trigger', 'limit', 'custom_tooltip_with_fail_root',
    
    # AI 条件
    'ai_weight', 'ai_build_at_chokepoint',
    
    # 事件条件
    'fire_only_once', 'is_triggered_only',
    
    # 修饰符条件（在 triggered_* 内部）
    # 注意：这些需要上下文检查
}

# Effect 块的键名（返回 None，有副作用）
EFFECT_KEYS = {
    # 通用 effect
    'effect', 'on_built', 'on_destroy', 'on_queued', 
    'on_unqueued', 'on_colonized',
    
    # 事件效果
    'immediate', 'after',
    
    # 选项效果
    'option_effect', 'default_option',
}

# Value 块的键名（返回 float/int）
VALUE_KEYS = {
    # 权重计算
    'base', 'weight', 'factor',
    
    # 算术修饰符（在 script_values 中）
    'modifier',
}

# 特殊结构（不能简单归类）
SPECIAL_KEYS = {
    'modifier': 'context_dependent',  # 需要上下文判断
    'weight_modifier': 'weighted_block',  # 权重修饰符
    'resources': 'resource_block',  # 资源块
    'inline_script': 'inline_script',  # 内联脚本
}

def get_block_type(key: str, parent_context: str = None) -> str:
    """
    获取块类型
    
    Args:
        key: 键名
        parent_context: 父级上下文（如 'building', 'triggered_modifier'）
    
    Returns:
        'trigger' | 'effect' | 'value' | 'nested_object' | 'special'
    """
    if key in TRIGGER_KEYS:
        return 'trigger'
    elif key in EFFECT_KEYS:
        return 'effect'
    elif key in VALUE_KEYS:
        # 在 script_values 文件中，modifier 是 value 块
        # 在其他文件中，modifier 可能是嵌套对象
        if parent_context == 'script_values':
            return 'value'
        return 'nested_object'
    elif key in SPECIAL_KEYS:
        return SPECIAL_KEYS[key]
    else:
        return 'nested_object'
```

### 2.3 第三层：AST 结构分析

分析 BlockNode 的内容来推断类型。

```python
# codegen/structure_analyzer.py

def analyze_block_structure(block: BlockNode) -> str:
    """通过分析块的结构推断类型"""
    
    # 统计特征
    has_comparisons = False  # 比较运算符 (>=, <, etc.)
    has_logic_ops = False    # 逻辑运算符 (AND, OR, NOT)
    has_assignments = False  # 赋值操作
    has_arithmetic = False   # 算术操作 (add, multiply)
    
    for stmt in block.statements:
        if isinstance(stmt, ComparisonNode):
            has_comparisons = True
        elif isinstance(stmt, PropertyNode):
            key = stmt.key
            
            # Trigger 特征
            if key in ('AND', 'OR', 'NOT', 'NAND', 'NOR'):
                has_logic_ops = True
            elif key in ('limit', 'trigger'):
                has_logic_ops = True
            
            # Effect 特征
            elif key.startswith(('add_', 'remove_', 'set_', 'change_')):
                has_assignments = True
            
            # Value 特征
            elif key in ('base', 'add', 'multiply', 'factor', 'weight'):
                has_arithmetic = True
    
    # 推断类型
    if has_arithmetic and not (has_logic_ops or has_assignments):
        return 'value'
    elif has_logic_ops or has_comparisons:
        return 'trigger'
    elif has_assignments:
        return 'effect'
    else:
        return 'nested_object'  # 无法确定，默认为嵌套对象
```

### 2.4 组合策略

```python
# codegen/block_classifier.py

class BlockClassifier:
    """块类型分类器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file_type = get_file_type(file_path)
        self.context_stack = []  # 上下文栈
    
    def classify_block(self, key: str, block: BlockNode) -> str:
        """
        分类一个块
        
        Returns:
            'trigger' | 'effect' | 'value' | 'nested_object'
        """
        
        # 1. 优先级最高：显式键名规则
        explicit_type = get_block_type(key, self.get_current_context())
        if explicit_type in ('trigger', 'effect', 'value'):
            return explicit_type
        
        # 2. 文件级别规则（仅用于顶层）
        if not self.context_stack and self.file_type in ('trigger', 'effect', 'value'):
            return self.file_type
        
        # 3. 结构分析
        inferred_type = analyze_block_structure(block)
        if inferred_type != 'nested_object':
            return inferred_type
        
        # 4. 默认为嵌套对象
        return 'nested_object'
    
    def get_current_context(self) -> str:
        """获取当前上下文"""
        if self.context_stack:
            return self.context_stack[-1]
        return self.file_type
```

## 3. 代码生成器实现

### 3.1 基础生成器

```python
# codegen/python_generator.py

class PythonCodeGenerator:
    """AST → Python 代码生成器"""
    
    def __init__(self, file_path: str):
        self.classifier = BlockClassifier(file_path)
        self.indent_level = 0
        self.lines = []
    
    def generate(self, ast: DocumentNode) -> str:
        """生成完整的 Python 代码"""
        
        # 导入语句
        self.add_line("from synthetipy import objects, trigger, effect, value, scope")
        self.add_line("")
        
        # 生成每个顶层对象
        for obj in ast.statements:
            if isinstance(obj, ObjectNode):
                self.generate_object(obj)
                self.add_line("")
        
        return '\n'.join(self.lines)
    
    def generate_object(self, obj: ObjectNode):
        """生成顶层对象"""
        
        obj_type = self.classifier.file_type
        
        if obj_type == 'trigger':
            self.generate_trigger_function(obj)
        elif obj_type == 'effect':
            self.generate_effect_function(obj)
        elif obj_type == 'value':
            self.generate_value_function(obj)
        else:
            self.generate_object_class(obj)
    
    def generate_object_class(self, obj: ObjectNode):
        """生成对象类定义"""
        
        # 装饰器
        category = self.guess_category(obj)
        self.add_line(f"@objects.{category}")
        
        # 类定义
        self.add_line(f"class {obj.name}:")
        self.indent()
        
        # 生成类体
        self.classifier.context_stack.append(obj.name)
        self.generate_block_body(obj.body)
        self.classifier.context_stack.pop()
        
        self.dedent()
    
    def generate_block_body(self, block: BlockNode):
        """生成块的内容"""
        
        if not block.statements:
            self.add_line("pass")
            return
        
        for stmt in block.statements:
            if isinstance(stmt, PropertyNode):
                self.generate_property(stmt)
    
    def generate_property(self, prop: PropertyNode):
        """生成属性"""
        
        key = prop.key
        value = prop.value
        
        # 如果值是块，需要判断类型
        if isinstance(value, BlockNode):
            block_type = self.classifier.classify_block(key, value)
            
            if block_type == 'trigger':
                self.generate_trigger_method(key, value)
            elif block_type == 'effect':
                self.generate_effect_method(key, value)
            elif block_type == 'value':
                self.generate_value_method(key, value)
            else:
                # 嵌套类
                self.generate_nested_class(key, value)
        else:
            # 简单属性
            self.add_line(f"{key} = {self.format_literal(value)}")
    
    def generate_trigger_method(self, name: str, block: BlockNode):
        """生成 trigger 方法"""
        
        self.add_line("@staticmethod")
        self.add_line(f"def {name}() -> bool:")
        self.indent()
        
        # TODO: 转换 trigger 逻辑为 Python 表达式
        self.add_line("# TODO: Convert trigger logic")
        self.add_line("return True")
        
        self.dedent()
    
    def generate_effect_method(self, name: str, block: BlockNode):
        """生成 effect 方法"""
        
        self.add_line("@staticmethod")
        self.add_line(f"def {name}() -> None:")
        self.indent()
        
        # TODO: 转换 effect 逻辑为 Python 语句
        self.add_line("# TODO: Convert effect logic")
        self.add_line("pass")
        
        self.dedent()
    
    def generate_nested_class(self, name: str, block: BlockNode):
        """生成嵌套类"""
        
        self.add_line(f"class {name}:")
        self.indent()
        
        self.classifier.context_stack.append(name)
        self.generate_block_body(block)
        self.classifier.context_stack.pop()
        
        self.dedent()
    
    # 辅助方法
    def add_line(self, line: str):
        """添加一行（自动缩进）"""
        indent = "    " * self.indent_level
        self.lines.append(indent + line if line else "")
    
    def indent(self):
        self.indent_level += 1
    
    def dedent(self):
        self.indent_level -= 1
    
    def format_literal(self, value: ASTNode) -> str:
        """格式化值为 Python 字面量"""
        if isinstance(value, LiteralNode):
            if value.value_type == 'string':
                return f"'{value.value}'"
            elif value.value_type == 'bool':
                return 'True' if value.value else 'False'
            else:
                return str(value.value)
        # TODO: 处理其他类型
        return "..."
```

## 4. 测试示例

### 输入 PDX：

```pdx
# common/buildings/research.txt
building_research_lab_1 = {
    category = research
    
    cost = {
        minerals = 400
    }
    
    potential = {
        owner = { is_regular_empire = yes }
        NOT = { has_modifier = slave_colony }
    }
    
    triggered_planet_modifier = {
        potential = {
            exists = owner
            owner = { is_gestalt = yes }
        }
        modifier = {
            job_brain_drone_add = 2
        }
    }
    
    on_built = {
        planet = {
            add_modifier = {
                modifier = research_boost
                years = 10
            }
        }
    }
}
```

### 期望输出：

```python
from synthetipy import objects, trigger, effect, value, scope

@objects.building
class building_research_lab_1:
    category = 'research'
    
    class cost:
        minerals = 400
    
    @staticmethod
    def potential() -> bool:
        return (
            scope.owner.is_regular_empire and
            not scope.has_modifier('slave_colony')
        )
    
    class triggered_planet_modifier:
        @staticmethod
        def potential() -> bool:
            return (
                scope.exists('owner') and
                scope.owner.is_gestalt
            )
        
        class modifier:
            job_brain_drone_add = 2
    
    @staticmethod
    def on_built() -> None:
        planet = scope.planet
        planet.add_modifier('research_boost', years=10)
```

## 5. 实现优先级

1. **阶段 1（MVP）**：
   - ✅ 文件路径规则
   - ✅ 基础键名知识库
   - ✅ 生成嵌套类（简单属性）
   - ⏳ 识别 trigger/effect 块，生成 @staticmethod 框架

2. **阶段 2（逻辑转换）**：
   - ⏳ Trigger 逻辑转换为 Python 布尔表达式
   - ⏳ Effect 逻辑转换为 Python 语句
   - ⏳ 作用域切换 (`owner`, `planet`)

3. **阶段 3（完善）**：
   - ⏳ Value 块的算术转换
   - ⏳ 复杂结构（weight_modifier, inline_script）
   - ⏳ 宏参数支持
   - ⏳ 类型注解生成

## 6. 当前困难和挑战

### 6.1 已识别的困难

1. **逻辑表达式转换**：
   - PDX: `AND = { a = yes b = yes }` → Python: `a and b`
   - PDX: `NOT = { has_x = yes }` → Python: `not has_x`
   - 嵌套逻辑的括号优先级

2. **作用域导航**：
   - PDX: `owner = { capital = { ... } }` → Python: `scope.owner.capital`
   - `with` 语句生成
   - 保存作用域 (`prev`, `from`)

3. **参数化**：
   - 识别可变参数（`$PARAM$`）
   - 生成函数签名

4. **类型推断**：
   - 为 scope 对象生成准确的类型注解
   - 根据上下文推断返回类型

### 6.2 未来优化

1. **智能化**：
   - 使用 ML 模型辅助识别块类型
   - 从游戏文件学习 Schema

2. **增量更新**：
   - 只重新生成修改的部分
   - 保留用户的自定义代码

3. **双向同步**：
   - Python → PDX 代码生成
   - 检测冲突并合并
