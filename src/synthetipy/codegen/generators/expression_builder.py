"""
表达式构建器

将 AST 节点转换为 Python 表达式
"""

from typing import Optional, Tuple
from ...ast_nodes import *


class ExpressionBuilder:
    """表达式构建器 - 核心转换逻辑"""
    
    def __init__(self, parent_generator):
        self.parent = parent_generator
        self.context = parent_generator.context
    
    def block_to_expression(self, block: BlockNode) -> Optional[str]:
        """
        将块转换为单一布尔表达式
        
        策略：
        - 顶层多个语句 = AND 组合
        - 单个语句 = 直接转换
        - 包含 OR/AND/NOT = 递归处理
        
        Returns:
            表达式字符串，如果无法转换则返回 None
        """
        if not block.statements:
            return "True"
        
        if len(block.statements) == 1:
            # 单个语句，直接转换
            return self.statement_to_expression(block.statements[0])
        
        # 多个语句，使用 AND 组合
        expressions = []
        for stmt in block.statements:
            expr = self.statement_to_expression(stmt)
            if expr:
                expressions.append(expr)
        
        if not expressions:
            return "True"
        elif len(expressions) == 1:
            return expressions[0]
        else:
            # 多个语句用 logic.AND 组合
            from .logic_blocks import LogicBlockGenerator
            logic_gen = LogicBlockGenerator(self.parent)
            return logic_gen.generate_and_expression(expressions)
    
    def statement_to_expression(self, stmt: ASTNode) -> Optional[str]:
        """
        将单个语句转换为表达式
        
        处理：
        - 比较：is_ai = yes -> scope.is_ai
        - 方法调用：has_technology = tech_name -> scope.has_technology('tech_name')
        - 逻辑块：OR {...} -> (expr1 or expr2)
        - 特殊调用：check_variable_arithmetic, value: 等
        """
        if isinstance(stmt, ComparisonNode):
            return self._comparison_to_expression(stmt)
        
        elif isinstance(stmt, PropertyNode):
            return self._property_to_expression(stmt)
        
        elif isinstance(stmt, ConditionNode):
            from .logic_blocks import LogicBlockGenerator
            logic_gen = LogicBlockGenerator(self.parent)
            return logic_gen.generate_logic_expression(stmt.operator, stmt.body)
        
        elif isinstance(stmt, LiteralNode):
            # 单独的字面量（少见）
            return self._literal_to_python(stmt)
        
        return None
    
    def _comparison_to_expression(self, comp: ComparisonNode) -> str:
        """
        比较表达式转换
        
        num_pops >= 50 -> scope.num_pops >= 50
        """
        left = comp.left if isinstance(comp.left, str) else str(comp.left)
        op = self.parent.COMPARISON_OPS.get(comp.operator, comp.operator)
        right = self._value_to_python(comp.right)
        
        return f"{self.context.current_scope_var}.{left} {op} {right}"
    
    def _property_to_expression(self, prop: PropertyNode) -> Optional[str]:
        """
        属性转换为表达式
        
        情况：
        1. is_ai = yes -> scope.is_ai()
        2. is_gestalt = no -> not scope.is_gestalt()
        3. has_technology = tech_name -> scope.has_technology('tech_name')
        4. owner = {...} -> with scope.owner 或 scope.owner.xxx
        5. OR = {...} -> 逻辑块
        6. free_district_slots = 0 -> scope.free_district_slots == 0 (数值比较)
        7. 特殊调用
        """
        key = prop.key if isinstance(prop.key, str) else str(prop.key)
        value = prop.value
        
        # 逻辑块
        if key in self.parent.LOGIC_OPERATORS:
            if isinstance(value, BlockNode):
                from .logic_blocks import LogicBlockGenerator
                logic_gen = LogicBlockGenerator(self.parent)
                return logic_gen.generate_logic_expression(key, value)
        
        # 特殊调用
        from .special_calls import SpecialCallHandler
        special_handler = SpecialCallHandler(self.parent)
        
        if special_handler.is_special_call(key):
            return special_handler.handle_special_call(key, value)
        
        # 作用域切换 (简单形式)
        if key in {'owner', 'capital', 'overlord', 'ruler', 'planet', 'from', 'root', 'prev'}:
            if isinstance(value, BlockNode):
                # 嵌套块：owner = { is_ai = yes }
                # 保存当前作用域，切换到新作用域
                old_scope = self.context.current_scope_var
                self.context.current_scope_var = f"{old_scope}.{key}"
                
                # 递归处理嵌套块
                nested_expr = self.block_to_expression(value)
                
                # 恢复作用域
                self.context.current_scope_var = old_scope
                
                return nested_expr
        
        # 方法调用
        if self.parent._is_method_call(key):
            return self._method_call_to_expression(key, value)
        
        # 属性访问 (布尔条件)
        if isinstance(value, LiteralNode):
            if value.value_type == 'bool':
                # is_ai = yes -> scope.is_ai()
                # is_gestalt = no -> not scope.is_gestalt()
                if value.value:
                    return f"{self.context.current_scope_var}.{key}()"
                else:
                    return f"not {self.context.current_scope_var}.{key}()"
            elif value.value_type in ('int', 'float'):
                # 数值比较：free_district_slots = 0 -> scope.free_district_slots == 0
                return f"{self.context.current_scope_var}.{key} == {value.value}"
        
        # IdentifierExpressionNode 处理 yes/no
        if hasattr(value, 'expression'):
            expr = value.expression
            if expr == 'yes':
                return f"{self.context.current_scope_var}.{key}()"
            elif expr == 'no':
                return f"not {self.context.current_scope_var}.{key}()"
            else:
                # 其他标识符作为参数
                return f"{self.context.current_scope_var}.{key}('{expr}')"
        
        return None
    
    def _method_call_to_expression(self, method: str, value: ASTNode) -> str:
        """
        方法调用转换
        
        has_technology = tech_name -> scope.has_technology('tech_name')
        has_planet_flag = flag_name -> scope.has_planet_flag('flag_name')
        free_jobs_of_type = { category = ruler value > 0 } -> scope.free_jobs_of_type(category='ruler') > 0
        is_gestalt = no -> not scope.is_gestalt()
        free_district_slots = 0 -> scope.free_district_slots == 0 (属性比较)
        """
        if isinstance(value, LiteralNode):
            # 布尔值特殊处理：is_gestalt = no -> not scope.is_gestalt()
            if value.value_type == 'bool':
                if value.value:
                    return f"{self.context.current_scope_var}.{method}()"
                else:
                    return f"not {self.context.current_scope_var}.{method}()"
            # 数值作为相等比较：free_district_slots = 0 -> scope.free_district_slots == 0
            elif value.value_type in ('int', 'float'):
                return f"{self.context.current_scope_var}.{method} == {value.value}"
            # 其他类型作为参数传递
            arg = self._literal_to_python(value)
            return f"{self.context.current_scope_var}.{method}({arg})"
        
        elif isinstance(value, BlockNode):
            # 复杂参数块
            args, comparison = self._extract_method_args_and_comparison(value)
            
            # 构建方法调用
            if args:
                args_str = ", ".join(f"{k}={v}" for k, v in args.items())
                method_call = f"{self.context.current_scope_var}.{method}({args_str})"
            else:
                method_call = f"{self.context.current_scope_var}.{method}()"
            
            # 如果有比较运算，添加比较
            if comparison:
                return f"{method_call} {comparison}"
            
            return method_call
        
        # IdentifierExpressionNode 处理：标识符作为参数
        elif hasattr(value, 'expression'):
            expr = value.expression
            if expr == 'yes':
                return f"{self.context.current_scope_var}.{method}()"
            elif expr == 'no':
                return f"not {self.context.current_scope_var}.{method}()"
            else:
                return f"{self.context.current_scope_var}.{method}('{expr}')"
        
        return f"{self.context.current_scope_var}.{method}()"
    
    def _extract_method_args_and_comparison(self, block: BlockNode) -> Tuple[dict, Optional[str]]:
        """
        从方法参数块中提取参数和比较运算
        
        { category = ruler value > 0 }
        -> args: {'category': "'ruler'"}, comparison: "> 0"
        """
        args = {}
        comparison = None
        
        for stmt in block.statements:
            if isinstance(stmt, PropertyNode):
                key = stmt.key if isinstance(stmt.key, str) else str(stmt.key)
                
                # 跳过 value 键（通常是比较的一部分）
                if key != 'value':
                    args[key] = self._value_to_python(stmt.value)
            
            elif isinstance(stmt, ComparisonNode):
                if stmt.left == 'value':
                    # value > 0
                    op = self.parent.COMPARISON_OPS.get(stmt.operator, stmt.operator)
                    right = self._value_to_python(stmt.right)
                    comparison = f"{op} {right}"
        
        return args, comparison
    
    def _value_to_python(self, value: ASTNode) -> str:
        """将值节点转换为 Python 代码"""
        if isinstance(value, LiteralNode):
            return self._literal_to_python(value)
        elif isinstance(value, BlockNode):
            # 块作为值（少见）
            return "{ ... }"
        # IdentifierExpressionNode 类型
        elif hasattr(value, 'expression'):
            expr = value.expression
            # 检查是否是简单宏参数
            if expr.startswith('$') and expr.endswith('$') and expr.count('$') == 2:
                param_name = expr[1:-1].split('|')[0]
                # 访问父生成器的参数字典
                if hasattr(self.parent, 'parameters') and param_name in self.parent.parameters:
                    if self.parent.parameters[param_name].is_simple:
                        return param_name  # 直接返回参数名
            return f"'{expr}'"
        return "None"
    
    def _literal_to_python(self, lit: LiteralNode) -> str:
        """字面量转 Python"""
        if lit.value_type == 'bool':
            return 'True' if lit.value else 'False'
        elif lit.value_type in ('int', 'float'):
            return str(lit.value)
        elif lit.value_type == 'string':
            return f'"{lit.value}"'
        elif lit.value_type == 'identifier':
            # 检查是否是简单宏参数
            val = lit.value
            if isinstance(val, str) and val.startswith('$') and val.endswith('$') and val.count('$') == 2:
                param_name = val[1:-1].split('|')[0]
                # 访问父生成器的参数字典
                if hasattr(self.parent, 'parameters') and param_name in self.parent.parameters:
                    if self.parent.parameters[param_name].is_simple:
                        return param_name  # 直接返回参数名
            # 使用运行时依赖的格式化函数
            return self.parent._format_literal(lit)
        elif lit.value_type == 'constant':
            # @constant_name
            return f"'{lit.value}'"
        # 其他类型也检查宏参数
        val_str = str(lit.value)
        if val_str.startswith('$') and val_str.endswith('$') and val_str.count('$') == 2:
            param_name = val_str[1:-1].split('|')[0]
            if hasattr(self.parent, 'parameters') and param_name in self.parent.parameters:
                if self.parent.parameters[param_name].is_simple:
                    return param_name
        return repr(lit.value)
