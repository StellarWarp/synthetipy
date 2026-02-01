"""
Trigger 方法生成器

将 PDX trigger 块转换为 Python 布尔表达式
使用共享的表达式生成器组件
"""

from typing import List, Dict
from ..ast_nodes import *
from .generators import (
    BaseExpressionGenerator,
    GeneratorContext,
    ControlFlowGenerator,
    ExpressionBuilder
)
from .macro_parameter_utils import (
    MacroParameter,
    MacroParameterCollector,
    ParameterTypeInferencer,
    generate_function_signature,
    generate_pdx_block
)
from .runtime_deps import get_decorator_for_type


class TriggerGenerator(BaseExpressionGenerator):
    """Trigger 方法生成器 - 使用共享组件"""
    
    def __init__(self):
        super().__init__()
        self.control_flow_gen = None
        self.expr_builder = None
        self.parameters: Dict[str, MacroParameter] = {}
        self.has_complex_params = False
    
    def generate(self, name: str, block: BlockNode, scope_param: str = "scope", add_decorator: bool = True) -> List[str]:
        """
        生成 trigger 方法
        
        Args:
            name: 方法名
            block: trigger 块节点
            scope_param: 作用域参数名
            add_decorator: 是否添加装饰器（顶层函数需要，类方法不需要）
        
        Returns:
            生成的代码行列表
        """
        self.lines = []
        self.indent_level = 0
        self.context = GeneratorContext(scope_param)
        self.context.in_trigger = True
        self.context.current_indent = 1  # 函数体从缩进 1 开始
        
        # 1. 收集宏参数
        collector = MacroParameterCollector()
        self.parameters = collector.collect(block)
        self.has_complex_params = collector.has_complex_usage
        
        # 2. 推断参数类型
        if self.parameters:
            ParameterTypeInferencer.infer_all(self.parameters)
        
        # 初始化共享组件
        self.control_flow_gen = ControlFlowGenerator(self)
        self.expr_builder = ExpressionBuilder(self)
        
        # 3. 生成装饰器和方法签名
        if add_decorator:
            decorator = get_decorator_for_type('trigger')
            if decorator:
                self._add_line(decorator)
        
        if self.parameters:
            signature = generate_function_signature(name, self.parameters, 'bool', scope_param)
            self._add_line(signature)
        else:
            self._add_line(f"def {name}({scope_param}) -> bool:")
        self._indent()
        
        # 4. 生成方法体
        if not block.statements:
            self._add_line("return True")
        elif self.has_complex_params:
            # 复杂参数：使用 meta.pdx()
            self._generate_pdx_trigger(block)
        else:
            # 简单参数：直接生成
            self._generate_trigger_body(block)
        
        self._dedent()
        return self.lines
    
    def _generate_trigger_body(self, block: BlockNode):
        """
        生成 trigger 主体
        
        策略：
        1. 检查是否有 if/else 控制流
        2. 如果有，生成 if/elif/else 语句
        3. 如果没有，尝试转换为单个表达式
        """
        # 检查是否包含控制流
        if self.control_flow_gen.has_control_flow(block):
            # 生成 if/elif/else 语句，使用回调处理分支内容
            self.control_flow_gen.generate_control_flow(
                block,
                self._handle_trigger_branch
            )
        else:
            # 尝试转换为表达式
            expr = self.expr_builder.block_to_expression(block)
            if expr:
                self._add_line(f"return {expr}")
            else:
                # 无法转换为单一表达式，生成多语句形式
                self._generate_statement_sequence(block)
    
    def _handle_trigger_branch(self, branch_block: BlockNode, branch_type: str):
        """处理 trigger 分支的回调"""
        # 递归生成分支内容
        self._generate_trigger_body(branch_block)
    
    def _generate_statement_sequence(self, block: BlockNode):
        """
        生成语句序列（当无法转换为单一表达式时）
        
        策略：使用局部变量保存中间结果，最后返回
        """
        # TODO: 实现复杂的语句序列生成（early return, 局部变量等）
        result_var = self.context.get_temp_var("_result")
        self._add_line(f"{result_var} = True")
        
        for stmt in block.statements:
            # 为每个语句生成检查
            expr = self.expr_builder.statement_to_expression(stmt)
            if expr:
                self._add_line(f"{result_var} = {result_var} and ({expr})")
        
        self._add_line(f"return {result_var}")
    
    def _generate_pdx_trigger(self, block: BlockNode):
        """生成复杂参数的 trigger（使用 meta.pdx()）"""
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
                f"在 trigger 序列化中遇到嵌套块，这需要特殊处理。"
                f"BlockNode 包含 {len(value.statements)} 个语句，"
                f"不能简单地转换为字符串"
            )
        else:
            from .exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                f"_serialize_value 遇到未处理的节点类型: {type(value).__name__}"
            )
