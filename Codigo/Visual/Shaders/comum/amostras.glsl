vec3 scene_sample(vec2 uv) {
    return texture(u_scene_tex, clamp(uv, vec2(0.0), vec2(1.0))).rgb;
}

float hud_alpha_blur(vec2 uv, float px_radius) {
    vec2 p = vec2(px_radius) / u_resolution;
    float a = texture(u_hud_tex, uv).a * 0.22;
    a += texture(u_hud_tex, uv + vec2( p.x,  0.0)).a * 0.10;
    a += texture(u_hud_tex, uv + vec2(-p.x,  0.0)).a * 0.10;
    a += texture(u_hud_tex, uv + vec2( 0.0,  p.y)).a * 0.10;
    a += texture(u_hud_tex, uv + vec2( 0.0, -p.y)).a * 0.10;
    a += texture(u_hud_tex, uv + vec2( p.x,  p.y)).a * 0.07;
    a += texture(u_hud_tex, uv + vec2(-p.x,  p.y)).a * 0.07;
    a += texture(u_hud_tex, uv + vec2( p.x, -p.y)).a * 0.07;
    a += texture(u_hud_tex, uv + vec2(-p.x, -p.y)).a * 0.07;
    a += texture(u_hud_tex, uv + vec2( p.x * 1.8,  0.0)).a * 0.06;
    a += texture(u_hud_tex, uv + vec2(-p.x * 1.8,  0.0)).a * 0.06;
    a += texture(u_hud_tex, uv + vec2( 0.0,  p.y * 1.8)).a * 0.06;
    a += texture(u_hud_tex, uv + vec2( 0.0, -p.y * 1.8)).a * 0.06;
    return clamp(a, 0.0, 1.0);
}
