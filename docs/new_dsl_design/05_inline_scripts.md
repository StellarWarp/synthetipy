# 内联脚本封装 (Inline Scripts)

直接在 Python 对象中展开 PDX 的 `inline_script` 会导致代码冗余且难以阅读。Synthetipy 采用封装引用的策略。

## 1. 语法设计

使用 `meta.inline_script` 创建引用对象，并赋值给具名变量。

```python
from synthetipy import meta


# 变量名 'ai_weight_logic' 仅用于 Python 端引用，编译时会被转换为 inline_script = { ... }
ai_weight_logic = meta.inline_script(
    script="districts/ai_research_extra_weighting",
    AMOUNT=10
)

# 2. 访问参数
# 在生成器或其他逻辑中可以轻松访问
# print(ai_weight_logic.params['AMOUNT'])
```

## 2. 编译输出

上述代码将被编译为：

```pdx
# ...
inline_script = {
    script = districts/ai_research_extra_weighting
    AMOUNT = 10
}

```
