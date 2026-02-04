"""
表达式生成器模块

包含 trigger、effect 和 value 生成器共用的逻辑组件
"""

from .base_generator import BaseExpressionGenerator, GeneratorContext
from .control_flow import ControlFlowGenerator
from .logic_blocks import LogicBlockGenerator
from .expression_builder import ExpressionBuilder
from .special_calls import SpecialCallHandler
from .scope_translator import ScopeTranslator

# Effect 专用生成器
from .effect_loops import EffectLoopGenerator
from .effect_variables import EffectVariableGenerator
from .effect_blocks import EffectBlockGenerator

__all__ = [
    'BaseExpressionGenerator',
    'GeneratorContext',
    'ControlFlowGenerator',
    'LogicBlockGenerator',
    'ExpressionBuilder',
    'SpecialCallHandler',
    'ScopeTranslator',
    # Effect 专用
    'EffectLoopGenerator',
    'EffectVariableGenerator',
    'EffectBlockGenerator',
]
