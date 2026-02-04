# AST Normalization Design (V4) - Strict Context & Structure

本文档描述了将原始 AST 转换为语义化 AST (Normalized AST) 的核心设计。与之前的版本不同，本设计基于 **Strict Determinism (严格确定性)** 原则：假设合法的 Paradox 脚本不会在同一 Block 内混用互斥的 Trigger/Effect 语句。

## 1. 核心流程概览

归一化过程分为三个阶段：
1.  **Context Initialization & Propagation**: 基于配置和关键字约束，严格确定每个 Block 的 `ContextType` (Trigger/Effect/Object) 和 `ScopeType`。
2.  **Structural Lifting**: 基于确定的 Context，将 `PropertyNode` 转换为 `BlockStatementNode` (结构) 或 `CallNode` (指令)。
3.  **Scope Refinement**: 基于内建指令的 Scope 约束，反向收缩推断 `ScopeType`。

## 2. Phase 1: Context Inference (上下文推断)

### 2.1 初始化 (Initialization)

Context 和 SCope 的初始状态由外部配置决定，而非猜测。

*   **输入**: 文件路径, 顶层 Key (如果是 Object 定义)。
*   **配置映射 (Configuration)**:
    *   `common/scripted_effects/*.txt` -> Root Context = `Effect`, Root Scope = `Any`
    *   `common/scripted_triggers/*.txt` -> Root Context = `Trigger`, Root Scope = `Any`
    *   `events/*.txt`:
        *   `country_event` -> Root Context = `Object` (Def), Root Scope = `Country`
        *   `planet_event` -> Root Context = `Object` (Def), Root Scope = `Planet`
    *   **默认回退**: Root Context = `Object`, Root Scope = `Any`

### 2.2 传播规则 (Propagation Rules)

在遍历 Block 时，Context 根据以下规则严格传播或切换：

1.  **Inheritance (继承)**:
    *   默认情况下，子 Block 继承父 Block 的 Context。
    *   Example: 在 Effect Block 中的 `if = { ... }`，其 Body 继承为 Effect Context。

2.  **Switching (切换)**:
    *   **Context Switchers** (硬编码):
        *   `limit = { ... }` -> 切换为 **Trigger**。
        *   `potential = { ... }` / `allow = { ... }` -> 切换为 **Trigger**。
        *   `trigger = { ... }` / `hidden_trigger = { ... }` -> 切换为 **Trigger**。
        *   `effect = { ... }` / `hidden_effect = { ... }` -> 切换为 **Effect**。
        *   `immediate = { ... }` -> 切换为 **Effect** (Common in events).

3.  **Validation (校验 / 强推断)**:
    *   如果在 `Inherited Context` 下发现了互斥关键字 (Exclusive Keywords)，进行校验：
    *   **Case A**: 当前是 Unknown/Object，发现了是一个 Exclusive Effect 关键字 -> 锁定当前及子 Block 为 **Effect**。
    *   **Case B**: 当前是 Effect，发现了 Exclusive Trigger 关键字 -> **Error/Warning** (除非被包裹在隐式的 Trigger 容器中)。

## 3. Phase 2: Structural Lifting (结构提升)

在 Context 确定的前提下，将 `PropertyNode(Key, Value)` 转换为语义节点。

### 3.1 节点类型定义

#### BlockStatementNode
```python
class BlockStatementNode(ASTNode):
    """
    statement_type:
      - 'control_flow': if, while (不改 Scope/Context)
      - 'scope': owner, from, event_target:x (改 Scope, 继承 Context)
      - 'context': hidden_trigger, limit (改 Context, 继承 Scope)
      - 'iterator': every_owned_planet (改 Scope + 副作用)
    """
    name: str
    body: BlockNode
    selectors: Optional[BlockNode] # from limit={...} or if-condition
    statement_type: str
```

#### CallNode
```python
class CallNode(ASTNode):
    """
    call_type: 'effect' | 'trigger'
    value: ComparisonNode (Simple) | BlockNode (Complex Args)
    """
    name: str
    value: Union[ComparisonNode, BlockNode]
    call_type: str
    is_inbuilt: bool
```

### 3.2 转换逻辑 (Transformation Logic)

**Input**: `node = PropertyNode(key, value)`

1.  **Check Hardcoded Control**:
    *   `if`, `while` -> **BlockStatementNode(type='control_flow')**.
    *   `hidden_trigger`, `trigger`, `limit` -> **BlockStatementNode(type='context')**.

2.  **Check Iterator**:
    *   Key 在 `ITERATOR_LIST` (e.g., `every_owned_planet`) -> **BlockStatementNode(type='iterator')**.
    *   Action: 提取内部的 `limit` 属性作为 `selectors`。

3.  **Check Scope Switch**:
    *   Key 在 `ALL_SCOPES` 中 -> **BlockStatementNode(type='scope')**.
    *   **Constraint**: Value 必须是 Block。
    *   (*Scope Inference*: 标记 input_scope 要求，推断 output_scope)。

4.  **Check Function Call (CallNode)**:
    *   **Condition**: 不是上述结构，且 (Key in `ALL_EFFECTS` or `ALL_TRIGGERS` or 无法识别但符合调用特征)。
    *   **Type Determination**: 严格使用当前的 `ContextType`。
        *   如果 Context 是 **Effect** -> Treat as Effect Call.
        *   如果 Context 是 **Trigger** -> Treat as Trigger Call.
    *   **Value Normalization**:
        *   `key = { ... }` -> `value` is BlockNode.
        *   `key = x` -> `value` wapped as `ComparisonNode(key, ==, x)`.
        *   `key > x` -> `value` kept as `ComparisonNode`.

## 4. Phase 3: Scope Inference (Type Constraining)

基于 Use-Def 分析反向推断 `Scope=Any` 的具体类型。

*   **Workflow**:
    1.  初始化 Scope 为 `ConfiguredRoot` (e.g. Country) 或 `Any`.
    2.  遇到 **CallNode (Inbuilt)**:
        *   查表获取 `SupportedScopes` (e.g. `add_minerals` requires `Country`).
        *   Narrowing: `CurrentScope = CurrentScope & SupportedScopes`.
    3.  遇到 **BlockStatementNode (Scope/Iterator)**:
        *   查表获取 `InputScope` (e.g. `every_owned_planet` requires `Country`).
        *   Narrowing: `CurrentScope = CurrentScope & InputScope`.
        *   Transform: 计算子配置的 `OutputScope`, 递归处理 Body。
    4.  遇到 **BlockStatementNode (Context/Control)**:
        *   Scope 不变，递归处理 Body。

---

## 5. 示例流程 (Example Walkthrough)

**Source**:
```pdx
# In common/scripted_effects/my_effect.txt
my_scripted_Effect = {
    every_owned_planet = {
        limit = { is_colony = yes }
        add_building = building_foundry
    }
}
```

**Step 1: Init**: 
*   File path matches `scripted_effects` -> Root Context = `Effect`, Root Scope = `Any`.

**Step 2: Parse & Normalize**:
1.  `my_scripted_Effect = { ... }`
    *   Top-level Object Definition. (Context=Effect)
2.  `every_owned_planet = { ... }`
    *   Detected as `ITERATOR`.
    *   Context = Effect (Inherited).
    *   InputScope Requirement = `Country` -> **Refine Root Scope to Country**.
    *   OutputScope = `Planet`.
    *   Transform to **BlockStatementNode(type='iterator', input='Country', output='Planet')**.
3.  Inside `every_owned_planet`:
    *   `limit = { ... }` -> Extracted as Selector. Context forced to **Trigger**.
        *   `is_colony = yes` -> **CallNode(type='trigger', is_inbuilt=True)**.
    *   `add_building = ...` -> Remainder. Context = Effect.
        *   Detected as `Inbuilt Call`.
        *   Transform to **CallNode(type='effect', name='add_building')**.
        *   SupportedScope = `Planet` -> Consistent with current `Planet` scope.

**Result AST**:
```
Object(Context=Effect, Scope=Country)
└── BlockStatementNode(type='iterator', name='every_owned_planet', Scope=Planet)
    ├── selectors (Context=Trigger):
    │   └── CallNode(name='is_colony', type='trigger')
    └── body (Context=Effect):
        └── CallNode(name='add_building', type='effect')
```
