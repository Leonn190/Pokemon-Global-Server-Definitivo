#version 330

in vec2 in_pos;
in vec2 in_uv;
out vec2 v_uv;

void main() {
    v_uv = vec2(in_uv.x, 1.0 - in_uv.y);
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
