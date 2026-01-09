from gltf import decode_file

def linearize_tree(node_ix, nodes):
    yield node_ix
    node = nodes[node_ix]
    if "children" not in node:
        return
    for child_ix in node["children"]:
        yield from linearize_tree(child_ix, nodes)

def build_tree(gltf):
    parents = {} # from child to parent

    # fixme: hack
    if len(gltf.json["nodes"]) == 1:
        return {}, [0]

    for node_ix, node in enumerate(gltf.json["nodes"]):
        if "children" not in node:
            continue
        for child_ix in node["children"]:
            assert child_ix not in parents
            parents[child_ix] = node_ix

    root_node_ix, = set(i for i in parents.values() if i not in parents)
    print(root_node_ix)
    traversal_order = list(linearize_tree(root_node_ix, gltf.json["nodes"]))

    return parents, traversal_order

if __name__ == "__main__":
    import sys
    filename = sys.argv[1]
    gltf = decode_file(filename)
    build_tree(gltf)
