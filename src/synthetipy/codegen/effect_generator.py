"""
Effect 方法生成器

将 PDX effect 块转换为 Python 命令式语句
使用共享的生成器组件
"""

from typing import List, Dict
from ..ast_nodes import BlockNode, PropertyNode, LiteralNode, ASTNode
from ..pdx_constants import SCOPE_SWITCHES
from .generators import (
    BaseExpressionGenerator,
    GeneratorContext,
    ExpressionBuilder,
    EffectLoopGenerator,
    EffectVariableGenerator,
    EffectBlockGenerator,
)
from .macro_parameter_utils import (
    MacroParameter,
    MacroParameterCollector,
    ParameterTypeInferencer,
    generate_function_signature,
    generate_pdx_block
)
from .runtime_deps import get_decorator_for_type


class EffectGenerator(BaseExpressionGenerator):
    """Effect 方法生成器 - 生成命令式代码"""
    
    # 使用集中管理的常量
    SCOPE_SWITCHES = SCOPE_SWITCHES
    
    def __init__(self):
        super().__init__()
        self.expr_builder = None
        self.loop_gen = None
        self.var_gen = None
        self.block_gen = None
        self.parameters: Dict[str, MacroParameter] = {}
        self.has_complex_params = False
    
    def generate(self, name: str, block: BlockNode, scope_param: str = "scope", add_decorator: bool = True) -> List[str]:
        """
        生成 effect 方法
        
        Args:
            name: 方法名
            block: effect 块节点
            scope_param: 作用域参数名
            add_decorator: 是否添加装饰器（顶层函数需要，类方法不需要）
        
        Returns:
            生成的代码行列表
        """
        self.lines = []
        self.indent_level = 0
        self.context = GeneratorContext(scope_param)
        self.context.in_effect = True
        self.context.current_indent = 1
        
        # 1. 收集宏参数
        collector = MacroParameterCollector()
        self.parameters = collector.collect(block)
        self.has_complex_params = collector.has_complex_usage
        
        # 2. 推断参数类型
        if self.parameters:
            ParameterTypeInferencer.infer_all(self.parameters)
        
        # 初始化共享组件
        self.expr_builder = ExpressionBuilder(self)
        self.loop_gen = EffectLoopGenerator(self)
        self.var_gen = EffectVariableGenerator(self)
        self.block_gen = EffectBlockGenerator(self)
        
        # 3. 生成装饰器和方法签名
        if add_decorator:
            decorator = get_decorator_for_type('effect')
            if decorator:
                self._add_line(decorator)
        
        if self.parameters:
            signature = generate_function_signature(name, self.parameters, 'None', scope_param)
            self._add_line(signature)
        else:
            self._add_line(f"def {name}({scope_param}) -> None:")
        self._indent()
        
        # 4. 生成方法体
        if not block.statements:
            self._add_line("pass")
        elif self.has_complex_params:
            # 复杂参数：使用 meta.pdx()
            self._generate_pdx_effect(block)
        else:
            # 简单参数：直接生成
            self._generate_effect_body(block)
        
        self._dedent()
        return self.lines
    
    def _generate_effect_body(self, block: BlockNode):
        """生成 effect 主体"""
        has_statements = False
        
        for stmt in block.statements:
            if self._generate_statement(stmt):
                has_statements = True
        
        if not has_statements:
            self._add_line("pass")
    
    def _generate_statement(self, stmt: ASTNode) -> bool:
        """生成单个语句"""
        if isinstance(stmt, PropertyNode):
            return self._generate_property_statement(stmt)
        return False
    
    def _generate_property_statement(self, prop: PropertyNode) -> bool:
        """生成属性语句"""
        key = prop.key if isinstance(prop.key, str) else str(prop.key)
        value = prop.value
        
        # 1. 控制流 (if/else/else_if)
        if key in ('if', 'else', 'else_if'):
            return self._generate_control_flow(prop, key)
        
        # 2. 循环遍历 (every_*, random_*)
        if self.loop_gen.is_loop(key):
            return self.loop_gen.generate_loop(key, value)
        
        # 3. 作用域切换
        if key in self.SCOPE_SWITCHES and isinstance(value, BlockNode):
            return self._generate_scope_switch(key, value)
        
        # 4. 变量操作
        if self.var_gen.is_variable_op(key):
            return self.var_gen.generate_variable_op(key, value)
        
        # 5. 标记操作
        if self.var_gen.is_flag_op(key):
            return self.var_gen.generate_flag_op(key, value)
        
        # 6. 内联脚本
        if key == 'inline_script':
            return self.block_gen.generate_inline_script(value)
        
        # 7. 脚本调用 (xxx = yes) - 必须在简单效果之前判断
        if self._is_script_call(value):
            return self.block_gen.generate_script_call(key)
        
        # 8. 简单效果 - 值为标识符 (add_building = building_xxx)
        if isinstance(value, LiteralNode) and value.value_type != 'bool':
            return self.block_gen.generate_simple_effect(key, value)
        
        # 9. IdentifierExpressionNode 作为标识符值
        if hasattr(value, 'expression') and value.expression not in ('yes', 'no'):
            return self.block_gen.generate_simple_effect(key, value)
        
        # 10. 带参数块的效果 (add_modifier = { ... })
        if self.block_gen.is_block_effect(key) and isinstance(value, BlockNode):
            return self.block_gen.generate_block_effect(key, value)
        
        # 11. 未知的块属性，作为方法调用处理
        if isinstance(value, BlockNode):
            return self.block_gen.generate_method_call(key, value)
        
        return False
    
    def _is_script_call(self, value: ASTNode) -> bool:
        """判断是否是脚本调用 (xxx = yes)"""
        if isinstance(value, LiteralNode):
            if value.value_type == 'bool' and value.value:
                return True
        if hasattr(value, 'expression'):
            if value.expression == 'yes':
                return True
        return False
    
    def _generate_control_flow(self, prop: PropertyNode, key: str) -> bool:
        """生成控制流语句"""
        if not isinstance(prop.value, BlockNode):
            return False
        
        block = prop.value
        
        # 提取 limit 条件
        limit_block = None
        body_stmts = []
        
        for stmt in block.statements:
            if isinstance(stmt, PropertyNode) and stmt.key == 'limit':
                limit_block = stmt.value
            else:
                body_stmts.append(stmt)
        
        # 生成条件表达式
        if key == 'if':
            if limit_block:
                condition = self.expr_builder.block_to_expression(limit_block)
                self._add_line(f"if {condition}:")
            else:
                self._add_line("if True:")
        elif key == 'else_if':
            if limit_block:
                condition = self.expr_builder.block_to_expression(limit_block)
                self._add_line(f"elif {condition}:")
            else:
                self._add_line("elif True:")
        elif key == 'else':
            self._add_line("else:")
        
        # 生成分支体
        self._indent()
        body_block = BlockNode(body_stmts)
        self._generate_effect_body(body_block)
        self._dedent()
        
        return True
    
    def _generate_scope_switch(self, key: str, value: BlockNode) -> bool:
        """
        生成作用域切换
        
        owner = { ... } -> owner = scope.owner; ...
        """
        # 生成变量赋值
        var_name = key
        self._add_line(f"{var_name} = {self.context.current_scope_var}.{key}")
        
        # 保存并切换作用域
        old_scope = self.context.current_scope_var
        self.context.current_scope_var = var_name
        
        # 生成嵌套语句
        self._generate_effect_body(value)
        
        # 恢复作用域
        self.context.current_scope_var = old_scope
        
        return True
    
    def _generate_pdx_effect(self, block: BlockNode):
        """生成复杂参数的 effect（使用 meta.pdx()）"""
        # 序列化块回 PDX 代码
        pdx_template = self._serialize_block_to_pdx(block)
        
        # 生成 meta.pdx() 调用
        pdx_lines = generate_pdx_block(pdx_template, self.parameters, indent=0)
        for line in pdx_lines:
            self._add_line(line)
    
    def _serialize_block_to_pdx(self, block: BlockNode) -> str:
        """将块序列化为 PDX 代码字符串（简化版）"""
        lines = []
        for stmt in block.statements:
            lines.append(self._serialize_statement(stmt))
        return '\n'.join(lines)
    
    def _serialize_statement(self, stmt: ASTNode, indent: int = 0) -> str:
        """序列化单个语句"""
        ind = '    ' * indent
        
        if isinstance(stmt, PropertyNode):
            key = stmt.key if isinstance(stmt.key, str) else str(stmt.key)
            if isinstance(stmt.value, BlockNode):
                lines = [f"{ind}{key} = {{"]
                for s in stmt.value.statements:
                    lines.append(self._serialize_statement(s, indent + 1))
                lines.append(f"{ind}}}")
                return '\n'.join(lines)
            else:
                val_str = self._serialize_value(stmt.value)
                return f"{ind}{key} = {val_str}"
        
        elif isinstance(stmt, ComparisonNode):
            left = stmt.left if isinstance(stmt.left, str) else str(stmt.left)
            right = self._serialize_value(stmt.right)
            return f"{ind}{left} {stmt.operator} {right}"
        
        elif isinstance(stmt, ConditionNode):
            lines = [f"{ind}{stmt.operator} = {{"]
            for s in stmt.body.statements:
                lines.append(self._serialize_statement(s, indent + 1))
            lines.append(f"{ind}}}")
            return '\n'.join(lines)
        
        return f"{ind}# TODO: {type(stmt).__name__}"
    
    def _serialize_value(self, value: ASTNode) -> str:
        """序列化值"""
        if isinstance(value, LiteralNode):
            return str(value.value)
        elif hasattr(value, 'expression'):
            return value.expression
        elif isinstance(value, BlockNode):
            from .exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                f"在 effect 序列化中遇到嵌套块，这需要特殊处理。"
                f"BlockNode 包含 {len(value.statements)} 个语句，"
                f"不能简单地转换为字符串"
            )
        else:
            from .exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                f"_serialize_value 遇到未处理的节点类型: {type(value).__name__}"
            )
