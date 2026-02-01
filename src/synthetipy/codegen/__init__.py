"""
代码生成模块 (Code Generation)

将 PDX AST 转换为目标代码（Python DSL、Schema 等）

模块结构：
- block_classifier.py       - 块类型识别（trigger/effect/value/nested_object）
- python_generator.py       - Python DSL 主生成器
- formatters.py             - 值格式化和标识符处理
- trigger_generator.py      - Trigger 方法生成（逻辑表达式转换）
- effect_generator.py       - Effect 方法生成（命令式语句转换）
- value_generator.py        - Value 方法生成（算术表达式转换）
- inline_script_generator.py - InlineScript 生成器（读取并展开脚本）
- scope_analyzer.py         - 作用域分析和类型推断

使用示例：
    from synthetipy.codegen import generate_python_code
    
    ast = parse(pdx_code)
    python_code = generate_python_code(ast, "common/buildings/test.txt")
"""

from .python_generator import PythonCodeGenerator, generate_python_code
from .block_classifier import BlockClassifier, get_file_type
from .inline_script_generator import (
    InlineScriptGenerator,
    InlineScriptContext,
    generate_inline_script,
    generate_from_inline_script_node,
)

__all__ = [
    'PythonCodeGenerator',
    'generate_python_code',
    'BlockClassifier',
    'get_file_type',
    'InlineScriptGenerator',
    'InlineScriptContext',
    'generate_inline_script',
    'generate_from_inline_script_node',
]
