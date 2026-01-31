"""
PDXLang Patcher - 语法分析器
将 Token 流转换为抽象语法树 (AST)
"""

from typing import List, Optional, Union
from .lexer import Token, TokenType
from .ast_nodes import (
    ASTNode, DocumentNode, ObjectNode, PropertyNode, BlockNode, ValueNode,
    ListNode, ConditionNode, ComparisonNode, CommentNode, ConstantDefinitionNode,
    DirectiveNode, IdentifierExpressionNode, MacroParam
)


# 系统级指令/标记列表
# 这些标识符单独出现时是有效的语句，不需要 = value
SYSTEM_DIRECTIVES = {
    'optimize_memory',
    'clear_all_variables',
    # 可以继续添加其他系统指令
}


class ParserError(Exception):
    """解析错误"""
    def __init__(self, message: str, token: Optional[Token] = None, context: str = None):
        self.token = token
        self.context = context
        
        # 构建详细的错误信息
        error_parts = [message]
        
        if token:
            error_parts.append(f"at line {token.line}, column {token.column}")
            
            # 添加 token 信息
            if token.type:
                error_parts.append(f"(token: {token.type.name} '{token.value}')")
        
        # 添加上下文
        if context:
            error_parts.append(f"\nContext: {context}")
        
        super().__init__(" ".join(error_parts))


class Parser:
    """递归下降语法分析器"""
    
    def __init__(self, tokens: List[Token], source_text: str = None):
        self.tokens = tokens
        self.current = 0
        self.source_text = source_text
        # 将源文本按行分割以便快速访问
        self.source_lines = source_text.splitlines() if source_text else []
        # 只过滤掉注释和 EOF，保留 NEWLINE 用于判断表达式边界
        self.filtered_tokens = [
            t for t in tokens 
            if t.type not in (TokenType.COMMENT, TokenType.EOF)
        ]
        self.current_filtered = 0
    
    # ==================== 辅助方法 ====================
    
    def is_at_end(self) -> bool:
        """是否到达末尾"""
        return self.current_filtered >= len(self.filtered_tokens)
    
    def peek(self) -> Optional[Token]:
        """查看当前 token"""
        if self.is_at_end():
            return None
        return self.filtered_tokens[self.current_filtered]
    
    def peek_ahead(self, offset: int = 1) -> Optional[Token]:
        """向前查看 token"""
        pos = self.current_filtered + offset
        if pos >= len(self.filtered_tokens):
            return None
        return self.filtered_tokens[pos]
    
    def previous(self) -> Optional[Token]:
        """获取前一个 token"""
        if self.current_filtered == 0:
            return None
        return self.filtered_tokens[self.current_filtered - 1]
    
    def advance(self) -> Token:
        """前进并返回当前 token"""
        if not self.is_at_end():
            token = self.filtered_tokens[self.current_filtered]
            self.current_filtered += 1
            return token
        return self.previous()
    
    def check(self, token_type: TokenType) -> bool:
        """检查当前 token 类型"""
        if self.is_at_end():
            return False
        return self.peek().type == token_type
    
    def check_value(self, value: str) -> bool:
        """检查当前 token 的值"""
        if self.is_at_end():
            return False
        return self.peek().value == value
    
    def match(self, *types: TokenType) -> bool:
        """匹配多个 token 类型之一"""
        for token_type in types:
            if self.check(token_type):
                self.advance()
                return True
        return False
    
    def consume(self, token_type: TokenType, message: str = None) -> Token:
        """消费指定类型的 token"""
        if self.check(token_type):
            return self.advance()
        
        current = self.peek()
        if message is None:
            message = "Token mismatch"
        
        expected_name = token_type.name
        got_name = current.type.name if current else "EOF"
        got_value = f"'{current.value}'" if current else "end of file"
        
        raise self.error(
            message,
            current,
            expected=expected_name,
            got=f"{got_name} {got_value}"
        )
    
    def is_logic_operator(self) -> bool:
        """检查是否是逻辑运算符"""
        if self.is_at_end():
            return False
        return self.peek().type in (
            TokenType.OR, TokenType.AND, TokenType.NOT,
            TokenType.NAND, TokenType.NOR
        )
    
    def is_comparison_operator(self) -> bool:
        """检查是否是比较运算符"""
        if self.is_at_end():
            return False
        return self.peek().type in (
            TokenType.EQUALS, TokenType.GT, TokenType.LT,
            TokenType.GTE, TokenType.LTE, TokenType.EQUALS_EQUALS,
            TokenType.NOT_EQUALS
        )
    
    def skip_newlines(self):
        """跳过所有连续的 NEWLINE token"""
        while not self.is_at_end() and self.check(TokenType.NEWLINE):
            self.advance()
    
    def get_context(self, token: Optional[Token] = None, radius: int = 2) -> str:
        """获取指定 token 周围的源代码上下文
        
        Args:
            token: 目标 token，如果为 None 则使用当前位置
            radius: 前后各显示多少行
        
        Returns:
            格式化的上下文字符串，包含行号和错误标记
        """
        if token is None:
            token = self.peek()
        
        if not token:
            return "<no context>"
        
        # 如果没有源代码，回退到 token 显示
        if not self.source_lines:
            return self._get_token_context(token)
        
        error_line = token.line
        error_col = token.column
        
        # 计算显示范围（注意：行号是从 1 开始的）
        start_line = max(1, error_line - radius)
        end_line = min(len(self.source_lines), error_line + radius)
        
        # 构建上下文显示
        lines = []
        max_line_num_width = len(str(end_line))
        
        for line_num in range(start_line, end_line + 1):
            line_index = line_num - 1  # 转换为 0-based 索引
            if line_index >= len(self.source_lines):
                break
            
            line_content = self.source_lines[line_index]
            line_num_str = str(line_num).rjust(max_line_num_width)
            
            # 错误行用箭头标记
            if line_num == error_line:
                lines.append(f"  {line_num_str} | {line_content}")
                # 添加指示符指向错误列
                # 计算缩进：前导空格(2) + 行号宽度 + " | "(3) + 错误列位置
                indent = ' ' * (2 + max_line_num_width + 3 + error_col - 1)
                lines.append(f"{indent}^--- here")
            else:
                lines.append(f"  {line_num_str} | {line_content}")
        
        return "\n" + "\n".join(lines)
    
    def _get_token_context(self, token: Token, radius: int = 5) -> str:
        """备用方法：当没有源代码时，显示 token 上下文"""
        try:
            token_index = self.current_filtered
        except:
            token_index = 0
        
        start = max(0, token_index - radius)
        end = min(len(self.filtered_tokens), token_index + radius + 1)
        
        context_parts = []
        for i in range(start, end):
            t = self.filtered_tokens[i]
            if t.type == TokenType.NEWLINE:
                continue
            
            if i == token_index:
                context_parts.append(f">>>{t.value}<<<")
            else:
                context_parts.append(t.value)
        
        return " ".join(context_parts)
    
    def error(self, message: str, token: Optional[Token] = None, 
              expected: str = None, got: str = None) -> ParserError:
        """创建格式化的解析错误
        
        Args:
            message: 基本错误信息
            token: 出错位置的 token
            expected: 期望的内容（可选）
            got: 实际得到的内容（可选）
        
        Returns:
            ParserError 异常对象
        """
        if token is None:
            token = self.peek()
        
        # 构建错误消息
        error_msg = message
        
        if expected and got:
            error_msg = f"{message}: expected {expected}, got {got}"
        elif expected:
            error_msg = f"{message}: expected {expected}"
        
        # 获取上下文
        context = self.get_context(token)
        
        return ParserError(error_msg, token, context)
    
    # ==================== 解析方法 ====================
    
    def parse(self) -> DocumentNode:
        """解析整个文档"""
        statements = []
        max_iterations = 100000  # 防止死循环
        iterations = 0
        
        while not self.is_at_end():
            self.skip_newlines()  # 跳过空行
            if self.is_at_end():
                break
            
            iterations += 1
            if iterations > max_iterations:
                raise ParserError("Reached maximum iterations - possible infinite loop")
            
            stmt = self.parse_top_level_statement()
            if stmt:
                statements.append(stmt)
        
        return DocumentNode(statements)
    
    def synchronize(self):
        """错误恢复：跳到下一个语句边界"""
        self.advance()
        
        while not self.is_at_end():
            # 遇到右大括号，可能是语句边界
            if self.previous().type == TokenType.RBRACE:
                return
            
            # 遇到新的标识符，可能是新语句
            if self.check(TokenType.IDENTIFIER):
                return
            
            self.advance()
    
    def parse_top_level_statement(self) -> Optional[ASTNode]:
        """解析顶层语句（对象定义或常量定义）"""
        if self.is_at_end():
            return None
        
        # 常量定义：@constant = value
        if self.check(TokenType.AT):
            at_token = self.advance()
            
            # @ 后面必须是标识符
            if not self.check(TokenType.IDENTIFIER):
                raise self.error(
                    "Expected identifier after '@' in constant definition",
                    expected="IDENTIFIER",
                    got=f"{self.peek().type.name} '{self.peek().value}'"
                )
            
            const_name_token = self.advance()
            const_name = '@' + const_name_token.value  # 例如 "@buildings_t1"
            
            # 必须有 =
            self.consume(TokenType.EQUALS, f"Expected '=' after constant '{const_name}'")
            
            # 解析值（通常是数字或标识符）
            value = self.parse_value()
            
            # 创建常量定义节点
            const_def = ConstantDefinitionNode(const_name, value)
            const_def.line = at_token.line
            const_def.column = at_token.column
            
            return const_def
        
        # 对象定义格式: identifier = { ... }
        # 或属性赋值: identifier = value (虽然不常见)
        if self.check(TokenType.IDENTIFIER):
            # 保存位置，以便回退
            saved_pos = self.current_filtered
            name_token = self.peek()
            
            # 尝试使用统一的解析方法
            # 先尝试当作 property_or_comparison 解析
            try:
                result = self.parse_property_or_comparison()
                
                # 检查是否是对象定义（key = { ... }）
                if isinstance(result, PropertyNode) and isinstance(result.value, BlockNode):
                    # 这是对象定义，转换为 ObjectNode
                    obj = ObjectNode(result.key, result.value)
                    obj.line = result.line
                    obj.column = result.column
                    return obj
                else:
                    # 这是普通的属性或比较（虽然在顶层不常见）
                    return result
            except ParserError:
                # 如果解析失败，回退并抛出错误
                self.current_filtered = saved_pos
                raise
        
        # 无法识别的顶层语句
        current = self.peek()
        raise self.error(
            f"Unexpected token at top level",
            current,
            expected="IDENTIFIER or AT (@)",
            got=f"{current.type.name} '{current.value}'"
        )
    
    def parse_block(self) -> BlockNode:
        """解析代码块 { ... }"""
        self.consume(TokenType.LBRACE, "Expected '{'")
        
        statements = []
        
        while not self.is_at_end() and not self.check(TokenType.RBRACE):
            self.skip_newlines()  # 跳过空行
            if self.check(TokenType.RBRACE):
                break
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        
        self.consume(TokenType.RBRACE, "Expected '}'")
        
        return BlockNode(statements)
    
    def parse_statement(self) -> Optional[ASTNode]:
        """解析语句（在代码块内部）"""
        if self.is_at_end():
            return None
        
        # 条件参数块: [[PARAM] ... ]
        if self.check(TokenType.CONDITIONAL_PARAM):
            return self.parse_conditional_param()
        
        # 逻辑条件: OR = { ... }
        if self.is_logic_operator():
            return self.parse_condition()
        
        # 属性或比较: key = value (key 可以是标识符、数字或字符串)
        # 或系统指令: optimize_memory
        if self.check(TokenType.IDENTIFIER):
            # 检查是否是系统指令（单独的标识符，不带值）
            current_token = self.peek()
            identifier = current_token.value
            
            # 向前看，如果后面不是 = 或比较运算符，且是系统指令，则作为 Directive 处理
            next_token = self.peek_ahead(1)
            if identifier in SYSTEM_DIRECTIVES and next_token and next_token.type not in (
                TokenType.EQUALS, TokenType.GT, TokenType.LT,
                TokenType.GTE, TokenType.LTE, TokenType.EQUALS_EQUALS, TokenType.NOT_EQUALS,
                TokenType.DOT, TokenType.DIVIDE, TokenType.COLON, TokenType.AT
            ):
                # 这是一个系统指令
                self.advance()
                directive = DirectiveNode(identifier)
                directive.line = current_token.line
                directive.column = current_token.column
                return directive
            
            # 否则按普通属性/比较处理
            return self.parse_property_or_comparison()
        
        if self.check(TokenType.NUMBER):
            return self.parse_property_or_comparison()
        
        # 字符串作为键: "KEY" = value
        if self.check(TokenType.STRING):
            return self.parse_property_or_comparison()
        
        # 无法识别的语句
        current = self.peek()
        raise self.error(
            f"Unexpected token in statement",
            current,
            expected="IDENTIFIER, NUMBER, STRING, or logical operator",
            got=f"{current.type.name} '{current.value}'"
        )
    
    def parse_condition(self) -> ConditionNode:
        """解析逻辑条件块"""
        operator_token = self.advance()  # OR, AND, NOT, etc.
        operator = operator_token.value.upper()
        
        self.consume(TokenType.EQUALS, f"Expected '=' after '{operator}'")
        
        body = self.parse_block()
        
        condition = ConditionNode(operator, body)
        condition.line = operator_token.line
        condition.column = operator_token.column
        
        return condition
    
    def parse_conditional_param(self) -> 'ConditionalParamNode':
        """解析条件参数块 [[PARAM] ... ]"""
        from .ast_nodes import ConditionalParamNode
        
        param_token = self.advance()  # [[PARAM]
        param_value = param_token.value  # 例如 "[[SPIRITUALIST]"
        
        # 提取参数名（去掉 [[ 和 ]）
        param_name = param_value[2:-1]  # "[[SPIRITUALIST]" -> "SPIRITUALIST"
        
        # 跳过 [[PARAM] 后的换行
        self.skip_newlines()
        
        # 读取到匹配的 ] 为止的所有语句
        body = []
        while not self.is_at_end() and not self.check(TokenType.RBRACKET):
            self.skip_newlines()  # 跳过语句之间的换行
            if self.check(TokenType.RBRACKET):
                break
            stmt = self.parse_statement()
            if stmt is not None:
                body.append(stmt)
        
        # 消费结束的 ]
        self.consume(TokenType.RBRACKET, f"Expected ']' to close conditional param '[[{param_name}]'")
        
        conditional = ConditionalParamNode(param_name, body)
        conditional.line = param_token.line
        conditional.column = param_token.column
        
        return conditional
    
    def parse_property_or_comparison(self) -> Union[PropertyNode, ComparisonNode]:
        """解析属性或比较表达式
        
        统一使用 parse_identifier_chain() 解析左值，避免代码重复
        数字和字符串也可以作为键：0 = value, "KEY" = value
        """
        # 特殊情况：字符串作为键（例如 "MIN" = $MIN$）
        if self.check(TokenType.STRING):
            str_token = self.advance()
            key = str_token.value
            
            # 字符串键通常只用于赋值，不支持比较运算符
            self.consume(TokenType.EQUALS, f"Expected '=' after string key '{key}'")
            value = self.parse_value()
            
            prop = PropertyNode(key, value)
            prop.line = str_token.line
            prop.column = str_token.column
            return prop
        
        # 特殊情况：数字作为键（例如 traits = { 0 = value }）
        if self.check(TokenType.NUMBER):
            num_token = self.advance()
            key = num_token.value
            
            # 检查比较运算符
            if self.check(TokenType.GT) or self.check(TokenType.LT) or \
               self.check(TokenType.GTE) or self.check(TokenType.LTE) or \
               self.check(TokenType.EQUALS_EQUALS) or self.check(TokenType.NOT_EQUALS):
                op_token = self.advance()
                operator = self.get_operator_string(op_token.type)
                right = self.parse_value()
                
                comparison = ComparisonNode(key, operator, right)
                comparison.line = num_token.line
                comparison.column = num_token.column
                return comparison
            
            # 普通属性赋值
            self.consume(TokenType.EQUALS, f"Expected '=' or comparison operator after '{key}'")
            value = self.parse_value()
            
            prop = PropertyNode(key, value)
            prop.line = num_token.line
            prop.column = num_token.column
            return prop
        
        # 正常情况：解析标识符链作为左值
        left_node = self.parse_identifier_chain()
        
        # 从节点中提取键名
        # parse_identifier_chain 返回 IdentifierExpressionNode
        if isinstance(left_node, IdentifierExpressionNode):
            # 直接使用表达式字符串作为 key
            key = left_node.expression
        elif hasattr(left_node, 'value'):
            # ValueNode
            key = left_node.value
        else:
            raise self.error(
                "Invalid left-hand side in property or comparison",
                expected="identifier expression or value",
                got=f"{type(left_node).__name__}"
            )
        
        # 检查比较运算符（>= <= == != > <）
        if self.check(TokenType.GT) or self.check(TokenType.LT) or \
           self.check(TokenType.GTE) or self.check(TokenType.LTE) or \
           self.check(TokenType.EQUALS_EQUALS) or self.check(TokenType.NOT_EQUALS):
            op_token = self.advance()
            operator = self.get_operator_string(op_token.type)
            
            # 解析右值
            right = self.parse_value()
            
            comparison = ComparisonNode(key, operator, right)
            comparison.line = left_node.line
            comparison.column = left_node.column
            
            return comparison
        
        # 检查：如果是宏表达式（包含 $）且后面是结束符，允许单独成行
        # 例如：[[PARAM] $MACRO_VAR$ ]
        if '$' in key and (self.check(TokenType.NEWLINE) or self.check(TokenType.RBRACKET) or self.check(TokenType.RBRACE)):
            # 宏表达式可以作为独立语句，直接返回表达式节点
            return left_node
        
        # 普通属性赋值: key = value
        self.consume(TokenType.EQUALS, f"Expected '=' or comparison operator after '{key}'")
        
        value = self.parse_value()
        
        prop = PropertyNode(key, value)
        prop.line = left_node.line
        prop.column = left_node.column
        
        return prop
    
    def get_operator_string(self, token_type: TokenType) -> str:
        """将 TokenType 转换为运算符字符串"""
        mapping = {
            TokenType.EQUALS: '=',
            TokenType.GT: '>',
            TokenType.LT: '<',
            TokenType.GTE: '>=',
            TokenType.LTE: '<=',
            TokenType.EQUALS_EQUALS: '==',
            TokenType.NOT_EQUALS: '!=',
        }
        return mapping.get(token_type, '=')
    
    def parse_value(self) -> ASTNode:
        """解析值（可能是标量、代码块或列表）"""
        # 负数值: -123 或 -$VAR$
        if self.check(TokenType.MINUS):
            minus_token = self.advance()
            # 递归解析后面的值
            inner_value = self.parse_value()
            # 如果是 ValueNode，将负号添加到值前面
            if isinstance(inner_value, ValueNode):
                inner_value.value = '-' + str(inner_value.value)
                inner_value.line = minus_token.line
                inner_value.column = minus_token.column
                return inner_value
            # 如果是 IdentifierExpressionNode（如 -$VAR$），创建新的表达式
            elif isinstance(inner_value, IdentifierExpressionNode):
                inner_value.expression = '-' + inner_value.expression
                inner_value.line = minus_token.line
                inner_value.column = minus_token.column
                return inner_value
            else:
                # 其他情况，保持原样
                return inner_value
        
        # 代码块: { ... }
        if self.check(TokenType.LBRACE):
            # 需要判断是 Block 还是 List
            # 先看看第一个元素
            return self.parse_block_or_list()
        
        # 数字
        if self.check(TokenType.NUMBER):
            token = self.advance()
            value = ValueNode(token.value)
            value.line = token.line
            value.column = token.column
            return value
        
        # 字符串
        if self.check(TokenType.STRING):
            token = self.advance()
            value = ValueNode(token.value, 'string')
            value.line = token.line
            value.column = token.column
            return value
        
        # 常量引用或内联算术: @constant 或 @[ expr ]
        if self.check(TokenType.AT):
            at_token = self.advance()
            
            # 检查是否是内联算术表达式 @[ expr ] 或 @\[ expr ]
            if self.check(TokenType.LBRACKET):
                return self._parse_inline_arithmetic(at_token)
            
            # 否则必须是 @identifier 形式的常量引用
            if not self.check(TokenType.IDENTIFIER):
                raise ParserError("Expected identifier after '@' in constant reference", self.peek())
            
            const_name = '@' + self.advance().value
            value = ValueNode(const_name, 'constant')
            value.line = at_token.line
            value.column = at_token.column
            return value
        
        # 标识符（可能是布尔值、关键字、作用域链、特殊调用等）
        if self.check(TokenType.IDENTIFIER):
            return self.parse_identifier_chain()
        
        current = self.peek()
        raise self.error(
            f"Unexpected token in value expression",
            current,
            expected="LBRACE, NUMBER, STRING, IDENTIFIER, or AT (@)",
            got=f"{current.type.name} '{current.value}'"
        )
    
    def parse_identifier_chain(self) -> ASTNode:
        """解析标识符链（可能包含 . : @ / 等）
        
        使用新的 IdentifierExpressionNode 统一处理所有表达式
        
        支持的模式:
            owner.overlord.capital_scope
            value:tech_cost|PARAM|
            event_target:name.star
            event_target:name@scope
            identifier@scope.property
            jobs/miners_add
            crisis.8020
            tech_$AREA$_1 (宏参数)
            $FROM$.property (宏后缀)
        
        策略：先收集所有属于表达式的 token，再构建表达式字符串
        """
        # 保存起始位置
        start_token = self.peek()
        start_pos = self.current_filtered
        
        # 收集所有属于表达式的 token
        expression_tokens = []
        
        # 表达式可能包含的 token 类型
        EXPRESSION_TOKENS = {
            TokenType.IDENTIFIER, TokenType.NUMBER, TokenType.STRING,
            TokenType.DOT, TokenType.COLON, TokenType.PIPE, 
            TokenType.AT, TokenType.DIVIDE
        }
        
        # 收集 token 直到遇到表达式结束标记
        last_token_type = None
        while not self.is_at_end():
            current = self.peek()
            
            # 遇到换行，表达式结束
            if current.type == TokenType.NEWLINE:
                break
            
            # 如果是表达式的一部分，收集它
            if current.type in EXPRESSION_TOKENS:
                # 检查：如果上一个 token 是标量（IDENTIFIER/NUMBER/STRING），
                # 而当前也是标量，中间必须有操作符连接
                if last_token_type in (TokenType.IDENTIFIER, TokenType.NUMBER, TokenType.STRING) and \
                   current.type in (TokenType.IDENTIFIER, TokenType.NUMBER, TokenType.STRING):
                    # 连续的标量没有操作符分隔，停止收集
                    break
                
                expression_tokens.append(current)
                last_token_type = current.type
                self.advance()
            else:
                # 遇到非表达式 token，停止收集
                break
        
        # 如果没有收集到任何 token，返回简单的 ValueNode
        if not expression_tokens:
            raise self.error(
                "Expected identifier in expression",
                expected="IDENTIFIER or expression start",
                got=f"{self.peek().type.name if self.peek() else 'EOF'}"
            )
        

        expression_parts = []
        
        i = 0
        while i < len(expression_tokens):
            token = expression_tokens[i]
            
            # 处理特殊情况：value: 调用后的参数
            if token.type == TokenType.COLON and i > 0:
                # 添加 :
                expression_parts.append(token.value)
                i += 1
                
                # 检查后面是否是函数名
                if i < len(expression_tokens) and expression_tokens[i].type == TokenType.IDENTIFIER:
                    expression_parts.append(expression_tokens[i].value)
                    i += 1
                    
                    # 检查是否有参数（PIPE 开头）
                    if i < len(expression_tokens) and expression_tokens[i].type == TokenType.PIPE:
                        # 收集所有参数直到没有更多 PIPE
                        # 参数格式: |name|value|name|value|
                        while i < len(expression_tokens) and expression_tokens[i].type == TokenType.PIPE:
                            expression_parts.append('|')
                            i += 1
                            
                            # 读取参数名/值
                            if i < len(expression_tokens) and expression_tokens[i].type in (
                                TokenType.IDENTIFIER, TokenType.NUMBER, TokenType.STRING
                            ):
                                expression_parts.append(expression_tokens[i].value)
                                i += 1
                            else:
                                # 最后一个 PIPE 后没有参数，结束
                                break
                continue
            
            # 普通 token，直接添加
            expression_parts.append(token.value)
            i += 1
        
        # 构建最终的表达式字符串
        full_expression = ''.join(expression_parts)
        
        # 创建 IdentifierExpressionNode
        expr_node = IdentifierExpressionNode(full_expression)
        expr_node.line = start_token.line
        expr_node.column = start_token.column
        
        return expr_node
    
    def _parse_scripted_value_arguments(self) -> list:
        """解析 scripted value 的参数列表
        
        格式: |param_name_1|param_value_1|param_name_2|param_value_2|
        参数是成对出现的：名称-值对
        
        注意：
        - 不支持换行，遇到 NEWLINE 立即终止
        - 如果参数名后面没有对应的值，报错
        - 最后一个 | 是结束标记（后面没有参数）
        """
        arguments = []
        
        while self.check(TokenType.PIPE):
            self.advance()  # 跳过 |
            
            # 检查是否遇到结束（没有更多参数）
            if self.is_at_end():
                break
            
            # 尝试读取参数名
            param_name = None
            if self.check(TokenType.IDENTIFIER):
                param_name = self.advance().value
            elif self.check(TokenType.NUMBER):
                param_name = self.advance().value
            elif self.check(TokenType.STRING):
                param_name = self.advance().value
            else:
                # 没有参数名，说明是最后一个 | 或遇到其他 token，参数列表结束
                break
            
            # 添加参数名
            arguments.append(param_name)
            
            # 参数名后面必须有 |
            if not self.check(TokenType.PIPE):
                raise self.error(
                    f"Expected '|' after parameter name '{param_name}' in scripted value call",
                    expected="PIPE (|)",
                    got=f"{self.peek().type.name} '{self.peek().value}'"
                )
            
            self.advance()  # 跳过 |
            
            # 读取参数值（必需）
            if self.check(TokenType.IDENTIFIER):
                arguments.append(self.advance().value)
            elif self.check(TokenType.NUMBER):
                arguments.append(self.advance().value)
            elif self.check(TokenType.STRING):
                arguments.append(self.advance().value)
            else:
                # 参数名后面没有值
                current = self.peek()
                raise self.error(
                    f"Expected parameter value after '{param_name}|' in scripted value call",
                    current,
                    expected="IDENTIFIER, NUMBER, or STRING",
                    got=f"{current.type.name} '{current.value}'"
                )
        
        return arguments
    
    def _parse_inline_arithmetic(self, at_token: Token) -> ASTNode:
        r"""解析内联算术表达式
        
        格式: @[ expr ] 或 @\[ expr ]
        例如: @[( 72 * $PROGRESS$ )]
        
        当前实现：保存原始表达式文本，不解析内部结构
        """
        from .ast_nodes import InlineArithmeticNode
        
        # 检查是否是转义形式 @\[
        escaped = at_token.value == '@\\'
        
        # 消费 [
        self.consume(TokenType.LBRACKET, "Expected '[' after '@' in inline arithmetic")
        
        # 收集所有 token 直到匹配的 ]
        expression_tokens = []
        bracket_depth = 1  # 已经消费了一个 [
        
        while not self.is_at_end() and bracket_depth > 0:
            current = self.peek()
            
            if current.type == TokenType.LBRACKET:
                bracket_depth += 1
            elif current.type == TokenType.RBRACKET:
                bracket_depth -= 1
                if bracket_depth == 0:
                    # 找到匹配的右括号，不包含在表达式中
                    break
            
            expression_tokens.append(self.advance())
        
        # 消费结束的 ]
        if not self.check(TokenType.RBRACKET):
            current = self.peek()
            raise self.error(
                "Expected ']' to close inline arithmetic expression",
                current,
                expected="RBRACKET (])",
                got=f"{current.type.name if current else 'EOF'}"
            )
        self.advance()
        
        # 构建表达式文本（不添加空格以保留原始格式）
        expression = ''.join(token.value for token in expression_tokens)
        
        # 创建节点
        node = InlineArithmeticNode(expression, escaped)
        node.line = at_token.line
        node.column = at_token.column
        return node
    
    def parse_block_or_list(self) -> Union[BlockNode, ListNode]:
        """解析代码块或列表
        
        代码块: { key = value ... }
        列表: { item1 item2 item3 }
        """
        start_token = self.peek()
        self.consume(TokenType.LBRACE)
        
        self.skip_newlines()  # 跳过开头的换行
        
        # 空块
        if self.check(TokenType.RBRACE):
            self.advance()
            return BlockNode([])
        
        # 判断是 Block 还是 List
        # 如果第一个 token 是逻辑运算符或条件参数，肯定是 Block
        if self.is_logic_operator() or self.check(TokenType.CONDITIONAL_PARAM):
            statements = []
            while not self.is_at_end() and not self.check(TokenType.RBRACE):
                self.skip_newlines()  # 跳过换行
                if self.check(TokenType.RBRACE):
                    break
                stmt = self.parse_statement()
                if stmt:
                    statements.append(stmt)
            
            self.consume(TokenType.RBRACE)
            block = BlockNode(statements)
            block.line = start_token.line
            block.column = start_token.column
            return block
        
        # 如果第一个 token 是 identifier、number 或 string，需要向前看找到 = 或比较运算符
        if self.check(TokenType.IDENTIFIER) or self.check(TokenType.NUMBER) or self.check(TokenType.STRING):
            # 向前扫描，跳过 . / 等，找到是否有 = 或比较运算符
            lookahead = 1
            has_assignment = False
            while lookahead < 20:  # 最多看 20 个 token
                ahead = self.peek_ahead(lookahead)
                if not ahead:
                    break
                
                # 跳过 NEWLINE
                if ahead.type == TokenType.NEWLINE:
                    lookahead += 1
                    continue
                
                # 找到赋值或比较运算符，这是 Block
                if ahead.type in (TokenType.EQUALS, TokenType.GT, TokenType.LT,
                                 TokenType.GTE, TokenType.LTE, TokenType.EQUALS_EQUALS,
                                 TokenType.NOT_EQUALS):
                    has_assignment = True
                    break
                
                # 如果遇到 }，说明是简单值列表
                if ahead.type == TokenType.RBRACE:
                    break
                
                # 继续向前看
                lookahead += 1
            
            if has_assignment:
                # 这是一个 Block
                statements = []
                while not self.is_at_end() and not self.check(TokenType.RBRACE):
                    self.skip_newlines()  # 跳过换行
                    if self.check(TokenType.RBRACE):
                        break
                    stmt = self.parse_statement()
                    if stmt:
                        statements.append(stmt)
                
                self.consume(TokenType.RBRACE)
                block = BlockNode(statements)
                block.line = start_token.line
                block.column = start_token.column
                return block
        
        # 否则是 List（值列表）
        items = []
        
        while not self.is_at_end() and not self.check(TokenType.RBRACE):
            self.skip_newlines()  # 跳过换行
            if self.check(TokenType.RBRACE):
                break
            
            # 解析列表项
            if self.check(TokenType.NUMBER):
                token = self.advance()
                items.append(ValueNode(token.value))
            elif self.check(TokenType.STRING):
                token = self.advance()
                items.append(ValueNode(token.value, 'string'))
            elif self.check(TokenType.IDENTIFIER):
                # IDENTIFIER 可能是简单值，也可能是复合表达式（如 marauder.15）
                # 向前看一个 token 来判断
                next_token = self.peek_ahead(1)
                if next_token and next_token.type in (TokenType.DOT, TokenType.COLON, TokenType.DIVIDE, TokenType.AT):
                    # 这是复合表达式，使用 parse_identifier_chain 解析
                    expr = self.parse_identifier_chain()
                    items.append(expr)
                else:
                    # 简单标识符
                    token = self.advance()
                    items.append(ValueNode(token.value))
            elif self.check(TokenType.AT):
                # 常量引用 @constant
                at_token = self.advance()
                if self.check(TokenType.IDENTIFIER):
                    const_name = '@' + self.advance().value
                    items.append(ValueNode(const_name, 'constant'))
                else:
                    # 单独的 @，也当作值
                    items.append(ValueNode('@', 'identifier'))
            else:
                break
        
        self.consume(TokenType.RBRACE)
        list_node = ListNode(items)
        list_node.line = start_token.line
        list_node.column = start_token.column
        return list_node


def parse(text: str) -> DocumentNode:
    """便捷函数：直接从文本解析为 AST"""
    from .lexer import Lexer
    
    lexer = Lexer(text)
    tokens = lexer.tokenize()
    
    parser = Parser(tokens, source_text=text)
    return parser.parse()


# ==================== 测试代码 ====================

if __name__ == '__main__':
    # 测试用例
    test_code = """
building_research_lab_1 = {
    category = research
    cost = {
        minerals = 400
    }
    
    potential = {
        NOT = { has_modifier = slave_colony }
    }
    
    destroy_trigger = {
        OR = {
            owner = { is_ai = no }
            has_modifier = slave_colony
            num_pops >= 50
        }
    }
    
    produces = {
        physics_research = 10
        society_research = 10
        engineering_research = 10
    }
    
    planet_modifier = {
        planet_researchers_produces_mult = 0.05
    }
    
    triggered_planet_modifier = {
        potential = {
            exists = owner
            owner = { is_regular_empire = yes }
        }
        modifier = {
            job_researcher_add = 2
        }
    }
}

building_research_lab_2 = {
    category = research
    base_buildtime = @b2_time
    can_build = yes
}
"""
    
    print("=" * 60)
    print("测试 Parser")
    print("=" * 60)
    
    # 解析
    ast = parse(test_code)
    
    print(f"\n解析结果: {ast}")
    print(f"顶层对象数量: {len(ast.statements)}")
    
    for i, obj in enumerate(ast.statements):
        if isinstance(obj, ObjectNode):
            print(f"\n对象 {i+1}: {obj.name}")
            print(f"  属性数量: {len(obj.body.statements)}")
            
            for prop in obj.body.statements[:5]:  # 只显示前 5 个属性
                if isinstance(prop, PropertyNode):
                    print(f"    - {prop.key} = {type(prop.value).__name__}")
                elif isinstance(prop, ConditionNode):
                    print(f"    - {prop.operator} (condition)")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
