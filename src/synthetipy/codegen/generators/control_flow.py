"""
控制流生成器

处理 if/else_if/else 等控制流结构
在 trigger 和 effect 中通用
"""

from typing import List, Optional, Callable
from ...ast_nodes import *
from ..exceptions import EmptyBlockError, MissingConditionError


class ControlFlowGenerator:
    """控制流生成器 - 处理 if/else 结构"""
    
    def __init__(self, parent_generator):
        """
        Args:
            parent_generator: 父生成器（需要有 _add_line, _indent, _dedent 等方法）
        """
        self.parent = parent_generator
        self.context = parent_generator.context
    
    def has_control_flow(self, block: BlockNode) -> bool:
        """检查块是否包含控制流（if/else）"""
        for stmt in block.statements:
            if isinstance(stmt, PropertyNode):
                if stmt.key == 'if' and isinstance(stmt.value, BlockNode):
                    return True
        return False
    
    def generate_control_flow(
        self, 
        block: BlockNode,
        branch_handler: Callable[[BlockNode, str], None]
    ):
        """
        生成 if/elif/else 控制流
        
        Args:
            block: 包含 if/else 的块
            branch_handler: 处理分支内容的回调函数
                签名: (branch_block: BlockNode, branch_type: str) -> None
                branch_type: 'if', 'elif', 'else'
        
        PDX:
            if = { limit = {...} ... }
            else_if = { limit = {...} ... }
            else = {...}
        
        Python:
            if condition:
                ...
            elif condition:
                ...
            else:
                ...
        """
        i = 0
        statements = block.statements
        is_first_branch = True
        
        while i < len(statements):
            stmt = statements[i]
            
            if isinstance(stmt, PropertyNode):
                if stmt.key == 'if' and isinstance(stmt.value, BlockNode):
                    # if 分支
                    keyword = "if" if is_first_branch else "elif"
                    self._generate_if_branch(stmt.value, keyword, branch_handler)
                    is_first_branch = False
                    
                elif stmt.key == 'else_if' and isinstance(stmt.value, BlockNode):
                    # elif 分支
                    self._generate_if_branch(stmt.value, "elif", branch_handler)
                    
                elif stmt.key == 'else' and isinstance(stmt.value, BlockNode):
                    # else 分支
                    self.parent._add_line("else:")
                    self.parent._indent()
                    branch_handler(stmt.value, 'else')
                    self.parent._dedent()
            
            i += 1
    
    def _generate_if_branch(
        self,
        if_block: BlockNode,
        keyword: str,
        branch_handler: Callable[[BlockNode, str], None]
    ):
        """
        生成 if/elif 分支
        
        if_block 结构：
        {
            limit = { ... }  # 条件
            ...              # 满足条件时的内容
        }
        """
        # 提取 limit 块
        limit_prop = if_block.get_property('limit')
        
        if limit_prop and isinstance(limit_prop.value, BlockNode):
            # 导入 logic_blocks 来生成条件表达式
            from .expression_builder import ExpressionBuilder
            
            expr_builder = ExpressionBuilder(self.parent)
            limit_expr = expr_builder.block_to_expression(limit_prop.value)
            
            self.parent._add_line(f"{keyword} {limit_expr}:")
            self.parent._indent()
            
            # 生成分支内容（排除 limit）
            branch_statements = [s for s in if_block.statements if s != limit_prop]
            if branch_statements:
                branch_block = BlockNode(branch_statements)
                branch_type = 'if' if keyword == 'if' else 'elif'
                branch_handler(branch_block, branch_type)
            else:
                # 空分支是不允许的
                raise EmptyBlockError(f"{keyword} 块在移除 limit 后为空，这可能是逻辑错误或未处理的特殊结构")
            
            self.parent._dedent()
        else:
            # 没有 limit是异常情况
            raise MissingConditionError(f"{keyword} 块缺少 limit 条件，无法生成条件判断")
    
    def extract_limit(self, block: BlockNode) -> Optional[BlockNode]:
        """从块中提取 limit 条件"""
        limit_prop = block.get_property('limit')
        if limit_prop and isinstance(limit_prop.value, BlockNode):
            return limit_prop.value
        return None
    
    def extract_body_without_limit(self, block: BlockNode) -> BlockNode:
        """提取块内容（排除 limit）"""
        limit_prop = block.get_property('limit')
        statements = [s for s in block.statements if s != limit_prop]
        return BlockNode(statements)
