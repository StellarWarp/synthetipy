from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from synthetipy.ast_nodes_basic import ASTNode


# Simple dataclasses for edit operations.
# Backwards-compatible: keep old numeric id fields (target/parent) while adding uid-based fields (target_uid/parent_uid)
# so we can migrate incrementally.

@dataclass(frozen=True)
class EditOp:
    """Base class for edit operations."""

    def to_dict(self) -> Dict[str, Any]:
        # default serializer for reporting/debugging
        d = {'op': self.__class__.__name__.lower()}
        for k, v in self.__dict__.items():
            d[k] = v
        return d


@dataclass(frozen=True)
class Insert(EditOp):
    parent_uid: int
    index: int
    node_uid: int
    node: ASTNode


@dataclass(frozen=True)
class Delete(EditOp):
    parent_uid: int
    target_uid: int


@dataclass(frozen=True)
class Move(EditOp):
    origin_parent_uid: int
    target_parent_uid: int
    target_uid: int
    index: int


@dataclass(frozen=True)
class Replace(EditOp):
    target_uid: int
    node_uid: int
    slot: str
    node: ASTNode


