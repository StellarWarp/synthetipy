"""
PDXLang Patcher - AST 节点定义
定义 Paradox 脚本语言的所有 AST 节点类型
"""

from typing import Any, List, Dict, Optional, Union
from abc import ABC, abstractmethod


# ============================================
# 宏参数和表达式解析
# ============================================

class MacroParam:
    """宏参数（可能有默认值）
    
    表示脚本中的宏参数，格式为 $PARAM$ 或 $PARAM|default$
    例如:
        $AREA$ -> MacroParam('AREA')
        $ID|none$ -> MacroParam('ID', 'none')
    """
    
    def __init__(self, param_str: str):
        """从参数字符串初始化（不含 $ 符号）
        
        Args:
            param_str: 参数字符串，如 "AREA" 或 "ID|none"
        """
        if '|' in param_str:
            parts = param_str.split('|', 1)
            self.name = parts[0]
            self.default = parts[1] if len(parts) > 1 else None
        else:
            self.name = param_str
            self.default = None
    
    def to_python(self) -> str:
        """转换为 Python 代码（用于语言服务）"""
        if self.default:
            return f"params.get('{self.name}', '{self.default}')"
        return f"params['{self.name}']"
    
    def to_source(self) -> str:
        """转换回 PDXLang 源代码"""
        if self.default:
            return f"${self.name}|{self.default}$"
        return f"${self.name}$"
    
    def __str__(self):
        return self.to_source()
    
    def __repr__(self):
        if self.default:
            return f"MacroParam('{self.name}', default='{self.default}')"
        return f"MacroParam('{self.name}')"


class ParsedExpression:
    """深度解析的表达式结构（用于语言服务）
    
    延迟解析的结果，包含完整的语义信息
    支持作用域链、宏参数、特殊调用等
    """
    
    def __init__(self):
        self.scope_chain: List[Union[str, MacroParam]] = []  # ['owner', 'overlord', 'capital']
        self.scope_binding: Optional[str] = None  # @prev
        
        # 特殊调用（value:, trigger:, event_target: 等）
        self.call_type: Optional[str] = None  # 'value', 'trigger', 'event_target'
        self.function_name: Optional[str] = None
        self.arguments: List[Union[str, MacroParam]] = []
        
        # 路径分隔符（jobs/miners_add）
        self.path_parts: List[str] = []
    
    def to_python(self) -> str:
        """转换为 Python 代码（用于语言服务）"""
        if self.call_type == 'value':
            args = ', '.join(
                p.to_python() if isinstance(p, MacroParam) else f"'{p}'"
                for p in self.arguments
            )
            return f"scope.get_scripted_value('{self.function_name}', [{args}])"
        elif self.call_type == 'event_target':
            target = self.function_name
            if self.scope_chain:
                chain = '.'.join(
                    p.to_python() if isinstance(p, MacroParam) else p
                    for p in self.scope_chain
                )
                return f"scope.get_event_target('{target}').{chain}"
            return f"scope.get_event_target('{target}')"
        elif self.path_parts:
            return "'" + '/'.join(self.path_parts) + "'"
        elif self.scope_chain:
            chain = '.'.join(
                p.to_python() if isinstance(p, MacroParam) else p
                for p in self.scope_chain
            )
            if self.scope_binding:
                return f"scope.get_saved('{self.scope_binding}').{chain}"
            return f"scope.{chain}"
        return "scope"
    
    def __repr__(self):
        parts = []
        if self.call_type:
            parts.append(f"call_type='{self.call_type}'")
        if self.function_name:
            parts.append(f"function='{self.function_name}'")
        if self.scope_chain:
            parts.append(f"scope_chain={self.scope_chain}")
        if self.scope_binding:
            parts.append(f"binding='@{self.scope_binding}'")
        if self.arguments:
            parts.append(f"args={self.arguments}")
        if self.path_parts:
            parts.append(f"path={self.path_parts}")
        return f"ParsedExpression({', '.join(parts)})"


class ASTNode(ABC):
    """AST 节点基类"""
    
    def __init__(self, line: int = 0, column: int = 0):
        self.line = line
        self.column = column
        self.parent: Optional[ASTNode] = None
    
    @abstractmethod
    def accept(self, visitor):
        """访问者模式接口"""
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}()"


class DocumentNode(ASTNode):
    """文档根节点 - 包含所有顶层语句"""
    
    def __init__(self, statements: List[ASTNode]):
        super().__init__()
        self.statements = statements
        for stmt in statements:
            stmt.parent = self
    
    def accept(self, visitor):
        return visitor.visit_document(self)
    
    def __repr__(self):
        return f"Document({len(self.statements)} statements)"


class ObjectNode(ASTNode):
    """顶层对象定义
    
    例如:
        building_research_lab_1 = {
            category = research
            cost = { minerals = 400 }
        }
        tech_$AREA$_1 = { ... }  # 宏参数
    """
    
    def __init__(self, name: Union[str, 'MacroIdentifierNode'], body: 'BlockNode'):
        super().__init__()
        self.name = name
        self.body = body
        body.parent = self
        if isinstance(name, ASTNode):
            name.parent = self
    
    def accept(self, visitor):
        return visitor.visit_object(self)
    
    def __repr__(self):
        name_str = str(self.name) if isinstance(self.name, str) else repr(self.name)
        return f"Object({name_str})"


class PropertyNode(ASTNode):
    """属性（键值对）
    
    例如:
        category = research
        cost = { minerals = 400 }
        tech_$AREA$ = value  # 宏参数
    """
    
    def __init__(self, key: Union[str, 'MacroIdentifierNode'], value: ASTNode):
        super().__init__()
        self.key = key
        self.value = value
        value.parent = self
        if isinstance(key, ASTNode):
            key.parent = self
    
    def accept(self, visitor):
        return visitor.visit_property(self)
    
    def __repr__(self):
        key_str = str(self.key) if isinstance(self.key, str) else repr(self.key)
        return f"Property({key_str} = {self.value})"


class BlockNode(ASTNode):
    """代码块 { ... }
    
    包含多个语句的代码块
    """
    
    def __init__(self, statements: List[ASTNode]):
        super().__init__()
        self.statements = statements
        for stmt in statements:
            stmt.parent = self
    
    def accept(self, visitor):
        return visitor.visit_block(self)
    
    def get_property(self, key: str) -> Optional[PropertyNode]:
        """获取指定键的属性"""
        for stmt in self.statements:
            if isinstance(stmt, PropertyNode) and stmt.key == key:
                return stmt
        return None
    
    def add_property(self, key: str, value: ASTNode):
        """添加新属性"""
        prop = PropertyNode(key, value)
        self.statements.append(prop)
        prop.parent = self
    
    def remove_property(self, key: str):
        """移除属性"""
        self.statements = [
            stmt for stmt in self.statements 
            if not (isinstance(stmt, PropertyNode) and stmt.key == key)
        ]
    
    def __repr__(self):
        return f"Block({len(self.statements)} statements)"


class ValueNode(ASTNode):
    """标量值
    
    支持的类型:
        - int: 100
        - float: 3.14
        - bool: yes, no
        - string: "some text"
        - identifier: research, @b1_time
    """
    
    def __init__(self, value: Union[int, float, bool, str], value_type: str = 'auto'):
        super().__init__()
        self.raw_value = value
        
        # 自动推断类型
        if value_type == 'auto':
            if isinstance(value, bool):
                self.value_type = 'bool'
                self.value = value
            elif isinstance(value, int):
                self.value_type = 'int'
                self.value = value
            elif isinstance(value, float):
                self.value_type = 'float'
                self.value = value
            elif isinstance(value, str):
                # 检查是否是布尔值
                if value.lower() in ('yes', 'true'):
                    self.value_type = 'bool'
                    self.value = True
                elif value.lower() in ('no', 'false'):
                    self.value_type = 'bool'
                    self.value = False
                # 检查是否是数字
                elif value.replace('.', '').replace('-', '').isdigit():
                    if '.' in value:
                        self.value_type = 'float'
                        self.value = float(value)
                    else:
                        self.value_type = 'int'
                        self.value = int(value)
                # 检查是否是变量引用
                elif value.startswith('@'):
                    self.value_type = 'variable'
                    self.value = value
                else:
                    self.value_type = 'identifier'
                    self.value = value
        else:
            self.value_type = value_type
            self.value = value
    
    def accept(self, visitor):
        return visitor.visit_value(self)
    
    def __repr__(self):
        return f"Value({self.value}, type={self.value_type})"
    
    def __str__(self):
        if self.value_type == 'bool':
            return 'yes' if self.value else 'no'
        elif self.value_type == 'string':
            return f'"{self.value}"'
        else:
            return str(self.value)


class ListNode(ASTNode):
    """列表 { item1 item2 item3 }
    
    包含多个值的列表（不是键值对）
    """
    
    def __init__(self, items: List[ValueNode]):
        super().__init__()
        self.items = items
        for item in items:
            item.parent = self
    
    def accept(self, visitor):
        return visitor.visit_list(self)
    
    def __repr__(self):
        return f"List({len(self.items)} items)"


class ConditionNode(ASTNode):
    """逻辑条件块
    
    例如:
        OR = {
            has_technology = tech_advanced
            owner = { is_ai = yes }
        }
    """
    
    OPERATORS = ['OR', 'AND', 'NOT', 'NAND', 'NOR']
    
    def __init__(self, operator: str, body: BlockNode):
        super().__init__()
        assert operator in self.OPERATORS, f"Invalid operator: {operator}"
        self.operator = operator
        self.body = body
        body.parent = self
    
    def accept(self, visitor):
        return visitor.visit_condition(self)
    
    def __repr__(self):
        return f"Condition({self.operator})"


class ComparisonNode(ASTNode):
    """比较表达式
    
    例如:
        minerals > 1000
        num_pops >= 50
        is_ai = yes
        tech_$AREA$ > 10  # 宏参数
    """
    
    OPERATORS = ['=', '>', '<', '>=', '<=', '==', '!=']
    
    def __init__(self, left: Union[str, 'MacroIdentifierNode'], operator: str, right: ASTNode):
        super().__init__()
        assert operator in self.OPERATORS, f"Invalid operator: {operator}"
        self.left = left
        self.operator = operator
        self.right = right
        right.parent = self
        if isinstance(left, ASTNode):
            left.parent = self
    
    def accept(self, visitor):
        return visitor.visit_comparison(self)
    
    def __repr__(self):
        left_str = str(self.left) if isinstance(self.left, str) else repr(self.left)
        return f"Comparison({left_str} {self.operator} {self.right})"


class InlineScriptNode(ASTNode):
    """内联脚本调用
    
    例如:
        inline_script = {
            script = jobs/researcher_add
            AMOUNT = 10
        }
    """
    
    def __init__(self, script_path: str, parameters: Dict[str, Any]):
        super().__init__()
        self.script_path = script_path
        self.parameters = parameters
    
    def accept(self, visitor):
        return visitor.visit_inline_script(self)
    
    def __repr__(self):
        return f"InlineScript('{self.script_path}')"


class CommentNode(ASTNode):
    """注释
    
    支持:
        # 单行注释
    """
    
    def __init__(self, text: str, is_inline: bool = False):
        super().__init__()
        self.text = text
        self.is_inline = is_inline  # 行尾注释 vs 独立行注释
    
    def accept(self, visitor):
        return visitor.visit_comment(self)
    
    def __repr__(self):
        return f"Comment('{self.text[:20]}...')"


class DirectiveNode(ASTNode):
    """系统指令/标记节点
    
    某些标识符本身就是有效的语句，不需要值
    例如:
        optimize_memory
        clear_all_variables
    """
    
    def __init__(self, name: str):
        super().__init__()
        self.name = name
    
    def accept(self, visitor):
        return visitor.visit_directive(self)
    
    def __repr__(self):
        return f"Directive('{self.name}')"


class ConditionalParamNode(ASTNode):
    """条件参数块
    
    例如:
        [[SPIRITUALIST]
            is_spiritualist = yes
        ]
        [[!SPIRITUALIST]
            is_spiritualist = no
        ]
    """
    
    def __init__(self, param_name: str, body: List[ASTNode]):
        super().__init__()
        self.param_name = param_name  # 例如 "SPIRITUALIST" 或 "!SPIRITUALIST"
        self.body = body
        for stmt in body:
            stmt.parent = self
    
    def accept(self, visitor):
        return visitor.visit_conditional_param(self)
    
    def __repr__(self):
        return f"ConditionalParam('[[{self.param_name}]')"


class ConstantNode(ASTNode):
    """常量引用（编译时确定的值）
    
    例如:
        @b1_time
        @b1_minerals
    
    注意：这是脚本中定义的常量，不是运行时变量
    """
    
    def __init__(self, name: str):
        super().__init__()
        self.name = name
    
    def accept(self, visitor):
        return visitor.visit_constant(self)
    
    def __repr__(self):
        return f"Constant('{self.name}')"


class ConstantDefinitionNode(ASTNode):
    """常量定义（编译时静态常量）
    
    例如:
        @buildings_t1 = 240
        @b1_time = 360
        @stabilitylevel2 = 40
    
    注意：这是常量的定义，不是变量。值在编译时确定。
    """
    
    def __init__(self, name: str, value: ASTNode):
        super().__init__()
        self.name = name  # 例如 "@buildings_t1"
        self.value = value
        value.parent = self
    
    def __repr__(self) -> str:
        return f"ConstantDefinition({self.name} = {self.value})"
    
    def accept(self, visitor: 'ASTVisitor'):
        return visitor.visit_constant_definition(self)


class IdentifierExpressionNode(ASTNode):
    """标识符表达式节点（统一处理宏和普通标识符）
    
    采用三层设计：
    1. 原始字符串（必需，用于序列化）
    2. 基本标记（用于快速查询）
    3. 结构化信息（延迟解析，用于语言服务）
    
    示例:
        owner.overlord.capital
        $FROM$.overlord.capital
        value:tech_cost|$AREA$|
        event_target:federation_leader
        jobs/miners_add
        tech_$AREA$_1
    """
    
    def __init__(self, expression: str):
        super().__init__()
        # 第一层：原始字符串
        self.expression = expression
        
        # 第二层：基本标记（快速查询）
        self.has_macro = '$' in expression
        self.call_pattern: Optional[str] = None  # 'value', 'event_target', 'trigger', None
        
        # 基本模式识别
        if ':' in expression:
            parts = expression.split(':', 1)
            self.call_pattern = parts[0]
        
        # 第三层：延迟解析（只在需要时计算）
        self._parsed: Optional[ParsedExpression] = None
    
    @property
    def parsed(self) -> ParsedExpression:
        """延迟解析：只在需要时才深度分析"""
        if self._parsed is None:
            self._parsed = self._deep_parse()
        return self._parsed
    
    def _deep_parse(self) -> ParsedExpression:
        """深度解析表达式结构（用于语言服务）"""
        result = ParsedExpression()
        expr = self.expression
        
        # 解析特殊调用（value:, event_target:, trigger: 等）
        if ':' in expr:
            prefix, rest = expr.split(':', 1)
            result.call_type = prefix
            
            # 解析函数名和参数
            if '|' in rest:
                # 带参数的调用: value:tech_cost|AREA|5|
                parts = rest.split('|')
                result.function_name = parts[0]
                result.arguments = [
                    MacroParam(p[1:-1]) if p.startswith('$') and p.endswith('$') else p
                    for p in parts[1:-1] if p  # 最后一个 | 后面是空的
                ]
            else:
                # 无参数调用: event_target:name 或 event_target:name.property
                if '.' in rest:
                    name_part, *scope_parts = rest.split('.')
                    result.function_name = name_part
                    result.scope_chain = [
                        MacroParam(p[1:-1]) if p.startswith('$') and p.endswith('$') else p
                        for p in scope_parts
                    ]
                else:
                    result.function_name = rest
            return result
        
        # 解析路径分隔符（jobs/miners_add）
        if '/' in expr:
            result.path_parts = expr.split('/')
            return result
        
        # 解析作用域绑定（identifier@scope）
        if '@' in expr and not expr.startswith('@'):
            parts = expr.split('@', 1)
            main_part = parts[0]
            result.scope_binding = parts[1]
            expr = main_part
        
        # 解析作用域链（owner.overlord.capital 或 $FROM$.capital）
        if '.' in expr:
            parts = expr.split('.')
            result.scope_chain = [
                MacroParam(p[1:-1]) if p.startswith('$') and p.endswith('$') else p
                for p in parts
            ]
        else:
            # 单个标识符或宏参数
            if expr.startswith('$') and expr.endswith('$'):
                result.scope_chain = [MacroParam(expr[1:-1])]
            else:
                result.scope_chain = [expr]
        
        return result
    
    def to_source(self) -> str:
        """序列化回 PDXLang"""
        return self.expression
    
    def __repr__(self) -> str:
        macro_flag = ' [macro]' if self.has_macro else ''
        call_flag = f' [{self.call_pattern}:]' if self.call_pattern else ''
        return f"IdentifierExpr('{self.expression}'{macro_flag}{call_flag})"
    
    def __str__(self):
        return self.expression
    
    def accept(self, visitor: 'ASTVisitor'):
        return visitor.visit_identifier_expression(self)


# ============================================
# 向后兼容的废弃类
# ============================================

class ScriptedValueCallNode(IdentifierExpressionNode):
    """[废弃] Scripted Value 调用（向后兼容）
    
    请使用 IdentifierExpressionNode 替代
    保留此类仅用于向后兼容
    """
    
    def __init__(self, function_name: str, arguments: List[str]):
        # 构建表达式字符串
        args_str = '|'.join(arguments) + '|' if arguments else ''
        expression = f"{function_name}|{args_str}" if args_str else function_name
        super().__init__(expression)
        
        # 保留原有属性供旧代码访问
        self.function_name = function_name
        self.arguments = arguments
    
    def __repr__(self) -> str:
        args_str = '|'.join(self.arguments)
        return f"ScriptedValueCall({self.function_name}|{args_str}|)"


class MacroParameterNode(ASTNode):
    """[废弃] 宏参数节点（向后兼容）
    
    请使用 MacroParam 类替代（非 ASTNode）
    保留此类仅用于向后兼容
    """
    
    def __init__(self, param_name: str):
        super().__init__()
        # 支持带默认值的参数: "ID|none"
        self.param_name = param_name
        self._macro_param = MacroParam(param_name)
    
    @property
    def name(self) -> str:
        return self._macro_param.name
    
    @property
    def default(self) -> Optional[str]:
        return self._macro_param.default
    
    def __repr__(self) -> str:
        return f"MacroParameterNode('{self._macro_param.to_source()}')"
    
    def accept(self, visitor: 'ASTVisitor'):
        return visitor.visit_macro_parameter(self)


class MacroIdentifierNode(IdentifierExpressionNode):
    """[废弃] 包含宏参数的复合标识符（向后兼容）
    
    请使用 IdentifierExpressionNode 替代
    保留此类仅用于向后兼容
    """
    
    def __init__(self, parts: List[Union[str, MacroParameterNode]]):
        # 构建表达式字符串
        expression = ''.join(
            f'${p.param_name}$' if isinstance(p, MacroParameterNode) else str(p)
            for p in parts
        )
        super().__init__(expression)
        
        # 保留原有属性供旧代码访问
        self.parts = parts
        for part in parts:
            if isinstance(part, ASTNode):
                part.parent = self
    
    def __repr__(self) -> str:
        return f"MacroIdentifier('{self.expression}')"


class InlineArithmeticNode(ASTNode):
    r"""内联算术表达式
    
    表示 @[ expr ] 或 @\[ expr ] 形式的内联计算
    例如:
        @[( 72 * $PROGRESS$ )]
        @\[( value + 10 )]
    
    目前保存原始表达式文本，不解析内部结构
    """
    
    def __init__(self, expression: str, escaped: bool = False):
        super().__init__()
        self.expression = expression  # 原始表达式文本（不含 @[ 和 ]）
        self.escaped = escaped  # 是否是 @\[ 形式
    
    def __repr__(self) -> str:
        prefix = '@\\[' if self.escaped else '@['
        return f"InlineArithmetic('{prefix}{self.expression}]')"
    
    def accept(self, visitor: 'ASTVisitor'):
        return visitor.visit_inline_arithmetic(self)


# ============================================
# 辅助类
# ============================================

class ASTVisitor(ABC):
    """访问者模式基类 - 用于遍历 AST"""
    
    def visit_document(self, node: DocumentNode):
        for stmt in node.statements:
            stmt.accept(self)
    
    def visit_object(self, node: ObjectNode):
        node.body.accept(self)
    
    def visit_property(self, node: PropertyNode):
        node.value.accept(self)
    
    def visit_block(self, node: BlockNode):
        for stmt in node.statements:
            stmt.accept(self)
    
    def visit_value(self, node: ValueNode):
        pass
    
    def visit_list(self, node: ListNode):
        for item in node.items:
            item.accept(self)
    
    def visit_condition(self, node: ConditionNode):
        node.body.accept(self)
    
    def visit_comparison(self, node: ComparisonNode):
        node.right.accept(self)
    
    def visit_inline_script(self, node: InlineScriptNode):
        pass
    
    def visit_comment(self, node: CommentNode):
        pass
    
    def visit_directive(self, node: DirectiveNode):
        pass
    
    def visit_constant(self, node: ConstantNode):
        pass
    
    def visit_macro_parameter(self, node: MacroParameterNode):
        pass
    
    def visit_macro_identifier(self, node: MacroIdentifierNode):
        # 废弃方法，向后兼容
        pass
    
    def visit_scripted_value_call(self, node):
        # 废弃方法，向后兼容
        pass
    
    def visit_identifier_expression(self, node: IdentifierExpressionNode):
        pass
    
    def visit_inline_arithmetic(self, node: InlineArithmeticNode):
        pass
    
    def visit_conditional_param(self, node: ConditionalParamNode):
        for stmt in node.body:
            stmt.accept(self)
    
    def visit_constant_definition(self, node: ConstantDefinitionNode):
        node.value.accept(self)


class ASTTransformer(ASTVisitor):
    """AST 转换器 - 用于修改 AST"""
    
    def transform(self, node: ASTNode) -> ASTNode:
        """转换节点（可以返回新节点或修改后的节点）"""
        return node
    
    def visit_document(self, node: DocumentNode):
        node.statements = [
            self.transform(stmt.accept(self)) 
            for stmt in node.statements
        ]
        return node
    
    def visit_object(self, node: ObjectNode):
        node.body = self.transform(node.body.accept(self))
        return node
    
    def visit_property(self, node: PropertyNode):
        node.value = self.transform(node.value.accept(self))
        return node
    
    def visit_block(self, node: BlockNode):
        node.statements = [
            self.transform(stmt.accept(self))
            for stmt in node.statements
        ]
        return node
    
    # 其他 visit 方法类似...


# ============================================
# 便捷函数
# ============================================

def create_property(key: str, value: Any) -> PropertyNode:
    """创建属性节点"""
    if isinstance(value, ASTNode):
        return PropertyNode(key, value)
    elif isinstance(value, dict):
        return PropertyNode(key, dict_to_block(value))
    elif isinstance(value, list):
        return PropertyNode(key, ListNode([ValueNode(v) for v in value]))
    else:
        return PropertyNode(key, ValueNode(value))


def dict_to_block(data: Dict[str, Any]) -> BlockNode:
    """将 Python 字典转换为 Block 节点"""
    statements = []
    for key, value in data.items():
        statements.append(create_property(key, value))
    return BlockNode(statements)


def block_to_dict(block: BlockNode) -> Dict[str, Any]:
    """将 Block 节点转换为 Python 字典"""
    result = {}
    for stmt in block.statements:
        if isinstance(stmt, PropertyNode):
            if isinstance(stmt.value, BlockNode):
                result[stmt.key] = block_to_dict(stmt.value)
            elif isinstance(stmt.value, ValueNode):
                result[stmt.key] = stmt.value.value
            elif isinstance(stmt.value, ListNode):
                result[stmt.key] = [item.value for item in stmt.value.items]
    return result
