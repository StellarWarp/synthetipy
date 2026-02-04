"""
特殊调用处理器

处理 PDX 中的特殊语法和调用：
- check_variable_arithmetic
- value: 前缀
- custom_tooltip
- 等等
"""

from typing import Optional
from ...ast_nodes import *
from ...pdx_constants import SPECIAL_CALLS


class SpecialCallHandler:
    """特殊调用处理器"""
    
    # 使用集中管理的常量
    SPECIAL_CALLS = SPECIAL_CALLS
    
    def __init__(self, parent_generator):
        self.parent = parent_generator
        self.context = parent_generator.context
    
    def is_special_call(self, key: str) -> bool:
        """判断是否是特殊调用"""
        return key in self.SPECIAL_CALLS
    
    def handle_special_call(self, key: str, value: ASTNode) -> Optional[str]:
        """处理特殊调用"""
        if key == 'check_variable_arithmetic':
            return self._handle_check_variable_arithmetic(value)
        
        elif key == 'check_variable':
            return self._handle_check_variable(value)
        
        elif key in ('custom_tooltip', 'custom_tooltip_with_fail_root', 'hidden_tooltip'):
            return self._handle_tooltip(value, tooltip_type=key)
        
        return None
    
    def _handle_check_variable_arithmetic(self, value: ASTNode) -> Optional[str]:
        """
        check_variable_arithmetic 简化
        
        check_variable_arithmetic = {
            which = value:script_value_name
            add = 10
            subtract = 5
            multiply = 2
            divide = 3
            value >= 100
        }
        
        -> ((script_value_name() + 10 - 5) * 2 / 3) >= 100
        """
        if not isinstance(value, BlockNode):
            return None
        
        # 提取 which
        which_prop = value.get_property('which')
        if not which_prop:
            return None
        
        # 解析 which (可能是 value:xxx 形式)
        which_expr = self._parse_which_expression(which_prop.value)
        
        # 提取运算操作 (按顺序：add/subtract, multiply/divide)
        operations = []
        
        # 加减法
        add_prop = value.get_property('add')
        if add_prop:
            op_value = self._value_to_python(add_prop.value)
            operations.append(('add', op_value))
        
        subtract_prop = value.get_property('subtract')
        if subtract_prop:
            op_value = self._value_to_python(subtract_prop.value)
            operations.append(('subtract', op_value))
        
        # 乘除法
        multiply_prop = value.get_property('multiply')
        if multiply_prop:
            op_value = self._value_to_python(multiply_prop.value)
            operations.append(('multiply', op_value))
        
        divide_prop = value.get_property('divide')
        if divide_prop:
            op_value = self._value_to_python(divide_prop.value)
            operations.append(('divide', op_value))
        
        # 构建左侧表达式
        left_expr = which_expr
        
        # 先处理加减
        add_sub_ops = [op for op in operations if op[0] in ('add', 'subtract')]
        if add_sub_ops:
            parts = [left_expr]
            for op_type, op_value in add_sub_ops:
                if op_type == 'add':
                    parts.append(f" + {op_value}")
                else:  # subtract
                    parts.append(f" - {op_value}")
            left_expr = f"({''.join(parts)})"
        
        # 再处理乘除
        mul_div_ops = [op for op in operations if op[0] in ('multiply', 'divide')]
        if mul_div_ops:
            for op_type, op_value in mul_div_ops:
                if op_type == 'multiply':
                    left_expr = f"({left_expr} * {op_value})"
                else:  # divide
                    left_expr = f"({left_expr} / {op_value})"
        
        # 提取比较运算
        for stmt in value.statements:
            if isinstance(stmt, ComparisonNode):
                if stmt.left == 'value':
                    # value >= 100
                    op = self.parent.COMPARISON_OPS.get(stmt.operator, stmt.operator)
                    right = self._value_to_python(stmt.right)
                    return f"{left_expr} {op} {right}"
        
        return left_expr
    
    def _handle_check_variable(self, value: ASTNode) -> Optional[str]:
        """
        check_variable 处理
        
        check_variable = { which = my_var value >= 10 }
        -> scope.get_variable('my_var') >= 10
        """
        if not isinstance(value, BlockNode):
            return None
        
        which_prop = value.get_property('which')
        if not which_prop:
            return None
        
        var_name = self._value_to_python(which_prop.value)
        var_expr = f"{self.context.current_scope_var}.get_variable({var_name})"
        
        # 查找比较运算
        for stmt in value.statements:
            if isinstance(stmt, ComparisonNode):
                if stmt.left == 'value':
                    op = self.parent.COMPARISON_OPS.get(stmt.operator, stmt.operator)
                    right = self._value_to_python(stmt.right)
                    return f"{var_expr} {op} {right}"
        
        return var_expr
    
    def _handle_tooltip(self, value: ASTNode, tooltip_type: str = 'custom_tooltip') -> Optional[str]:
        """
        tooltip 处理 - 生成函数调用形式
        
        custom_tooltip = {
            text = "tooltip_key"
            <actual_condition>
        }
        
        -> custom_tooltip(
               text='tooltip_key',
               condition=<actual_condition>
           )
        """
        if not isinstance(value, BlockNode):
            return None
        
        from .expression_builder import ExpressionBuilder
        
        # 提取 text 参数
        text_value = None
        for stmt in value.statements:
            if isinstance(stmt, PropertyNode) and str(stmt.key) == 'text':
                text_value = self._value_to_python(stmt.value)
                break
        
        # 提取非 text/fail_text 的语句作为条件
        conditions = [s for s in value.statements 
                     if not (isinstance(s, PropertyNode) and 
                            str(s.key) in ('text', 'fail_text', 'success_text'))]
        
        # 生成条件表达式
        condition_expr = "True"
        if conditions:
            expr_builder = ExpressionBuilder(self.parent, self.parent.value_formatter)
            condition_block = BlockNode(conditions)
            condition_expr = expr_builder.block_to_expression(condition_block)
        
        # 生成函数调用
        indent_str = getattr(self.context, 'indent_str', "    ")
        
        # 检查是否需要换行
        if text_value:
            single_line = f"{tooltip_type}(text={text_value}, condition={condition_expr})"
        else:
            single_line = f"{tooltip_type}(condition={condition_expr})"
        
        max_len = getattr(self.context, 'max_line_length', 88)
        
        if len(single_line) <= max_len and '\n' not in condition_expr:
            return single_line
        
        # 需要换行
        lines = [f"{tooltip_type}("]
        if text_value:
            lines.append(f"{indent_str}text={text_value},")
        
        # 处理多行条件
        if '\n' in condition_expr:
            cond_lines = condition_expr.split('\n')
            lines.append(f"{indent_str}condition={cond_lines[0]}")
            for sub_line in cond_lines[1:]:
                lines.append(f"{indent_str}{sub_line}")
            lines[-1] += ","
        else:
            lines.append(f"{indent_str}condition={condition_expr},")
        
        lines.append(")")
        
        return "\n".join(lines)
    
    def _parse_which_expression(self, value: ASTNode) -> str:
        """
        解析 which 表达式
        
        value:script_value_name -> script_value_name()
        @variable_name -> scope.get_variable('@variable_name')
        """
        # IdentifierExpressionNode 类型（value:xxx, event_target:xxx 等）
        if hasattr(value, 'call_pattern') and hasattr(value, 'expression'):
            expr = value.expression
            call_pattern = value.call_pattern
            
            # value: 前缀 - script value 调用
            if call_pattern == 'value':
                func_name = expr.split(':', 1)[1] if ':' in expr else expr
                # 处理带参数的情况 value:func|arg1|arg2|
                if '|' in func_name:
                    parts = func_name.split('|')
                    func_name = parts[0]
                return f"{func_name}()"
            
            # event_target: 前缀
            if call_pattern == 'event_target':
                target_name = expr.split(':', 1)[1] if ':' in expr else expr
                return f"{self.context.current_scope_var}.get_event_target('{target_name}')"
            
            # 其他情况，返回表达式本身
            return f"'{expr}'"
        
        if isinstance(value, LiteralNode):
            val_str = str(value.value)
            
            # value: 前缀 - script value 调用
            if val_str.startswith('value:'):
                func_name = val_str[6:]  # 去掉 'value:' 前缀
                return f"{func_name}()"
            
            # @ 前缀 - 变量引用
            if val_str.startswith('@'):
                return f"{self.context.current_scope_var}.get_variable('{val_str}')"
            
            # event_target: 前缀
            if val_str.startswith('event_target:'):
                target_name = val_str[13:]
                return f"{self.context.current_scope_var}.get_event_target('{target_name}')"
            
            return f"'{val_str}'"
        
        return "None"
    
    def _value_to_python(self, value: ASTNode) -> str:
        """将值节点转换为 Python 代码"""
        from .expression_builder import ExpressionBuilder
        expr_builder = ExpressionBuilder(self.parent, self.parent.value_formatter)
        return expr_builder._value_to_python(value)
