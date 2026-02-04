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
        """检查块是否包含控制流（if/else）、循环或 scope 切换"""
        for stmt in block.statements:
            if isinstance(stmt, PropertyNode):
                # if/else/else_if/else
                if str(stmt.key) in ('if', 'else_if', 'else') and isinstance(stmt.value, BlockNode):
                    return True
                # iteration scopes (every_*, random_*)
                if hasattr(self.parent, 'scope_translator') and self.parent.scope_translator.is_iteration_scope(stmt.key):
                    return True
                # scope LHS (owner = { ... })
                if hasattr(self.parent, 'scope_translator') and self.parent.scope_translator.is_scope_lhs(stmt.key) and isinstance(stmt.value, BlockNode):
                    return True
        return False
    
    def generate_control_flow(
        self,
        prop: PropertyNode,
        branch_handler: Callable[[BlockNode, str], None]
    ) -> bool:
        """处理单个 PropertyNode 的控制流/循环/作用域逻辑。

        Returns True 如果该 PropertyNode 被处理（已生成代码），否则返回 False。
        """
        # 对非 PropertyNode 明确返回 False
        if not isinstance(prop, PropertyNode):
            return False

        key_str = str(prop.key)

        # if / else_if / else
        if key_str == 'if' and isinstance(prop.value, BlockNode):
            self._generate_if_branch(prop.value, 'if', branch_handler)
            return True
        if key_str == 'else_if' and isinstance(prop.value, BlockNode):
            self._generate_if_branch(prop.value, 'elif', branch_handler)
            return True
        if key_str == 'else' and isinstance(prop.value, BlockNode):
            self.parent._add_line('else:')
            self.parent._indent()
            branch_handler(prop.value, 'else')
            self.parent._dedent()
            return True

        # iteration
        if hasattr(self.parent, 'scope_translator') and self.parent.scope_translator.is_iteration_scope(prop.key):
            if hasattr(self.parent, 'loop_gen') and self.parent.loop_gen:
                self.parent.loop_gen.generate_loop(str(prop.key), prop.value)
                return True
            else:
                raise RuntimeError("Loop generator not available on parent for iteration scope")

        # scope switch
        if hasattr(self.parent, 'scope_translator') and self.parent.scope_translator.is_scope_lhs(prop.key) and isinstance(prop.value, BlockNode):
            scope_key = str(prop.key)
            scope_var = self.parent.scope_translator.enter_scope_block(scope_key)
            branch_handler(prop.value, 'scope')
            self.parent.scope_translator.exit_scope_block()
            return True

        return False
    
    def _generate_if_branch(
        self,
        if_block: BlockNode,
        keyword: str,
        branch_handler: Callable[[BlockNode, str], None]
    ):
        """生成 if/elif 分支

        if_block 结构：
        {
            limit = { ... }  # 条件
            ...              # 满足条件时的内容
        }
        """
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
            
            expr_builder = ExpressionBuilder(self.parent, self.parent.value_formatter)
            limit_expr = expr_builder.block_to_expression(limit_prop.value)
            
            # If limit expression could not be converted, raise a clear error rather than
            # generating invalid Python like `if None:`.
            if not limit_expr:
                from ..exceptions import MissingConditionError
                raise MissingConditionError(
                    f"{keyword} block limit could not be converted to an expression"
                )

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