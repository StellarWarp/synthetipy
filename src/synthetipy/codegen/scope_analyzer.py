"""
作用域分析器

分析 PDX 代码中的作用域使用，推断类型和参数
"""

from typing import Optional, List, Dict, Set
from ..ast_nodes import *


class ScopeAnalyzer:
    """作用域分析器"""
    
    # 作用域类型映射（简化版）
    SCOPE_TYPES = {
        'planet': 'scope.Planet',
        'country': 'scope.Country',
        'pop': 'scope.Pop',
        'ship': 'scope.Ship',
        'fleet': 'scope.Fleet',
        'leader': 'scope.Leader',
        'system': 'scope.System',
        'starbase': 'scope.Starbase',
        'megastructure': 'scope.Megastructure',
    }
    
    def __init__(self):
        self.used_scopes: Set[str] = set()
    
    def infer_scope_type(self, method_name: str, parent_context: Optional[str] = None) -> str:
        """
        根据方法名和上下文推断作用域类型
        
        Args:
            method_name: 方法名（如 'potential', 'on_built'）
            parent_context: 父级上下文（如 'building', 'district'）
        
        Returns:
            作用域类型字符串（如 'scope.Planet'）
        """
        # TODO: 实现更复杂的推断逻辑
        
        # 建筑相关方法通常使用 planet 作用域
        if parent_context in ('building', 'district'):
            return 'scope.Planet'
        
        # 科技相关方法通常使用 country 作用域
        elif parent_context == 'technology':
            return 'scope.Country'
        
        # 默认使用通用作用域
        else:
            return 'scope.Scope'
    
    def analyze_block(self, block: BlockNode) -> Dict[str, any]:
        """
        分析块中使用的作用域
        
        Args:
            block: 要分析的块节点
        
        Returns:
            分析结果字典
        """
        self.used_scopes = set()
        
        # 遍历块中的语句
        for stmt in block.statements:
            if isinstance(stmt, PropertyNode):
                key = str(stmt.key) if not isinstance(stmt.key, str) else stmt.key
                
                # 检测作用域切换关键字
                if key in ('owner', 'capital', 'planet', 'country', 'fleet'):
                    self.used_scopes.add(key)
        
        return {
            'used_scopes': list(self.used_scopes),
            'requires_scope_param': len(self.used_scopes) > 0,
        }
    
    def get_scope_chain(self, expr: str) -> List[str]:
        """
        解析作用域链
        
        Args:
            expr: 表达式字符串（如 'owner.capital.size'）
        
        Returns:
            作用域链列表
        """
        # TODO: 实现完整的作用域链解析
        parts = expr.split('.')
        return parts
