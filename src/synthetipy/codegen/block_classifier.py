"""
块类型识别器
用于识别 PDX 代码块的类型：trigger、effect、value、nested_object

使用自动生成的游戏规则进行精确识别
"""

from typing import Optional, List
from ..ast_nodes import *
from ..game_rules import (
    ALL_TRIGGERS, ALL_EFFECTS, SCOPES,
    SHARED_IDENTIFIERS, TRIGGER_EXCLUSIVE, EFFECT_EXCLUSIVE,
    CONTROL_FLOW_BLOCKS, HIDDEN_BLOCKS, RANDOM_BLOCKS
)
from ..pdx_constants import FILE_TYPE_RULES, LOGIC_OPERATORS


# ============================================
# 键名知识库（从游戏文档自动生成）
# ============================================

# Trigger 块的键名（从游戏文档提取）
TRIGGER_KEYS = TRIGGER_EXCLUSIVE | SHARED_IDENTIFIERS

# Effect 块的键名（从游戏文档提取）
EFFECT_KEYS = EFFECT_EXCLUSIVE | SHARED_IDENTIFIERS

# Value 块的键名（权重计算相关）
VALUE_KEYS = {
    'base', 'weight', 'factor',
}

# 特殊结构（需要上下文判断）
CONTEXT_DEPENDENT_KEYS = {
    'modifier',  # 在 script_values 中是算术操作，在其他地方是嵌套对象
    'ai_weight',  # 可能是 value，也可能是包含 weight 的嵌套对象
}

# 特殊结构（需要上下文判断）
CONTEXT_DEPENDENT_KEYS = {
    'modifier',  # 在 script_values 中是算术操作，在其他地方是嵌套对象
    'ai_weight',  # 可能是 value，也可能是包含 weight 的嵌套对象
}


# ============================================
# 文件类型规则
# ============================================

# 文件类型规则从 pdx_constants 导入


# ============================================
# 结构分析器
# ============================================

def analyze_block_structure(block: BlockNode) -> str:
    """
    通过分析块的结构推断类型（当键名不在已知规则中时使用）
    
    Args:
        block: 要分析的块节点
    
    Returns:
        'trigger' | 'effect' | 'value' | 'nested_object'
    """
    if not block.statements:
        return 'nested_object'
    
    # 统计特征
    has_comparisons = False      # 比较运算符 (>=, <, etc.)
    has_logic_ops = False        # 逻辑运算符 (AND, OR, NOT)
    has_known_triggers = False   # 已知的 trigger 标识符
    has_known_effects = False    # 已知的 effect 标识符
    has_arithmetic = False       # 算术操作 (add, multiply)
    
    for stmt in block.statements:
        if isinstance(stmt, ComparisonNode):
            has_comparisons = True
        elif isinstance(stmt, PropertyNode):
            key = stmt.key if isinstance(stmt.key, str) else str(stmt.key)
            
            # 检查是否是已知的 trigger/effect
            if key in TRIGGER_KEYS:
                has_known_triggers = True
            elif key in EFFECT_KEYS:
                has_known_effects = True
            
            # 逻辑运算符
            if key in LOGIC_OPERATORS:
                has_logic_ops = True
            
            # Value 特征
            elif key in ('base', 'add', 'multiply', 'factor', 'weight'):
                has_arithmetic = True
    
    # 推断类型（基于游戏规则）
    if has_arithmetic and not (has_logic_ops or has_known_triggers or has_known_effects):
        return 'value'
    elif has_known_triggers or has_logic_ops or has_comparisons:
        return 'trigger'
    elif has_known_effects:
        return 'effect'
    else:
        return 'nested_object'


# ============================================
# 块类型分类器
# ============================================

class BlockClassifier:
    """块类型分类器"""
    
    def __init__(self, file_path: str):
        """
        初始化分类器
        
        Args:
            file_path: 当前处理的文件路径
        """
        self.file_path = file_path
        self.file_type = self._get_file_type(file_path)
        self.context_stack: List[str] = []  # 上下文栈
    
    def _get_file_type(self, file_path: str) -> str:
        """
        根据文件路径获取默认类型
        
        Args:
            file_path: 文件路径
        
        Returns:
            'trigger' | 'effect' | 'value' | 'object' | 'event'
        """
        file_path = file_path.replace('\\', '/')
        
        for pattern, obj_type in FILE_TYPE_RULES.items():
            if pattern in file_path:
                return obj_type
        
        return 'object'  # 默认
    
    def classify_block(self, key: str, block: BlockNode) -> str:
        """
        分类一个块
        
        Args:
            key: 键名
            block: 块节点
        
        Returns:
            'trigger' | 'effect' | 'value' | 'nested_object'
        """
        # 1. 优先级最高：显式键名规则
        if key in TRIGGER_KEYS:
            return 'trigger'
        elif key in EFFECT_KEYS:
            return 'effect'
        elif key in VALUE_KEYS:
            return 'value'
        
        # 2. 上下文相关的键
        if key in CONTEXT_DEPENDENT_KEYS:
            if key == 'modifier' and self.file_type == 'value':
                return 'value'
            elif key == 'ai_weight':
                # 分析结构：如果有 base/factor/weight 子键，则是 value
                for stmt in block.statements:
                    if isinstance(stmt, PropertyNode):
                        sub_key = stmt.key if isinstance(stmt.key, str) else str(stmt.key)
                        if sub_key in ('base', 'factor', 'weight', 'modifier'):
                            return 'value'
            # 否则是嵌套对象
            return 'nested_object'
        
        # 3. 文件级别规则（仅用于顶层）
        if not self.context_stack and self.file_type in ('trigger', 'effect', 'value'):
            return self.file_type
        
        # 4. 结构分析
        inferred_type = analyze_block_structure(block)
        if inferred_type != 'nested_object':
            return inferred_type
        
        # 5. 默认为嵌套对象
        return 'nested_object'
    
    def push_context(self, name: str):
        """进入一个上下文"""
        self.context_stack.append(name)
    
    def pop_context(self):
        """退出当前上下文"""
        if self.context_stack:
            self.context_stack.pop()
    
    def get_current_context(self) -> Optional[str]:
        """获取当前上下文名称"""
        return self.context_stack[-1] if self.context_stack else None
    
    def is_top_level(self) -> bool:
        """是否是顶层"""
        return len(self.context_stack) == 0
