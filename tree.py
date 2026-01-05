from gltf import decode_file

def build_tree(gltf):
    parents = {} # from child to parent

    for node_ix, node in enumerate(gltf.json["nodes"]):
        if "children" not in node:
            continue
        for child_ix in node["children"]:
            assert child_ix not in parents
            parents[child_ix] = node_ix

    for skin in gltf.json["skins"]:
        seen = set()
        for joint in skin["joints"]:
            parent = parents[joint]
            assert parent in seen or parent not in skin["joints"], (parent, joint, seen)
            seen.add(joint)

    return parents

if __name__ == "__main__":
    import sys
    filename = sys.argv[1]
    gltf = decode_file(filename)
    build_tree(gltf)
