"""
Effect 循环遍历生成器

处理 every_*, random_*, ordered_* 等循环语句
"""

from typing import Tuple, List, Optional
from ...ast_nodes import BlockNode, PropertyNode
from ...pdx_constants import LOOP_PREFIXES, LOOP_MAPPINGS


class EffectLoopGenerator:
    """Effect 循环生成器"""
    
    # 使用集中管理的常量
    LOOP_PREFIXES = LOOP_PREFIXES
    LOOP_MAPPINGS = LOOP_MAPPINGS
    
    def __init__(self, parent_generator):
        self.parent = parent_generator
        self.context = parent_generator.context
    
    def is_loop(self, key: str) -> bool:
        """判断是否是循环关键字"""
        for prefix in self.LOOP_PREFIXES:
            if key.startswith(prefix):
                return True
        return False
    
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
            if isinstance(stmt, PropertyNode) and stmt.key == 'limit':
                limit_block = stmt.value
            else:
                body_stmts.append(stmt)
        
        # 推断迭代器名称和集合
        iter_var, collection = self._parse_loop_type(key)
        
        # 生成 for 循环
        self.parent._add_line(f"for {iter_var} in {self.context.current_scope_var}.{collection}:")
        self.parent._indent()
        
        # 如果有 limit，生成 continue 条件
        if limit_block:
            self._generate_limit_condition(limit_block, iter_var)
        
        # 保存并切换作用域
        old_scope = self.context.current_scope_var
        self.context.current_scope_var = iter_var
        
        # 生成循环体
        if body_stmts:
            body_block = BlockNode(body_stmts)
            self.parent._generate_effect_body(body_block)
        else:
            self.parent._add_line("pass")
        
        # 恢复作用域
        self.context.current_scope_var = old_scope
        self.parent._dedent()
        
        return True
    
    def _generate_limit_condition(self, limit_block: BlockNode, iter_var: str):
        """生成 limit 作为 continue 条件"""
        # 保存作用域，切换到循环变量
        old_scope = self.context.current_scope_var
        self.context.current_scope_var = iter_var
        
        condition = self.parent.expr_builder.block_to_expression(limit_block)
        
        # 恢复作用域
        self.context.current_scope_var = old_scope
        
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
    
    def _parse_loop_type(self, loop_type: str) -> Tuple[str, str]:
        """解析循环类型，返回 (迭代变量名, 集合名)"""
        # 去掉 every_, random_, ordered_ 前缀
        base_type = loop_type
        for prefix in self.LOOP_PREFIXES:
            if loop_type.startswith(prefix):
                base_type = loop_type[len(prefix):]
                break
        
        if base_type in self.LOOP_MAPPINGS:
            return self.LOOP_MAPPINGS[base_type]
        
        # 默认：去掉复数 s
        if base_type.endswith('s'):
            return (base_type[:-1], base_type)
        return (base_type, f"{base_type}s")
