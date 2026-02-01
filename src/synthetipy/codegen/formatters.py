"""
格式化工具模块

提供值格式化、标识符处理等通用功能
"""

from typing import Union
from ..ast_nodes import *


class Formatter:
    """格式化工具类"""
    
    @staticmethod
    def format_value(value: ASTNode) -> str:
        """
        格式化值为 Python 字面量
        
        Args:
            value: 值节点
        
        Returns:
            Python 字面量字符串
        """
        if isinstance(value, LiteralNode):
            if value.value_type == 'string':
                # 字符串需要转义
                escaped = str(value.value).replace("'", "\\'")
                return f"'{escaped}'"
            elif value.value_type == 'bool':
                return 'True' if value.value else 'False'
            elif value.value_type in ('int', 'float'):
                return str(value.value)
            elif value.value_type == 'identifier':
                # 标识符作为字符串
                return f"'{value.value}'"
            elif value.value_type == 'variable':
                # 变量引用（@xxx）
                return f"'{value.value}'"
            else:
                return f"'{value.value}'"
        elif isinstance(value, ListNode):
            # 递归处理列表
            elements = [Formatter.format_value(elem) for elem in value.items]
            return '[' + ', '.join(elements) + ']'
        elif isinstance(value, IdentifierExpressionNode):
            # 标识符表达式
            # 特殊处理 yes/no 作为布尔值
            if value.expression == 'yes':
                return 'True'
            elif value.expression == 'no':
                return 'False'
            else:
                return f"'{value.expression}'"
        elif isinstance(value, BlockNode):
            # 块节点不应该用 format_value 处理，应该生成嵌套类
            return "..."
        else:
            # 其他类型尝试获取字符串表示
            if hasattr(value, 'value'):
                return f"'{value.value}'"
            elif hasattr(value, 'expression'):
                return f"'{value.expression}'"
            else:
                return "..."
    
    @staticmethod
    def format_list(lst: ListNode) -> str:
        """
        格式化列表
        
        Args:
            lst: 列表节点
        
        Returns:
            Python 列表字符串
        """
        elements = [Formatter.format_value(elem) for elem in lst.items]
        return '[' + ', '.join(elements) + ']'
    
    @staticmethod
    def get_identifier(node: Union[str, ASTNode]) -> str:
        """
        获取标识符字符串
        
        Args:
            node: 标识符节点或字符串
        
        Returns:
            标识符字符串
        """
        if isinstance(node, str):
            return node
        else:
            # 处理 AST 节点 - 转换为字符串
            # TODO: 处理 MacroIdentifierNode 等复杂情况
            if hasattr(node, 'name'):
                return str(node.name)
            elif hasattr(node, 'value'):
                return str(node.value)
            else:
                return str(node)
    
    @staticmethod
    def sanitize_class_name(name: str) -> str:
        """
        清理类名，确保符合 Python 规范
        
        Args:
            name: 原始名称
        
        Returns:
            清理后的类名
        """
        # TODO: 处理特殊字符、关键字冲突等
        return name
    
    @staticmethod
    def escape_string(s: str) -> str:
        """
        转义字符串中的特殊字符
        
        Args:
            s: 原始字符串
        
        Returns:
            转义后的字符串
        """
        return s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
    
    @staticmethod
    def format_value_reference(value: ASTNode, scope_var: str = "scope", macro_params: dict = None) -> str:
        """
        格式化 value:xxx 引用为 Python 代码
        
        支持:
        - value:func_name -> func_name(scope)
        - value:func|PARAM|val| -> func(scope, PARAM=val)
        - IdentifierExpressionNode 带 call_pattern = 'value'
        
        Args:
            value: 值节点
            scope_var: 作用域变量名
            macro_params: 宏参数字典（用于识别简单参数）
        
        Returns:
            Python 调用代码，如果不是 value: 引用则返回 None
        """
        expr_str = None
        call_pattern = None
        
        # 处理 IdentifierExpressionNode
        if hasattr(value, 'call_pattern') and hasattr(value, 'expression'):
            call_pattern = value.call_pattern
            expr_str = value.expression
        elif isinstance(value, LiteralNode):
            expr_str = str(value.value)
            if expr_str.startswith('value:'):
                call_pattern = 'value'
        
        if call_pattern != 'value' or not expr_str:
            return None
        
        # 解析 value:xxx 或 value:xxx|PARAM|val|
        if ':' in expr_str:
            _, rest = expr_str.split(':', 1)
        else:
            rest = expr_str
        
        # 检查是否有参数
        if '|' in rest:
            parts = rest.split('|')
            func_name = parts[0]
            # 解析参数对: |PARAM|val|PARAM2|val2|
            params = []
            i = 1
            while i + 1 < len(parts):
                param_name = parts[i]
                param_val = parts[i + 1]
                if param_name:  # 跳过空字符串
                    # 格式化参数值
                    formatted_val = Formatter._format_param_value(param_val, macro_params)
                    params.append(f"{param_name}={formatted_val}")
                i += 2
            
            if params:
                params_str = ", ".join(params)
                return f"{func_name}({scope_var}, {params_str})"
            else:
                return f"{func_name}({scope_var})"
        else:
            return f"{rest}({scope_var})"
    
    @staticmethod
    def _format_param_value(val: str, macro_params: dict = None) -> str:
        """格式化参数值"""
        # 宏参数 $xxx$ - 检查是否是简单参数
        if val.startswith('$') and val.endswith('$') and val.count('$') == 2:
            param_name = val[1:-1]
            if '|' in param_name:
                param_name = param_name.split('|')[0]
            # 如果是已知的简单参数，直接返回参数名
            if macro_params and param_name in macro_params:
                param_obj = macro_params[param_name]
                if param_obj.is_simple:
                    return param_name  # 直接返回参数名，不加引号
            return repr(val)  # 复杂参数或未知参数保留字符串
        # 尝试解析数值
        try:
            if '.' in val:
                return str(float(val))
            return str(int(val))
        except ValueError:
            return repr(val)
    
    @staticmethod
    def format_modifier_reference(value: ASTNode, scope_var: str = "scope", macro_params: dict = None) -> str:
        """
        格式化 modifier:xxx 引用
        
        modifier:xxx -> scope.get_modifier('xxx')
        """
        expr_str = None
        
        if hasattr(value, 'expression'):
            expr_str = value.expression
        elif isinstance(value, LiteralNode):
            expr_str = str(value.value)
        
        if not expr_str or not expr_str.startswith('modifier:'):
            return None
        
        modifier_name = expr_str[9:]  # 去掉 'modifier:' 前缀
        return f"{scope_var}.get_modifier({repr(modifier_name)})"
    
    @staticmethod
    def format_special_reference(value: ASTNode, scope_var: str = "scope", macro_params: dict = None) -> str:
        """
        格式化特殊引用（value:, modifier:, event_target: 等）
        
        Args:
            value: 值节点
            scope_var: 作用域变量名
            macro_params: 宏参数字典
        
        Returns:
            格式化后的 Python 代码，如果不是特殊引用则返回 None
        """
        # 尝试 value: 引用
        result = Formatter.format_value_reference(value, scope_var, macro_params)
        if result:
            return result
        
        # 尝试 modifier: 引用
        result = Formatter.format_modifier_reference(value, scope_var, macro_params)
        if result:
            return result
        
        # event_target: 引用
        expr_str = None
        if hasattr(value, 'expression'):
            expr_str = value.expression
        elif isinstance(value, LiteralNode):
            expr_str = str(value.value)
        
        if expr_str and expr_str.startswith('event_target:'):
            target_name = expr_str[13:]
            return f"{scope_var}.get_event_target({repr(target_name)})"
        
        return None
