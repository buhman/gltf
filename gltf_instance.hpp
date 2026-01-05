#ifndef GLTF_INSTANCE_HPP_
#define GLTF_INSTANCE_HPP_

struct NodeInstance {
  const Node * node;
  D3DXVECTOR3 translation;
  D3DXQUATERNION rotation;
  D3DXVECTOR3 scale;
};

#endif
