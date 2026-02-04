"""
ScopeTranslator

提供统一的 scope 访问/切换/循环的转换工具，供生成器调用。

统一负责：
- 作用域访问和切换
- 作用域判断逻辑

最小 API：
- dotted(scope_or_name) -> str
- enter_scope_block(scope_name) -> str (returns new scope var name and emits with-line)
- exit_scope_block()
- enter_iteration_loop(key, limit_block, expr_builder) -> str
- exit_iteration_loop()
- generate_loop(key, value, expr_builder, body_generator)
- exists_expr(value_node) -> str
- iteration_info(key) -> Optional[(collection_name, item_type)]
- is_scope_lhs(node) -> bool
- is_iteration_scope(node) -> bool

"""
from typing import Any, Optional, Tuple, Callable
from ...pdx_constants import ITERATION_SCOPES, safe_identifier
from ...ast_nodes import ScopeNode, ScopeObjectNode, EventTargetNode, IdentifierExpressionNode, LiteralNode, BlockNode, PropertyNode
from ...pdx_constants import safe_identifier



class ScopeTranslator:
    def __init__(self, parent_generator):
        self.parent = parent_generator
        self.context = parent_generator.context

    def dotted(self, scope_or_name) -> str:
        """Return a dotted access string for a scope or name (e.g. scope.owner.capital)"""
        base = self.context.current_scope_var

        # If given a ScopeNode (chain), build dotted access
        if not isinstance(scope_or_name, ScopeNode):
            raise ValueError("dotted() expects a ScopeNode")
        parts = []
        for s in scope_or_name.scopes:
            if isinstance(s, ScopeObjectNode):
                parts.append(safe_identifier(s.scope_name))
            elif isinstance(s, EventTargetNode):
                # EventTargetNode should be accessed via helper
                if hasattr(s, 'target_macro'):
                    # Macro param - let caller handle usage
                    parts.append(f"get_event_target({s.target_macro.name})")
                else:
                    parts.append(f"get_event_target('{s.target.name}')")
        return f"{base}." + '.'.join(parts), parts[-1]

        

    def enter_scope_block(self, key: ScopeNode, dotted_expr = False, inline = False) -> str:
        """Generate a with block for entering a new scope and return the temp var name.
        Emits the with-line using parent's _add_line and updates context via ScopeManager.
        """
        assert not (dotted_expr and inline), "dotted_expr and inline cannot be used together"
        (access, current) = self.dotted(key)
        scope_var = current
        if not inline:
            if dotted_expr:
                self.parent._add_line(f"{scope_var} = {access}")
            else:
                self.parent._add_line(f"with {access} as {scope_var}:")
                self.parent._indent()
            # push scope to context
            self.context.push_scope(scope_var)
            return scope_var
        else:
            self.context.push_scope(access)
            return access

    def exit_scope_block(self, dotted_expr = False, inline = False):
        """Exit previously entered scope block (pop and dedent)."""
        self.context.pop_scope()
        if not dotted_expr and not inline:
            self.parent._dedent()

    def exists_expr(self, value_node) -> str:
        """Return a python expression string for `exists = <value_node>` semantics."""
        base = self.context.current_scope_var
        # IdentifierExpressionNode with simple identifier
        if isinstance(value_node, IdentifierExpressionNode):
            name = str(value_node.scope)
            if name:
                return f"{base}.exists('{name}')"
        elif isinstance(value_node, ScopeNode):
            name = str(value_node)
            return f"{base}.exists('{name}')"
            
        # Fallback: return an expression string for unknown node
        # Caller should handle UnsupportedFeatureError if needed
        return f"{base}.exists('{str(value_node)}')"

    def iteration_info(self, key: str) -> Optional[Tuple[str, str]]:
        """Get iteration info for a given key from ITERATION_SCOPES.
        Returns (item_type, collection_name) or None if not found.
        """
        return ITERATION_SCOPES.get(key)

    def enter_iteration_loop(self, key: str) -> str:
        """Emit a for-loop for an iteration scope and return the loop variable name."""
        info = self.iteration_info(key)
        if not info:
            raise ValueError(f"Unknown iteration scope: {key}")
        item_type = info[0]
        loop_var = self.context.get_loop_var(item_type)
        self.parent._add_line(f"for {loop_var} in {self.context.current_scope_var}.{safe_identifier(str(key))}:")
        self.parent._indent()
        # Set current scope to loop var so inner generation references it
        self.context.push_scope(loop_var)
        return loop_var

    def exit_iteration_loop(self):
        """Exit an iteration loop (pop scope and dedent)."""
        self.context.pop_scope()
        self.parent._dedent()

    def is_scope_lhs(self, key) -> bool:
        """Return True if the given node is a structured scope-only LHS.

        Conditions:
        - node is IdentifierExpressionNode
        - node.scope is present and contains at least one ScopeObjectNode or EventTargetNode
        - node has no call_info and is not a macro_expression
        """
        if isinstance(key, ScopeNode):
            return True
        return False
        
    def is_iteration_scope(self, key) -> bool:
        """Check if a given key represents an iteration scope.
        
        Args:
            key: String key or AST node (will be automatically converted to string)
            
        Returns:
            True if the key string exists in ITERATION_SCOPES
        """
        # Automatically convert to string if not already
        return str(key) in ITERATION_SCOPES
