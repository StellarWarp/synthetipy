"""
Value 方法生成器

将 PDX value 块转换为 Python 算术表达式函数
返回 float 类型的数值计算

PDX Value 语法:
- base = 数值          -> result = 数值
- set = value:xxx      -> result = xxx(scope)
- add = 数值           -> result += 数值
- subtract = 数值      -> result -= 数值
- multiply = 数值      -> result *= 数值
- mult = value:xxx     -> result *= xxx(scope)
- divide = 数值        -> result /= 数值
- modifier = { ... }   -> if 条件: result += ...
- complex_trigger_modifier = { ... }
- value:xxx|PARAM|val| -> 带参数的 value 引用
"""

from typing import List, Optional, Tuple, Dict
from ..ast_nodes import *
from .formatters import Formatter
from .macro_parameter_utils import (
    MacroParameterCollector,
    ParameterTypeInferencer,
    generate_function_signature,
    generate_pdx_block
)
from .runtime_deps import get_decorator_for_type
from ..pdx_constants import safe_identifier


class ValueGenerator:
    """Value 方法生成器 - 生成返回 float 的函数"""
    
    # 算术操作映射
    ARITHMETIC_OPS = {
        'add': '+=',
        'subtract': '-=',
        'multiply': '*=',
        'mult': '*=',
        'divide': '/=',
        'set': '=',
        'base': '=',
    }
    
    def __init__(self):
        self.indent_level = 0
        self.lines: List[str] = []
        self.scope_var = "scope"
        self.parameters = {}  # 收集的宏参数

    
    def generate(self, name: str, block: BlockNode, scope_param: str = "scope", add_decorator: bool = True) -> List[str]:
        """
        生成 value 计算函数
        
        Args:
            name: 函数名
            block: value 块节点
            scope_param: 作用域参数
            add_decorator: 是否添加装饰器（顶层函数需要，类方法不需要）
        
        Returns:
            生成的代码行列表
        """
        self.lines = []
        self.indent_level = 0
        self.scope_var = scope_param
        
        # 1. 收集宏参数
        collector = MacroParameterCollector()
        self.parameters = collector.collect(block)
        # 保留 collector 引用，供生成时查询 macro_lefts
        self.collector = collector
        
        # 2. 推断参数类型
        ParameterTypeInferencer.infer_all(self.parameters)
        
        # 3. 生成装饰器和函数签名
        if add_decorator:
            decorator = get_decorator_for_type('value')
            if decorator:
                self._add_line(decorator)
        
        if self.parameters:
            signature = generate_function_signature(name, self.parameters, 'float', scope_param)
            self._add_line(signature)
        else:
            self._add_line(f"def {name}({scope_param}) -> float:")
        
        self._indent()
        
        # 4. 生成方法体
        if not block.statements:
            self._add_line("return 0.0")
        elif self.has_complex_params:
            # 复杂参数 - 使用 meta.pdx()
            self._generate_pdx_value(block)
        else:
            # 简单参数 - 直接生成
            self._generate_value_body(block)
        
        self._dedent()
        return self.lines
    
    def _generate_pdx_value(self, block: BlockNode):
        """生成使用 meta.pdx() 的复杂 value"""
        # 重新序列化 PDX 代码
        pdx_template = self._serialize_block_to_pdx(block)
        
        # 生成 meta.pdx() 调用
        pdx_lines = generate_pdx_block(pdx_template, self.parameters, 0)
        for line in pdx_lines:
            self._add_line(line)
    
    def _serialize_block_to_pdx(self, block: BlockNode) -> str:
        """将 AST 块序列化回 PDX 代码"""
        lines = []
        for stmt in block.statements:
            lines.append(self._serialize_statement(stmt))
        return '\n'.join(lines)
    
    def _serialize_statement(self, stmt: ASTNode, indent: int = 0) -> str:
        """序列化单个语句为 PDX"""
        indent_str = "    " * indent
        
        if isinstance(stmt, PropertyNode):
            key = str(stmt.key)
            value = self._serialize_value(stmt.value)
            
            if isinstance(stmt.value, BlockNode):
                # 块值
                block_lines = [f"{indent_str}{key} = {{"]
                for sub_stmt in stmt.value.statements:
                    block_lines.append(self._serialize_statement(sub_stmt, indent + 1))
                block_lines.append(f"{indent_str}}}")
                return '\n'.join(block_lines)
            else:
                # 简单值
                return f"{indent_str}{key} = {value}"
        
        elif isinstance(stmt, ComparisonNode):
            left = stmt.left if isinstance(stmt.left, str) else str(stmt.left)
            right = self._serialize_value(stmt.right)
            return f"{indent_str}{left} {stmt.operator} {right}"
        
        return f"{indent_str}# TODO: {type(stmt).__name__}"
    
    def _serialize_value(self, value: ASTNode) -> str:
        """序列化值节点为 PDX"""
        if isinstance(value, LiteralNode):
            return str(value.value)
        elif isinstance(value, IdentifierExpressionNode):
            return value.expression
        elif isinstance(value, BlockNode):
            return "{ ... }"
        else:
            return str(value)
    
    def _generate_value_body(self, block: BlockNode):
        """生成 value 方法体"""
        # 初始化结果变量
        self._add_line("result = 0.0")
        
        for stmt in block.statements:
            if isinstance(stmt, PropertyNode):
                self._generate_value_statement(stmt)
        
        # 返回结果
        self._add_line("return result")
    
    def _generate_value_statement(self, prop: PropertyNode):
        """生成单个 value 语句"""
        key = str(prop.key)
        value = prop.value
        
        # 算术操作
        if key in self.ARITHMETIC_OPS:
            self._generate_arithmetic_op(key, value)
        
        # modifier 块（条件算术）
        elif key == 'modifier':
            self._generate_modifier(value)
        
        # complex_trigger_modifier
        elif key == 'complex_trigger_modifier':
            self._generate_complex_trigger_modifier(value)
        
        # 其他未知操作，作为注释
        else:
            self._add_line(f"# TODO: {key} = ...")
    
    def _generate_arithmetic_op(self, op: str, value: ASTNode):
        """生成算术操作"""
        py_op = self.ARITHMETIC_OPS[op]
        val_str = Formatter.format_literal_any(value, self.parameters)
        
        if op in ('base', 'set'):
            self._add_line(f"result = {val_str}")
        else:
            self._add_line(f"result {py_op} {val_str}")
    
    def _generate_modifier(self, block: ASTNode):
        """
        生成 modifier 块（条件算术）
        
        modifier = {
            条件...
            add = 数值
        }
        """
        if not isinstance(block, BlockNode):
            return
        
        # 分离条件和操作
        conditions = []
        operations = []
        
        for stmt in block.statements:
            if isinstance(stmt, PropertyNode):
                key = str(stmt.key)
                if key in self.ARITHMETIC_OPS:
                    operations.append(stmt)
                else:
                    conditions.append(stmt)
            elif isinstance(stmt, ComparisonNode):
                conditions.append(stmt)
        
        # 生成条件 if
        if conditions:
            condition_str = self._format_conditions(conditions)
            self._add_line(f"if {condition_str}:")
            self._indent()
        
        # 生成操作
        if operations:
            for op_stmt in operations:
                key = str(op_stmt.key)
                self._generate_arithmetic_op(key, op_stmt.value)
        else:
            self._add_line("pass")
        
        if conditions:
            self._dedent()
    
    def _generate_complex_trigger_modifier(self, block: ASTNode):
        """
        生成 complex_trigger_modifier
        
        complex_trigger_modifier = {
            trigger = num_districts
            parameters = { type = district_city }
            mode = add
        }
        """
        if not isinstance(block, BlockNode):
            return
        
        trigger = None
        params = {}
        mode = 'add'
        
        for stmt in block.statements:
            if isinstance(stmt, PropertyNode):
                key = str(stmt.key)
                
                if key == 'trigger':
                    trigger = self._get_literal_value(stmt.value)
                elif key == 'mode':
                    mode = self._get_literal_value(stmt.value)
                elif key == 'parameters' and isinstance(stmt.value, BlockNode):
                    for p in stmt.value.statements:
                        if isinstance(p, PropertyNode):
                            pkey = str(p.key)
                            params[pkey] = self._get_literal_value(p.value)
        
        if trigger:
            # 生成方法调用
            if params:
                # 格式化参数值（处理宏参数）
                formatted_params = []
                for k, v in params.items():
                    formatted_val = Formatter.format_literal_any(v, self.parameters)
                    formatted_params.append(f"{k}={formatted_val}")
                params_str = ", ".join(formatted_params)
                call = f"{self.scope_var}.{safe_identifier(trigger)}({params_str})"
            else:
                call = f"{self.scope_var}.{trigger}()"
            
            py_op = self.ARITHMETIC_OPS.get(mode, '+=')  
            self._add_line(f"result {py_op} {call}")
    
    def _format_conditions(self, conditions: List[ASTNode]) -> str:
        """格式化条件列表为 Python 表达式"""
        parts = []
        
        for cond in conditions:
            if isinstance(cond, PropertyNode):
                key = str(cond.key)
                
                # 逻辑块 NOT = { ... }
                if key == 'NOT' and isinstance(cond.value, BlockNode):
                    inner = self._format_conditions(cond.value.statements)
                    parts.append(f"not ({inner})")
                    continue
                
                elif key == 'NOR' and isinstance(cond.value, BlockNode):
                    inner = self._format_conditions(cond.value.statements)
                    parts.append(f"not ({inner})")
                    continue
                
                elif key == 'OR' and isinstance(cond.value, BlockNode):
                    inner_parts = []
                    for stmt in cond.value.statements:
                        inner_parts.append(self._format_conditions([stmt]))
                    parts.append(f"({' or '.join(inner_parts)})")
                    continue
                
                elif key == 'AND' and isinstance(cond.value, BlockNode):
                    inner = self._format_conditions(cond.value.statements)
                    parts.append(f"({inner})")
                    continue
                
                val = self._get_literal_value(cond.value)
                
                # 布尔检查 has_xxx = yes/no
                if val in ('yes', 'no', True, False):
                    is_true = val in ('yes', True)
                    if is_true:
                        parts.append(f"{self.scope_var}.{safe_identifier(key)}()")
                    else:
                        parts.append(f"not {self.scope_var}.{safe_identifier(key)}()")
                
                # has_xxx = something (方法调用带参数)
                elif key.startswith('has_'):
                    parts.append(f"{self.scope_var}.{safe_identifier(key)}({repr(val)})")
                
                # is_xxx = something
                elif key.startswith('is_'):
                    parts.append(f"{self.scope_var}.{safe_identifier(key)}({repr(val)})")
                
                # 其他属性检查
                else:
                    parts.append(f"{self.scope_var}.{safe_identifier(key)} == {repr(val)}")
            
            elif isinstance(cond, ComparisonNode):
                left = str(cond.left)
                right = Formatter.format_literal_any(cond.right, self.parameters) if hasattr(cond, 'right') else "0"
                op = cond.operator
                # 转换操作符
                if op == '=':
                    op = '=='
                parts.append(f"{self.scope_var}.{safe_identifier(left)} {op} {right}")
        
        if not parts:
            return "True"
        
        return " and ".join(parts)
    
    def _get_literal_value(self, value: ASTNode):
        """获取字面量值"""
        if isinstance(value, LiteralNode):
            return value.value
        elif isinstance(value, IdentifierExpressionNode):
            return value.expression
        elif isinstance(value, BlockNode):
            from .exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                f"在 value 计算中遇到嵌套块，这需要特殊处理。"
                f"BlockNode 包含 {len(value.statements)} 个语句，"
                f"不能简单地转换为字符串"
            )
        else:
            from .exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                f"_get_literal_value 遇到未处理的节点类型: {type(value).__name__}"
            )
    
    def _add_line(self, line: str = ""):
        """添加一行代码"""
        if line:
            indent = "    " * self.indent_level
            self.lines.append(indent + line)
        else:
            self.lines.append("")
    
    def _indent(self):
        """增加缩进"""
        self.indent_level += 1
    
    def _dedent(self):
        """减少缩进"""
        if self.indent_level > 0:
            self.indent_level -= 1

