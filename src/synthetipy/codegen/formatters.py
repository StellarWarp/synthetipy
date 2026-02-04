"""
格式化工具模块

提供值格式化、标识符处理等通用功能
"""

from typing import Union
from ..ast_nodes import *
from ..pdx_constants import safe_identifier



class Formatter:
    """格式化工具类"""
    
    @staticmethod
    def format_literal(value: ASTNode) -> str:
        """
        格式化值为 Python 字面量
        
        Args:
            value: 值节点
        
        Returns:
            Python 字面量字符串
        """
        if isinstance(value, LiteralNode):
            if value.value_type == 'string':
                # 字符串需要转义
                escaped = str(value.value).replace("'", "\\'")
                return f"'{escaped}'"
            elif value.value_type == 'bool':
                return 'True' if value.value else 'False'
            elif value.value_type in ('int', 'float'):
                return str(value.value)
            elif value.value_type == 'identifier':
                # 标识符作为字符串
                return f"'{value.value}'"
            elif value.value_type == 'variable':
                # 变量引用（@xxx）
                return f"'{value.value}'"
            else:
                return f"'{value.value}'"
        elif isinstance(value, ListNode):
            # 递归处理列表
            elements = [Formatter.format_literal(elem) for elem in value.items]
            return '[' + ', '.join(elements) + ']'
        elif isinstance(value, IdentifierExpressionNode):
            # 标识符表达式
            # 特殊处理 yes/no 作为布尔值
            if value.expression == 'yes':
                return 'True'
            elif value.expression == 'no':
                return 'False'
            else:
                return f"'{value.expression}'"
        elif isinstance(value, BlockNode):
            # 块节点不应该用 format_literal 处理，应该生成嵌套类
            return "..."
        else:
            # 其他类型尝试获取字符串表示
            if hasattr(value, 'value'):
                return f"'{value.value}'"
            elif hasattr(value, 'expression'):
                return f"'{value.expression}'"
            else:
                return "..."
    
    @staticmethod
    def format_list(lst: ListNode) -> str:
        """
        格式化列表
        
        Args:
            lst: 列表节点
        
        Returns:
            Python 列表字符串
        """
        elements = [Formatter.format_literal(elem) for elem in lst.items]
        return '[' + ', '.join(elements) + ']'
    
    @staticmethod
    def get_identifier(node: Union[str, ASTNode]) -> str:
        """
        获取标识符字符串（返回安全的 Python 标识符）
        
        Args:
            node: 标识符节点或字符串
        
        Returns:
            标识符字符串（已做安全处理）
        """
        if isinstance(node, str):
            return safe_identifier(node)
        else:
            # 处理 AST 节点 - 转换为字符串并做安全处理
            # TODO: 处理 MacroIdentifierNode 等复杂情况
            if hasattr(node, 'name'):
                return safe_identifier(str(node.name))
            elif hasattr(node, 'value'):
                return safe_identifier(str(node.value))
            else:
                return safe_identifier(str(node))
    
    @staticmethod
    def sanitize_class_name(name: str) -> str:
        """
        清理类名，确保符合 Python 规范
        
        Args:
            name: 原始名称
        
        Returns:
            清理后的类名
        """
        # TODO: 处理特殊字符、关键字冲突等
        return name
    
    @staticmethod
    def escape_string(s: str) -> str:
        """
        转义字符串中的特殊字符
        
        Args:
            s: 原始字符串
        
        Returns:
            转义后的字符串
        """
        return s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
    
    @staticmethod
    def format_literal_reference(value: ASTNode, scope_var: str = "scope", macro_params: dict = None) -> str:
        """
        格式化 value:xxx 引用为 Python 代码
        
        支持:
        - value:func_name -> func_name(scope)
        - value:func|PARAM|val| -> func(scope, PARAM=val)
        - IdentifierExpressionNode 带 call_pattern = 'value'
        
        Args:
            value: 值节点
            scope_var: 作用域变量名
            macro_params: 宏参数字典（用于识别简单参数）
        
        Returns:
            Python 调用代码，如果不是 value: 引用则返回 None
        """
        expr_str = None
        call_pattern = None
        
        # 处理 IdentifierExpressionNode
        if hasattr(value, 'call_pattern') and hasattr(value, 'expression'):
            call_pattern = value.call_pattern
            expr_str = value.expression
        elif isinstance(value, LiteralNode):
            expr_str = str(value.value)
            if expr_str.startswith('value:'):
                call_pattern = 'value'
        
        if call_pattern != 'value' or not expr_str:
            return None
        
        # 解析 value:xxx 或 value:xxx|PARAM|val|
        if ':' in expr_str:
            _, rest = expr_str.split(':', 1)
        else:
            rest = expr_str
        
        # 检查是否有参数
        if '|' in rest:
            parts = rest.split('|')
            func_name = parts[0]
            # 解析参数对: |PARAM|val|PARAM2|val2|
            params = []
            i = 1
            while i + 1 < len(parts):
                param_name = parts[i]
                param_val = parts[i + 1]
                if param_name:  # 跳过空字符串
                    # 格式化参数值
                    formatted_val = Formatter._format_param_value(param_val, macro_params)
                    params.append(f"{param_name}={formatted_val}")
                i += 2
            
            if params:
                params_str = ", ".join(params)
                return f"{safe_identifier(func_name)}({scope_var}, {safe_identifier(params_str)})"
            else:
                return f"{safe_identifier(func_name)}({scope_var})"
        else:
            return f"{safe_identifier(rest)}({scope_var})"
    

    @staticmethod
    def format_literal_any(value, macro_params: dict = None) -> str:
        """
        通用的字面量格式化接口，接受 AST 节点或原始值。
        - 如果是 AST 节点，使用现有的 `format_literal` 处理
        - 如果是字符串或原始类型，根据宏参数表（macro_params）判断是否保留为参数名
        """
        # AST 节点情况
        if hasattr(value, '__class__') and isinstance(value, ASTNode):
            return Formatter.format_literal(value)

        # 布尔值
        if isinstance(value, bool):
            return 'True' if value else 'False'

        # 数字
        if isinstance(value, (int, float)):
            return str(value)

        # 字符串处理
        if isinstance(value, str):
            # 简单宏参数 $PARAM$
            if value.startswith('$') and value.endswith('$') and value.count('$') == 2:
                param_name = value[1:-1].split('|')[0]
                if macro_params and param_name in macro_params:
                    return param_name
                return repr(value)

            # yes/no
            if value in ('yes', 'no'):
                return 'True' if value == 'yes' else 'False'

            # @ 常量引用
            if value.startswith('@'):
                return repr(value)

            # 纯数字字符串
            try:
                if '.' in value:
                    float(value)
                    return value
                int(value)
                return value
            except Exception:
                pass

            # 默认字符串字面量
            return repr(value)

        # 其他类型回退到 repr
        return repr(value)

    # -------------------- Identifier / Call helpers --------------------
    @staticmethod
    def _callinfo_args_to_kwargs(call_info: 'CallInfo', macro_params: dict = None) -> str:
        """
        将 CallInfo.arguments 转换为关键字参数字符串，
        MacroParam（simple）会映射为参数名（不加引号），否则按 literal 处理。
        Returns: "k1=v1, k2=v2"
        """
        parts = []
        for key, val in call_info.arguments:
            # MacroParam -> simple param name if available
            from ..ast_nodes_expression import MacroParam
            if isinstance(val, MacroParam):
                pname = val.name
                if macro_params and pname in macro_params and macro_params[pname].is_simple:
                    parts.append(f"{key}={pname}")
                else:
                    # unknown macro param -> keep as raw $...$
                    parts.append(f"{key}={repr(val.to_source())}")
            else:
                # raw value -> use format_literal_any
                formatted = Formatter.format_literal_any(val, macro_params)
                parts.append(f"{key}={formatted}")
        return ", ".join(parts)

    @staticmethod
    def scope_to_access(scope_node: 'ScopeNode', scope_var: str = "scope") -> str:
        """
        将 ScopeNode 转为作用域访问表达式（仅负责 scope 部分）。
        例如: ScopeNode(owner.overlord) -> scope_var.owner.overlord
        event_target:federation_leader -> scope_var.get_event_target('federation_leader')
        注意：该函数仅接受 ScopeNode（或类似包含 scopes 属性的节点），不处理 identifier 或 call_info。
        """
        if scope_node is None:
            return scope_var

        # 判断第一个 scope 是否为 event_target
        first = scope_node.scopes[0]
        if isinstance(first, ASTNode) and getattr(first, 'scope_name', None) == 'event_target':
            target = first.target
            if hasattr(target, 'name'):
                target_name = target.name
            else:
                target_name = str(target)
            return f"{scope_var}.get_event_target({repr(target_name)})"

        # 否则生成普通链式访问
        chain = '.'.join(s.scope_name for s in scope_node.scopes)
        return f"{scope_var}.{chain}"

    @staticmethod
    def identifier_to_call(node: 'IdentifierExpressionNode', scope_var: str = "scope", macro_params: dict = None, call_kind: str = 'auto') -> 'Optional[str]':
        """
        统一入口：把 IdentifierExpressionNode (带 call_info) 转为 value/modifier/trigger 调用的 Python 片段。
        返回 None 表示该 node 不代表可生成的 call（或是 macro 表达式需要打包）。
        """
        # macro expressions should be handled by package_macro_* helpers
        if node.is_macro_expression:
            return None

        if not node.call_info:
            return None

        call = node.call_info
        # value: -> script value function, first arg is target scope
        if call.call_type == 'value':
            # target scope expression
            target = scope_var
            if node.scope:
                target = Formatter.scope_to_access(node.scope, scope_var)
            # build kwargs
            kw = Formatter._callinfo_args_to_kwargs(call, macro_params)
            if kw:
                return f"{safe_identifier(call.function_name)}({target}, {kw})"
            else:
                return f"{safe_identifier(call.function_name)}({target})"

        # modifier: treated as numeric accessor? map to scope_var.<scope>.modifier.<name>
        if call.call_type == 'modifier':
            if node.scope:
                scope_access = Formatter.scope_to_access(node.scope, scope_var)
                return f"{scope_access}.modifier.{safe_identifier(call.function_name)}"
            else:
                return f"{scope_var}.modifier.{safe_identifier(call.function_name)}"

        # trigger or other call types -> method-like boolean call on scope
        if call.call_type in ('trigger',):
            target = scope_var
            if node.scope:
                target = Formatter.scope_to_access(node.scope, scope_var)
            kw = Formatter._callinfo_args_to_kwargs(call, macro_params)
            if kw:
                return f"{target}.{safe_identifier(call.function_name)}({kw})"
            else:
                return f"{target}.{safe_identifier(call.function_name)}()"

        # unknown call types: default to None
        return None

    @staticmethod
    def _serialize_block_to_pdx(block: 'BlockNode') -> str:
        """
        简单序列化 BlockNode 为 PDX 源（用于 meta.pdx 打包）
        """
        lines = []
        for stmt in block.statements:
            if isinstance(stmt, PropertyNode):
                key = stmt.key.to_source() if hasattr(stmt.key, 'to_source') else str(stmt.key)
                if isinstance(stmt.value, BlockNode):
                    inner = Formatter._serialize_block_to_pdx(stmt.value)
                    lines.append(f"{key} = {{")
                    for l in inner.split('\n'):
                        lines.append(f"    {l}")
                    lines.append("}")
                else:
                    val = stmt.value.to_source() if hasattr(stmt.value, 'to_source') else str(stmt.value)
                    lines.append(f"{key} = {val}")
            elif isinstance(stmt, ComparisonNode):
                left = stmt.left if isinstance(stmt.left, str) else str(stmt.left)
                right = stmt.right.to_source() if hasattr(stmt.right, 'to_source') else str(stmt.right)
                lines.append(f"{left} {stmt.operator} {right}")
            else:
                lines.append(f"# TODO: serialize {type(stmt).__name__}")
        return '\n'.join(lines)

    @staticmethod
    def package_macro_lhs(value_node, macro_params: dict = None) -> str:
        """
        将左值 MacroExpression 或 IdentifierExpressionNode（macro）转换为 f-string 形式的字符串片段。
        例如: MacroExpression('tech_$AREA$_1') -> "f'tech_{AREA}_1'"
        """
        # accept either MacroExpression or IdentifierExpressionNode with macro_expression
        macro = None
        if hasattr(value_node, 'is_macro_expression') and value_node.is_macro_expression:
            macro = value_node.macro_expression
        elif isinstance(value_node, MacroExpression):
            macro = value_node
        else:
            raise ValueError('package_macro_lhs requires a MacroExpression or IdentifierExpressionNode with macro')

        fmt = macro.raw_expression
        # replace $NAME$ with {NAME}
        import re
        def repl(m):
            inner = m.group(1).split('|')[0]
            return f"{{{inner}}}"
        pattern = r"\$([^$]+)\$"
        body = re.sub(pattern, repl, fmt)
        # return template body (to be used inside an f-string externally)
        return body

    @staticmethod
    def package_macro_statement_pdx(stmt, scope_var: str = "scope", macro_params: dict = None, pdx_inner_indent: int = 4) -> list:
        """
        将带有 MacroExpression 左值的语句包装为 meta.pdx(...) 调用，支持多行 block。
        使用现有的 generate_pdx_block 以保证参数和模板格式一致。

        pdx_inner_indent: number of spaces to prefix to the lines inside the PDX template
        (so the lines inside triple-quoted string are indented visually under the opening quote).
        """
        if isinstance(stmt, PropertyNode):
            lhs_node = stmt.key
            rhs_block = stmt.value
        else:
            lhs_node, rhs_block = stmt

        if not (hasattr(lhs_node, 'is_macro_expression') and lhs_node.is_macro_expression):
            raise ValueError('package_macro_statement_pdx expects lhs to be macro expression')

        # Accept RHS as BlockNode or single value. For BlockNode we serialize as multi-line; otherwise single-line value.
        if isinstance(rhs_block, BlockNode):
            body = Formatter._serialize_block_to_pdx(rhs_block)
            if hasattr(lhs_node, 'is_macro_expression') and lhs_node.is_macro_expression:
                raw_lhs = lhs_node.macro_expression.raw_expression
            elif isinstance(lhs_node, MacroExpression):
                raw_lhs = lhs_node.raw_expression
            else:
                raw_lhs = str(lhs_node)

            pdx_template = f"{raw_lhs} = {{\n{body}\n}}"
        else:
            # single-line value
            rhs_src = rhs_block.to_source() if hasattr(rhs_block, 'to_source') else str(rhs_block)
            if hasattr(lhs_node, 'is_macro_expression') and lhs_node.is_macro_expression:
                raw_lhs = lhs_node.macro_expression.raw_expression
            elif isinstance(lhs_node, MacroExpression):
                raw_lhs = lhs_node.raw_expression
            else:
                raw_lhs = str(lhs_node)

            pdx_template = f"{raw_lhs} = {rhs_src}"

        # Build meta.pdx(...) lines directly (avoid generate_pdx_block - deprecated)
        lines: list[str] = []

        # opening
        lines.append('meta.pdx("""')

        # body: multi-line or single line
        for line in pdx_template.strip().split('\n'):
            lines.append((' ' * pdx_inner_indent) + line)

        # closing + params
        params = macro_params or {}
        if params:
            param_strs = [f"{p.name}={p.name}" for p in sorted(params.values(), key=lambda x: x.name)]
            params_str = ", ".join(param_strs)
            lines.append(f'""", {params_str})')
        else:
            lines.append('""")')

        return lines

    @staticmethod
    def package_macro_value_macro(value_node, macro_params: dict = None) -> list:
        """
        将右值为 MacroExpression 的情况包装为 meta.pdx_macro(f'...') 单行调用。
        返回生成的代码行列表（一行）。
        """
        # accept MacroExpression or IdentifierExpressionNode with macro_expression
        if hasattr(value_node, 'is_macro_expression') and value_node.is_macro_expression:
            macro = value_node.macro_expression
        elif isinstance(value_node, MacroExpression):
            macro = value_node
        else:
            raise ValueError('package_macro_value_macro expects a MacroExpression or IdentifierExpressionNode with macro')

        body = Formatter.package_macro_lhs(value_node, macro_params)
        # produce a single-line meta.pdx_macro with an f-string
        call_line = f"meta.pdx_macro(f\"{body}\")"
        return [call_line]

    @staticmethod
    def package_macro_statement(stmt, scope_var: str = "scope", macro_params: dict = None) -> list:
        """
        包装一整条宏赋值语句为 meta.pdx 调用行（或 meta.pdx_macro），返回要插入的代码行列表。
        输入可以是 PropertyNode 或 (key, BlockNode)
        """
        if isinstance(stmt, PropertyNode):
            lhs_node = stmt.key
            rhs_block = stmt.value
        else:
            lhs_node, rhs_block = stmt

        if not (hasattr(lhs_node, 'is_macro_expression') and lhs_node.is_macro_expression):
            raise ValueError('package_macro_statement expects lhs to be macro expression')
        if not isinstance(rhs_block, BlockNode):
            raise ValueError('package_macro_statement expects rhs to be BlockNode')

        lhs_template = Formatter.package_macro_lhs(lhs_node, macro_params)
        body = Formatter._serialize_block_to_pdx(rhs_block)

        # Build an f-string triple-quoted block: meta.pdx_macro(f"""{lhs_template} =\n{body}\n""")
        # Note: body is inserted verbatim; for P0 we assume body does not contain triple quotes.
        call_line = f"meta.pdx_macro(f\"\"\"{lhs_template} =\n{body}\n\"\"\")"
        return [call_line]
    
   