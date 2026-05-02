vec3 aplicar_clima_batalha(vec3 color, vec2 screen_uv, float aspect, float battle_sun, float battle_sand, float battle_fog) {
    if (battle_sun > 0.001) {
        vec2 sun_pos = vec2(-0.10, 1.10);
        float sun_dist = length((screen_uv - sun_pos) * vec2(aspect, 1.0));
        float glare = 1.0 - smoothstep(0.15, 1.16, sun_dist);
        float ray_seed = screen_uv.x * 5.2 + screen_uv.y * 2.5 + sin(u_time * 0.18) * 0.18;
        float rays = pow(max(0.0, sin(ray_seed * PI) * 0.5 + 0.5), 5.0);
        rays *= smoothstep(1.04, 0.20, sun_dist);
        color = mix(color, min(color * vec3(1.12, 1.06, 0.90) + vec3(0.055, 0.044, 0.020), vec3(1.0)), battle_sun * 0.42);
        color += vec3(0.35, 0.28, 0.10) * (glare * 0.20 + rays * 0.16) * battle_sun;
    }

    if (battle_sand > 0.001) {
        float sand_n = noise21(vec2(screen_uv.x * 12.0 - u_time * 2.2, screen_uv.y * 28.0 + u_time * 0.32));
        vec2 sand_offset = vec2((sand_n - 0.5) * 0.012 * battle_sand, 0.0);
        vec3 sandy = scene_sample(v_uv + sand_offset);
        float sheet = smoothstep(0.42, 1.0, sand_n) * (0.35 + 0.65 * smoothstep(0.08, 0.92, screen_uv.y));
        color = mix(color, sandy * vec3(1.08, 1.01, 0.82), battle_sand * 0.30);
        color = mix(color, vec3(0.76, 0.66, 0.43), sheet * battle_sand * 0.16);
    }

    if (battle_fog > 0.001) {
        float fog_n = noise21(vec2(screen_uv.x * 5.5 - u_time * 0.12, screen_uv.y * 7.0 + u_time * 0.05));
        float veil = smoothstep(0.10, 0.92, fog_n) * (0.55 + 0.45 * smoothstep(0.04, 0.78, screen_uv.y));
        color = saturate_color(color, 1.0 - battle_fog * 0.34);
        color = mix(color, vec3(0.72, 0.76, 0.75), battle_fog * (0.18 + veil * 0.24));
        color = mix(vec3(0.5), color, 1.0 - battle_fog * 0.16);
    }

    return color;
}
