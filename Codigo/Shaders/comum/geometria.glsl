vec2 rotate2d(vec2 p, float a) {
    float s = sin(a);
    float c = cos(a);
    return vec2(c * p.x - s * p.y, s * p.x + c * p.y);
}

float ellipse_orbit(vec2 rel, vec2 radius, float angle, float thickness, float dash_phase) {
    vec2 p = rotate2d(rel, angle) / max(radius, vec2(0.0001));
    float ring = 1.0 - smoothstep(thickness, thickness * 2.4, abs(length(p) - 1.0));
    float theta = atan(p.y, p.x);

    float dash = 0.58 + 0.42 * sin(theta * 2.0 + dash_phase);
    dash *= 0.66 + 0.34 * sin(theta * 4.0 - dash_phase * 0.7);
    dash = smoothstep(0.53, 0.96, dash);
    return ring * dash;
}

float star_field(vec2 screen_uv) {
    vec2 uv = screen_uv;
    uv.x *= u_resolution.x / u_resolution.y;
    uv *= 24.0;

    vec2 gv = fract(uv) - 0.5;
    vec2 id = floor(uv);
    float rnd = hash21(id);
    float mask = step(0.9925, rnd);
    float d = length(gv);
    float blink = 0.65 + 0.35 * sin(u_time * (2.0 + rnd * 4.0) + rnd * 30.0);
    return smoothstep(0.17, 0.0, d) * mask * blink;
}
