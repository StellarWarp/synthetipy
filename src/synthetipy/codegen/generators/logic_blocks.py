"""
逻辑块生成器

处理 AND/OR/NOT/NOR/NAND 等逻辑操作符
生成函数式调用: logic.AND(...), logic.OR(...) 等
"""

from typing import List
from ...ast_nodes import *


class LogicBlockGenerator:
    """逻辑块生成器 - 生成函数式逻辑调用"""
    
    # 逻辑模块前缀，可配置
    LOGIC_PREFIX = "logic"
    
    def __init__(self, parent_generator):
        self.parent = parent_generator
        self.context = parent_generator.context
    
    def is_logic_block(self, key: str) -> bool:
        """判断是否是逻辑块"""
        return key in self.parent.LOGIC_OPERATORS
    
    def generate_logic_expression(self, operator: str, block: BlockNode) -> str:
        """
        生成逻辑表达式 (函数式风格)
        
        AND {...} -> logic.AND(expr1, expr2, expr3)
        OR {...} -> logic.OR(expr1, expr2, expr3)
        NOT {...} -> logic.NOT(expr1, expr2)
        NOR {...} -> logic.NOR(expr1, expr2)
        NAND {...} -> logic.NAND(expr1, expr2)
        """
        from .expression_builder import ExpressionBuilder
        
        expr_builder = ExpressionBuilder(self.parent, self.parent.value_formatter)
        expressions = []
        
        for stmt in block.statements:
            expr = expr_builder.statement_to_expression(stmt)
            if expr:
                expressions.append(expr)
        
        if not expressions:
            raise ValueError(f"Logic block with operator {operator} has no valid expressions")
        
        # 单个表达式时，AND/OR 可以直接返回
        if len(expressions) == 1 and operator in ('AND', 'OR'):
            return expressions[0]
        
        # 生成函数调用
        return self._generate_logic_call(operator, expressions)
    
    def _generate_logic_call(self, operator: str, expressions: List[str]) -> str:
        """
        生成逻辑函数调用
        
        logic.AND(
            expr1,
            expr2,
            expr3,
        )
        """
        indent_str = getattr(self.context, 'indent_str', "    ")
        max_len = getattr(self.context, 'max_line_length', 88)
        
        # 尝试单行
        args_str = ", ".join(expressions)
        single_line = f"{self.LOGIC_PREFIX}.{operator}({args_str})"
        
        if len(single_line) <= max_len and '\n' not in args_str:
            return single_line
        
        # 需要换行 - 每个参数一行
        lines = [f"{self.LOGIC_PREFIX}.{operator}("]
        for expr in expressions:
            # 处理嵌套的多行表达式
            if '\n' in expr:
                expr_lines = expr.split('\n')
                lines.append(f"{indent_str}{expr_lines[0]}")
                for sub_line in expr_lines[1:]:
                    lines.append(f"{indent_str}{sub_line}")
                # 最后一个子行加逗号
                lines[-1] += ","
            else:
                lines.append(f"{indent_str}{expr},")
        lines.append(")")
        
        return "\n".join(lines)
    
    def generate_and_expression(self, expressions: List[str]) -> str:
        """
        生成 AND 表达式（供外部使用，如多语句组合）
        
        当只有一个表达式时直接返回，否则生成 logic.AND(...)
        """
        if len(expressions) == 1:
            return expressions[0]
        return self._generate_logic_call('AND', expressions)

