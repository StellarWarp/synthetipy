"""
Effect 变量和标记操作生成器

处理 set_variable, add_variable, set_planet_flag 等操作
"""

from typing import Optional
from ...ast_nodes import ASTNode, BlockNode, PropertyNode, LiteralNode
from ...pdx_constants import VARIABLE_OPS, FLAG_OPS


class EffectVariableGenerator:
    """Effect 变量操作生成器"""
    
    # 使用集中管理的常量
    VARIABLE_OPS = VARIABLE_OPS
    FLAG_OPS = FLAG_OPS
    
    def __init__(self, parent_generator):
        self.parent = parent_generator
        self.context = parent_generator.context
    
    def is_variable_op(self, key: str) -> bool:
        """判断是否是变量操作"""
        return key in self.VARIABLE_OPS
    
    def is_flag_op(self, key: str) -> bool:
        """判断是否是标记操作"""
        return key in self.FLAG_OPS
    
    def generate_variable_op(self, op: str, value: BlockNode) -> bool:
        """
        生成变量操作
        
        set_variable = { which = x value = 10 }
        -> scope.set_variable('x', 10)
        """
        if not isinstance(value, BlockNode):
            return False
        
        which = None
        val = None
        
        for stmt in value.statements:
            if isinstance(stmt, PropertyNode):
                if stmt.key == 'which':
                    which = self._extract_value(stmt.value)
                elif stmt.key == 'value':
                    val = self._extract_value(stmt.value)
        
        if which is None:
            return False
        
        # 映射操作名
        method_map = {
            'set_variable': 'set_variable',
            'add_variable': 'add_variable',
            'subtract_variable': 'subtract_variable',
            'multiply_variable': 'multiply_variable',
            'divide_variable': 'divide_variable',
            'clear_variable': 'clear_variable',
            'change_variable': 'add_variable',  # 别名
        }
        
        method = method_map.get(op, op)
        
        if op == 'clear_variable':
            self.parent._add_line(f"{self.context.current_scope_var}.{method}('{which}')")
        else:
            self.parent._add_line(f"{self.context.current_scope_var}.{method}('{which}', {val})")
        
        return True
    
    def generate_flag_op(self, op: str, value: ASTNode) -> bool:
        """
        生成标记操作
        
        set_planet_flag = flag_name -> scope.set_flag('flag_name')
        """
        flag_name = self._extract_value(value)
        
        # 解析操作类型和方法名
        if op.startswith('set_'):
            method = 'set_flag'
        elif op.startswith('remove_'):
            method = 'remove_flag'
        else:
            method = op
        
        self.parent._add_line(f"{self.context.current_scope_var}.{method}('{flag_name}')")
        return True
    
    def _extract_value(self, value: ASTNode) -> str:
        """提取值的字符串表示"""
        if isinstance(value, LiteralNode):
            return str(value.value)
        elif hasattr(value, 'expression'):
            return value.expression
        elif isinstance(value, BlockNode):
            from ...codegen.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                f"在变量操作中遇到嵌套块，这需要特殊处理。"
                f"BlockNode 包含 {len(value.statements)} 个语句，"
                f"不能简单地转换为字符串"
            )
        elif hasattr(value, 'value'):
            return str(value.value)
        else:
            from ...codegen.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                f"_extract_value 遇到未处理的节点类型: {type(value).__name__}"
            )
