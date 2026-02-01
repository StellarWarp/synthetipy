"""
运行时依赖配置 - 统一管理所有代码生成的运行时依赖

这个模块集中管理：
1. 装饰器（@trigger, @effect, @value）
2. Import 语句
3. 辅助函数（meta.pdx, meta.inline_script, logic.xxx）
4. 字面量处理规则
"""

from typing import List, Set
from dataclasses import dataclass


@dataclass
class RuntimeDependencies:
    """运行时依赖配置"""
    
    # 基础 import（所有文件都需要）
    BASE_IMPORTS = [
        "from synthetipy import objects, scope"
    ]
    
    # 逻辑运算符 import（trigger 需要）
    LOGIC_IMPORTS = [
        "from synthetipy import logic"
    ]
    
    # meta 工具 import（使用 pdx/inline_script 时需要）
    META_IMPORTS = [
        "from synthetipy import meta"
    ]
    
    # 装饰器
    TRIGGER_DECORATOR = "@trigger"
    EFFECT_DECORATOR = "@effect"
    VALUE_DECORATOR = "@value"
    
    # meta 函数调用
    META_PDX_CALL = "meta.pdx"
    META_INLINE_SCRIPT = "meta.inline_script"
    
    # 逻辑运算符
    LOGIC_AND = "logic.AND"
    LOGIC_OR = "logic.OR"
    LOGIC_NOT = "logic.NOT"
    LOGIC_NAND = "logic.NAND"
    LOGIC_NOR = "logic.NOR"
    
    # 需要自动加引号的标识符模式
    # 这些是游戏中的常量/枚举，应该被当作字符串字面量
    STELLARIS_IDENTIFIERS = {
        # 科技
        'tech_',
        # 建筑
        'building_',
        # 修正
        'modifier_',
        # 特质
        'trait_',
        # 政策
        'policy_',
        # 法令
        'edict_',
        # 区划
        'district_',
        # 职位
        'job_',
        # 舰船类型
        'shipsize_',
        # 组件
        'component_',
    }


class ImportManager:
    """Import 语句管理器"""
    
    def __init__(self):
        self.imports: Set[str] = set()
        self.needs_logic = False
        self.needs_meta = False
    
    def add_base_imports(self):
        """添加基础 import"""
        for imp in RuntimeDependencies.BASE_IMPORTS:
            self.imports.add(imp)
    
    def add_logic_imports(self):
        """添加逻辑运算 import"""
        self.needs_logic = True
        for imp in RuntimeDependencies.LOGIC_IMPORTS:
            self.imports.add(imp)
    
    def add_meta_imports(self):
        """添加 meta 工具 import"""
        self.needs_meta = True
        for imp in RuntimeDependencies.META_IMPORTS:
            self.imports.add(imp)
    
    def get_import_lines(self) -> List[str]:
        """获取所有 import 语句"""
        return sorted(list(self.imports))


def should_quote_identifier(name: str) -> bool:
    """
    判断标识符是否应该被当作字符串字面量
    
    Args:
        name: 标识符名称
    
    Returns:
        True 如果应该加引号
    """
    if not isinstance(name, str):
        return False
    
    # 检查是否以特定前缀开头
    for prefix in RuntimeDependencies.STELLARIS_IDENTIFIERS:
        if name.startswith(prefix):
            return True
    
    return False


def format_identifier(name: str) -> str:
    """
    格式化标识符 - 如果是游戏常量则加引号
    
    Args:
        name: 标识符名称
    
    Returns:
        格式化后的字符串（可能带引号）
    """
    if should_quote_identifier(name):
        return repr(name)
    return name


def get_decorator_for_type(file_type: str) -> str:
    """
    获取文件类型对应的装饰器
    
    Args:
        file_type: 'trigger', 'effect', 'value'
    
    Returns:
        装饰器字符串
    """
    decorators = {
        'trigger': RuntimeDependencies.TRIGGER_DECORATOR,
        'effect': RuntimeDependencies.EFFECT_DECORATOR,
        'value': RuntimeDependencies.VALUE_DECORATOR,
    }
    return decorators.get(file_type, '')


def format_pdx_call(content: str, **params) -> str:
    """
    格式化 meta.pdx() 调用
    
    Args:
        content: PDX 代码内容
        **params: 宏参数
    
    Returns:
        格式化的 meta.pdx() 调用字符串
    """
    if not params:
        return f'{RuntimeDependencies.META_PDX_CALL}("""{content}""")'
    
    param_strs = [f'{k}={v}' for k, v in params.items()]
    params_part = ', '.join(param_strs)
    return f'{RuntimeDependencies.META_PDX_CALL}("""{content}""", {params_part})'


def format_inline_script_call(script_path: str, **params) -> str:
    """
    格式化 meta.inline_script() 调用
    
    Args:
        script_path: 脚本路径
        **params: 参数
    
    Returns:
        格式化的 meta.inline_script() 调用字符串
    """
    if not params:
        return f'{RuntimeDependencies.META_INLINE_SCRIPT}("{script_path}")'
    
    param_strs = [f'{k}={v}' for k, v in params.items()]
    params_part = ', '.join(param_strs)
    return f'{RuntimeDependencies.META_INLINE_SCRIPT}("{script_path}", {params_part})'
