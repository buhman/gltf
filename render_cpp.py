import sys
from pprint import pprint
from generate import renderer

from gltf import decode_file
from gltf import validate_mesh
from gltf import decode_accessor

filename = sys.argv[1]
gltf = decode_file(filename)

def type_name(type):
    return {
        "SCALAR": "DWORD",
        "VEC2": "D3DXVECTOR2",
        "VEC3": "D3DXVECTOR3",
        "VEC4": "D3DXVECTOR4",
        # MAT2
        # MAT3
        "MAT4": "D3DXMATRIX",
    }[type]

def float_s(f):
    return f"{f:10.7f}f"

def sv(v, c_type):
    args = ", ".join(
        float_s(c) for c in v
    )
    return f"{c_type}({args})"

def mv(v, c_type):
    assert len(v) == 16
    assert c_type == "D3DXMATRIX"

    v = [float_s(c) for c in v]

    return f"""
D3DXMATRIX({v[ 0]}, {v[ 1]}, {v[ 2]}, {v[ 3]},
             {v[ 4]}, {v[ 5]}, {v[ 6]}, {v[ 7]},
             {v[ 8]}, {v[ 9]}, {v[10]}, {v[11]},
             {v[12]}, {v[13]}, {v[14]}, {v[15]})
""".strip()

def render_value(value, c_type):
    if "MAT" in c_type:
        return mv(value, c_type)
    elif "VEC" in c_type:
        return sv(value, c_type)
    elif type(value) in {int, float}:
        return f"{value}"
    else:
        assert False

def render_accessors(gltf):
    for accessor_ix, accessor in enumerate(gltf.json["accessors"]):
        components = list(decode_accessor(gltf, accessor))
        accessor_name = f"accessor_{accessor_ix}"
        accessor_type = accessor['type']
        if type(components[0]) in {int, float}:
            c_type = "DWORD" if type(components[0]) is int else "float"
        else:
            c_type = type_name(accessor_type)
        yield f"const {c_type} {accessor_name}[] = {{"
        for v in components:
            yield f"{render_value(v, c_type)},"
        yield "};"
        yield f"const int {accessor_name}_length = (sizeof ({accessor_name})) / (sizeof ({accessor_name}[0]));"

def render_meshes(gltf):
    for mesh_ix, mesh in enumerate(gltf.json["meshes"]):
        validate_mesh(gltf, mesh)
        primitive, = mesh["primitives"]
        attributes = primitive["attributes"]
        position = attributes["POSITION"]
        normal = attributes.get("NORMAL", None)
        texcoord_0 = attributes.get("TEXCOORD_0", None)
        indices = primitive["indices"]
        yield f"const Mesh mesh_{mesh_ix} = {{"
        yield f"accessor_{position}, // position"
        yield f"accessor_{normal}, // normal" if normal is not None else "NULL,"
        yield f"accessor_{texcoord_0}, // texcoord_0" if texcoord_0 is not None else "NULL,"
        yield f"accessor_{indices}, // indices"
        yield "};"

def render_nodes(gltf):
    for node in gltf.json["nodes"]:
        if "skin" not in node:
            continue
        skin = node["skin"]
        yield f"const Skin skin_{skin};"

    for node_ix, node in enumerate(gltf.json["nodes"]):
        skin = f"&skin_{node['skin']}" if "skin" in node else "NULL"
        mesh = f"&mesh_{node['skin']}" if "mesh" in node else "NULL"

        scale = (1, 1, 1)
        translation = (0, 0, 0)
        rotation = (0, 0, 0, 1)
        if "scale" in node:
            scale = node["scale"]
        if "translation" in node:
            translation = node["translation"]
        if "rotation" in node:
            rotation = node["rotation"]

        yield f"const Node node_{node_ix} = {{"
        yield f"{skin}, // skin"
        yield f"{mesh}, // mesh"
        yield f"{render_value(scale, 'D3DXVECTOR3')}, // scale"
        yield f"{render_value(translation, 'D3DXVECTOR3')}, // translation"
        yield f"{render_value(rotation, 'D3DXVECTOR4')}, // rotation"
        yield "};"

def render_skins(gltf):
    for skin_ix, skin in enumerate(gltf.json["skins"]):
        yield f"const Node * skin_{skin_ix}__joints[] = {{"
        for joint in skin["joints"]:
            yield f"&node_{joint},"
        yield "};"

    for skin_ix, skin in enumerate(gltf.json["skins"]):
        inverse_bind_matrices = skin["inverseBindMatrices"]
        yield f"const Skin skin_{skin_ix} = {{"
        yield f"accessor_{inverse_bind_matrices}, // inverse bind matrices"
        yield f"{{ skin_{skin_ix}__joints, {len(skin['joints'])} }},"
        yield "};"

def render_animation_samplers(animation_ix, samplers):
    for sampler_ix, sampler in enumerate(samplers):
        yield f"const AnimationSampler animation_{animation_ix}__sampler_{sampler_ix} = {{"
        yield f"accessor_{sampler['input']}, // input, keyframe timestamps"
        yield f"accessor_{sampler['output']}, // output, keyframe values (void *)"
        yield "};"


def render_animation_channels(animation_ix, channels):
    yield f"const AnimationChannel animation_{animation_ix}__channels[] = {{"
    for channel in channels:
        sampler = channel["sampler"]
        target_node = channel["target"]["node"]
        target_path = channel["target"]["path"]
        yield f"&animation_{animation_ix}__sampler_{sampler}, // animation sampler"
        yield "{"
        yield f"&node_{target_node}, // target node"
        yield f"ACP__{target_path.upper()}, // target path"
        yield "},"
    yield "};"

def render_animations(gltf):
    for animation_ix, animation in enumerate(gltf.json["animations"]):
        yield from render_animation_samplers(animation_ix, animation["samplers"])
        yield from render_animation_channels(animation_ix, animation["channels"])

def render_gltf(gltf):
    yield from render_accessors(gltf)
    yield from render_meshes(gltf)
    yield from render_nodes(gltf)
    yield from render_skins(gltf)
    yield from render_animations(gltf)

render, out = renderer()
render(render_gltf(gltf))
print(out.getvalue())
