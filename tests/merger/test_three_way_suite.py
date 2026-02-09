import pytest
from synthetipy.parser import parse
from synthetipy.script_merger.merge import three_way_merge, MergeContext, MergeError
from synthetipy.script_merger.utils import postorder, node_label, structural_equal
from synthetipy.script_merger.gumtree_hash import compute_subtree_hashes
from synthetipy.ast_nodes import PropertyNode, LiteralNode
from synthetipy.compiler import compile_ast

def _obj_from(text: str):
    return parse(text).statements[0]

def test_three_way_non_conflicting():
    base = _obj_from("""
b = {
	prop_a = { x = 1 }
	prop_b = { y = 2 }
}
""")
    left = _obj_from("""
b = {
	prop_a = { x = 10 }
	prop_b = { y = 2 }
}
""")
    right = _obj_from("""
b = {
	prop_a = { x = 1 }
	prop_b = { y = 20 }
}
""")

    merged, conflicts = three_way_merge(base, left, right)

    expected = _obj_from("""
b = {
	prop_a = { x = 10 }
	prop_b = { y = 20 }
}
""")
    
    print(compile_ast(merged))
    for line in conflicts:
        print('Conflict:', line)

    assert structural_equal(merged, expected)
    assert conflicts == []

# test_three_way_non_conflicting()

def test_move_and_update_mergeable():
    base = _obj_from("""
b = {
    first = { }
    second = { v = 1 }
}
""")
    left = _obj_from("""
b = {
    second = { v = 1 }
    first = { }
}
""")
    right = _obj_from("""
b = {
    first = { }
    second = { v = 2 }
}
""")

    merged, conflicts = three_way_merge(base, left, right)
    assert conflicts == []
    # expect order like left and value applied
    # check second present and its child value updated to 2
    print(compile_ast(merged))
    for line in conflicts:
        print('Conflict:', line)

# test_move_and_update_mergeable()

def test_delete_vs_modify_should_report_conflict():
    base = _obj_from("""
b = { p = { v = 1 } }
""")
    left = _obj_from("""
b = { }
""")
    right = _obj_from("""
b = { p = { v = 2 } }
""")

    merged, conflicts = three_way_merge(base, left, right)
    print(compile_ast(merged))
    for line in conflicts:
        print('Conflict:', line)

# test_delete_vs_modify_should_report_conflict()

def test_insert_same_key_same_value_no_conflict():
    base = _obj_from("""
b = { 
    c = {
        prop_a = { x = 10 }
        prop_b = { y = 20 }
    }
}
""")
    left = _obj_from("""
b = {
    c = {
        prop_a = { x = 10 }
        prop_b = { y = 20 }
    }
    n = { v = 1 } 
}
""")
    right = _obj_from("""
b = {
    c = {
        prop_a = { x = 10 }
        prop_b = { y = 20 }
    }
    n = { v = 1 }
}
""")

    merged, conflicts = three_way_merge(base, left, right)
    merged, conflicts = three_way_merge(base, left, right)
    print(compile_ast(merged))
    for line in conflicts:
        print('Conflict:', line)

# test_insert_same_key_same_value_no_conflict()

def test_insert_same_key_diff_value_conflict():
    base = _obj_from("""
b = { 
    c = {
        prop_a = { x = 10 }
        prop_b = { y = 20 }
    }
    n = { v = 1 } 
}
""")
    left = _obj_from("""
b = {
    c = {
        prop_a = { x = 10 }
        prop_b = { y = 20 }
    }
    n = { v = 3 } 
}
""")
    right = _obj_from("""
b = {
    c = {
        prop_a = { x = 10 }
        prop_b = { y = 20 }
    }
    n = { v = 2 }
}
""")


    merged, conflicts = three_way_merge(base, left, right)
    print(compile_ast(merged))
    for line in conflicts:
        print('Conflict:', line)
        
test_insert_same_key_diff_value_conflict()



def test_merge_context_insert_raises_on_missing_parent():
    obj = _obj_from('b = { }')
    