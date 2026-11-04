#version 450
layout(push_constant) uniform Parameters { vec4 color; float depth; } parameters;
void main()
{
    const vec2 positions[3] = vec2[3](vec2(-1, -1), vec2(3, -1), vec2(-1, 3));
    gl_Position = vec4(positions[gl_VertexIndex], parameters.depth, 1);
}
