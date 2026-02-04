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
    ExpressionBuilder,
    ScopeTranslator,
)
from .macro_parameter_utils import (
    MacroParameter,
    MacroParameterCollector,
    ParameterTypeInferencer,
    generate_function_signature,
    generate_pdx_block
)
from ..compiler import compile_ast
from ..pdx_constants import LOGIC_OPERATORS
from .runtime_deps import get_decorator_for_type


class TriggerGenerator(BaseExpressionGenerator):
    """Trigger 方法生成器 - 使用共享组件"""
    
    def __init__(self):
        super().__init__()
        self.control_flow_gen = None
        self.expr_builder = None
        self.scope_translator = None
        self.parameters: Dict[str, MacroParameter] = {}

    
    def generate(self, name: str, 
                 block: BlockNode, scope_param: str = "scope", add_decorator: bool = True) -> List[str]:
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
        # 保留 collector 引用，供生成时查询 macro_lefts
        self.collector = collector
        
        # 2. 推断参数类型
        if self.parameters:
            ParameterTypeInferencer.infer_all(self.parameters)
         
        self.scope_translator = ScopeTranslator(self)
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
        self._generate_trigger_body(block)
        
        self._dedent()
        return self.lines
    
    def _generate_trigger_body(self, block: BlockNode):
        for stmt in block.statements:
            self._generate_statement(stmt)
                

    def _handle_trigger_branch(self, branch_block: BlockNode, branch_type: str):
        """处理 trigger 分支的回调"""
        # 递归生成分支内容
        self._generate_trigger_body(branch_block)

    def _generate_statement(self, stmt: PropertyNode):
        """按语句生成（委托 ControlFlowGenerator 或本地 property 处理）"""
        if isinstance(stmt, PropertyNode):
            
            # 宏左值优先插入
            if getattr(self, 'collector', None):
                macro = self.collector.macro_lefts.get(stmt)
                if macro:
                    for l in macro.meta_lines:
                        self._add_line(l)
                    return
            # 先让 ControlFlowGenerator 处理结构化语句（if/loop/scope）
            if self.control_flow_gen.generate_control_flow(stmt, lambda b, t: self._generate_trigger_body(b)):
                return
            

            key = str(stmt.key)
            if key in INBUILT_TRIGGER_METHODS:
                # 内置 trigger 方法调用
                expr = self.expr_builder._method_call_to_expression(key, stmt.value)
                self._add_line(f"return {expr}")
                self._dedent()
                return
            if key in LOGIC_OPERATORS:
                # 尝试将该语句转换为表达式
                expr = self.expr_builder.statement_to_expression(stmt)
                if expr:
                    self._add_line(f"return {expr}")
                    self._dedent()
                    return
            
            raise ValueError(f"Unsupported trigger statement: {key}")

        else:
            raise ValueError("TriggerGenerator only supports PropertyNode statements")


