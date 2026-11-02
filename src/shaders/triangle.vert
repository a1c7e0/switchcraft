#version 450
const vec2 p[3] = vec2[3](vec2(-0.7,-0.6),vec2(0.7,-0.6),vec2(0,0.7));
void main() { gl_Position=vec4(p[gl_VertexIndex],0,1); }
