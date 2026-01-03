import struct
import json
import base64

class GLTF:
    def __init__(self, json, buffers):
        # json: dict
        # buffers: list[memoryview]
        self.json = json
        self.buffers = buffers

class Mesh:
    def __init__(self, attributes, indices):
        # attributes: list
        # indices: list
        self.attributes = attributes
        self.indices = indices

def parse_header(mem, offset):
    magic, version, length = struct.unpack("<III", mem[offset:offset + 12])
    assert magic == 0x46546c67
    assert version == 0x2
    return offset + 12, length

def parse_json_chunk(mem, offset):
    chunk_length, chunk_type = struct.unpack("<II", mem[offset:offset + 8])
    assert chunk_type == 0x4e4f534a
    data = json.loads(bytes(mem[offset + 8:offset + 8 + chunk_length]))
    return offset + 8 + chunk_length, data

def parse_bin_chunk(mem, offset):
    chunk_length, chunk_type = struct.unpack("<II", mem[offset:offset + 8])
    assert chunk_type == 0x004e4942
    data = mem[offset + 8:offset + 8 + chunk_length]
    return offset + 8 + chunk_length, data

def component_type_format(n):
    return {
        5120: ("<b", 1), # "BYTE",
        5121: ("<B", 1), # "UNSIGNED_BYTE",
        5122: ("<h", 2), # "SHORT",
        5123: ("<H", 2), # "UNSIGNED_SHORT",
        5125: ("<I", 4), # "UNSIGNED_INT",
        5126: ("<f", 4), # "FLOAT",
    }[n]

def element_type_count(s):
    return {
        "SCALAR": 1,
        "VEC2": 2,
        "VEC3": 3,
        "VEC4": 4,
        "MAT2": 4,
        "MAT3": 9,
        "MAT4": 16,
    }[s]

def decode_components(gltf, accessor):
    components_per_element = element_type_count(accessor["type"])
    accessor_count = accessor["count"]

    accessor_buffer_view = accessor["bufferView"]
    buffer_view = gltf.json["bufferViews"][accessor_buffer_view]

    buffer = gltf.buffers[buffer_view["buffer"]]

    accessor_byte_offset = accessor["byteOffset"] if "byteOffset" in accessor else 0
    buffer_view_byte_offset = buffer_view.get("byteOffset", 0)

    offset = accessor_byte_offset + buffer_view_byte_offset
    buffer_end = offset + buffer_view["byteLength"]

    accessor_component_type = accessor["componentType"]
    format, size = component_type_format(accessor_component_type)

    byte_stride = size * components_per_element
    if "byteStride" in buffer_view:
        assert buffer_view["byteStride"] >= byte_stride
        byte_stride = buffer_view["byteStride"]

    components = []
    for _ in range(accessor_count):
        for i in range(components_per_element):
            start = offset + i * size
            end = offset + i * size + size
            assert end <= buffer_end
            c, = struct.unpack(format, buffer[start:end])
            components.append(c)
        offset += byte_stride
    return components

def decode_accessor(gltf, accessor):
    components = decode_components(gltf, accessor)
    components_per_element = element_type_count(accessor["type"])
    for i in range(accessor["count"]):
        if accessor["type"] == "SCALAR":
            yield components[i]
        else:
            yield tuple(
                components[i*components_per_element+j] for j in range(components_per_element)
            )

def validate_mesh(gltf, mesh):
    assert len(mesh["primitives"]) == 1
    primitive, = mesh["primitives"]
    assert "mode" not in primitive or primitive["mode"] == 4 # triangles

def decode_glb(mem):
    offset = 0
    offset, length = parse_header(mem, offset)
    offset, json_chunk = parse_json_chunk(mem, offset)
    offset, bin_chunk = parse_bin_chunk(mem, offset)
    assert offset == length
    gltf = GLTF(json_chunk, [bin_chunk])
    return gltf

def remove_uri_prefix(uri):
    prefixes = [
        "data:application/octet-stream;base64,",
        "data:application/gltf-buffer;base64,",
    ]
    for prefix in prefixes:
        if uri.startswith(prefix):
            return uri[len(prefix):]
    assert False, uri

def decode_gltf(mem):
    gltf_json = json.loads(bytes(mem))

    buffers = []
    for buffer in gltf_json["buffers"]:
        uri = buffer["uri"]
        uri = remove_uri_prefix(uri)
        data = base64.b64decode(uri)
        assert len(data) == buffer["byteLength"]
        buffers.append(memoryview(data))

    gltf = GLTF(gltf_json, buffers)
    return gltf

def decode_file(filename):
    with open(filename, "rb") as f:
        buf = f.read()
        mem = memoryview(buf)
    if filename.lower().endswith(".glb"):
        return decode_glb(mem)
    elif filename.lower().endswith(".gltf"):
        return decode_gltf(mem)
    else:
        assert False, filename

if __name__ == "__main__":
    import sys
    gltf = decode_file(sys.argv[1])
    import json
    print(json.dumps(gltf.json, indent=4))
