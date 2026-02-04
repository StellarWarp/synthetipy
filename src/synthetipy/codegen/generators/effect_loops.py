"""
Effect 循环遍历生成器

处理 every_*, random_*, ordered_* 等循环语句
仅负责循环体生成，循环判断和scope管理委托给ScopeTranslator
"""

from typing import Tuple, List, Optional
from ...ast_nodes import BlockNode, PropertyNode


class EffectLoopGenerator:
    """Effect 循环生成器 - 仅处理循环体生成，循环判断和scope管理委托给ScopeTranslator"""
    
    def __init__(self, parent_generator):
        self.parent = parent_generator
    
    def generate_loop(self, key: str, value: BlockNode) -> bool:
        """
        生成循环语句
        
        every_owned_planet = { ... } -> for planet in scope.owned_planets: ...
        """
        if not isinstance(value, BlockNode):
            return False
        
        # 提取 limit 和 body
        limit_block = None
        body_stmts = []
        
        for stmt in value.statements:
            if isinstance(stmt, PropertyNode) and str(stmt.key) == 'limit':
                limit_block = stmt.value
            else:
                body_stmts.append(stmt)
        
        # 使用ScopeTranslator进入循环（自动管理scope和生成for语句）
        loop_var = self.parent.scope_translator.enter_iteration_loop(key)
        
        # 如果有 limit，生成 continue 条件
        if limit_block:
            self._generate_limit_condition(limit_block)
        
        # 生成循环体
        if body_stmts:
            body_block = BlockNode(body_stmts)
            self.parent._generate_effect_body(body_block)
        else:
            self.parent._add_line("pass")
        
        # 使用ScopeTranslator退出循环（自动恢复scope）
        self.parent.scope_translator.exit_iteration_loop()
        
        return True
    
    def _generate_limit_condition(self, limit_block: BlockNode):
        """生成 limit 作为 continue 条件"""
        # scope已经由ScopeTranslator管理，直接生成条件表达式
        condition = self.parent.expr_builder.block_to_expression(limit_block)
        
        # 智能否定处理：避免双重否定
        if condition.startswith("not "):
            # not xxx -> if xxx: continue
            positive_condition = condition[4:]
            self.parent._add_line(f"if {positive_condition}:")
        else:
            # xxx -> if not xxx: continue
            self.parent._add_line(f"if not {condition}:")
        
        self.parent._indent()
        self.parent._add_line("continue")
        self.parent._dedent()
