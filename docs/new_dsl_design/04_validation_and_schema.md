# Schema 与校验系统

Schema 在 Synthetipy 中扮演 **文档查询** 和 **编译时检查 (Linter)** 的角色，而非强制的继承基类。

## 生成示例

生成的 Schema 模块将包含详细的类型注解，既可以用作文档，也可以被 IDE 用于自动补全（如果用户选择继承它）。

```python
# synthetipy/generated/buildings/schema.py

class building_schema:
    """建筑对象的标准结构定义"""
    base_buildtime: int
    category: str
    prerequisites: list['Technology']
    
    # 嵌套结构定义
    class resources:
        category: str
        
        class cost:
            minerals: int
            energy: int
            # ... 其他动态生成的资源 ...
            
        class upkeep:
            energy: int
            # ...
```

## 1. Schema 的角色

生成的 Schema 文件（如 `synthetipy/generated/buildings/schema.py`）包含了所有游戏内置属性的定义。

生成的 Schema 文件（如 `synthetipy/generated/buildings/schema.py`）包含了所有游戏内置属性的定义。

它用于：
1.  **查询**：开发者可以随时打印或查看 Schema 类来确认某个块里能填什么。
2.  **Linting**：编译器在后台通过对比用户代码和 Schema，发现拼写错误或非法属性。

```python
# 错误示例
class cost:
    minerlas = 100  # 拼写错误
```

**编译结果**：
> Warning: Property 'minerlas' is not defined in schema 'cost'. Did you mean 'minerals'?

## 2. 逃生舱：自定义属性 (@allow_unknown)

对于 Mod 新增的资源或 Schema 尚未覆盖的属性，使用装饰器屏蔽警告。

```python
from synthetipy import allow_unknown

class building_supercomputer(Building):
    
    class resources:
        
        # 显式标记：此块包含自定义属性，跳过 Schema 检查
        @allow_unknown
        class cost:
            minerals = 100
            # 自定义资源，不会触发警告
            dark_matter_shards = 5
```
