"""
基础生成器类

定义所有生成器共用的基础设施
"""

from typing import List, Optional
from abc import ABC, abstractmethod
from ...ast_nodes import *
from ...pdx_constants import COMPARISON_OPS, LOGIC_OPERATORS, METHOD_PREFIXES


class GeneratorContext:
    """生成器上下文 - 跟踪生成状态"""
    
    def __init__(self, scope_var: str = "scope"):
        self.scope_stack = [scope_var]       # 作用域栈
        self.temp_var_counter = 0            # 临时变量计数
        self.loop_var_counter = 0            # 循环变量计数
        self.in_loop = False                 # 是否在循环中
        self.in_trigger = False              # 是否在 trigger 上下文
        self.in_effect = False               # 是否在 effect 上下文
        self.current_scope_var = scope_var   # 当前作用域变量
        
        # 格式化配置
        self.max_line_length = 88            # 最大行长度 (Black 风格)
        self.indent_str = "    "             # 缩进字符串
        self.current_indent = 0              # 当前缩进层级（用于表达式换行）
    
    def push_scope(self, scope_name: str) -> str:
        """进入新作用域，返回新的作用域变量名"""
        self.scope_stack.append(scope_name)
        self.current_scope_var = scope_name
        return scope_name
    
    def pop_scope(self):
        """退出作用域"""
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
            self.current_scope_var = self.scope_stack[-1]
    
    def get_temp_var(self, prefix: str = "_temp") -> str:
        """生成临时变量名"""
        self.temp_var_counter += 1
        return f"{prefix}_{self.temp_var_counter}"
    
    def get_loop_var(self, item_type: str = "item") -> str:
        """生成循环变量名"""
        self.loop_var_counter += 1
        return f"{item_type}_{self.loop_var_counter}" if self.loop_var_counter > 1 else item_type
    
    def reset(self):
        """重置计数器（用于新的函数生成）"""
        self.temp_var_counter = 0
        self.loop_var_counter = 0


class BaseExpressionGenerator(ABC):
    """表达式生成器基类"""
    
    # 使用集中管理的常量
    COMPARISON_OPS = COMPARISON_OPS
    LOGIC_OPERATORS = LOGIC_OPERATORS
    METHOD_PREFIXES = METHOD_PREFIXES
    
    def __init__(self):
        self.indent_level = 0
        self.lines: List[str] = []
        self.context: Optional[GeneratorContext] = None
    
    # === 代码行管理 ===
    
    def _add_line(self, line: str = ""):
        """添加一行代码（支持多行字符串）"""
        if not line:
            self.lines.append("")
            return
            
        indent = "    " * self.indent_level
        
        # 处理多行表达式
        if '\n' in line:
            sub_lines = line.split('\n')
            # 第一行使用当前缩进
            self.lines.append(indent + sub_lines[0])
            # 后续行添加额外缩进以对齐
            continuation_indent = indent + "    "
            for sub_line in sub_lines[1:]:
                self.lines.append(continuation_indent + sub_line)
        else:
            self.lines.append(indent + line)
    
    def _indent(self):
        """增加缩进"""
        self.indent_level += 1
        if self.context:
            self.context.current_indent = self.indent_level
    
    def _dedent(self):
        """减少缩进"""
        if self.indent_level > 0:
            self.indent_level -= 1
        if self.context:
            self.context.current_indent = self.indent_level
    
    # === 辅助方法 ===
    
    def _is_method_call(self, key: str) -> bool:
        """判断是否是方法调用"""
        for prefix in self.METHOD_PREFIXES:
            if key.startswith(prefix):
                return True
        
        # 其他已知的方法名
        known_methods = {
            'check_variable', 'free_jobs_of_type', 'count_owned_planet',
            'set_variable', 'change_variable', 'clear_variable'
        }
        
        return key in known_methods
    
    @abstractmethod
    def generate(self, *args, **kwargs) -> List[str]:
        """生成代码（子类实现）"""
        pass
