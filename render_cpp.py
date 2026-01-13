from os import path
import sys
from pprint import pprint
from generate import renderer

from gltf import decode_file
from gltf import validate_mesh
from gltf import decode_accessor

from tree import build_tree

def type_name(type):
    return {
        "SCALAR": "int",
        "VEC2": "XMFLOAT2",
        "VEC3": "XMFLOAT3",
        "VEC4": "XMFLOAT4",
        # MAT2
        # MAT3
        "MAT4": "XMMATRIX",
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
    assert c_type == "XMMATRIX"

    v = [float_s(c) for c in v]

    return f"""
XMMATRIX({v[ 0]}, {v[ 1]}, {v[ 2]}, {v[ 3]},
         {v[ 4]}, {v[ 5]}, {v[ 6]}, {v[ 7]},
         {v[ 8]}, {v[ 9]}, {v[10]}, {v[11]},
         {v[12]}, {v[13]}, {v[14]}, {v[15]})
""".strip()

def render_value(value, c_type):
    if "MATRIX" in c_type:
        return mv(value, c_type)
    elif "FLOAT" in c_type:
        return sv(value, c_type)
    elif type(value) in {int, float}:
        return f"{value}"
    else:
        assert False

def accessor_c_type(accessor, components):
    accessor_type = accessor['type']
    if type(components[0]) in {int, float}:
        return "int" if type(components[0]) is int else "float"
    else:
        return type_name(accessor_type)

def render_accessors(gltf):
    for accessor_ix, accessor in enumerate(gltf.json["accessors"]):
        components = list(decode_accessor(gltf, accessor))
        c_type = accessor_c_type(accessor, components)
        accessor_name = f"accessor_{accessor_ix}"
        yield f"const {c_type} {accessor_name}[] = {{"
        for v in components:
            yield f"{render_value(v, c_type)},"
        yield "};"

def render_accessors_extern(gltf):
    for accessor_ix, accessor in enumerate(gltf.json["accessors"]):
        components = list(decode_accessor(gltf, accessor))
        c_type = accessor_c_type(accessor, components)
        accessor_name = f"accessor_{accessor_ix}"
        yield f"extern const {c_type} {accessor_name}[];";
        yield f"const int {accessor_name}__length = {len(components)};"
        yield f"const int {accessor_name}__size = (sizeof ({c_type})) * {len(components)};"

def render_meshes(gltf):
    for mesh_ix, mesh in enumerate(gltf.json["meshes"]):
        validate_mesh(gltf, mesh)
        primitive, = mesh["primitives"]
        attributes = primitive["attributes"]
        position = attributes["POSITION"]
        normal = attributes.get("NORMAL", None)
        texcoord_0 = attributes.get("TEXCOORD_0", None)
        weights_0 = attributes.get("WEIGHTS_0", None)
        joints_0 = attributes.get("JOINTS_0", None)
        indices = primitive["indices"]
        yield f"const Mesh mesh_{mesh_ix} = {{"
        yield f"accessor_{position}, // position"
        yield f"accessor_{position}__size,"
        yield f"accessor_{normal}, // normal" if normal is not None else "NULL, // normal"
        yield f"accessor_{normal}__size," if normal is not None else "0,"
        yield f"accessor_{texcoord_0}, // texcoord_0" if texcoord_0 is not None else "NULL, // texcoord_0"
        yield f"accessor_{texcoord_0}__size," if texcoord_0 is not None else "0,"
        yield f"accessor_{weights_0}, // weights_0" if weights_0 is not None else "NULL, // weights_0"
        yield f"accessor_{weights_0}__size," if weights_0 is not None else "0,"
        yield f"accessor_{joints_0}, // joints_0" if joints_0 is not None else "NULL, // joints_0"
        yield f"accessor_{joints_0}__size," if joints_0 is not None else "0,"
        yield f"accessor_{indices}, // indices"
        yield f"accessor_{indices}__size,"

        yield "};"

def render_nodes(gltf):
    for node in gltf.json["nodes"]:
        if "skin" not in node:
            continue
        skin = node["skin"]
        yield f"extern const Skin skin_{skin};"

    node_parents, traversal_order = build_tree(gltf)

    for node_ix, node in enumerate(gltf.json["nodes"]):
        if "mesh" in node:
            print(f"mesh node {node_ix}", file=sys.stderr)

        skin = f"&skin_{node['skin']}" if "skin" in node else "NULL"
        mesh = f"&mesh_{node['mesh']}" if "mesh" in node else "NULL"

        scale = (1, 1, 1)
        translation = (0, 0, 0)
        rotation = (0, 0, 0, 1)
        if "scale" in node:
            scale = node["scale"]
        if "translation" in node:
            translation = node["translation"]
        if "rotation" in node:
            rotation = node["rotation"]

        parent_ix = node_parents.get(node_ix, "(int)-1")

        yield f"const Node node_{node_ix} = {{"
        yield f"{parent_ix}, // parent_ix"
        yield f"{skin}, // skin"
        yield f"{mesh}, // mesh"
        yield f"{render_value(translation, 'XMFLOAT3')}, // translation"
        yield f"{render_value(rotation, 'XMFLOAT4')}, // rotation"
        yield f"{render_value(scale, 'XMFLOAT3')}, // scale"
        yield "};"

    yield "const Node * nodes[] = {"
    for node_ix in range(len(gltf.json["nodes"])):
        yield f"&node_{node_ix},"
    yield "};"

def render_nodes_extern(gltf):
    for node_ix, node in enumerate(gltf.json["nodes"]):
        yield f"extern const Node node_{node_ix};"
    yield "extern const Node * nodes[];"
    yield f'const int nodes__length = {len(gltf.json["nodes"])};'

def render_skins(gltf):
    if "skins" not in gltf.json:
        return

    for skin_ix, skin in enumerate(gltf.json["skins"]):
        yield f"const int skin_{skin_ix}__joints[] = {{"
        for joint in skin["joints"]:
            yield f"{joint},"
        yield "};"

    for skin_ix, skin in enumerate(gltf.json["skins"]):
        inverse_bind_matrices = skin["inverseBindMatrices"]
        yield f"const Skin skin_{skin_ix} = {{"
        yield f"accessor_{inverse_bind_matrices}, // inverse bind matrices"
        yield f"skin_{skin_ix}__joints, // joints"
        yield f"{len(skin['joints'])}, // joints length"
        yield "};"

def render_skins_extern(gltf):
    if "skins" not in gltf.json:
        return
    for skin_ix, skin in enumerate(gltf.json["skins"]):
        yield f"const int skin_{skin_ix}__joints__length = {len(skin['joints'])};"

def render_animation_samplers(animation_ix, samplers):
    for sampler_ix, sampler in enumerate(samplers):
        yield f"const AnimationSampler animation_{animation_ix}__sampler_{sampler_ix} = {{"
        yield f"accessor_{sampler['input']}, // input, keyframe timestamps"
        yield f"accessor_{sampler['output']}, // output, keyframe values (void *)"
        yield f"accessor_{sampler['input']}__length, // length"
        yield "};"

def render_animation_channels(animation_ix, channels):
    yield f"const AnimationChannel animation_{animation_ix}__channels[] = {{"
    for channel in channels:
        sampler = channel["sampler"]
        target_node = channel["target"]["node"]
        target_path = channel["target"]["path"]
        yield f"&animation_{animation_ix}__sampler_{sampler}, // animation sampler"
        yield "{"
        yield f"{target_node}, // target node index"
        yield f"ACP__{target_path.upper()}, // target path"
        yield "},"
    yield "};"

def render_animations_extern(animation_ix):
    if "animations" not in gltf.json:
        return
    for animation_ix, animation in enumerate(gltf.json["animations"]):
        yield f"extern const AnimationChannel animation_{animation_ix}__channels[];"
        length = len(animation["channels"])
        yield f"const int animation_{animation_ix}__channels__length = {length};"

def render_animations(gltf):
    if "animations" not in gltf.json:
        return
    for animation_ix, animation in enumerate(gltf.json["animations"]):
        yield from render_animation_samplers(animation_ix, animation["samplers"])
        yield from render_animation_channels(animation_ix, animation["channels"])

def render_gltf_header(gltf, prefix):
    yield "#pragma once"
    yield f"#ifndef _{prefix.upper()}_HPP_"
    yield f"#define _{prefix.upper()}_HPP_"
    yield f"namespace {prefix} {{"
    yield from render_skins_extern(gltf)
    yield from render_accessors_extern(gltf)
    yield from render_nodes_extern(gltf)
    yield from render_animations_extern(gltf)
    yield "}"
    yield "#endif"

def render_gltf_source(gltf, prefix, filename_hpp):
    header_name = path.split(filename_hpp)[1]
    yield '#include "directxmath/directxmath.h"'
    yield '#include "gltf.hpp"'
    yield f'#include "{header_name}"'
    yield f"namespace {prefix} {{"
    yield from render_accessors(gltf)
    yield from render_meshes(gltf)
    yield from render_nodes(gltf)
    yield from render_skins(gltf)
    yield from render_animations(gltf)
    yield "}"

filename = sys.argv[1]
prefix = sys.argv[2]
filename_cpp = sys.argv[3]
assert filename_cpp.endswith(".cpp")
filename_hpp = sys.argv[4]
assert filename_hpp.endswith(".hpp")
gltf = decode_file(filename)

with open(filename_cpp, "w") as f:
    render, out = renderer()
    render(render_gltf_source(gltf, prefix, filename_hpp))
    f.write(out.getvalue())

with open(filename_hpp, "w") as f:
    render, out = renderer()
    render(render_gltf_header(gltf, prefix))
    f.write(out.getvalue())
