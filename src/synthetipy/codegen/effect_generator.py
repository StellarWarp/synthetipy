"""
Effect 方法生成器

将 PDX effect 块转换为 Python 命令式语句
使用共享的生成器组件
"""

from typing import List, Dict

from synthetipy.codegen.generators.control_flow import ControlFlowGenerator
from ..ast_nodes import BlockNode, PropertyNode, LiteralNode, ASTNode
from .generators import (
    BaseExpressionGenerator,
    GeneratorContext,
    ExpressionBuilder,
    EffectLoopGenerator,
    EffectVariableGenerator,
    EffectBlockGenerator,
    ScopeTranslator,
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
    
    def __init__(self):
        super().__init__()
        self.expr_builder = None
        self.loop_gen = None
        self.var_gen = None
        self.block_gen = None
        self.value_formatter = None
        self.scope_translator = None
        self.parameters: Dict[str, MacroParameter] = {}

    
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
        # 保留 collector 引用，供生成时查询 macro_lefts
        self.collector = collector
        
        # 2. 推断参数类型
        if self.parameters:
            ParameterTypeInferencer.infer_all(self.parameters)
        
        # 初始化共享组件
        # ValueFormatter 已被移除，使用集中 Formatter/ExpressionBuilder 的内部逻辑
        self.expr_builder = ExpressionBuilder(self)
        self.scope_translator = ScopeTranslator(self)
        self.loop_gen = EffectLoopGenerator(self)
        self.var_gen = EffectVariableGenerator(self)
        self.block_gen = EffectBlockGenerator(self)
        self.control_flow_gen = ControlFlowGenerator(self)
        
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
        # 宏左值打包 (tech_$AREA$_1 = { ... })
        if getattr(self, 'collector', None):
            macro = self.collector.macro_lefts.get(prop)
            if macro:
                for l in macro.meta_lines:
                    self._add_line(l)
                return True

        # 首先交由 ControlFlowGenerator 统一处理控制流 / 迭代 / scope 切换
        if self.control_flow_gen.generate_control_flow(prop, lambda block, t: self._generate_effect_body(block)):
            return True
        
        key = str(prop.key)
        value = prop.value
               
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

    
    

