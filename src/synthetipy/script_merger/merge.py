"""Three-way merge for PDX AST using uid-based mapping strategy."""

from collections import defaultdict
from typing import Dict, Set, Tuple, Optional, List
import copy

from ..ast_nodes import (
    ASTNode,
    DocumentNode,
    ObjectNode,
    BlockNode,
    PropertyNode,
    LiteralNode,
)
from .gumtree_hash import compute_subtree_hashes
from .edits import generate_edit_script
from .matcher import gumtree_match
from .ops import EditOp, Insert, Delete, Move, Replace


from .utils import mutable_list_children, named_children, astnode_children, postorder


class MergeError(RuntimeError):
    """Raised when a merge operation cannot be applied due to invariant violation."""

class MergeContext:
    
    def __init__(self, 
                 root: ASTNode,
                 uid_map: Dict[ASTNode, int],
                 base_uid_map: Dict[ASTNode, int],
                 ours_ops: List[EditOp],
                 theirs_ops: List[EditOp]
                 ):
        self.root = root
        self.uid_map = uid_map
        self.current_node_2_uid = base_uid_map
        self.uid_2_current_node: Dict[int, ASTNode] = {}
        for n, uid in base_uid_map.items():
            self.uid_2_current_node[uid] = n
        
    def remove_subtree_uids(self, node: ASTNode):
        """only remove the UID mapping for the node itself, not its children, since they may moved."""
        uid = self.current_node_2_uid.get(node)
        assert uid is not None, f"Missing UID for node {node}"
        assert uid in self.uid_2_current_node, f"UID {uid} not found in uid_to_node"
        self.current_node_2_uid.pop(node)
        self.uid_2_current_node.pop(uid)
        self.uid_map.pop(node)
        # for child in non_leaf_children(node):
        #     remove_subtree_uids(child)
    
    def tree_copy(self, node: ASTNode) -> ASTNode:
        """Deep copy a subtree and register UIDs."""
        assert node not in self.current_node_2_uid, f"Node {node} is in the merged tree but should be copied as new. This indicates a logic error in edit generation."
        new_node = copy.deepcopy(node)
        for n_old, n_new in zip(postorder(node), postorder(new_node)):
            uid_c_old = self.uid_map.get(n_old)
            assert uid_c_old is not None, f"Missing UID for node {n_old}"
            self.uid_map[n_new] = uid_c_old
            self.uid_2_current_node[uid_c_old] = n_new
            self.current_node_2_uid[n_new] = uid_c_old
  
        return new_node
    

    def insert(self, op: Insert):
        parent = self.uid_2_current_node.get(op.parent_uid)
        if parent is None:
            raise MergeError(f"Insert failed: Parent UID {op.parent_uid} not found (maybe deleted?).")
        
        # Deepcopy the node to insert (to be safe and independent)
        new_node = self.tree_copy(op.node)
        
        # Register new UIDs
        # 注意：这里的 op.node_uid 是对应新节点的根 UID
        # 如果新节点是一颗子树，我们需要为子树内所有节点注册？
        # 简化处理：目前只注册根。如果后续有 Op 指向子树内部，这会报错。
        # 正确做法：Edit Generator 应该只生成针对顶层的 Op。
        # register_subtree_uids(new_node) done in tree_copy
        
        container = mutable_list_children(parent)
        assert container is not None, f"Insert failed: Parent {parent} has no mutable list children."
        # 安全检查 index
        idx = op.index
        if idx > len(container): idx = len(container) # Clamp
        container.insert(idx, new_node)
        # Update parent pointer? If AST structure requires it
        if hasattr(new_node, 'parent'): new_node.parent = parent

    def delete(self, op: Delete):
        target = self.uid_2_current_node.get(op.target_uid)
        # 一致性删除已经被操作合并处理，不应该删除不存在的节点
        assert target is not None, f"Delete failed: Target UID {op.target_uid} not found (maybe already deleted?)."
       
        parent = self.uid_2_current_node.get(op.parent_uid)
        
        # remove form list
        l_children = mutable_list_children(parent)
        if l_children and target in l_children:
            l_children.remove(target)
            self.remove_subtree_uids(target)
        else:
            assert False, f"Delete failed: Target {target} not found in parent's list children. Parent: {parent}, Target: {target}"

    def move(self, op: Move):
        # Move(target_uid, parent_uid, index)
        target = self.uid_2_current_node.get(op.target_uid)
        new_parent = self.uid_2_current_node.get(op.target_parent_uid)
        
        if target is None: raise MergeError(f"Move failed: Target {op.target_uid} missing.")
        if new_parent is None: raise MergeError(f"Move failed: Parent {op.target_parent_uid} missing.")
        
        # 1. Remove from old location
        old_parent = self.uid_2_current_node.get(op.origin_parent_uid)
        assert old_parent is not None, f"Move failed: Origin parent {op.origin_parent_uid} missing."
        l_list = mutable_list_children(old_parent)
        if l_list and target in l_list:
            l_list.remove(target)
            # Check named slots not needed usually for Move (List ops)
        
        # 2. Add to new location
        target_list = mutable_list_children(new_parent)
        assert target_list is not None, f"Move failed: New parent {new_parent} has no mutable list children."
        idx = op.index
        if idx > len(target_list): idx = len(target_list)
        target_list.insert(idx, target)
        if hasattr(target, 'parent'): target.parent = new_parent
        
    def replace(self, op: Replace):
        # Replace(target_uid, slot, node, node_uid)
        # 语义：在 target_uid (Parent) 的 slot 位置，放入 new_node
        # 不需要对原本的uid进行删除，因为后继原节点可能被移动
        parent = self.uid_2_current_node.get(op.target_uid) # Note: Replace target is Parent
        if parent is None: raise MergeError(f"Replace failed: Parent {op.target_uid} missing.")
        
        if op.node_uid in self.uid_2_current_node:
            # slot move
            node = self.uid_2_current_node[op.node_uid]
            # self.remove_protential_delete_entry(node)
        else:
            # new node
            node = self.tree_copy(op.node)
        
        # Directly set attribute
        if hasattr(parent, op.slot):
            # self.mark_subtree_protential_delete(getattr(parent, op.slot))
            setattr(parent, op.slot, node)
            if hasattr(node, 'parent'): node.parent = parent
        else:
            raise MergeError(f"Replace failed: Slot {op.slot} not found on {type(parent)}.")

    def apply_edit(self, op: EditOp):
        if isinstance(op, Insert):
            self.insert(op)
        elif isinstance(op, Delete):
            self.delete(op)
        elif isinstance(op, Move):
            self.move(op)
        elif isinstance(op, Replace):
            self.replace(op)
        else:
            raise MergeError(f"Unknown operation type: {type(op)}")



def generate_uid_mapping(base: ASTNode, ours: ASTNode, theirs: ASTNode,
                         matches_ouers2base, matches_theirs2base) -> Dict[int, str]:
    uid_map: Dict[ASTNode, int] = {}
    base_uid_map: Dict[ASTNode, int] = {}
    for n in postorder(base):
        uid_map[n] = id(n)
        base_uid_map[n] = id(n)
    for n in postorder(ours):
        match_base = matches_ouers2base.get(id(n))
        if match_base is not None:
            assert uid_map.get(match_base), f"Missing uid mapping for base node id={id(match_base)}"
            uid_map[n] = uid_map.get(match_base)
        else:
            # New node in ours, assign new uid
            uid_map[n] = id(n)
    for n in postorder(theirs):
        match_base = matches_theirs2base.get(id(n))
        if match_base is not None:
            assert uid_map.get(match_base), f"Missing uid mapping for base node id={id(match_base)}"
            uid_map[n] = uid_map.get(match_base)
        else:
            # New node in theirs, assign new uid
            uid_map[n] = id(n)
    return uid_map, base_uid_map

def three_way_merge(
    base: ASTNode,
    ours: ASTNode,
    theirs: ASTNode
) -> Tuple[ASTNode, List[str]]:
    """
    执行三方合并，使用 uid-based mapping 策略。
    
    Args:
        base: 共同祖先节点
        ours: 当前分支节点
        theirs: 要合并的分支节点
        
    Returns:
        (merged_tree, conflicts):
        - merged_tree: 合并后的树
        - conflicts: 冲突描述列表（如果有）
    """
    # 第一步：深拷贝 base 并建立映射
    merged_root = copy.deepcopy(base)  # 确保我们有一个独立的树实例
        
    # 第三步：计算 base->ours 和 base->theirs 的编辑脚本
    base_content, base_content_to_nodes = compute_subtree_hashes(merged_root)
    ours_content, ours_content_to_nodes = compute_subtree_hashes(ours)
    theirs_content, theirs_content_to_nodes = compute_subtree_hashes(theirs)
    
    # 匹配树结构（使用预计算的 subtree-hash 映射以避免重复计算）
    matches_ouers2base, matches_base2ours = gumtree_match(merged_root, ours, base_content, base_content_to_nodes, ours_content, ours_content_to_nodes)
    matches_theirs2base, matches_base2theirs = gumtree_match(merged_root, theirs, base_content, base_content_to_nodes, theirs_content, theirs_content_to_nodes)
    
    uid_map, base_uid_map = generate_uid_mapping(merged_root, ours, theirs, matches_ouers2base, matches_theirs2base)
    
    # 生成编辑脚本（将所有预计算结果显式传入以避免在内部重复计算）
    ours_ops = generate_edit_script(merged_root, ours, matches_ouers2base, matches_base2ours, uid_map)
    theirs_ops = generate_edit_script(merged_root, theirs, matches_theirs2base, matches_base2theirs, uid_map)
    
    merge_identical_ops(ours_ops, theirs_ops, ours_content, theirs_content)
    
    ctx = MergeContext(merged_root, uid_map, base_uid_map,
                       ours_ops, theirs_ops)
    
    valid_ops, conflicts = detect_conflicts(
        ours_ops,
        theirs_ops,
        base_uid_map, # Base Node -> UID
        uid_map,
        merged_root)
    
    for op in valid_ops:
        ctx.apply_edit(op)
    
            
    return merged_root, conflicts 

#delete identical ops in theirs_ops
def merge_identical_ops(ours_ops: List[EditOp], theirs_ops: List[EditOp],
                        ours_content: Dict[ASTNode, str], theirs_content: Dict[ASTNode, str]):
    # 这里的 "identical" 定义比较 tricky，因为同样的语义可能有不同的表示（比如 Replace 的 node 可能是不同实例但结构相同）
    # 简化处理：目前只删除完全相同的 ops（同类型、同属性值）。后续可以考虑更复杂的语义等价判断。
    theirs_ops_remove = []
    for op_theirs in theirs_ops:
        for op_ours in ours_ops:
            if type(op_theirs) != type(op_ours):
                continue
            if isinstance(op_theirs, Insert) and isinstance(op_ours, Insert):
                if op_theirs.parent_uid == op_ours.parent_uid and op_theirs.index == op_ours.index:
                    # 进一步比较插入的节点内容
                    content_theirs = theirs_content.get(op_theirs.node)
                    content_ours = ours_content.get(op_ours.node)
                    if content_theirs == content_ours:
                        theirs_ops_remove.append(op_theirs) # Identical Insert, can be ignored
            elif isinstance(op_theirs, Delete) and isinstance(op_ours, Delete):
                if op_theirs.target_uid == op_ours.target_uid:
                    theirs_ops_remove.append(op_theirs) # Identical Delete, can be ignored
            elif isinstance(op_theirs, Move) and isinstance(op_ours, Move):
                if (op_theirs.target_uid == op_ours.target_uid and 
                    op_theirs.target_parent_uid == op_ours.target_parent_uid and 
                    op_theirs.index == op_ours.index):
                    theirs_ops_remove.append(op_theirs) # Identical Move, can be ignored
            elif isinstance(op_theirs, Replace) and isinstance(op_ours, Replace):
                if (op_theirs.target_uid == op_ours.target_uid and 
                    op_theirs.slot == op_ours.slot):
                    content_theirs = theirs_content.get(op_theirs.node)
                    content_ours = ours_content.get(op_ours.node)
                    if content_theirs == content_ours:
                        theirs_ops_remove.append(op_theirs) # Identical Replace, can be ignored
    # Remove identified identical ops from theirs_ops
    for op in theirs_ops_remove:
        theirs_ops.remove(op)

def detect_conflicts(
    ours_ops: List[EditOp], 
    theirs_ops: List[EditOp],
    uid_2_current_node: Dict[int, ASTNode],
    uid_map: Dict[ASTNode, int], # Base/Others -> UID
    base_root: ASTNode
) -> Tuple[List[EditOp], List[str]]:
    
    # 更好的是直接遍历 Base 建立准确的映射
    for n in postorder(base_root):
        if n in uid_map:
            uid_2_current_node[uid_map[n]] = n
            
    uid_parent_map: Dict[int, Optional[int]] = {}
    def build_parent_map(node: ASTNode, parent_uid: Optional[int]):
        node_uid = uid_map.get(node)
        if node_uid is not None:
            uid_parent_map[node_uid] = parent_uid
            parent_uid = node_uid
        for child in astnode_children(node):
            build_parent_map(child, parent_uid)
    build_parent_map(base_root, None)
    
    killer_op_mapping: Dict[int, EditOp] = defaultdict(list) # UID -> List of ops that kill this UID (Delete or Replace)
    # 2. 收集双方的"杀手操作" (Explicit Destructors)
    # 记录哪些 UID 被直接删除了
    def get_killed_uids(ops: List[EditOp]) -> Set[int]:
        killed = set()
        for op in ops:
            if isinstance(op, Delete):
                killed.add(op.target_uid)
                killer_op_mapping[op.target_uid] = op
                
            elif isinstance(op, Replace):
                # Replace 比较特殊，它是杀死了占据该 Slot 的旧节点
                # 我们需要查 Base 树，看谁在这个 Slot 上
                parent_base = uid_2_current_node.get(op.target_uid)
                if parent_base:
                    # 查找该 Slot 原来的 occupant
                    slots = named_children(parent_base)
                    old_node = slots.get(op.slot)
                    if old_node and old_node in uid_map:
                        killed.add(uid_map[old_node])
                        killer_op_mapping[uid_map[old_node]] = op
        return killed

    ours_killed = get_killed_uids(ours_ops)
    theirs_killed = get_killed_uids(theirs_ops)
    
    # 3. 收集"逃逸操作" (Moved Nodes)
    # 只要一个节点被 Move 了，它就不受其旧 Parent 死亡的影响
    def get_moved_uids(ops: List[EditOp]) -> Set[int]:
        uid_set = set()
        for op in ops:
            if isinstance(op, Move):
                uid_set.add(op.target_uid)
            if isinstance(op, Replace):
                # Replace 也可能是一个隐式的 Move（如果 node_uid 已经存在于树中）
                if op.node_uid in uid_2_current_node:
                    uid_set.add(op.node_uid)
        return uid_set
    
    ours_moved = get_moved_uids(ours_ops)
    theirs_moved = get_moved_uids(theirs_ops)
    
    valid_ops = []
    conflicts = []

    # 4. 辅助函数：判断节点是否因外界操作而"孤儿化"
    def is_orphaned(target_uid: int, killer_uids: Set[int], savior_moved_uids: Set[int]) -> Tuple[bool, Optional[EditOp]]:
        """
        检查 target_uid 是否位于被 killer_uids 删除的子树中，
        且中间没有通过 savior_moved_uids 逃逸。
        """
        curr_uid = target_uid
        # 向上回溯 Base 树
        while curr_uid in uid_2_current_node:
            node = uid_2_current_node[curr_uid]
            
            # 如果当前节点就是被杀死的节点，且它没有被 Move 救走
            if curr_uid in killer_uids:
                # 只有当 curr_uid 自身被 Move 了，它才算逃逸
                # （注意：如果是 target 的祖先被 move，那还是在这个祖先的死区里）
                # 等等，如果祖先被 Kill，但 target 本身被 Move 出去了 -> Saved.
                # 所以我们只要在遇到 Killer 之前遇到了 Move，就安全了。
                op = killer_op_mapping.get(curr_uid)
                return True, op # Hit a killer barrier
            
            # 检查是否逃逸：如果在遇到 Killer 之前遇到了 Move 操作
            if curr_uid in savior_moved_uids:
                return False, None # Escaped! 既然已经移走了，旧父母的死活与我无关
            
            # 继续向上找
            curr_uid = uid_parent_map.get(curr_uid)
            if curr_uid is None:
                break
        return False, None

    def simple_conflict(op1: EditOp, op2: EditOp) -> bool:
        # 互斥操作
        if isinstance(op1, Replace) and isinstance(op2, Replace):
            target_conflict = op1.target_uid == op2.target_uid and op1.slot == op2.slot
            node_conflict = op1.node_uid == op2.node_uid
            if target_conflict or node_conflict:
                return True
        if isinstance(op1, Move) and isinstance(op2, Move):
            if op1.target_uid == op2.target_uid:
                return True
        return False
    # 5. 遍历检查所有操作
    
    conflicts_ops = set() # 记录所有被检测为冲突的操作，避免重复报告
    
    # 检查 Ours 的操作是否被 Theirs 杀死
    for op in ours_ops:
        target_uid = get_op_target(op)
        assert target_uid is not None, f"Unexpectedly missing target UID for op {op}"
        
        has_conflict = False
        for op_theirs in theirs_ops:
            if simple_conflict(op, op_theirs):
                conflicts.append(f"Conflict: Ours op {op} directly conflicts with Theirs op {op_theirs}.")
                conflicts_ops.add(op)
                conflicts_ops.add(op_theirs)
                has_conflict = True
                break
        if has_conflict:
            continue
        
        # 冲突检测 2: 层级冲突 (Hierarchical)
        # 检查 target 是否处于 theirs_killed 的势力范围，且未被 ours_moved 拯救
        if not isinstance(op, Delete):
            orphaned, killer_op = is_orphaned(target_uid, theirs_killed, ours_moved)
            if orphaned:
                conflicts.append(f"Conflict: Ours op {op} targets a subtree deleted by Theirs (killer op: {killer_op}).")
                conflicts_ops.add(op)
                conflicts_ops.add(killer_op)
                continue
        if op in conflicts_ops:
            continue
        valid_ops.append(op)

    # 检查 Theirs 的操作是否被 Ours 杀死
    for op in theirs_ops:
        target_uid = get_op_target(op)
        assert target_uid is not None, f"Unexpectedly missing target UID for op {op}"
        
        if not isinstance(op, Delete):
            orphaned, killer_op = is_orphaned(target_uid, ours_killed, theirs_moved)
            if orphaned:
                conflicts.append(f"Conflict: Theirs op {op} targets a subtree deleted by Ours (killer op: {killer_op}).")
                if killer_op in valid_ops:
                    valid_ops.remove(killer_op) # 如果杀手操作在有效列表里，移除它（因为它已经导致冲突了） 
                conflicts_ops.add(op)
                conflicts_ops.add(killer_op)
                continue
        if op in conflicts_ops:
            continue
        valid_ops.append(op)
        
    return valid_ops, conflicts



def get_op_target(op: EditOp) -> Optional[int]:
    if isinstance(op, Delete):
        return op.target_uid
    if isinstance(op, Move):
        return op.target_parent_uid # Move 的目标是新的父节点
    if isinstance(op, Insert):
        return op.parent_uid # Insert 也是依赖 Parent 存活的
    if isinstance(op, Replace):
        return op.target_uid # Replace 依赖 Parent 存活
    return None

