from synthetipy.ast_nodes_basic import DocumentNode, ObjectNode, BlockNode, PropertyNode, LiteralNode
from synthetipy.script_merger.gumtree_hash import compute_subtree_hashes
from synthetipy.script_merger.matcher import match_by_hash


def make_simple_doc(name: str, key: str, val: int):
    lit = LiteralNode(val)
    prop = PropertyNode(key, lit)
    block = BlockNode([prop])
    obj = ObjectNode(name, block)
    doc = DocumentNode([obj])
    return doc


def test_compute_subtree_hashes_consistent():
    doc1 = make_simple_doc('a', 'x', 1)
    doc2 = make_simple_doc('a', 'x', 1)

    obj1 = doc1.statements[0]
    obj2 = doc2.statements[0]

    h1_content, h1_buckets, _, _ = compute_subtree_hashes(obj1)
    h2_content, h2_buckets, _, _ = compute_subtree_hashes(obj2)

    # Expect that some content hashes overlap (e.g., literal nodes, property, object)
    common_hashes = set(h1_buckets.keys()) & set(h2_buckets.keys())
    assert len(common_hashes) >= 3


def test_match_by_hash_identical():
    base_doc = make_simple_doc('a', 'x', 1)
    other_doc = make_simple_doc('a', 'x', 1)

    base = base_doc.statements[0]
    other = other_doc.statements[0]

    matches = match_by_hash(base, other)
    # expect matches for multiple nodes (literal, property, object) — matching uses content-hash buckets
    assert len(matches) >= 3


def test_duplicate_siblings_disambiguated():
    # block with two identical properties should get distinct unique hashes after disambiguation
    lit1 = LiteralNode(5)
    prop1 = PropertyNode('k', lit1)
    prop2 = PropertyNode('k', LiteralNode(5))
    block = BlockNode([prop1, prop2])
    obj = ObjectNode('dup', block)
    doc = DocumentNode([obj])

    # compute per-object (do not call on the whole document)
    content_map, content_buckets, unique_map, unique_buckets = compute_subtree_hashes(obj)
    # ensure the two property nodes have same content hash but different unique hashes
    prop_ids = [id(prop1), id(prop2)]
    content_hashes = [content_map.get(pid) for pid in prop_ids]
    unique_hashes = [unique_map.get(pid) for pid in prop_ids]
    assert content_hashes[0] == content_hashes[1]
    assert unique_hashes[0] != unique_hashes[1], 'Expected duplicate sibling nodes to have distinct unique hashes'

