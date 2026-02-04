"""
InlineScript 生成器

负责将 inline_script 转换为 Python 代码
遇到嵌套的 inline_script 时生成 meta.inline_script(...) 调用

工作流程：
1. 加载脚本文件并替换参数
2. 解析为 AST
3. 根据上下文（trigger/effect）生成代码
4. 嵌套的 inline_script 生成 meta.inline_script(...) 而不是展开
"""

from typing import List, Dict, Optional, Any, Union
from pathlib import Path
from enum import Enum, auto

from ..ast_nodes import BlockNode, PropertyNode, LiteralNode, ASTNode, ObjectNode
from ..inline_script_utils import (
    InlineScriptLoader,
    extract_script_info,
    replace_parameters,
    is_inline_script,
    format_meta_inline_script,
)
from .exceptions import UnsupportedFeatureError
from ..pdx_constants import safe_identifier


class InlineScriptContext(Enum):
    """内联脚本的嵌入上下文"""
    TRIGGER = auto()     # 嵌入在 trigger 中，生成条件表达式
    EFFECT = auto()      # 嵌入在 effect 中，生成动作语句
    DEFINITION = auto()  # 嵌入在定义块中（如 building），生成属性赋值
    RAW = auto()         # 原样返回 AST 内容（用于通用场景）


class InlineScriptGenerator:
    """
    InlineScript 生成器
    
    加载 inline_script 文件并根据上下文生成 Python 代码。
    嵌套的 inline_script 不展开，而是生成 meta.inline_script(...) 调用。
    """
    
    def __init__(self, game_root: Optional[Union[str, Path]] = None):
        """
        初始化生成器
        
        Args:
            game_root: 游戏根目录，如果不提供则从环境变量获取
        """
        if game_root is None:
            from ..config import config
            game_root = config.game_dir
        
        if game_root is None:
            raise ValueError("游戏目录未设置。请设置环境变量 STELLARIS_GAME_DIR 或传入 game_root 参数")
        
        self.loader = InlineScriptLoader(game_root)
        self.trigger_generator = None  # 延迟导入
        self.effect_generator = None
    
    def generate_from_node(
        self,
        node: PropertyNode,
        context: InlineScriptContext,
        scope_var: str = "scope"
    ) -> List[str]:
        """
        从 inline_script 属性节点生成代码
        
        Args:
            node: inline_script 属性节点
            context: 嵌入上下文
            scope_var: 当前作用域变量名
        
        Returns:
            生成的代码行列表
        """
        script_path, params = extract_script_info(node)
        
        if not script_path:
            return [f"# ERROR: Could not extract script path from inline_script"]
        
        return self.generate_from_path(script_path, context, params, scope_var)
    
    def generate_from_path(
        self,
        script_path: str,
        context: InlineScriptContext,
        parameters: Optional[Dict[str, Any]] = None,
        scope_var: str = "scope"
    ) -> List[str]:
        """
        从脚本路径生成代码
        
        Args:
            script_path: 脚本路径
            context: 嵌入上下文
            parameters: 脚本参数
            scope_var: 当前作用域变量名
        
        Returns:
            生成的代码行列表
        """
        # 加载脚本
        script_text = self.loader.load(script_path)
        if script_text is None:
            return [f"# ERROR: inline_script '{script_path}' not found"]
        
        # 替换参数
        if parameters:
            script_text = replace_parameters(script_text, 
                {k: str(v) for k, v in parameters.items()})
        
        # 解析为 AST
        from ..parser import parse
        wrapped = f"_wrapper = {{\n{script_text}\n}}"
        ast = parse(wrapped)

        if not ast.statements:
            raise ValueError(f"inline_script '{script_path}' produced empty AST")

        # 提取内容块
        first_stmt = ast.statements[0]
        if isinstance(first_stmt, ObjectNode):
            content_block = first_stmt.body
        else:
            content_block = BlockNode(ast.statements)

        # 生成代码（不递归展开，嵌套的 inline_script 生成 meta.inline_script）
        return self._generate_from_block(content_block, context, scope_var)
    
    def _generate_from_block(
        self,
        block: BlockNode,
        context: InlineScriptContext,
        scope_var: str
    ) -> List[str]:
        """从 BlockNode 生成代码"""
        if context == InlineScriptContext.TRIGGER:
            return self._generate_trigger_code(block, scope_var)
        elif context == InlineScriptContext.EFFECT:
            return self._generate_effect_code(block, scope_var)
        elif context == InlineScriptContext.DEFINITION:
            return self._generate_definition_code(block, scope_var)
        else:  # RAW
            return self._generate_raw_code(block, scope_var)
    
    def _generate_trigger_code(self, block: BlockNode, scope_var: str) -> List[str]:
        """生成 trigger 上下文的代码（返回表达式）"""
        # 检查是否有嵌套的 inline_script
        processed_block = self._process_nested_inline_scripts_for_trigger(block)
        
        if self.trigger_generator is None:
            from .trigger_generator import TriggerGenerator
            self.trigger_generator = TriggerGenerator()
        
        from .generators import ExpressionBuilder, GeneratorContext
        
        # 创建临时上下文（无需 ValueFormatter）
        temp_generator = type('TempGenerator', (), {
            'context': GeneratorContext(scope_var),
            'parameters': {}
        })()
        temp_generator.context.in_trigger = True
        
        expr_builder = ExpressionBuilder(temp_generator)
        expression = expr_builder.block_to_expression(processed_block)
        
        if expression:
            return [expression]
        return ["True"]
    
    def _generate_effect_code(self, block: BlockNode, scope_var: str) -> List[str]:
        """生成 effect 上下文的代码（返回语句列表）"""
        if self.effect_generator is None:
            from .effect_generator import EffectGenerator
            self.effect_generator = EffectGenerator()
        
        from .generators import (
            GeneratorContext, ExpressionBuilder,
            EffectLoopGenerator, EffectVariableGenerator, EffectBlockGenerator
        )
        
        # 重置生成器状态
        self.effect_generator.lines = []
        self.effect_generator.indent_level = 0
        self.effect_generator.context = GeneratorContext(scope_var)
        self.effect_generator.context.in_effect = True
        
        # 初始化子生成器（不使用 ValueFormatter）
        self.effect_generator.expr_builder = ExpressionBuilder(self.effect_generator)
        self.effect_generator.loop_gen = EffectLoopGenerator(self.effect_generator)
        self.effect_generator.var_gen = EffectVariableGenerator(self.effect_generator)
        self.effect_generator.block_gen = EffectBlockGenerator(self.effect_generator)
        
        # 处理块中的语句，嵌套 inline_script 特殊处理
        self._generate_effect_statements(block, scope_var)
        
        return self.effect_generator.lines
    
    def _generate_effect_statements(self, block: BlockNode, scope_var: str):
        """生成 effect 语句，处理嵌套的 inline_script"""
        for stmt in block.statements:
            if is_inline_script(stmt):
                # 嵌套的 inline_script：生成 meta.inline_script(...) 调用
                script_path, params = extract_script_info(stmt)
                if script_path:
                    meta_call = format_meta_inline_script(script_path, params)
                    self.effect_generator._add_line(meta_call)
            else:
                # 普通语句：递归处理
                self.effect_generator._generate_statement(stmt)
    
    def _process_nested_inline_scripts_for_trigger(self, block: BlockNode) -> BlockNode:
        """
        处理 trigger 块中嵌套的 inline_script
        
        将 inline_script 节点转换为特殊的表达式节点，
        以便在表达式构建时生成 meta.inline_script(...)
        """
        # 对于 trigger，嵌套的 inline_script 需要特殊标记
        # 这里暂时保持原样，因为 trigger 中的 inline_script 较少见
        # TODO: 如果需要，可以添加专门的处理逻辑
        return block
    
    def _generate_definition_code(self, block: BlockNode, scope_var: str) -> List[str]:
        """
        生成定义块上下文的代码（如 building 顶级块）
        
        在这种上下文中，inline_script 展开的内容是属性定义，
        如 planet_modifier、triggered_planet_modifier 等
        """
        lines = []
        
        for stmt in block.statements:
            if is_inline_script(stmt):
                # 嵌套的 inline_script：生成 meta.inline_script(...) 调用
                script_path, params = extract_script_info(stmt)
                if script_path:
                    meta_call = format_meta_inline_script(script_path, params)
                    lines.append(meta_call)
            elif isinstance(stmt, PropertyNode):
                # 属性定义：生成赋值或方法调用
                lines.append(self._generate_definition_property(stmt, scope_var))
            else:
                # 其他节点：生成注释
                lines.append(f"# Unhandled definition node: {type(stmt).__name__}")
        
        return lines
    
    def _generate_definition_property(self, prop: PropertyNode, scope_var: str) -> str:
        """生成定义块中的属性代码"""
        key = prop.key
        value = prop.value
        
        # 特殊处理常见的定义属性
        if isinstance(value, LiteralNode):
            # 简单属性：planet_housing_add = 100
            val_str = self._format_literal(value)
            return f"{scope_var}.{safe_identifier(str(key))} = {val_str}"
        elif isinstance(value, BlockNode):
            # 块属性：planet_modifier = { ... }
            # 生成方法调用形式
            args = self._block_to_kwargs(value)
            if args:
                return f"{scope_var}.{safe_identifier(str(key))}({args})"
            else:
                return f"{scope_var}.{safe_identifier(str(key))}()"
        else:
            # 其他未处理的类型
            raise UnsupportedFeatureError(
                f"在 inline_script 属性生成中遇到未处理的类型: {type(value).__name__}，"
                f"键名: {key}"
            )
    
    def _format_literal(self, node: LiteralNode) -> str:
        """格式化字面量值"""
        val = node.value
        if isinstance(val, str):
            # 检查是否是变量引用 (@var) 或特殊标识符
            if val.startswith('@') or val in ('yes', 'no', 'true', 'false'):
                return repr(val)
            # 尝试判断是否是数字
            try:
                if '.' in val:
                    return str(float(val))
                return str(int(val))
            except (ValueError, TypeError):
                return repr(val)
        return repr(val)
    
    def _block_to_kwargs(self, block: BlockNode) -> str:
        """将块转换为关键字参数字符串"""
        parts = []
        for stmt in block.statements:
            if isinstance(stmt, PropertyNode):
                key = str(stmt.key)
                if isinstance(stmt.value, LiteralNode):
                    val = self._format_literal(stmt.value)
                elif isinstance(stmt.value, BlockNode):
                    # 嵌套块不应该在这里处理，应该被展开或生成为完整代码
                    raise UnsupportedFeatureError(
                        f"在 inline_script 参数中遇到嵌套块 {key}={{...}}，"
                        f"包含 {len(stmt.value.statements)} 个语句。"
                        f"这需要特殊处理或展开，不能简单地转换为字符串"
                    )
                else:
                    val = repr(str(stmt.value))
                parts.append(f"{safe_identifier(key)}={val}")
        return ", ".join(parts)
    
    def _generate_raw_code(self, block: BlockNode, scope_var: str) -> List[str]:
        """
        生成原始代码（通用场景）
        
        简单地将每个语句转换为字符串表示
        """
        lines = []
        
        for stmt in block.statements:
            if is_inline_script(stmt):
                script_path, params = extract_script_info(stmt)
                if script_path:
                    meta_call = format_meta_inline_script(script_path, params)
                    lines.append(meta_call)
            elif isinstance(stmt, PropertyNode):
                key = str(stmt.key)
                if isinstance(stmt.value, LiteralNode):
                    lines.append(f"{key} = {self._format_literal(stmt.value)}")
                elif isinstance(stmt.value, BlockNode):
                    lines.append(f"{key} = {{ ... }}")
                else:
                    lines.append(f"{key} = {stmt.value}")
            else:
                lines.append(f"# {type(stmt).__name__}")
        
        return lines


# 便捷函数

def generate_inline_script(
    script_path: str,
    context: InlineScriptContext,
    parameters: Optional[Dict[str, Any]] = None,
    scope_var: str = "scope",
    game_root: Optional[Union[str, Path]] = None
) -> List[str]:
    """从脚本路径生成代码"""
    generator = InlineScriptGenerator(game_root)
    return generator.generate_from_path(script_path, context, parameters, scope_var)


def generate_from_inline_script_node(
    node: PropertyNode,
    context: InlineScriptContext,
    scope_var: str = "scope",
    game_root: Optional[Union[str, Path]] = None
) -> List[str]:
    """从 AST 节点生成代码"""
    generator = InlineScriptGenerator(game_root)
    return generator.generate_from_node(node, context, scope_var)
