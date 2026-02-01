# Synthetipy DSL 设计总览

Synthetipy 旨在提供一种**原生的 Python 体验**来编写 Paradox 脚本。

## 核心理念

1.  **原生结构 (Native Structure)**
    拒绝复杂的构建器模式（Builder Pattern）。
    直接利用 Python 的 **类 (Class)**、**内联类 (Inline Class)** 和 **函数 (Function)** 来映射 PDX 的字典树结构。

2.  **代码生成优先 (Codegen First)**
    核心库依赖 `synthetipy gen` 生成的 Python 模块。
    这些生成的模块提供了基础类（`Building`, `Technology`）和类型定义。

3.  **可选的约束 (Optional Constraints)**
    Schema（模式）文件存在，但主要用于**文档查询**和**编译时检查 (Linting)**。
    不强制要求用户代码继承 Schema 类。

4.  **智能转换 (Smart Transpilation)**
    利用 Python AST 分析，将 Python 的 `with` 语句、变量赋值等习惯用法智能转换为 PDX 的作用域切换逻辑。
