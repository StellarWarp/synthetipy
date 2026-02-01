"""
作用域管理器

处理作用域切换和嵌套：
- owner = { ... }
- any_owned_planet = { ... }
- every_owned_planet = { ... }
"""

from typing import Optional
from ...ast_nodes import *
from ...pdx_constants import SCOPE_SWITCHES, ITERATION_SCOPES


class ScopeManager:
    """作用域管理器"""
    
    # 使用集中管理的常量
    SCOPE_SWITCHES = SCOPE_SWITCHES
    ITERATION_SCOPES = ITERATION_SCOPES
    
    def __init__(self, parent_generator):
        self.parent = parent_generator
        self.context = parent_generator.context
    
    def is_scope_switch(self, key: str) -> bool:
        """判断是否是简单作用域切换"""
        return key in self.SCOPE_SWITCHES
    
    def is_iteration_scope(self, key: str) -> bool:
        """判断是否是迭代作用域"""
        return key in self.ITERATION_SCOPES or key.startswith('any_') or key.startswith('every_')
    
    def generate_scope_switch(self, key: str, block: BlockNode):
        """
        生成简单作用域切换
        
        owner = { is_ai = yes }
        
        -> with scope.owner as owner:
               return owner.is_ai
        """
        scope_var = self.context.get_temp_var(key)
        
        self.parent._add_line(f"with {self.context.current_scope_var}.{key} as {scope_var}:")
        self.parent._indent()
        
        # 进入新作用域
        self.context.push_scope(scope_var)
        
        # 生成块内容（由调用者提供）
        # 这个方法主要是设置框架
        
        return scope_var
    
    def exit_scope_switch(self):
        """退出作用域切换"""
        self.context.pop_scope()
        self.parent._dedent()
    
    def get_iteration_info(self, key: str) -> Optional[tuple]:
        """
        获取迭代信息
        
        Returns:
            (collection_name, item_type) 或 None
            例如: ('owned_planets', 'planet')
        """
        if key in self.ITERATION_SCOPES:
            return self.ITERATION_SCOPES[key]
        
        # 动态推断
        if key.startswith('any_owned_'):
            item_type = key[10:]  # 去掉 'any_owned_'
            return (f'owned_{item_type}s', item_type)
        elif key.startswith('every_owned_'):
            item_type = key[12:]  # 去掉 'every_owned_'
            return (f'owned_{item_type}s', item_type)
        elif key.startswith('any_'):
            item_type = key[4:]  # 去掉 'any_'
            return (f'{item_type}s', item_type)
        elif key.startswith('every_'):
            item_type = key[6:]  # 去掉 'every_'
            return (f'{item_type}s', item_type)
        
        return None
