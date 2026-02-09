from typing import List, Dict, Set, Optional
from collections import deque
from difflib import SequenceMatcher

from synthetipy.ast_nodes_basic import ASTNode
from .ops import EditOp, Insert, Delete, Move, Replace
from .utils import mutable_list_children, named_children

def _enqueue_children(node: ASTNode, queue: deque, visited: Set[ASTNode]):
    """辅助函数：将子节点加入队列"""
    list_children = mutable_list_children(node)
    if list_children:
        for c in list_children:
            if c not in visited:
                queue.append((c, node, '[List]'))  # '[List]' 表示这是列表中的元素
                visited.add(c)
    
    slots = named_children(node)
    if slots:
        for k, c in slots.items():
            if c and c not in visited:
                queue.append((c, node, k))  # also pass parent and slot key
                visited.add(c)
                
def generate_edit_script(
    base_root: ASTNode,
    other_root: ASTNode,
    matches_o_2_b: Dict[ASTNode, ASTNode],
    matches_b_2_o: Dict[ASTNode, ASTNode],
    uid_map: Dict[ASTNode, int]
) -> List[EditOp]:
    
    script: List[EditOp] = []

    # 1. Update Phase: 既然我们要用 Replace/Insert 代替 Update，这里可以跳过
    # 或者如果你保留 Update op 用于日志，可以在这里做检查，但核心逻辑不依赖它。
    # (已省略)

    # 2. Align Phase (BFS)
    # 我们遍历 Other 树，确保 Base 树的结构变换成 Other 树
    bfs_queue = deque([(other_root, None, None)])
    visited = {other_root}
    replaced_name_child: Set[ASTNode] = set() # 记录已经被 Replace 过的父节点，避免 Delete 

    while bfs_queue:
        w,p_w,slot_key = bfs_queue.popleft() # w is current node in Other

        if w == other_root:
            _enqueue_children(w, bfs_queue, visited)
            continue

        # --- 核心逻辑：处理 w 本身 ---
        # 此时 w 的父节点 p_w 肯定已经处理过了（因为是 BFS）
        match_p_w = matches_o_2_b.get(p_w)
        
        target_parent_uid = uid_map[match_p_w] if match_p_w else uid_map[p_w]
        
        is_new_node = w not in matches_o_2_b

        # 判断 w 位于父节点的什么位置（List Index 还是 Named Slot）
        # 我们需要查 p_w 的结构来决定生成什么指令
        parent_list = mutable_list_children(p_w)
        
        is_in_list = False
        current_index = 0
        current_slot = None
        
        if slot_key == '[List]':
            is_in_list = True
            current_index = parent_list.index(w)
        else:
            # Named Slot
            current_slot = slot_key
                
        # -------------------------------------------------
        # Case A: w 是 List 中的元素 -> 使用 Insert / Move
        # -------------------------------------------------
        if is_in_list:
            if is_new_node:
                # Insert
                script.append(Insert(
                    node=w,
                    parent_uid=target_parent_uid,
                    index=current_index,
                    node_uid=uid_map[w]
                ))
                continue
            else:
                # Move check
                u = matches_o_2_b[w] # Base node
                original_parent = u.parent
                
                # Check 1: Reparenting
                if original_parent != match_p_w:
                     script.append(Move(
                        origin_parent_uid=uid_map[original_parent],
                        target_parent_uid=target_parent_uid,
                        target_uid=uid_map[u],
                        index=current_index
                    ))
                
                # Check 2: Reordering (LCS)
                # 只有当父亲没变时才需要 LCS 检查
                # 如果我们在这个阶段不做 LCS，最简单的就是假定都 Move
                elif match_p_w:
                     # 这里的逻辑稍后在 BFS 循环外单独对父节点做一次 LCS 即可
                     # 或者暂时简单处理：如果不做 LCS，就生成一个 Move 以确保顺序
                     # 推荐：在循环外处理 LCS，这里只处理 Reparenting
                    pass
                
                _enqueue_children(w, bfs_queue, visited)

        # -------------------------------------------------
        # Case B: w 是 Named Slot 中的元素 -> 使用 Replace
        # -------------------------------------------------
        elif current_slot:
            # 无论 w 是新节点还是旧节点，只要它现在占据了这个 Slot
            # 我们就发出一个 Replace 指令（语义：Set Slot）
            
            # 但我们需要区分：
            # 1. 它是新节点 -> 直接 Replace(Parent, Slot, NewNode)
            # 2. 它是旧节点(u) -> 它是从别的地方移过来的？还是原本就在这？
            
            if is_new_node:
                # New node in slot
                script.append(Replace(
                    target_uid=target_parent_uid, # Parent UID
                    node=w,
                    node_uid=uid_map[w],
                    slot=current_slot
                ))
                replaced_name_child.add((target_parent_uid, current_slot)) # 记录这个父节点的这个槽位已经被 Replace 过了
                continue
            else:
                u = matches_o_2_b[w]
                # Old node u matches w.
                # Check if u was already in this slot of the matching parent?
                u_parent = u.parent
                
                # 获取 u 原来的 slot
                u_slots = named_children(u_parent)
                u_slot_name = None
                for k, v in u_slots.items():
                    if v is u:
                        u_slot_name = k
                        break
                
                # 如果 父节点变了 OR 槽位名变了 -> 需要 Move/Replace
                if u_parent != match_p_w or u_slot_name != current_slot:
                    script.append(Replace(
                        target_uid=target_parent_uid,
                        node=None, # 旧节点
                        node_uid=uid_map[u], # 使用旧 ID
                        slot=current_slot
                    ))
                    replaced_name_child.add((target_parent_uid, current_slot)) # 记录这个父节点的这个槽位已经被 Replace 过了
                # else: 完全没变，不做任何事
                _enqueue_children(w, bfs_queue, visited)

    # 3. Reordering Phase for List Children (LCS Optimization)
    # 再次遍历所有已匹配的父节点，处理其 List Children 的内部顺序
    for o_parent in matches_o_2_b:
        o_list = mutable_list_children(o_parent)
        if not o_list: continue # Not a list container
        
        b_parent = matches_o_2_b[o_parent]
        b_list = mutable_list_children(b_parent)
        if not b_list: continue # Should change type? Unlikely
        
        # 提取双方 ID 序列
        seq1 = [c for c in b_list if c in matches_b_2_o and matches_b_2_o[c].parent == o_parent]
        seq2 = [c for c in o_list if c in matches_o_2_b] # Current desired order of matched nodes
        
        seq1_map = [matches_b_2_o[c] for c in seq1] # Map to other nodes for comparison
        
        sm = SequenceMatcher(None, seq1_map, seq2)
        lcs_set = set()
        for i, j, n in sm.get_matching_blocks():
            for k in range(n):
                lcs_set.add(seq1_map[i+k])
        
        # Generate Moves for nodes not in LCS
        for idx, child in enumerate(o_list):
            if child in matches_o_2_b:
                # Only move if it's NOT in LCS (and thus out of order)
                # AND it is not a reparenting case (reparenting handled in BFS)
                base_child = matches_o_2_b[child]
                
                # Check if it was originally child of b_parent
                if base_child.parent == b_parent:
                     if child not in lcs_set:
                         script.append(Move(
                             target_uid=uid_map[base_child],
                             origin_parent_uid=uid_map[base_child.parent],
                             target_parent_uid=uid_map[b_parent],
                             index=idx
                         ))

    # 4. Delete Phase: Post-order traversal
    # 基本保持不变，任何 Base 中没匹配的都删掉
    # 对于 Named Slot，Delete 其实意味着 set slot = None，但在 AST 层面 Delete Node 也就够了
    stack = [(base_root, None, None)]
    while stack:
        n, parent, slot = stack.pop()
        
        if n not in matches_b_2_o:
            script.append(Delete(
                parent_uid=uid_map[parent] if parent else None,
                target_uid=uid_map[n]))
            # Stop recurring down deleted subtrees
            continue
        
        # Add children
        c_list = mutable_list_children(n)
        if c_list:
            for c in reversed(c_list): # reversed for post-order
                if c not in matches_b_2_o:
                    stack.append((c, n, '[List]'))
        
        c_slots = named_children(n)
        if c_slots:
            for k, v in c_slots.items():
                if (uid_map[n], k) in replaced_name_child:
                    # 这个槽位已经被 Replace 过了，说明它的新值在 Other 树中占位了，不应该删除
                    continue
                if v: stack.append((v, n, k))
                
    return script