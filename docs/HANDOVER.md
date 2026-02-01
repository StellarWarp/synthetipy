# 项目交接文档

**项目名称**: PDXLang Patcher - Python DSL 代码生成器  
**交接日期**: 2026年2月1日  
**当前状态**: 基础架构完成，核心 Bug 修复中（40% 完成）

---

## 📖 项目背景

### 什么是这个项目？
将 Paradox Interactive 游戏（如 Stellaris）的脚本语言（PDXLang）转换为 Python 代码，方便 mod 开发者使用 Python 编写游戏逻辑。

### 为什么需要它？
- PDXLang 语法复杂，缺乏类型检查和 IDE 支持
- Python 有更好的开发工具、调试能力和可维护性
- 自动转换可以减少手写代码错误，提高开发效率

### 核心功能
```
PDXLang 脚本 → 解析 → AST → 代码生成 → Python 代码
```

**示例转换**:
```pdx
# PDXLang
add_modifier = {
    modifier = growth_bonus
    years = 10
}
```
→
```python
# Python
scope.add_modifier(modifier='growth_bonus', years=10)
```

---

## 🏗️ 架构概览

### 核心模块结构
```
src/synthetipy/
├── lexer.py              # 词法分析器（已完成）
├── parser.py             # 语法分析器（基础完成）
├── ast_nodes.py          # AST 节点定义（已完成）
├── exceptions.py         # 异常系统（已完成）
├── pdx_constants.py      # 常量定义（逐步淘汰中）
│
├── game_rules/           # 🔥 游戏规则（自动生成）
│   ├── identifiers.py    # 1044 triggers, 1026 effects 分类
│   ├── trigger_rules.py  # Trigger 使用格式
│   ├── effect_rules.py   # Effect 使用格式
│   ├── scope_rules.py    # Scope 定义
│   ├── modifier_rules.py # Modifier 定义
│   └── special_blocks.py # 特殊块（control_flow, random 等）
│
└── codegen/              # 🔥 代码生成器（重点工作区）
    ├── block_classifier.py       # 块类型识别
    ├── generators/
    │   ├── base.py              # 基础生成器
    │   ├── effect_blocks.py     # Effect 生成器（已重构✅）
    │   ├── trigger_blocks.py    # Trigger 生成器（待统一）
    │   ├── value_blocks.py      # Value 生成器（待统一）
    │   ├── control_flow.py      # 控制流（⚠️有 Bug）
    │   └── scope_operations.py  # Scope 操作
    │
    └── pdx_to_python.py         # 主入口

tools/
├── parse_game_docs.py           # 游戏文档解析器（已完成）
└── generate_python_rules.py    # Python 规则生成器（已完成）

tests/
├── test_effect_generator.py     # Effect 生成器测试（✅ 通过）
├── test_control_flow_bugs.py    # 控制流 Bug 测试（❌ 失败）
└── test_*.py                    # 其他测试套件
```

---

## 🎯 关键技术决策

### 1. 自动化游戏规则生成（核心创新）

**问题**: 手写的硬编码规则不准确，维护困难。

**解决方案**: 
1. 解析游戏官方文档 → JSON (`parse_game_docs.py`)
2. JSON → Python 模块 (`generate_python_rules.py`)

**成果**:
- 从游戏文档提取：1044 triggers, 1026 effects, 90 scopes, 40445 modifiers
- 自动分类：11 共享标识符, 1033 trigger 独占, 1015 effect 独占
- 包含使用格式（usage_format）：simple_value/comparison/block/alternatives

**关键文件**:
- `tools/parse_game_docs.py` - 解析器
- `tools/generate_python_rules.py` - 生成器
- `src/synthetipy/game_rules/*.py` - 生成的规则模块

### 2. 统一值格式化标准（最近完成）

**问题**: 之前的逻辑混淆了参数位置、键名和值类型，导致错误。

**错误示例**:
```python
# 错误：add_resource 不存在于游戏中
if k in RESOURCE_KEYS:
    args.insert(0, f"'{k}'")  # minerals 作为第一参数
    args.append(str(v))
```

**新标准** (`effect_blocks.py._format_value()`):
```python
def _format_value(self, value: Any) -> str:
    """只根据值类型判断是否加引号"""
    if isinstance(value, bool):
        return str(value)           # True/False 不加引号
    if isinstance(value, (int, float)):
        return str(value)           # 123, 3.14 不加引号
    if value in self.parent.parameters:
        return value                # $PARAM$ 不加引号
    # 默认加引号（游戏标识符）
    return repr(value)              # 'building_factory'
```

**修复**:
- ✅ 删除 PRIMARY_KEYS, RESOURCE_KEYS 硬编码
- ✅ 所有参数作为关键字参数
- ✅ 统一处理数字、布尔、宏参数、标识符

### 3. 占位符 → 异常转换

**问题**: 不支持的语法生成 `Block(X statements)` 占位符，导致代码不可运行。

**解决方案**:
```python
# exceptions.py
class UnsupportedFeatureError(SynthetipyError):
    """遇到不支持的 PDXLang 特性"""
    pass

# 使用
raise UnsupportedFeatureError(
    f"If/else block content generation not implemented: {len(statements)} statements"
)
```

**好处**: 清晰标记未实现功能，便于测试和调试。

---

## 🔍 当前工作状态

### 已完成 ✅

1. **基础架构**
   - 词法分析器、语法分析器、AST 定义
   - 异常系统（5 个异常类）
   - Block 类型识别（trigger/effect/value/nested_object）

2. **游戏规则系统**
   - 文档解析器（处理共享 Supported Scopes 等边缘情况）
   - Python 规则生成器（支持 usage 格式解析）
   - 7 个规则模块（1044 triggers, 1026 effects, etc.）

3. **Effect 生成器重构**
   - 删除硬编码规则（PRIMARY_KEYS/RESOURCE_KEYS）
   - 统一值格式化逻辑（_format_value）
   - 所有测试通过（test_effect_generator.py）

### 待修复 ⚠️

#### P0 - 阻塞功能（必须修复）
1. **If/Else 块内容丢失** (`control_flow.py`)
   - 现状: 抛出 UnsupportedFeatureError
   - 问题: 条件分支的内容未生成
   - 测试: `test_control_flow_bugs.py` → 失败

2. **Hidden 块处理**
   - hidden_trigger, hidden_effect 需要特殊处理
   - 建议: 转换为注释或特殊标记

3. **Switch 语句支持**
   - 现状: 未实现
   - 需要: 转换为 Python if/elif/else

4. **Python 关键字冲突**
   - `from`, `if` 等保留字需要重命名（from_）

#### P1 - 常见场景（影响较大）
5. **Random_list 结构** (`control_flow.py`)
   - 概率权重的 random 选择
   - 需要生成 `random.choices()` 代码

6. **特殊语法转换**
   - `trigger:` → 条件检查
   - `modifier:` → 修正查询
   - `event_target:` → 目标解析

7. **条件参数块 [[PARAM]]**
   - `[[SOME_PARAM]]` → `if SOME_PARAM:`
   - `[[!SOME_PARAM]]` → `if not SOME_PARAM:`

8. **Trigger/Value 生成器统一**
   - 迁移到 `_format_value()` 方法
   - 与 Effect 生成器保持一致

#### P2 - 增强功能（提升质量）
9. **游戏规则参数顺序优化**
   - 当前: 所有参数都是关键字参数
   - 改进: 根据 `params[0]` 提取第一个位置参数
   - 示例: `add_modifier('x', years=10)` 代替 `add_modifier(modifier='x', years=10)`

10. **引用解析接口实现**
    - `_try_resolve_reference()` 当前总是返回 None
    - 目标: `'building_xxx'` → `buildings.building_xxx`

---

## 🚀 快速上手指南

### 环境搭建
```bash
# 1. 克隆仓库
git clone <repo_url>
cd pdxlang_patcher

# 2. 创建虚拟环境
conda create -n synthetipy python=3.10
conda activate synthetipy

# 3. 安装依赖
pip install -r requirements.txt  # 如果有的话
```

### 运行测试
```bash
# 运行 Effect 生成器测试（✅ 应该全部通过）
python tests/test_effect_generator.py

# 运行控制流 Bug 测试（❌ 预期失败）
python tests/test_control_flow_bugs.py

# 运行所有测试
python -m pytest tests/
```

### 调试单个转换
```python
from src.synthetipy.lexer import Lexer
from src.synthetipy.parser import Parser
from src.synthetipy.codegen.pdx_to_python import PDXToPythonConverter

# 1. 准备 PDXLang 代码
pdx_code = """
add_modifier = {
    modifier = growth_bonus
    years = 10
}
"""

# 2. 词法分析
lexer = Lexer(pdx_code)
tokens = lexer.tokenize()

# 3. 语法分析
parser = Parser(tokens)
ast = parser.parse()

# 4. 代码生成
converter = PDXToPythonConverter(ast, indent=1, scope_name="scope")
python_code = converter.generate()
print(python_code)
```

### 重新生成游戏规则
```bash
# 如果游戏文档更新了
python tools/parse_game_docs.py
python tools/generate_python_rules.py
```

---

## 📚 关键文件详解

### `src/synthetipy/codegen/generators/effect_blocks.py`
**作用**: 生成 Effect 块的 Python 代码（如 `add_modifier`, `fire_event`）

**核心方法**:
- `generate_simple_effect(stmt)` - 简单赋值型 effect
- `generate_block_effect(stmt)` - 带参数块的 effect
- `_format_value(value)` - 统一值格式化（🔥 重要）
- `_try_resolve_reference(identifier)` - 引用解析（预留接口）

**最近修改**:
- 删除 PRIMARY_KEYS/RESOURCE_KEYS 硬编码
- 所有参数作为关键字参数
- 统一值格式化逻辑

**测试**: `tests/test_effect_generator.py`（✅ 全部通过）

---

### `src/synthetipy/codegen/generators/control_flow.py`
**作用**: 生成控制流代码（if/else, switch, random_list）

**⚠️ 已知问题**:
```python
def generate_if_statement(self, stmt: IfStatement) -> str:
    # 🐛 Bug: 条件块的内容未生成
    raise UnsupportedFeatureError(
        f"If/else block content generation not implemented: ..."
    )
```

**待修复**:
1. 生成 if/else 块的内容
2. 支持 switch 语句
3. 实现 random_list 结构

**测试**: `tests/test_control_flow_bugs.py`（❌ 失败）

---

### `src/synthetipy/codegen/block_classifier.py`
**作用**: 识别块的类型（trigger/effect/value/nested_object）

**核心逻辑**:
```python
if identifier in TRIGGER_KEYS:
    return 'trigger'
elif identifier in EFFECT_KEYS:
    return 'effect'
elif identifier in VALUE_KEYS:
    return 'value'
else:
    return 'nested_object'
```

**依赖**: 从 `game_rules` 导入 TRIGGER_KEYS (1044), EFFECT_KEYS (1026)

**最近修改**: 删除手写规则，使用自动生成的规则

---

### `src/synthetipy/game_rules/*.py`
**作用**: 游戏规则定义（自动生成，不要手动编辑）

**重要模块**:
- `identifiers.py` - SHARED_IDENTIFIERS, TRIGGER_EXCLUSIVE, EFFECT_EXCLUSIVE
- `effect_rules.py` - EFFECTS_BLOCK, EFFECTS_SIMPLE, EFFECTS_COMPARISON 等
- `trigger_rules.py` - TRIGGERS_BLOCK, TRIGGERS_SIMPLE, TRIGGERS_COMPARISON 等

**格式示例**:
```python
EFFECTS_BLOCK = {
    'add_modifier': {
        'usage_format': 'block',
        'params': [
            {'name': 'modifier', 'type': 'string', 'required': True},
            {'name': 'years', 'type': 'int'},
            {'name': 'days', 'type': 'int'}
        ],
        'supported_scopes': ['planet', 'country', 'pop'],
        'description': 'Adds a timed modifier to the scope.'
    }
}
```

**如何更新**: 运行 `python tools/generate_python_rules.py`

---

### `tools/parse_game_docs.py`
**作用**: 解析游戏官方文档，提取规则

**关键方法**:
- `parse_triggers()` - 提取 trigger 定义
- `parse_effects()` - 提取 effect 定义
- `parse_scopes()` - 提取 scope 定义
- `_parse_entry()` - 解析单个条目（名称、描述、usage、scopes）

**输出**: `codegen_rules/*.json` (triggers.json, effects.json, etc.)

**边缘情况处理**:
- 共享 Supported Scopes（多个条目共享一个 scopes 列表）
- 名称中包含 usage（如 `trigger = { ... }`）
- 等号后的 usage 说明

---

### `tools/generate_python_rules.py`
**作用**: 将 JSON 规则转换为 Python 模块

**核心类**:
- `UsageParser` - 解析 usage 字符串
  - `simple_value` - 直接赋值
  - `comparison` - 比较表达式
  - `block` - 带参数块
  - `alternatives` - 多种格式
- `PythonRulesGenerator` - 生成 Python 文件

**输出**: `src/synthetipy/game_rules/*.py` (7 个模块)

---

## 🐛 常见陷阱和注意事项

### 1. 不要手动编辑 `game_rules/*.py`
这些文件是自动生成的，修改会在重新生成时丢失。

**正确做法**: 修改 `tools/parse_game_docs.py` 或 `tools/generate_python_rules.py`，然后重新生成。

### 2. 值格式化必须使用 `_format_value()`
不要手动判断是否加引号，统一使用 `_format_value()` 方法。

**错误**:
```python
if isinstance(v, int):
    code = f"{k}={v}"  # ❌ 逻辑分散
else:
    code = f"{k}='{v}'"
```

**正确**:
```python
formatted = self._format_value(v)  # ✅ 统一接口
code = f"{k}={formatted}"
```

### 3. 测试先行
修改代码生成器之前，先写测试用例验证现有逻辑。

```bash
# 先运行测试确认当前状态
python tests/test_effect_generator.py

# 然后修改代码

# 最后再次运行测试验证
python tests/test_effect_generator.py
```

### 4. 占位符 → 异常
遇到不支持的语法，不要生成占位符，而是抛出异常。

**错误**:
```python
return "Block(X statements)"  # ❌ 无法运行
```

**正确**:
```python
raise UnsupportedFeatureError(
    f"Feature not implemented: {feature_name}"
)  # ✅ 清晰标记
```

### 5. 宏参数不加引号
宏参数（如 `$AMOUNT$`）在 Python 代码中应该是变量，不加引号。

```python
# PDXLang
add_minerals = $AMOUNT$

# Python (正确)
scope.add_minerals(AMOUNT)  # ✅ 变量

# Python (错误)
scope.add_minerals('AMOUNT')  # ❌ 字符串
```

---

## 📊 进度追踪

### 整体进度
```
████████░░░░░░░░░░░░ 40%

基础架构: 100% ✅
核心修复:  20% 🔄
规则集成:  10% ⏳
高级特性:   0% ⏳
```

### 详细清单
- [x] 词法分析器
- [x] 语法分析器
- [x] AST 定义
- [x] 异常系统
- [x] 游戏文档解析器
- [x] Python 规则生成器
- [x] Block 类型识别
- [x] Effect 生成器统一值格式化
- [ ] If/Else 块内容生成（P0 - 阻塞）
- [ ] Hidden 块处理（P0）
- [ ] Switch 语句（P0）
- [ ] Python 关键字冲突（P0）
- [ ] Random_list 结构（P1）
- [ ] 特殊语法转换（P1）
- [ ] 条件参数块（P1）
- [ ] Trigger/Value 统一格式化（P1）
- [ ] 游戏规则参数顺序优化（P2）
- [ ] 引用解析接口（P2）

---

## 🎯 下一步建议

### 立即着手（P0 任务）
1. **修复 If/Else 块内容丢失**
   - 文件: `src/synthetipy/codegen/generators/control_flow.py`
   - 方法: `generate_if_statement()`
   - 测试: `tests/test_control_flow_bugs.py`
   - 预期时间: 2-4 小时

2. **实现 Hidden 块处理**
   - 识别 `hidden_trigger`, `hidden_effect`
   - 转换为注释: `# Hidden trigger: ...`
   - 预期时间: 1-2 小时

3. **添加 Switch 语句支持**
   - 转换为 Python `if/elif/else`
   - 处理 `default` 分支
   - 预期时间: 2-3 小时

### 短期目标（1-2 周）
- 完成所有 P0 任务（阻塞功能修复）
- 完成 P1 任务中的高优先级部分（Random_list, 特殊语法）
- 确保核心测试套件通过率 > 90%

### 中期目标（1 个月）
- 完成所有 P1 任务
- 开始 P2 任务（游戏规则深度集成）
- 增加测试覆盖率
- 文档完善

---

## 📞 联系和资源

### 关键文档
- [架构设计](ARCHITECTURE.md) - 系统架构说明
- [实现指南](IMPLEMENTATION_GUIDE.md) - 实现细节
- [任务树](tasks_tree.md) - 任务清单
- [Bug 列表](bug.md) - 已知问题

### 参考资源
- Paradox 游戏官方文档（效果、触发器定义）
- Stellaris Wiki（游戏机制说明）
- Python AST 文档（代码生成参考）

### 调试技巧
```bash
# 打印 AST 结构
python -c "from src.synthetipy.parser import Parser; ..."

# 打印生成的代码
python example_usage.py

# 运行单个测试
python tests/test_effect_generator.py -v

# 查看游戏规则
python -c "from src.synthetipy.game_rules import EFFECTS_BLOCK; print(EFFECTS_BLOCK['add_modifier'])"
```

---

## 🎓 学习路径建议

### 第 1 天：环境搭建 + 运行测试
1. 搭建开发环境
2. 运行现有测试，了解哪些通过，哪些失败
3. 阅读 README.md 和本文档

### 第 2-3 天：理解架构
1. 阅读 `ARCHITECTURE.md`
2. 跟踪一个简单的转换流程（从 PDXLang → Python）
3. 理解 AST 节点结构（`ast_nodes.py`）

### 第 4-5 天：深入代码生成器
1. 研究 `effect_blocks.py` 的实现（已重构，代码质量高）
2. 对比 `trigger_blocks.py` 和 `value_blocks.py`（待统一）
3. 理解 `_format_value()` 的设计理念

### 第 6-7 天：修复第一个 Bug
1. 选择 P0 任务（建议从 If/Else 开始）
2. 写测试用例
3. 实现修复
4. 运行测试验证

### 第 2 周：深度工作
1. 完成 P0 任务
2. 开始 P1 任务
3. 熟悉游戏规则系统

---

## ✅ 验收标准

### 核心功能验收
- [ ] 所有 P0 Bug 修复完成
- [ ] 核心测试套件通过率 > 95%
- [ ] 能正确转换至少 100 个真实游戏文件

### 代码质量验收
- [ ] 所有生成器使用统一的 `_format_value()` 方法
- [ ] 不再有硬编码的游戏规则
- [ ] 占位符全部替换为异常

### 文档验收
- [ ] 所有公开方法有 docstring
- [ ] 关键决策有注释说明
- [ ] README 包含使用示例

---

## 🚨 紧急联系

如果遇到无法解决的问题：
1. 查看 `docs/bug.md` 中是否有记录
2. 检查 Git 提交历史中的相关修改
3. 运行测试定位问题范围
4. 查看异常堆栈追踪

**最后修改**: 2026年2月1日  
**文档版本**: v1.0  
**状态**: 当前有效
