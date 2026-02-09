"""Utilities for AST traversal, labeling, and structural equality checks."""
from typing import List, Tuple, Any, Optional, Dict
from synthetipy.ast_nodes_basic import *
from synthetipy.ast_nodes_expression import IdentifierExpressionNode, ScopeNode


def postorder(root: ASTNode):
    """Yield nodes in postorder (children before parent)."""
    if root is None:
        return

    def _recurse(node):
        for c in astnode_children(node):
            yield from _recurse(c)
        yield node

    yield from _recurse(root)




def astnode_children(node: ASTNode) -> List[ASTNode]:
    """Return immediate child ASTNode list for common node types."""
    res = []
    if isinstance(node, DocumentNode):
        raise ValueError("children: DocumentNode should not be passed here; iterate top-level objects instead.")
    elif isinstance(node, ObjectNode):
        # not include name
        res.append(node.body)
    elif isinstance(node, BlockNode):
        res.extend(node.statements)
    elif isinstance(node, ListNode):
        res.extend(node.items)
    elif isinstance(node, PropertyNode):
        res.append(node.key)
        res.append(node.value)
    elif isinstance(node, ConditionNode):
        res.append(node.operator)
        res.append(node.body)
    elif isinstance(node, ComparisonNode):
        res.append(node.operator)
        res.append(node.left)
        res.append(node.right)
    elif isinstance(node, ConstantDefinitionNode):
        res.append(node.name)
        res.append(node.value)
    elif isinstance(node, InlineScriptNode):
        res.append(node.script_path)
        for k, v in node.parameters.items():
            res.append(k)
            res.append(v)
    elif isinstance(node, ConditionalParamNode):
        res.append(node.param_name)
        res.extend(node.body)
    return res

def non_leaf_children_weights(node: ASTNode) -> List[float]:
    """Return immediate child ASTNode list for common node types."""
    res = None
    if isinstance(node, DocumentNode):
        raise ValueError("children: DocumentNode should not be passed here; iterate top-level objects instead.")
    elif isinstance(node, ObjectNode):
        # not include name
        res = None # weight by subtree size (default)
    elif isinstance(node, BlockNode):
        res = None # weight by subtree size (default)
    elif isinstance(node, ListNode):
        res = None # weight by subtree size (default)
    elif isinstance(node, PropertyNode):
        res = [0.5, 0.5]
    elif isinstance(node, ConditionNode):
        res = [0.3, 0.7] # operator less important than body
    elif isinstance(node, ComparisonNode):
        res = [0.2, 0.4, 0.4]
    elif isinstance(node, ConstantDefinitionNode):
        res = [1.0, 0.0] # name less important than value
    elif isinstance(node, InlineScriptNode):
        res = [0.5] + [0.5/len(node.parameters)] * len(node.parameters)
    elif isinstance(node, ConditionalParamNode):
        res = [0.5] + [0.5/len(node.body)] * len(node.body)
    return res

def leaf_label(node: ASTNode) -> str:
    """Return a canonical label string for a node, based on type and key info."""
    if isinstance(node, LiteralNode):
        return f"Literal:{node.value_type}:{str(node.value)}"
    elif isinstance(node, IdentifierExpressionNode):
        return f"Identifier:{str(node)}"
    elif isinstance(node, ScopeNode):
        return f"Scope:{str(node)}"
    elif isinstance(node, ConstantNode):
        return f"Constant:{node.name}"
    elif isinstance(node, DirectiveNode):
        return f"Directive:{node.name}"
    elif isinstance(node, CommentNode):
        return f"Comment:{node.text}"
    elif isinstance(node, InlineArithmeticNode):
        return f"InlineArithmetic:{node.expression}"
    elif isinstance(node, WrappedString):
        return f"String:{node}"
    raise ValueError(f"leaf_label: unexpected non-leaf node type {node.__class__.__name__}")

def is_leaf(node: ASTNode) -> bool:
    """Return True if node is considered a leaf (atomic value) for diffing.

    This centralizes the project's decision about what counts as a leaf.
    """
    # Common explicit leaf types
    assert isinstance(node, ASTNode), "is_leaf should only be called on ASTNode"
    if isinstance(node, (LiteralNode,
                         IdentifierExpressionNode,
                         ScopeNode,
                         CommentNode,
                         DirectiveNode,
                         ConstantNode,
                         InlineArithmeticNode,
                         WrappedString
                         )):
        return True
    return False
    


def mutable_list_children(node: ASTNode) -> Optional[List[ASTNode]]:
    """Return a mutable list container that holds node's sequential children, or None.

    This should be used by mutation code (merge operations) to insert/delete/replace children
    in a consistent way without duplicating traversal logic.
    """
    if isinstance(node, BlockNode):
        return node.statements
    elif isinstance(node, ListNode):
        return node.items
    elif isinstance(node, ConditionalParamNode):
        return node.body
    return None


def named_children(node: ASTNode) -> Dict[str, Optional[ASTNode]]:
    """Return a mapping of named child slots for non-container nodes.

    Example:
      PropertyNode -> {'key': ASTNode or None, 'value': ASTNode or None}
      ComparisonNode -> {'left': ..., 'right': ...}
    For container nodes this returns an empty dict (use `mutable_list_children`).
    """
    slots: Dict[str, Optional[ASTNode]] = {}
    if isinstance(node, ObjectNode):
        slots['body'] = node.body
    elif isinstance(node, PropertyNode):
        slots['key'] = node.key
        slots['value'] = node.value
    elif isinstance(node, ConditionNode):
        slots['body'] = node.body
        slots['operator'] = node.operator
    elif isinstance(node, ComparisonNode):
        slots['left'] = node.left
        slots['operator'] = node.operator
        slots['right'] = node.right
    elif isinstance(node, ConstantDefinitionNode):
        slots['name'] = node.name
        slots['value'] = node.value
    elif isinstance(node, InlineScriptNode):
        slots['script_path'] = node.script_path
        for k, v in node.parameters.items():
            slots[f'{k}'] = v
    elif isinstance(node, ConditionalParamNode):
        slots['param_name'] = node.param_name
    return slots


# for test
def node_label(node: ASTNode) -> str:
    """Return a canonical label string for a node, based on type and key info."""
    if isinstance(node, ObjectNode):
        return f"Object:{str(node.name)}"
    elif isinstance(node, LiteralNode):
        return f"Literal:{node.value_type}:{str(node.value)}"
    elif isinstance(node, ConditionNode):
        return f"Condition:{node.operator}"
    elif isinstance(node, ComparisonNode):
        return f"Comparison:{node.operator}"
    elif isinstance(node, InlineScriptNode):
        return f"InlineScript:{node.script_path}"
    elif isinstance(node, ConditionalParamNode):
        return f"ConditionalParam:{node.param_name}"
    elif isinstance(node, ConstantDefinitionNode):
        return f"ConstantDef:{node.name}"
    elif isinstance(node, ConstantNode):
        return f"Constant:{node.name}"
    elif isinstance(node, DirectiveNode):
        return f"Directive:{node.name}"
    elif isinstance(node, CommentNode):
        return f"Comment:{node.text}"
    elif isinstance(node, WrappedString):
        return f"String:{node}"
    return node.__class__.__name__

def structural_equal(a: ASTNode, b: ASTNode) -> bool:
    """Conservative structural equality check (type + key/label + recursively for children).

    This is intentionally strict: nodes must have same labels and children recursively equal.
    """
    if a is None or b is None:
        return a is b
    if a.__class__ is not b.__class__:
        return False
    if node_label(a) != node_label(b):
        return False
    a_children = astnode_children(a)
    b_children = astnode_children(b)
    if len(a_children) != len(b_children):
        return False
    for ac, bc in zip(a_children, b_children):
        if not structural_equal(ac, bc):
            return False
    return True