"""AST-level merger utilities (GumTree-style hashing & matching PoC)

Public functions:
- compute_subtree_hashes(root): returns (node_id_to_hash, hash_to_node_ids)
- match_by_hash(base_root, other_root): returns mapping other_node_id -> base_node_id
"""

from .gumtree_hash import compute_subtree_hashes

__all__ = [
    "compute_subtree_hashes",
]
