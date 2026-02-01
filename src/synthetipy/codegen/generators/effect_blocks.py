"""
Effect 块效果生成器

处理带参数块的效果，如 add_modifier, fire_event 等
"""

from typing import Dict, List, Any
from ...ast_nodes import ASTNode, BlockNode, PropertyNode, LiteralNode
from ...pdx_constants import BLOCK_EFFECTS, PRIMARY_KEYS, RESOURCE_KEYS
from ..runtime_deps import format_identifier


# 检查 InlineScriptNode 是否可用
try:
    from ...ast_nodes import InlineScriptNode
    HAS_INLINE_SCRIPT_NODE = True
except ImportError:
    HAS_INLINE_SCRIPT_NODE = False


class EffectBlockGenerator:
    """Effect 块效果生成器"""
    
    # 使用集中管理的常量
    BLOCK_EFFECTS = BLOCK_EFFECTS
    PRIMARY_KEYS = PRIMARY_KEYS
    RESOURCE_KEYS = RESOURCE_KEYS
    
    def __init__(self, parent_generator):
        self.parent = parent_generator
        self.context = parent_generator.context
    
    def is_block_effect(self, key: str) -> bool:
        """判断是否是块效果"""
        return key in self.BLOCK_EFFECTS
    
    def generate_block_effect(self, key: str, value: BlockNode) -> bool:
        """
        生成带参数块的效果
        
        add_modifier = { modifier = x years = 10 }
        -> scope.add_modifier('x', years=10)
        """
        if not isinstance(value, BlockNode):
            return False
        
        # 提取参数
        args = []
        kwargs = {}
        
        for stmt in value.statements:
            if isinstance(stmt, PropertyNode):
                k = stmt.key if isinstance(stmt.key, str) else str(stmt.key)
                v = self._extract_value(stmt.value)
                
                # 主参数
                if k in self.PRIMARY_KEYS:
                    args.insert(0, f"'{v}'")
                # 资源类型作为第一个参数
                elif k in self.RESOURCE_KEYS:
                    args.insert(0, f"'{k}'")
                    args.append(str(v))
                else:
                    # 其他作为关键字参数
                    kwargs[k] = v
        
        # 构建方法调用
        all_args = args + [f"{k}={self._format_kwarg(v)}" for k, v in kwargs.items()]
        args_str = ", ".join(all_args)
        
        self.parent._add_line(f"{self.context.current_scope_var}.{key}({args_str})")
        return True
    
    def generate_method_call(self, key: str, value: BlockNode) -> bool:
        """
        生成通用方法调用（未知的块效果）
        """
        # 提取所有参数
        kwargs = {}
        for stmt in value.statements:
            if isinstance(stmt, PropertyNode):
                k = stmt.key if isinstance(stmt.key, str) else str(stmt.key)
                v = self._extract_value(stmt.value)
                kwargs[k] = v
        
        if kwargs:
            args_str = ", ".join(f"{k}={self._format_kwarg(v)}" for k, v in kwargs.items())
            self.parent._add_line(f"{self.context.current_scope_var}.{key}({args_str})")
        else:
            self.parent._add_line(f"{self.context.current_scope_var}.{key}()")
        
        return True
    
    def generate_simple_effect(self, key: str, value: ASTNode) -> bool:
        """
        生成简单效果
        
        add_building = building_xxx -> scope.add_building('building_xxx')
        add_minerals = $MINERALS$ -> scope.add_minerals(MINERALS)
        add_minerals = 100 -> scope.add_minerals(100)
        """
        val = self._extract_value(value)
        
        # 判断是否需要加引号
        # 1. 如果是纯数字，不加引号
        try:
            float(val)
            formatted_val = val
        except (ValueError, TypeError):
            # 2. 如果 _extract_value 返回的是参数名（不含$），检查是否在参数列表中
            if hasattr(self.parent, 'parameters') and val in self.parent.parameters:
                # 是宏参数，不加引号
                formatted_val = val
            else:
                # 3. 其他情况（游戏标识符、枚举等），加引号
                formatted_val = repr(val)
        
        self.parent._add_line(f"{self.context.current_scope_var}.{key}({formatted_val})")
        return True
    
    def generate_script_call(self, key: str) -> bool:
        """
        生成脚本效果调用
        
        my_scripted_effect = yes -> my_scripted_effect(scope)
        """
        self.parent._add_line(f"{key}({self.context.current_scope_var})")
        return True
    
    def generate_inline_script(self, value: ASTNode) -> bool:
        """
        生成内联脚本调用
        
        根据设计文档 (05_inline_scripts.md):
        inline_script = script_name 
            -> meta.inline_script(script='script_name')
        inline_script = { script = xxx PARAM = val } 
            -> meta.inline_script(script='xxx', PARAM=val)
        
        如果需要展开脚本内容，使用 InlineScriptGenerator
        """
        script_path = None
        params = {}
        
        # 检查是否是 InlineScriptNode (带参数的块形式)
        if HAS_INLINE_SCRIPT_NODE:
            from ...ast_nodes import InlineScriptNode
            if isinstance(value, InlineScriptNode):
                script_path = value.script_path
                params = value.parameters or {}
        
        # BlockNode 形式: inline_script = { script = xxx PARAM = val }
        if script_path is None and isinstance(value, BlockNode):
            for stmt in value.statements:
                if isinstance(stmt, PropertyNode):
                    k = stmt.key if isinstance(stmt.key, str) else str(stmt.key)
                    v = self._extract_value(stmt.value)
                    
                    if k == 'script':
                        script_path = v
                    else:
                        # 其他都是参数 (通常是大写的参数名)
                        params[k] = v
        
        # 简单字符串形式: inline_script = script_name
        if script_path is None:
            script_path = self._extract_value(value)
        
        # 生成 meta.inline_script 调用
        if params:
            params_str = ", ".join(f"{k}={self._format_kwarg(v)}" 
                                   for k, v in params.items())
            self.parent._add_line(f"meta.inline_script(script='{script_path}', {params_str})")
        else:
            self.parent._add_line(f"meta.inline_script(script='{script_path}')")
        
        return True
    
    def generate_inline_script_expanded(self, node: PropertyNode) -> bool:
        """
        展开内联脚本内容（从游戏目录读取脚本文件并生成代码）
        
        这个方法会实际读取脚本文件并将其内容展开为 Python 代码。
        使用 InlineScriptResolver 在 AST 层面展开，然后生成代码。
        
        Args:
            node: inline_script 属性节点（完整的 PropertyNode）
        """
        from ..inline_script_generator import InlineScriptGenerator, InlineScriptContext
        
        try:
            generator = InlineScriptGenerator()
            lines = generator.generate_from_node(
                node=node,
                context=InlineScriptContext.EFFECT,
                scope_var=self.context.current_scope_var
            )
            
            for line in lines:
                self.parent._add_line(line)
            
            return True
            
        except ValueError as e:
            # 游戏目录未设置，回退到 meta.inline_script 形式
            self.parent._add_line(f"# WARNING: {e}")
            return self.generate_inline_script(node.value)
    
    def _extract_value(self, value: ASTNode) -> str:
        """提取值的字符串表示"""
        if isinstance(value, LiteralNode):
            val_str = str(value.value)
            # 检查是否是简单宏参数
            if val_str.startswith('$') and val_str.endswith('$') and val_str.count('$') == 2:
                param_name = val_str[1:-1].split('|')[0]
                # 访问父生成器的参数字典
                if hasattr(self.parent, 'parameters') and param_name in self.parent.parameters:
                    if self.parent.parameters[param_name].is_simple:
                        return param_name  # 直接返回参数名（不带引号）
            return val_str
        elif hasattr(value, 'expression'):
            expr = value.expression
            # 检查是否是简单宏参数
            if expr.startswith('$') and expr.endswith('$') and expr.count('$') == 2:
                param_name = expr[1:-1].split('|')[0]
                if hasattr(self.parent, 'parameters') and param_name in self.parent.parameters:
                    if self.parent.parameters[param_name].is_simple:
                        return param_name
            return expr
        elif isinstance(value, BlockNode):
            from ...codegen.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                f"在简单 effect 调用中遇到嵌套块，这需要特殊处理。"
                f"BlockNode 包含 {len(value.statements)} 个语句，"
                f"不能简单地转换为字符串"
            )
        elif hasattr(value, 'value'):
            return str(value.value)
        else:
            from ...codegen.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                f"_extract_value 遇到未处理的节点类型: {type(value).__name__}"
            )
    
    def _format_kwarg(self, value) -> str:
        """格式化关键字参数值"""
        if isinstance(value, bool):
            return str(value)
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            # 检查是否是数字
            try:
                int(value)
                return value
            except ValueError:
                try:
                    float(value)
                    return value
                except ValueError:
                    return f"'{value}'"
        return f"'{value}'"
