from gltf import decode_file

def build_tree(gltf):
    parents = {} # from child to parent

    for node_ix, node in enumerate(gltf.json["nodes"]):
        if "children" not in node:
            continue
        for child_ix in node["children"]:
            assert child_ix > node_ix, (child_ix, node_ix)
            assert child_ix not in parents
            parents[child_ix] = node_ix

    return parents

if __name__ == "__main__":
    import sys
    filename = sys.argv[1]
    gltf = decode_file(filename)
    build_tree(gltf)
