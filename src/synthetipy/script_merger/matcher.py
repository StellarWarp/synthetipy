# ...existing code...
from collections import deque, defaultdict
from typing import Any, Counter, Dict, List, Tuple, Set, Deque, Optional

from .utils import astnode_children, is_leaf
from synthetipy.ast_nodes_basic import ASTNode
from difflib import SequenceMatcher

def _build_maps(root: ASTNode):
    """Traverse tree, return id->node, children_map, parent_map, is_leaf set"""
    parent_map: Dict[Any, Optional[Any]] = {}
    is_leaf: Set[Any] = set()
    
    def walk(n: ASTNode, parent: Optional[ASTNode]):
        if parent is not None:
            parent_map[n] = parent
        else:
            parent_map[n] = None
        children = astnode_children(n)
        if not children or len(children) == 0:
            is_leaf.add(n)
        else:
            for c in children:
                walk(c, n)

    walk(root, None)
    return parent_map, is_leaf


def gumtree_match(
    base_root: ASTNode,
    other_root: ASTNode,
    base_content_map: Dict[ASTNode, str],
    base_content_buckets: Dict[str, List[ASTNode]],
    other_content_map: Dict[ASTNode, str],
    other_content_buckets: Dict[str, List[ASTNode]],
    similarity_threshold: float = 0.5
) -> Dict[ASTNode, ASTNode]:
    """
    GumTree-like seed-and-expand matcher.

    Returns mapping other_node_id -> base_node_id.

    Strategy:
    1) Seed: match unique content-hash pairs (count==1 on both sides) and match leaves by content-hash greedily.
    2) Expand: maintain queue of parent-pairs derived from matched children. For each parent pair,
       compute similarity between unmatched children and greedily pair best matches above threshold.
    3) Final: global greedy match for remaining nodes (respecting parent consistency when possible).
    """
    # build traversal maps
    # base_parent, base_is_leaf = _build_maps(base_root)
    # other_parent, other_is_leaf = _build_maps(other_root)

    matches_o_2_b: Dict[ASTNode, ASTNode] = {}          # other_node -> base_node
    matches_b_2_o: Dict[ASTNode, ASTNode] = {}      # base_node -> other_node (for quick lookup of matched base nodes)

    # 1) Seed: unique content-hash matches
    for h, b_list in base_content_buckets.items():
        o_list = other_content_buckets.get(h)
        if not o_list:
            continue
        if len(b_list) == 1 and len(o_list) == 1:
            b = b_list[0]; o = o_list[0]
            matches_o_2_b[o] = b
            matches_b_2_o[b] = o

    # 1b.1)b_tree and o_tree are identical by hash, match all nodes reccursively
    def match_subtree(b_tree: ASTNode, o_tree: ASTNode):
        prev_base = matches_o_2_b.get(o_tree)
        if prev_base is not None and prev_base != b_tree:
            matches_b_2_o.pop(prev_base, None)
        matches_o_2_b[o_tree] = b_tree
        matches_b_2_o[b_tree] = o_tree
        b_children_nodes = astnode_children(b_tree)
        o_children_nodes = astnode_children(o_tree)
        assert len(b_children_nodes) == len(o_children_nodes)
        for bc, oc in zip(b_children_nodes, o_children_nodes):
            match_subtree(bc, oc)
    
    # 1b.2) search for seed to match entire subtrees
    def find_and_match_identical_subtrees(o_node: ASTNode):
        if o_node in matches_o_2_b:
            b_node = matches_o_2_b[o_node]
            assert b_node is not None
            match_subtree(b_node, o_node)
        else:
            # search for children
            for c in astnode_children(o_node):
                find_and_match_identical_subtrees(c)
        
    find_and_match_identical_subtrees(other_root)
    
    # ---------------------------------------------------------
    # Phase 2: Bottom-up Matching (Container Matching)
    # ---------------------------------------------------------
    # 目的：匹配那些“内容大部分相同但自身未匹配”的容器节点
    # 策略：如果两个未匹配节点的子节点中，有足够多的一对一匹配，则这两个父节点也应该匹配。
       
    subtree_leaf_heashes_cache: Dict[ASTNode, Set[str]] = {}
    
    def subtree_leaf_heashes(n: ASTNode,
                             content_map: Dict[ASTNode, str]
                             ) -> List[str]:
        """收集子树的叶子节点的内容哈希集合"""
        if n in subtree_leaf_heashes_cache:
            return subtree_leaf_heashes_cache[n]
        hashes = []
        children_nodes = astnode_children(n)
        for c in children_nodes:
            if is_leaf(c):
                h = content_map.get(c)
                if h is not None:
                    hashes.append(h)
            else:
                child_hashes = subtree_leaf_heashes(
                    c,
                    content_map)
                hashes.extend(child_hashes)
                hashes.append(n.__class__.__name__)
        subtree_leaf_heashes_cache[n] = hashes
        return hashes
    
    get_matched_children_score_cache: Dict[Tuple[ASTNode, ASTNode], float] = {}
    def get_matched_children_score(b: ASTNode, o: ASTNode) -> float:
        """计算两个节点的匹配子节点相似度 (Jaccard-like or Common Ratio)"""
        if (b, o) in get_matched_children_score_cache:
            return get_matched_children_score_cache[(b, o)]
        base_leaf_hashes = subtree_leaf_heashes(b, base_content_map)
        other_leaf_hashes = subtree_leaf_heashes(o, other_content_map)
        
        b_cnt = Counter(base_leaf_hashes)
        o_cnt = Counter(other_leaf_hashes)
        inter = b_cnt & o_cnt
        denom = len(base_leaf_hashes) + len(other_leaf_hashes)
        score = 0.0 if denom == 0 else (2.0 * sum(inter.values()) / denom)
        get_matched_children_score_cache[(b, o)] = score
        return score

    # 简单的候选者查找策略：查看已匹配子节点的父节点
    # 迭代多次以传播匹配（或者按层级自底向上遍历一次）
    # 这里演示一个基于候选投票的简化版 Bottom-up
    
    # 初始化待处理队列，包含 Phase 1 的所有种子匹配
    processing_matches = list(matches_b_2_o.items())
    
    while len(processing_matches) > 0:
        potential_pairs: List[Tuple[ASTNode, ASTNode]] = []
        potential_pairs_set: Set[Tuple[ASTNode, ASTNode]] = set() # for deduplication
        # 1. 发现阶段：仅从“本轮新增的匹配”向上寻找父亲候选
        for b_child, o_child in processing_matches:
            b_p = b_child.parent
            o_p = o_child.parent
            
            # --- 向上看 Base 的父节点 ---
            if b_p is not None:
                # 只有当 Base 父节点还没匹配时，才值得找对象
                if b_p in matches_b_2_o:
                    continue
                
                # --- 向上找 Other 的候选父节点 (和之前一样，支持 Wrap) ---
                curr_o = o_p
                dist = 0
                max_dist = 3 # 向上找3层
                
                while curr_o is not None and dist < max_dist:
                    if curr_o not in matches_o_2_b and type(b_p) == type(curr_o): # 类型必须匹配
                        # 这是一个有效的候选对 (Base_Parent, Other_Ancestor)
                        if (b_p, curr_o) not in potential_pairs_set:
                            potential_pairs.append((b_p, curr_o))
                            potential_pairs_set.add((b_p, curr_o))
                    curr_o = curr_o.parent
                    dist += 1

        # 清空队列，准备接收下一轮的新匹配
        processing_matches = []
        
        if not potential_pairs or len(potential_pairs) == 0:
            break

        # 2. 评分阶段
        scored_candidates = [] 
        for b_p, o_p in potential_pairs:
            score = get_matched_children_score(b_p, o_p)
            if score > similarity_threshold:
                scored_candidates.append((score, b_p, o_p))
        
        # 3. 排序阶段 (至关重要)
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # 4. 匹配阶段
        for score, b_p, o_p in scored_candidates:
            # 双重检查
            if b_p in matches_b_2_o or o_p in matches_o_2_b:
                continue
            
            # 建立匹配
            matches_b_2_o[b_p] = o_p
            matches_o_2_b[o_p] = b_p
            
            # [关键点] 将新产生的匹配加入队列
            # 这样在下一轮循环中，我们会寻找 b_p 的父节点（即祖父节点）
            processing_matches.append((b_p, o_p))

    # Roots are forced to match
    if base_root not in matches_b_2_o and other_root not in matches_o_2_b:
        matches_b_2_o[base_root] = other_root
        matches_o_2_b[other_root] = base_root
    # ---------------------------------------------------------
    # Phase 3: Alignment & Recovery (Refinement)
    # ---------------------------------------------------------
    
    # 我们使用一个队列来处理需要 Refine 的父节点对
    # 初始只包含 Phase 1 & 2 匹配的节点
    refine_queue = list(matches_b_2_o.items())
    
    # 标记已处理过的父节点，防止无限循环
    processed_parents = set()


    # 指针遍历，不用 for loop 因为队列会动态增加
    idx = 0
    while idx < len(refine_queue):
        b_parent, o_parent = refine_queue[idx]
        idx += 1
        
        if (b_parent, o_parent) in processed_parents:
            continue
        processed_parents.add((b_parent, o_parent))

        # 1. 获取尚未匹配的子节点
        b_children = astnode_children(b_parent)
        o_children = astnode_children(o_parent)
        
        # 过滤出未匹配的，但必须保留原始索引信息以便 LCS (这里稍微变通一下，直接用列表)
        b_unmatched = [c for c in b_children if c not in matches_b_2_o]
        o_unmatched = [c for c in o_children if c not in matches_o_2_b]
        
        if not b_unmatched or not o_unmatched:
            continue

        # --- Sub-Phase 3.1: 优先匹配 Hash 相同的 (LCS) ---
        b_seq = [base_content_map.get(n) for n in b_unmatched]
        o_seq = [other_content_map.get(n) for n in o_unmatched]
        assert all(h is not None for h in b_seq)
        assert all(h is not None for h in o_seq)
        
        sm = SequenceMatcher(None, b_seq, o_seq, autojunk=False)
        
        matched_indices_b = set()
        matched_indices_o = set()
        
        for i, j, n in sm.get_matching_blocks():
            if n == 0: continue
            for k in range(n):
                b_node = b_unmatched[i+k]
                o_node = o_unmatched[j+k]
                
                if b_node not in matches_b_2_o and o_node not in matches_o_2_b:
                    matches_b_2_o[b_node] = o_node
                    matches_o_2_b[o_node] = b_node
                    matched_indices_b.add(i+k)
                    matched_indices_o.add(j+k)
                    
                    match_subtree(b_node, o_node)

        # --- Sub-Phase 3.2: 挽救结构相似但不相同的子树 (Recovery) ---
        # 针对刚才 LCS 剩下的“缝隙”中的节点
        
        # 收集真正剩下的
        b_real_remaining = [n for k, n in enumerate(b_unmatched) if k not in matched_indices_b]
        o_real_remaining = [n for k, n in enumerate(o_unmatched) if k not in matched_indices_o]
        
        if b_real_remaining and o_real_remaining:
            # 在这里进行两两比较，计算结构相似度
            # 因为是局部比较，n*m 不会太大
            candidates = []
            
            for b_n in b_real_remaining:
                for o_n in o_real_remaining:
                    # 类型不同绝对不匹配（因为不做 update）
                    if type(b_n) != type(o_n):
                        continue
                        
                    # 再次利用之前定义的评分函数！
                    # 它会递归看叶子哈希的重叠度
                    score = get_matched_children_score(b_n, o_n)
                    
                    # 这里阈值可以稍微低一点，因为父节点已经匹配了，上下文约束很强
                    if score > 0.4: 
                        candidates.append((score, b_n, o_n))
            
            # 排序后贪婪匹配
            candidates.sort(key=lambda x: x[0], reverse=True)
            
            for score, b_n, o_n in candidates:
                if b_n not in matches_b_2_o and o_n not in matches_o_2_b:
                    matches_b_2_o[b_n] = o_n
                    matches_o_2_b[o_n] = b_n
                    
                    # [递归的关键]
                    # 这个节点匹配是因为“结构相似”（score高），说明内部肯定有差异
                    # 必须把它加入队列，深入内部去对齐它的子节点！
                    refine_queue.append((b_n, o_n))
    for o,b in matches_o_2_b.items():
        assert matches_b_2_o.get(b) == o, f"Inconsistent match: {o} -> {b} but {b} -> {matches_b_2_o.get(b)}"
        assert type(o) == type(b), f"Type mismatch in final matches: {o} ({type(o)}) vs {b} ({type(b)})"
    return matches_o_2_b, matches_b_2_o

    