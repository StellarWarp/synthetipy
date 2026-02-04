# Parser 升级与语义化设计文档 (V3)

本文档描述了 AST 归一化 (Normalization) 的设计思路。目标是将原始的 Key-Value 解析树（基于 `PropertyNode`）转换为语义明确的逻辑树，以区分控制流、Scope 切换、函数调用等核心游戏逻辑。

## 1. 核心设计原则

*   **Semantic Lifting**: 在 AST 阶段就完成“此节点是 Effect 还是 Scope”的判断，而不是留给 Code Generator。
*   **Context Inference**: 使用启发式规则（Heuristics）和Use-Def分析推断当前代码块的 **Context** (Effect/Trigger) 和 **Scope** (This Type)。
*   **Unified Structure**: 将通过 Block 进行结构控制的语句（If, Scope, Iterator）统一抽象，将所有执行指令（Inbuilt/Script）统一抽象。

## 2. AST 节点数据结构 (AST Refinement)

原本通用的 `PropertyNode` (Key=Value) 将被归一化为以下几种具有具体语义的节点：

### 2.1 BlockStatementNode (结构化语句)

统一表示所有带有 Body Block 的结构化语句，包括控制流、Scope 切换、迭代器和语境切换。

```python
class BlockStatementNode(ASTNode):
    """统一块语句节点
    
    涵盖:
    1. Control Flow: if = { ... }, while = { ... }
    2. Scope Switch: owner = { ... }, event_target:x = { ... }
    3. Iterator: every_owned_planet = { limit={...} ... }
    4. Context Switch: hidden_trigger = { ... } (强制内部为 Trigger Context)
    """
    def __init__(self, 
                 name: Union[str, 'IdentifierExpressionNode'], # 节点标识符 (e.g., 'if', 'owner', 'event_target:XX')
                 body: BlockNode,                              # 执行体
                 selectors: Optional[BlockNode] = None,        # 筛选条件/参数 (e.g., 'limit={...}')
                 statement_type: str = 'scope'                 # 'control_flow' | 'scope' | 'context' | 'iterator'
                 ):
        self.name = name
        self.body = body
        self.selectors = selectors
        self.statement_type = statement_type
        
        # --- Inference Metadata (归一化阶段注入) ---
        self.input_scope: Optional[str] = None   # 当前节点所需的 This Scope (e.g. 'Country')
        self.output_scope: Optional[str] = None  # 内部 Body 的 This Scope (e.g. 'Planet')
        self.context_type: Optional[str] = None  # 内部 Body 的 Context (Trigger/Effect)
```

### 2.2 CallNode (指令调用)

统一表示 **Effect** (动作) 和 **Trigger** (条件检查) 的调用。
**注意**: 此节点不用于 Script Value (右值调用)。

```python
class CallNode(ASTNode):
    """Effect 或 Trigger 调用
    
    涵盖:
    1. Block Parameters: spawn_pirates = { type = x size = y } (value 为 BlockNode)
    2. Comparison Trigger: pop_amount > 10 (value 为 ComparisonNode)
    3. Boolean Trigger: is_ai = yes (value 为 ComparisonNode[is_ai = yes])
    """
    def __init__(self, 
                 name: str, 
                 value: Union[ASTNode, BlockNode], # 参数体：可能是 Block，也可能是 ComparisonNode
                 call_type: str,   # 'effect' | 'trigger' (由 Context 决定)
                 is_inbuilt: bool  # 是否为内建指令 (基于 ALL_EFFECTS/ALL_TRIGGERS)
                 ):
        self.name = name
        self.value = value  
        self.call_type = call_type
        self.is_inbuilt = is_inbuilt
```

>  为了统一简单调用和复杂调用，我们将 `pop_amount > 10` 和 `is_ai = yes` 统一封装进 `CallNode`。
> *   对于 `pop_amount > 10`: `CallNode(name='pop_amount', value=ComparisonNode(left=pop_amount, op=>, right=10))`
> *   对于 `is_ai = yes`: `CallNode(name='is_ai', value=ComparisonNode(left=is_ai, op==, right=yes))`
> *   对于 `spawn_pirates = { ... }`: `CallNode(name='spawn_pirates', value=BlockNode(...))`

这样，Generator 只需处理 `CallNode` 这一种逻辑单元，根据 `value` 类型决定生成代码的格式。

## 3. 归一化策略 (Normalization Strategy)

归一化过程在 Parse 之后进行，采用两遍扫描 (Two-Pass Analysis)。

## 2. Phase 1: Context Inference (上下文推断)

由于缺乏明确的顶层关键字 (如 `effect = {}`)，我们需要通过内容推断来确定每个 Block 的 Context (Trigger vs Effect)。

### 2.1 初始化 (Initialization)

Context 和 Scope 的初始状态可用外部配置决定。

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

3.  **Inference (推断)**:
    *   **Case A**: 
        *   **Case A.1** 当前是 Object，发现了是一个 Exclusive Effect 关键字 -> 推断当前 Block 为 **Effect** 入口。
        *   **Case A.2** 当前是 Object，发现了一个**Effect/Trigger**公用关键字 -> 设定为待定状态
            *   如果是控制流关键字 (e.g. `if = { ... }`) -> 进入子块继续推断
                *   子块内发现 Exclusive Effect 关键字 -> 为推断之前的待定状态赋为 Effect 入口
            *   否则继续扫描同级关键字
    *   **Case B**: 当前是 Effect，发现了 Exclusive Trigger 关键字。抛出异常或警告。
    *   如果在 `Inherited Context` 下发现了互斥关键字 (Exclusive Keywords)，抛出异常或警告。

### Phase 2: Node Transformation (结构转换)

在已知 Context 的前提下，自顶向下遍历并转换节点。

**Input**: `PropertyNode(key, value)` or `ComparisonNode(left, op, right)`

**Logic**:

1.  **Check Hardcoded Structures**:
    *   Key in `['if', 'while','else_if', 'else']` -> **`BlockStatementNode(type='control_flow')`**
    *   Key in `ITERATOR_LIST` (e.g. `every_owned_planet`) -> **`BlockStatementNode(type='iterator')`**
        *   提取内部的 `limit` 属性作为 `selectors`。

2.  **Check Scope Switch**:
    *   Key in `SCOPES_IDENTIFIERS` (e.g. `owner`) -> **`BlockStatementNode(type='scope')`**
        *   (*Constraint*: Value 必须是 Block。如果是 `set_owner = root`，这是 Effect Call，见下文)。

3.  **Check Call (Default Fallback for Keyword Match)**:
    *   如果 Key 是已知的 Effect 或 Trigger 关键字：
        *   转换为 **`CallNode`**。
        *   `call_type` = Current Context (Effect/Trigger)。
        *   Wrap Value:
            *   如果 Value 是 Block -> 保持 Block。
            *   如果 Value 是 ComparisonNode -> 保持 ComparisonNode。
            *   如果 Value 是 Literal -> 转换为 `ComparisonNode(left=Key, op==, right=Literal)`。

### Phase 3: Scope Inference (Reverse Analysis)

利用 `CallNode` 中的内建指令需求，反向推断 Block 入口的 Scope 类型。

1.  初始化 Current Scope 为 `Unknown` (Set of all scopes)。
2.  遍历 Block 内所有 `CallNode` (Inbuilt only)：
    *   获取指令的 `SupportedScopes`。
    *   CurrentScope = CurrentScope ∩ SupportedScope （SupportedScope不为 any）
3.  遍历 `BlockStatementNode` (Scopes)：
    *   有 Scope 切换
        *   获取 Scope 切换的 `InputScope` 要求。
        *   CurrentScope = CurrentScope ∩ InputScope。
        *   子 Block 的 Scope 无需推测，因为 Scope 切换已明确指定。
    *   没有 Scope 切换
        *   先 CurrentScope = CurrentScope ∩ SupportedScope （SupportedScope不为 any）
        *   进入子Block继续递归推断。


## 4. 总结

新的 AST 结构清晰地区分了“结构”与“指令”：
*   **结构 (Statement)**: 负责改变流程、Scope 或 Context。
*   **指令 (Call)**: 负责执行具体逻辑（原子操作）。简单赋值 (`= yes`) 和 复杂赋值 (`= { ... }`) 被统一。

这将极大地简化后续的 Code Generation 以及 IntelliSense/Validation 逻辑。
