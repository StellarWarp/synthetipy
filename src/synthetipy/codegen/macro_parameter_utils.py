"""
宏参数工具模块

提供宏参数收集、简单性判断等功能
"""

from typing import Dict, List, Set, Optional, Any
from ..ast_nodes import *
from ..compiler import compile_ast
import re


class MacroParameter:
    """宏参数信息"""
    
    def __init__(self, name: str, default: Optional[str] = None):
        self.name = name
        self.default = default
        self.inferred_type = 'str'  # 'int', 'float', 'str', 'bool'
        self.usages: List[str] = []  # 使用上下文
    
    def __repr__(self):
        return f"MacroParameter({self.name}, type={self.inferred_type})"


class MacroInfo:
    """宏左值的序列化与参数集合

    包含：
        - pdx_template: 原始 PDX 片段（字符串）
        - parameters: 局部参数字典（仅该宏左值范围）
        - meta_lines: 可直接插入的 meta.pdx(...) 行（不含 return，便于在上下文中插入）
    """

    def __init__(self, pdx_template: str, parameters: Dict[str, MacroParameter], meta_lines: Optional[List[str]] = None):
        self.pdx_template = pdx_template
        self.parameters = parameters
        self.meta_lines = meta_lines or []


class MacroParameterCollector:
    """收集 AST 中的宏参数"""
    
    def __init__(self):
        self.parameters: Dict[str, MacroParameter] = {}
        # 存储 PropertyNode -> MacroInfo 的映射
        self.macro_lefts: Dict[PropertyNode, MacroInfo] = {}
    
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
            # 将 Property 的处理委托到单独方法以保持 _visit 简洁
            self._handle_property_node(node)
        elif isinstance(node, BlockNode):
            for stmt in node.statements:
                self._visit(stmt)
        elif isinstance(node, ComparisonNode):
            self._visit(node.left)
            self._visit(node.right)
        elif isinstance(node, ListNode):
            for item in node.items:
                self._visit(item)
        else:
            raise NotImplementedError(f"Unsupported AST node type: {type(node).__name__}")

    def _handle_property_node(self, node: PropertyNode):
        """处理 PropertyNode：收集右侧参数，识别并注册宏左值"""
        # 先收集右侧的通用参数
        self._visit(node.value)

        # 处理键：键可以是字符串或 AST 节点
        key_source = None
        if isinstance(node.key, str):
            if '$' in node.key:
                key_source = node.key
                self._check_string_for_params(node.key, context='property_key')
        else:
            key_source = node.key.to_source()

        # 如果键含有宏参数（$），则收集该宏左值的局部参数并序列化为 pdx 模板
        if key_source and '$' in key_source:
            local_collector = MacroParameterCollector()
            if isinstance(node.key, str):
                local_collector._check_string_for_params(node.key, context='property_key_local')
            else:
                local_collector._visit(node.key)
            local_collector._visit(node.value)

            # 合并局部参数到全局参数集合
            for pname, pinfo in local_collector.parameters.items():
                self._add_parameter(pname, pinfo.default, context='macro_left')



            # 序列化 PDX 模板（键 + 右值）使用 Compiler 提供的序列化
            pdx_template = compile_ast(node)

            # 生成 meta.pdx 行（不含 return，方便插入语句中）
            meta_lines = generate_pdx_block(pdx_template, local_collector.parameters, indent=0, include_return=False)

            # 存储 MacroInfo
            self.macro_lefts[node] = MacroInfo(pdx_template, local_collector.parameters, meta_lines)

        # 非宏左值的 PropertyNode 不做额外处理（右侧已在开头处理）
        return
    
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
                self._add_parameter(name, default, context='literal')
            else:
                self._add_parameter(param_name, context='literal')
        elif '$' in value:
            # 字符串拼接：building_$TYPE$_$LEVEL$
            self._check_string_for_params(value, context='concatenation')
    
    def _check_identifier(self, node: IdentifierExpressionNode):
        """检查标识符表达式中的宏参数"""
        # 宏表达式模式：直接提取 MacroParam
        if getattr(node, 'is_macro_expression', False):
            for mp in node.macro_expression.macro_params:
                self._add_parameter(mp.name, mp.default, context='identifier_macro')
            return

        # 结构化模式：检查 call_info 参数、identifier 名称及 scope
        if getattr(node, 'call_info', None):
            for key, val in node.call_info.arguments:
                # 值可能是 MacroParam、IdentifierExpressionNode、字符串等
                if isinstance(val, MacroParam):
                    self._add_parameter(val.name, val.default, context='call_arg')
                elif isinstance(val, IdentifierExpressionNode):
                    self._visit(val)
                elif isinstance(val, str):
                    self._check_string_for_params(val, context='call_arg')

        # 检查 identifier 名称是否包含宏
        if getattr(node, 'identifier', None):
            ident = node.identifier
            if isinstance(ident, IdentifierNode):
                if isinstance(ident.name, str) and '$' in ident.name:
                    self._check_string_for_params(ident.name, context='identifier_name')
                if getattr(ident, 'scope_binding', None):
                    self._visit(ident.scope_binding)

        # 检查 scope 链
        if getattr(node, 'scope', None):
            self._visit(node.scope)


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
                self._add_parameter(name, default, context=context)
            else:
                self._add_parameter(param_str, context=context)


    
    def _add_parameter(self, name: str, default: Optional[str] = None, 
                       context: str = ''):
        """添加或更新参数"""
        if name not in self.parameters:
            self.parameters[name] = MacroParameter(name, default)
        else:
            # 更新现有参数
            param = self.parameters[name]
            if default and not param.default:
                param.default = default
        
        # 记录使用上下文
        if context:
            self.parameters[name].usages.append(context)
    # PDX 序列化由 Compiler 提供（compile_ast 函数），移除该模块中的手写序列化以降低重复代码和维护成本。
    # 在需要生成 PDX 模板时直接调用 compile_ast(node)。


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
    indent: int = 0,
    include_return: bool = True
) -> List[str]:
    """
    生成 meta.pdx() 调用代码
    
    Args:
        pdx_template: PDX 代码模板
        parameters: 参数字典
        indent: 缩进级别
        include_return: 是否包含前导 return（用于 value/trigger 顶层返回），默认 True 保持向后兼容
    
    Returns:
        生成的代码行
    """
    indent_str = "    " * indent
    lines = []
    
    # 构建参数列表
    param_strs = [f"{p.name}={p.name}" for p in sorted(parameters.values(), key=lambda x: x.name)]
    params = ", ".join(param_strs)
    
    # 生成 meta.pdx() 调用
    prefix = f"{indent_str}return " if include_return else f"{indent_str}"
    lines.append(f'{prefix}meta.pdx("""')
    
    # 添加 PDX 模板内容（保持原格式）
    for line in pdx_template.strip().split('\n'):
        lines.append(f'{indent_str}{line}')
    
    lines.append(f'{indent_str}""", {params})')
    
    return lines
