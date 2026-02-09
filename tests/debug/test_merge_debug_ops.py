from synthetipy.parser import parse
from synthetipy.script_merger.gumtree_hash import compute_subtree_hashes
from synthetipy.script_merger.matcher import match_trees
from synthetipy.script_merger.edits import generate_edit_script
from synthetipy.script_merger.merge import copy_with_mapping
from synthetipy.script_merger.utils import postorder, node_label, node_id


def test_debug_ops_move_and_update():
    BASE = r'''
b = {
    first = { }
    second = { v = 1 }
}
'''
    LEFT = r'''
b = {
    second = { v = 1 }
    first = { }
}
'''
    RIGHT = r'''
b = {
    first = { }
    second = { v = 2 }
}
'''

    base = next(n for n in postorder(parse(BASE)) if node_label(n).startswith('Object:'))
    left = next(n for n in postorder(parse(LEFT)) if node_label(n).startswith('Object:'))
    right = next(n for n in postorder(parse(RIGHT)) if node_label(n).startswith('Object:'))

    # precompute
    base_content, base_buckets, base_unique, base_unique_to_nodes = compute_subtree_hashes(base)
    left_content, left_buckets, left_unique, left_unique_to_nodes = compute_subtree_hashes(left)
    right_content, right_buckets, right_unique, right_unique_to_nodes = compute_subtree_hashes(right)

    left_matches = match_trees(base, left, base_content, base_buckets, left_content, left_buckets)
    right_matches = match_trees(base, right, base_content, base_buckets, right_content, right_buckets)

    left_ops = generate_edit_script(base, left, left_matches, base_content, base_buckets, left_content, left_buckets, base_unique, left_unique)
    right_ops = generate_edit_script(base, right, right_matches, base_content, base_buckets, right_content, right_buckets, base_unique, right_unique)

    print('\n=== LEFT OPS ===')
    for op in left_ops:
        print(type(op).__name__, op)
    print('\n=== RIGHT OPS ===')
    for op in right_ops:
        print(type(op).__name__, op)

    merged, uid_to_merged, merged_id_to_uid = copy_with_mapping(base)
    print('\n=== MAPPED UIDS (sample) ===')
    for k in list(uid_to_merged.keys())[:20]:
        print(' ', k)

    # Inspect Update ops in right_ops: check target_uid presence
    for op in right_ops:
        if type(op).__name__ == 'Update':
            print('\nFound Update op: target', op.target, 'target_uid', op.target_uid, 'new_value', op.new_value)
            print('  in base_unique values?', op.target_uid in base_unique.values())
            print('  in merged uid_to_merged?', op.target_uid in uid_to_merged)

    # Inspect Delete/Insert ops in left_ops
    for op in left_ops:
        if type(op).__name__ == 'Delete':
            print('\nFound Delete op: target', op.target, 'target_uid', op.target_uid)
        if type(op).__name__ == 'Insert':
            print('\nFound Insert op: parent', op.parent, 'parent_uid', op.parent_uid, 'node_uid', getattr(op, 'node_uid', None))

    # Assertions to capture failing conditions
    # At least one Update should have target_uid that exists in base_unique
    updates = [op for op in right_ops if type(op).__name__ == 'Update']
    assert updates, 'No Update ops found in right_ops'
    for op in updates:
        assert op.target_uid in base_unique.values(), f"Update target_uid {op.target_uid} not in base_unique values"

    # Ensure deletes have uid set (not None) when possible
    deletes = [op for op in left_ops if type(op).__name__ == 'Delete']
    for op in deletes:
        assert op.target_uid is not None, f"Delete op missing target_uid for target {op.target}"


def test_debug_apply_ours_then_check_update_target():
    # Recompute setup: apply only left/ours ops to merged context and inspect uid mapping before applying right ops
    from synthetipy.parser import parse
    from synthetipy.script_merger.gumtree_hash import compute_subtree_hashes
    from synthetipy.script_merger.matcher import match_trees
    from synthetipy.script_merger.edits import generate_edit_script

    BASE = r'''
b = {
    first = { }
    second = { v = 1 }
}
'''
    LEFT = r'''
b = {
    second = { v = 1 }
    first = { }
}
'''
    RIGHT = r'''
b = {
    first = { }
    second = { v = 2 }
}
'''

    base = next(n for n in postorder(parse(BASE)) if node_label(n).startswith('Object:'))
    left = next(n for n in postorder(parse(LEFT)) if node_label(n).startswith('Object:'))
    right = next(n for n in postorder(parse(RIGHT)) if node_label(n).startswith('Object:'))

    base_content, base_buckets, base_unique, base_unique_to_nodes = compute_subtree_hashes(base)
    left_content, left_buckets, left_unique, left_unique_to_nodes = compute_subtree_hashes(left)
    right_content, right_buckets, right_unique, right_unique_to_nodes = compute_subtree_hashes(right)

    left_matches = match_trees(base, left, base_content, base_buckets, left_content, left_buckets)
    right_matches = match_trees(base, right, base_content, base_buckets, right_content, right_buckets)

    left_ops = generate_edit_script(base, left, left_matches, base_content, base_buckets, left_content, left_buckets, base_unique, left_unique)
    right_ops = generate_edit_script(base, right, right_matches, base_content, base_buckets, right_content, right_buckets, base_unique, right_unique)

    updates = [op for op in right_ops if type(op).__name__ == 'Update']

    merged, uid_map, rev = copy_with_mapping(base)
    from synthetipy.script_merger.merge import MergeContext, _apply_operation
    ctx = MergeContext(merged, uid_map, rev)
    for op in left_ops:
        print('\nApplying ours op:', type(op).__name__, op)
        _apply_operation(ctx, op)
    print('\nUIDs after applying ours ops:')
    for k in list(ctx.uid_to_merged.keys())[:30]:
        print(' ', k)
    for op in updates:
        print('\nChecking Update target_uid presence for', op.target_uid)
        assert op.target_uid in ctx.uid_to_merged, f"Update target_uid {op.target_uid} missing after applying ours ops"


def test_debug_insert_same_key():
    BASE = r'''
b = { }
'''
    LEFT = r'''
b = { n = { v = 1 } }
'''
    RIGHT = r'''
b = { n = { v = 1 } }
'''
    base = next(n for n in postorder(parse(BASE)) if node_label(n).startswith('Object:'))
    left = next(n for n in postorder(parse(LEFT)) if node_label(n).startswith('Object:'))
    right = next(n for n in postorder(parse(RIGHT)) if node_label(n).startswith('Object:'))

    base_content, base_buckets, base_unique, base_unique_to_nodes = compute_subtree_hashes(base)
    left_content, left_buckets, left_unique, left_unique_to_nodes = compute_subtree_hashes(left)
    right_content, right_buckets, right_unique, right_unique_to_nodes = compute_subtree_hashes(right)

    left_matches = match_trees(base, left, base_content, base_buckets, left_content, left_buckets)
    right_matches = match_trees(base, right, base_content, base_buckets, right_content, right_buckets)

    left_ops = generate_edit_script(base, left, left_matches, base_content, base_buckets, left_content, left_buckets, base_unique, left_unique)
    right_ops = generate_edit_script(base, right, right_matches, base_content, base_buckets, right_content, right_buckets, base_unique, right_unique)

    print('\n=== INSERT CASE LEFT OPS ===')
    for op in left_ops:
        print(' ', type(op).__name__, op)
    print('\n=== INSERT CASE RIGHT OPS ===')
    for op in right_ops:
        print(' ', type(op).__name__, op)

    # show any Delete with missing uid
    for op in left_ops + right_ops:
        if type(op).__name__ == 'Delete':
            print('Found Delete op: target', op.target, 'target_uid', op.target_uid)
            assert op.target_uid is not None, 'Delete op target_uid is None'