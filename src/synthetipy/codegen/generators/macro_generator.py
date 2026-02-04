"""
MacroGenerator

Handles serialization of macro-related codegen tasks:
- Serializing RHS with macro concatenations into f-string templates and parameter lists
- Serializing blocks into meta.pdx(...) calls
- Producing pdx macro call lines
"""
from typing import Tuple, Dict, List
from ...ast_nodes import LiteralNode, BlockNode
from ..macro_parameter_utils import generate_pdx_block


class MacroGenerator:
    def __init__(self, parent_generator):
        self.parent = parent_generator
        self.context = parent_generator.context

    def rhs_to_fstring(self, value_node) -> Tuple[str, Dict[str, str]]:
        """Convert a value node containing macros to an f-string template and params mapping.

        Returns (template, params) where params maps NAME -> NAME (caller will wire parameter values).
        """
        text = None
        if isinstance(value_node, LiteralNode):
            text = str(value_node.value)
        elif hasattr(value_node, 'expression'):
            text = value_node.expression
        else:
            text = str(value_node)

        import re
        # matches $NAME$ or $NAME|default$
        matches = re.findall(r'\$([A-Z_][A-Z0-9_]*)(?:\|[^$]+)?\$', text)
        template = text
        params = {}
        for m in matches:
            template = template.replace(f"${m}$", f"{{{m}}}")
            params[m] = m
        return template, params

    def serialize_block_to_pdx(self, block: BlockNode) -> str:
        """Return PDX template string for a BlockNode using parent's serializer"""
        return self.parent._serialize_block_to_pdx(block)

    def pdx_call_lines(self, pdx_template: str, parameters: Dict[str, object]) -> List[str]:
        """Return lines for meta.pdx(...) call using generate_pdx_block"""
        return generate_pdx_block(pdx_template, parameters, indent=0)

    def format_macro_lhs(self, lhs_node, rhs_block) -> List[str]:
        """High-level helper to format macro-LHS + RHS into pdx call lines."""
        pdx_template = self.serialize_block_to_pdx(rhs_block)
        params = self.parent.parameters if hasattr(self.parent, 'parameters') else {}
        return self.pdx_call_lines(pdx_template, params)
