#version 450
layout(location = 0) in vec4 position;
layout(set = 0, binding = 3) uniform sampler2D unusedTex;
layout(constant_id = 7) const float unusedSpec = 1.0;
void main() { gl_Position = position; }
