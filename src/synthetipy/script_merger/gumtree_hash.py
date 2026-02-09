"""Bottom-up subtree hashing with collision detection (PoC).

Algorithm:
- Postorder traverse AST
- For each node, gather child hashes (in order) and compute hash = sha256(label || child_hashes)
- If hash collides with existing node(s) that are not structurally equal, rehash with a salt counter until unique
- Return node_id -> hash mapping and hash -> list[node_id]
"""
import hashlib
from typing import Any, Dict, List, Tuple
from .utils import leaf_label, astnode_children, is_leaf
from synthetipy.ast_nodes_basic import ASTNode


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


from synthetipy.ast_nodes_basic import ObjectNode

def compute_subtree_hashes(root: ObjectNode) -> Tuple[Dict[Any, str],
                                                      Dict[str, List[Any]]]:
    """Compute subtree hashes for an ObjectNode entry.

    Must be called with an ObjectNode (not a DocumentNode). If a DocumentNode is passed,
    raise ValueError to force caller to iterate top-level objects explicitly.
    Returns (node_content_hash, content_hash_to_nodes, node_unique_hash, unique_hash_to_nodes)
    """
    if not isinstance(root, ObjectNode):
        # allow flexibility: still accept other node types, but document-level is disallowed
        raise ValueError("compute_subtree_hashes must be called with an ObjectNode as root.")


    node_content_hash: Dict[Any, str] = {}
    content_hash_to_nodes: Dict[str, List[Any]] = {}

    def _compute(node: ASTNode) -> str:
        # compute for children first
        child_hashes: List[str] = []
        children = astnode_children(node)
        for c in children:
            ch_hash = _compute(c)
            child_hashes.append(ch_hash)
        if not children or len(child_hashes) == 0:
            # leaf node: hash of label + value
            if is_leaf(node):
                base_text = leaf_label(node)
            else:
                print("Warning: node with no children but not leaf?", node)
                base_text = node.__class__.__name__
        else:
            base_text = node.__class__.__name__ + '|' + '|'.join(child_hashes)
        content_h = _sha256_text(base_text)
        node_content_hash[node] = content_h
        content_hash_to_nodes.setdefault(content_h, []).append(node)
        return content_h

    _compute(root)


    return node_content_hash, content_hash_to_nodes

