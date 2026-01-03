template <typename T>
struct Array {
  T * e;
  int length;
};

struct Mesh {
  D3DXVECTOR3 * position;
  D3DXVECTOR3 * normal;
  D3DXVECTOR2 * texcoord_0;
  DWORD * indices;
};

struct Skin;

struct Node {
  Skin * skin; // skin index (global)
  Mesh * mesh; // mesh index (global)
  D3DXVECTOR3 scale;
  D3DXVECTOR3 translation;
  D3DXQUATERNION rotation;
};

struct Skin {
  D3DXMATRIX * inverse_bind_matrices; // accessor
  Array<Node *> joints;
};

enum AnimationChannelPath {
  ACP__WEIGHTS,
  ACP__ROTATION,
  ACP__TRANSLATION,
  ACP__SCALE,
};

struct AnimationSampler {
  float * input;  // accessor index, containing keyframe timestamps
  void * output; // accessor index, containing keyframe values (type depends on channel target path)
};

struct AnimationChannel {
  AnimationSampler * sampler; // sampler index, this animation
  struct {
    Node * node; // node index
    AnimationChannelPath path; // property to animate
  } target;
};

struct Animation {
  Array<AnimationChannel> channels;
  Array<AnimationSampler> samplers;
};
