"""
宏参数工具模块

提供宏参数收集、简单性判断等功能
"""

from typing import Dict, List, Set, Optional, Any
from ..ast_nodes import *
import re


class MacroParameter:
    """宏参数信息"""
    
    def __init__(self, name: str, default: Optional[str] = None, is_simple: bool = True):
        self.name = name
        self.default = default
        self.is_simple = is_simple  # True=简单使用，False=需要meta.pdx
        self.inferred_type = 'str'  # 'int', 'float', 'str', 'bool'
        self.usages: List[str] = []  # 使用上下文
    
    def __repr__(self):
        return f"MacroParameter({self.name}, type={self.inferred_type}, simple={self.is_simple})"


class MacroParameterCollector:
    """收集 AST 中的宏参数"""
    
    def __init__(self):
        self.parameters: Dict[str, MacroParameter] = {}
        self.has_complex_usage = False
    
    def collect(self, node: ASTNode) -> Dict[str, MacroParameter]:
        """
        收集节点树中的所有宏参数
        
        Args:
            node: AST 节点
        
        Returns:
            参数字典 {name: MacroParameter}
        """
        self._visit(node)
        return self.parameters
    
    def _visit(self, node: ASTNode):
        """遍历 AST 节点"""
        if isinstance(node, LiteralNode):
            self._check_literal(node)
        elif isinstance(node, IdentifierExpressionNode):
            self._check_identifier(node)
        elif isinstance(node, PropertyNode):
            self._visit(node.value)
            # 检查键是否包含宏参数
            if isinstance(node.key, str):
                self._check_string_for_params(node.key, context='property_key')
        elif isinstance(node, BlockNode):
            for stmt in node.statements:
                self._visit(stmt)
        elif isinstance(node, ComparisonNode):
            self._visit(node.left)
            self._visit(node.right)
        elif isinstance(node, ListNode):
            for item in node.items:
                self._visit(item)
    
    def _check_literal(self, node: LiteralNode):
        """检查字面量中的宏参数"""
        value = str(node.value)
        
        # 检查是否是纯宏参数
        if value.startswith('$') and value.endswith('$') and value.count('$') == 2:
            # 单纯的 $PARAM$
            param_name = value[1:-1]
            if '|' in param_name:
                # 带默认值：$PARAM|default$
                name, default = param_name.split('|', 1)
                self._add_parameter(name, default, is_simple=True, context='literal')
            else:
                self._add_parameter(param_name, is_simple=True, context='literal')
        elif '$' in value:
            # 字符串拼接：building_$TYPE$_$LEVEL$
            self._check_string_for_params(value, context='concatenation')
    
    def _check_identifier(self, node: IdentifierExpressionNode):
        """检查标识符表达式中的宏参数"""
        expr = node.expression
        
        # 检查是否是纯宏参数
        if expr.startswith('$') and expr.endswith('$') and expr.count('$') == 2:
            param_name = expr[1:-1]
            if '|' in param_name:
                name, default = param_name.split('|', 1)
                self._add_parameter(name, default, is_simple=True, context='identifier')
            else:
                self._add_parameter(param_name, is_simple=True, context='identifier')
            return  # 早返回，不继续处理
        
        # 检查解析后的参数（value:func|PARAM|$VAR$|）优先
        if hasattr(node, 'parsed') and node.parsed and hasattr(node.parsed, 'arguments'):
            parsed = node.parsed
            # 检查参数列表
            has_forwarding = False
            for arg in parsed.arguments:
                # 处理 MacroParam 对象
                if hasattr(arg, 'name'):  # MacroParam 对象
                    self._add_parameter(
                        arg.name, 
                        arg.default, 
                        is_simple=True, 
                        context='parameter_forwarding'
                    )
                    has_forwarding = True
                # 处理字符串形式的宏参数
                elif isinstance(arg, str) and arg.startswith('$') and arg.endswith('$') and arg.count('$') == 2:
                    param_name = arg[1:-1]
                    if '|' in param_name:
                        name, default = param_name.split('|', 1)
                        self._add_parameter(name, default, is_simple=True, context='parameter_forwarding')
                    else:
                        self._add_parameter(param_name, is_simple=True, context='parameter_forwarding')
                    has_forwarding = True
                # 参数拼接在转发中
                elif isinstance(arg, str) and '$' in arg:
                    self._check_string_for_params(arg, context='parameter_forwarding_concat')
                    has_forwarding = True
            
            # 如果有参数转发，不再处理表达式字符串本身
            if has_forwarding:
                return
        
        # 其他情况：拼接或动态调用
        if '$' in expr:
            self._check_string_for_params(expr, context='expression')
    
    def _check_string_for_params(self, text: str, context: str):
        """检查字符串中的宏参数（包括拼接情况）"""
        # 正则匹配 $PARAM$ 或 $PARAM|default$
        pattern = r'\$([A-Z_][A-Z0-9_]*(?:\|[^$]+)?)\$'
        
        for match in re.finditer(pattern, text):
            param_str = match.group(1)
            
            # 判断是否是拼接
            is_concatenated = len(text.strip()) > len(match.group(0))
            
            if '|' in param_str:
                name, default = param_str.split('|', 1)
                self._add_parameter(
                    name, 
                    default, 
                    is_simple=not is_concatenated,
                    context=context
                )
            else:
                self._add_parameter(
                    param_str, 
                    is_simple=not is_concatenated,
                    context=context
                )
    
    def _add_parameter(self, name: str, default: Optional[str] = None, 
                       is_simple: bool = True, context: str = ''):
        """添加或更新参数"""
        if name not in self.parameters:
            self.parameters[name] = MacroParameter(name, default, is_simple)
            # 首次添加时也要检查是否复杂
            if not is_simple:
                self.has_complex_usage = True
        else:
            # 更新现有参数
            param = self.parameters[name]
            if default and not param.default:
                param.default = default
            # 如果任何一次使用是复杂的，整体标记为复杂
            if not is_simple:
                param.is_simple = False
                self.has_complex_usage = True
        
        # 记录使用上下文
        if context:
            self.parameters[name].usages.append(context)


class ParameterTypeInferencer:
    """推断宏参数类型"""
    
    @staticmethod
    def infer_type(param: MacroParameter) -> str:
        """
        推断参数类型
        
        Returns:
            'int', 'float', 'str', 'bool'
        """
        # 基于命名约定推断
        if param.name.endswith('LEVEL') or param.name.endswith('TIER') or param.name.endswith('COUNT'):
            return 'int'
        
        if param.name.endswith('AMOUNT') or param.name.endswith('MULT') or param.name.endswith('MULTIPLIER'):
            return 'float'
        
        if param.name.startswith('HAS_') or param.name.startswith('IS_'):
            return 'bool'
        
        # 基于默认值推断
        if param.default:
            try:
                int(param.default)
                return 'int'
            except ValueError:
                try:
                    float(param.default)
                    return 'float'
                except ValueError:
                    if param.default in ('yes', 'no', 'true', 'false'):
                        return 'bool'
        
        # 基于使用上下文
        if 'concatenation' in param.usages or 'expression' in param.usages:
            return 'str'
        
        # 默认字符串
        return 'str'
    
    @staticmethod
    def infer_all(parameters: Dict[str, MacroParameter]):
        """批量推断参数类型"""
        for param in parameters.values():
            param.inferred_type = ParameterTypeInferencer.infer_type(param)


def generate_function_signature(
    name: str,
    parameters: Dict[str, MacroParameter],
    return_type: str,
    scope_type: str = "scope"
) -> str:
    """
    生成带参数的函数签名
    
    Args:
        name: 函数名
        parameters: 宏参数字典
        return_type: 返回类型
        scope_type: 作用域类型
    
    Returns:
        函数签名字符串
    """
    # 作用域参数始终是第一个
    param_strs = [scope_type]
    
    # 按名称排序参数
    sorted_params = sorted(parameters.values(), key=lambda p: p.name)
    
    for param in sorted_params:
        py_type = param.inferred_type
        
        if param.default:
            # 有默认值，根据类型转换
            default_value = param.default
            if py_type == 'int':
                try:
                    default_repr = str(int(default_value))
                except (ValueError, TypeError):
                    default_repr = repr(default_value)
            elif py_type == 'float':
                try:
                    default_repr = str(float(default_value))
                except (ValueError, TypeError):
                    default_repr = repr(default_value)
            elif py_type == 'bool':
                if isinstance(default_value, str):
                    default_repr = 'True' if default_value.lower() in ('yes', 'true', '1') else 'False'
                else:
                    default_repr = 'True' if default_value else 'False'
            else:
                # str 或其他类型，保持字符串
                default_repr = repr(default_value)
            param_strs.append(f"{param.name}: {py_type} = {default_repr}")
        else:
            # 无默认值，设置为 None
            param_strs.append(f"{param.name}: {py_type} = None")
    
    params_str = ", ".join(param_strs)
    return f"def {name}({params_str}) -> {return_type}:"


def format_parameter_value(param_name: str, param_type: str = 'str') -> str:
    """
    格式化参数值在代码中的使用
    
    Args:
        param_name: 参数名
        param_type: 参数类型
    
    Returns:
        Python 代码中的参数引用
    """
    # 简单情况：直接使用参数名
    return param_name


def generate_pdx_block(
    pdx_template: str,
    parameters: Dict[str, MacroParameter],
    indent: int = 0
) -> List[str]:
    """
    生成 meta.pdx() 调用代码
    
    Args:
        pdx_template: PDX 代码模板
        parameters: 参数字典
        indent: 缩进级别
    
    Returns:
        生成的代码行
    """
    indent_str = "    " * indent
    lines = []
    
    # 构建参数列表
    param_strs = [f"{p.name}={p.name}" for p in sorted(parameters.values(), key=lambda x: x.name)]
    params = ", ".join(param_strs)
    
    # 生成 meta.pdx() 调用
    lines.append(f'{indent_str}return meta.pdx("""')
    
    # 添加 PDX 模板内容（保持原格式）
    for line in pdx_template.strip().split('\n'):
        lines.append(f'{indent_str}{line}')
    
    lines.append(f'{indent_str}""", {params})')
    
    return lines
