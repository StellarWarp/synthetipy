# Python 代码生成修复任务树

## 📋 总览
当前状态：基础架构完成，核心 bug 修复中

---

## 🔧 1. 核心 Bug 修复

### 1.1 控制流问题
- [ ] **If/Else 块内容丢失**
  - [ ] 修复 control_flow.py 中的块内容提取
  - [ ] 确保 if/else_if/else 的所有语句都被正确生成
  - [ ] 测试：test_control_flow_bugs.py

- [ ] **Switch 语句支持**
  - [ ] 实现 switch 语句的代码生成
  - [ ] 处理 default 分支
  - [ ] 转换为 Python if/elif/else
  - [ ] 测试：test_control_flow_bugs.py

### 1.2 特殊块处理
- [ ] **Hidden 块**
  - [ ] hidden_trigger → 注释或特殊标记
  - [ ] hidden_effect → 注释或特殊标记
  - [ ] 测试：test_control_flow_bugs.py

- [ ] **Random_list 结构**
  - [ ] 解析概率权重
  - [ ] 生成 random.choices() 或自定义函数
  - [ ] 处理嵌套 random_list
  - [ ] 测试：test_random_list_bugs.py

### 1.3 特殊语法
- [ ] **Prefix 语法转换**
  - [ ] trigger: → .trigger() 或条件检查
  - [ ] modifier: → .modifier() 或修正查询
  - [ ] event_target: → .event_target() 或目标解析
  - [ ] 测试：test_special_syntax_bugs.py

- [ ] **条件参数块 [[PARAM]]**
  - [ ] 解析 [[PARAM]] 语法
  - [ ] 生成条件代码（if PARAM: ...）
  - [ ] 处理 [[!PARAM]] 否定条件
  - [ ] 测试：test_conditional_param_bugs.py

### 1.4 边缘情况
- [ ] **Python 关键字冲突**
  - [ ] from → from_
  - [ ] 其他保留字处理
  - [ ] 测试：test_keyword_conflicts.py

- [ ] **数字键处理**
  - [ ] random_list 中的数字权重键
  - [ ] 转换为合法的 Python 标识符
  - [ ] 测试：test_random_list_bugs.py

---

## 🎯 2. 基于游戏规则的增强

### 2.1 Effect 生成器
- [x] ~~删除 PRIMARY_KEYS/RESOURCE_KEYS 硬编码~~
- [x] ~~统一值格式化（_format_value）~~
- [ ] **利用游戏规则优化参数顺序**
  - [ ] 读取 EFFECTS_BLOCK/EFFECTS_SIMPLE 中的 params
  - [ ] 根据 params[0] 确定第一个位置参数
  - [ ] 支持 alternatives 格式（simple_value vs block）
- [ ] **实现引用解析接口**
  - [ ] _try_resolve_reference() 实现
  - [ ] 'building_xxx' → buildings.building_xxx
  - [ ] 查询游戏数据库验证引用存在

### 2.2 Trigger 生成器
- [ ] **统一值格式化逻辑**
  - [ ] 迁移到 _format_value() 方法
  - [ ] 处理宏参数不加引号
  - [ ] 处理数字/布尔值
- [ ] **利用游戏规则**
  - [ ] 读取 TRIGGERS_BLOCK/TRIGGERS_SIMPLE
  - [ ] 根据 usage_format 生成正确代码
  - [ ] 支持 comparison/block/simple_value 格式

### 2.3 Value 生成器
- [ ] **统一值格式化逻辑**
  - [ ] 迁移到 _format_value() 方法
  - [ ] 确保数字不加引号
- [ ] **算术表达式优化**
  - [ ] base/add/multiply 转换为 Python 运算
  - [ ] 利用 game_rules.MODIFIERS

---

## 🔄 3. 代码质量改进

### 3.1 一致性优化
- [ ] **宏参数处理统一**
  - [ ] 所有生成器使用相同的 _extract_value() 逻辑
  - [ ] 确保 $PARAM$ 在所有上下文中一致处理
  - [ ] 验证 is_simple 检查在所有地方正确工作

- [ ] **错误处理标准化**
  - [ ] 所有占位符都抛出 UnsupportedFeatureError
  - [ ] 带上下文信息（节点类型、语句数量等）
  - [ ] 统一错误消息格式

### 3.2 测试覆盖
- [ ] **现有测试更新**
  - [ ] test_effect_generator.py - 验证新逻辑
  - [ ] test_trigger_generator.py - 验证新逻辑
  - [ ] test_value_generator.py - 验证新逻辑

- [ ] **新测试用例**
  - [ ] 游戏规则集成测试
  - [ ] 引用解析测试
  - [ ] 边缘情况覆盖

---

## 📦 4. 游戏规则集成

### 4.1 规则查询接口
- [ ] **创建统一的规则查询类**
  ```python
  class GameRulesRegistry:
      def get_effect_info(name: str) -> Dict
      def get_trigger_info(name: str) -> Dict
      def get_param_order(name: str, type: str) -> List[str]
      def is_block_format(name: str, type: str) -> bool
  ```

### 4.2 动态代码生成
- [ ] **根据 usage_format 生成代码**
  - [ ] 'simple_value' → 直接赋值
  - [ ] 'comparison' → 比较表达式
  - [ ] 'block' → 带参数块
  - [ ] 'alternatives' → 多种格式支持

- [ ] **参数验证**
  - [ ] 检查必需参数
  - [ ] 类型提示（基于 params.type）
  - [ ] 默认值处理（default）

---

## 🚀 5. 高级特性（可选）

### 5.1 类型注解生成
- [ ] 根据游戏规则生成类型提示
- [ ] scope 参数的精确类型（Planet/Country/etc.）
- [ ] 返回值类型推断

### 5.2 文档生成
- [ ] 从游戏规则的 description 生成 docstring
- [ ] 参数说明（基于 params）
- [ ] 示例代码生成

### 5.3 性能优化
- [ ] 缓存游戏规则查询
- [ ] 延迟加载规则模块
- [ ] 代码生成性能分析

---

## 📊 优先级排序

### P0 - 必须修复（阻塞功能）
1. If/Else 块内容丢失
2. Hidden 块处理
3. Switch 语句支持
4. Python 关键字冲突

### P1 - 重要（影响常见场景）
5. Random_list 结构
6. 特殊语法转换（trigger:/modifier:）
7. 条件参数块 [[PARAM]]
8. Trigger/Value 生成器统一值格式化

### P2 - 增强（提升质量）
9. 游戏规则参数顺序优化
10. 引用解析接口实现
11. 宏参数处理统一
12. 测试覆盖完善

### P3 - 可选（锦上添花）
13. 类型注解生成
14. 文档生成
15. 性能优化

---

## 📝 当前进度

```
总体进度: ████████░░░░░░░░░░░░ 40%

✅ 基础架构 (100%)
  ├─ 异常系统
  ├─ 游戏规则解析
  ├─ Python 规则生成
  └─ Block classifier 更新

🔄 核心修复 (20%)
  ├─ Effect 生成器统一值格式化 ✅
  ├─ 测试用例创建 ✅
  └─ 待修复: 8 个核心 bug

⏳ 规则集成 (10%)
  └─ 基础规则已生成，待深度集成

⏳ 高级特性 (0%)
  └─ 尚未开始
```

---

## 🎯 下一步行动

建议优先处理顺序：
1. 修复 If/Else 块内容丢失（最高优先级）
2. 实现 Hidden 块处理
3. 添加 Switch 语句支持
4. 修复 Python 关键字冲突
5. 统一 Trigger/Value 生成器的值格式化
6. 实现游戏规则参数顺序优化
