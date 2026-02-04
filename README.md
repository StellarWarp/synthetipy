# PDXLang Patcher

**为 Stellaris Mod 开发提供类似编译器的 Python 工具链**

---

## 项目目标

将 Stellaris Mod 开发从**文本操作**升级到**元编程**，让你可以直接用 Python 编写 Paradox 脚本。


当前架构如下

Paradox 脚本  ←→  AST 

AST  ←→  Python DSL 

目前（Paradox 脚本  ←→  AST）部分已经完成 AST 到 Python DSL 的转换正在修复各类bug，其主要用于提供相关的语言服务（如自动补全、跳转定义等）

Python DSL 到 Paradox 脚本 的转换正在设计中，目标是让用户可以用 Pythonic 的方式编写 Stellaris Mod 脚本，然后生成符合 Stellaris 语法的脚本文件。


--- 

