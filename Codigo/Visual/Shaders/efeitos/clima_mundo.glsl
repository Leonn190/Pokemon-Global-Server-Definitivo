vec3 aplicar_chuva_mundo(vec3 color, vec2 screen_uv, float rain, float battle_acid) {
    if (rain <= 0.001) {
        return color;
    }

    float ripple = noise21(vec2(screen_uv.x * 28.0 + u_time * 0.35, screen_uv.y * 36.0 - u_time * 3.8));
    vec2 wet_offset = vec2((ripple - 0.5) * 0.010 * rain, 0.0);
    vec3 rainy = scene_sample(v_uv + wet_offset);
    vec3 rain_grade = mix(vec3(0.92, 0.98, 1.03), vec3(0.84, 1.07, 0.76), battle_acid);
    color = mix(color, rainy * rain_grade, rain * 0.20);

    float reflection_mask = smoothstep(0.40, 1.0, screen_uv.y) * (1.0 - u_inside * 0.55);
    float streak = smoothstep(0.56, 1.0, ripple);
    vec3 rain_glow = mix(vec3(0.025, 0.045, 0.060), vec3(0.025, 0.085, 0.018), battle_acid);
    color += rain_glow * reflection_mask * rain * (0.30 + 0.70 * streak);
    color = mix(color, color * mix(vec3(0.84, 0.90, 0.98), vec3(0.80, 0.98, 0.78), battle_acid), rain * 0.22);
    return color;
}

vec3 aplicar_estrelas_luz_player(vec3 color, vec2 screen_uv, float aspect, float dark, float rain) {
    if (u_star_strength > 0.01 && u_inside < 0.5) {
        float top_mask = smoothstep(0.40, 0.82, screen_uv.y);
        float stars = star_field(screen_uv) * u_star_strength * top_mask;
        color += vec3(0.42, 0.46, 0.54) * stars;
    }

    vec2 light_delta = screen_uv - u_player_uv;
    light_delta.x *= aspect;
    float dist = length(light_delta);
    float inner_radius = mix(0.045, 0.085, dark);
    float outer_radius = mix(0.16, 0.24, dark);
    float glow_core = 1.0 - smoothstep(inner_radius, outer_radius, dist);
    float glow_soft = 1.0 - smoothstep(outer_radius, outer_radius * 1.65, dist);
    glow_core = pow(max(glow_core, 0.0), 1.45);
    glow_soft = pow(max(glow_soft, 0.0), 1.8);
    float glow = (glow_core * 0.82 + glow_soft * 0.18) * dark;
    glow *= mix(1.0, 0.88, rain * 0.45);
    return mix(color, min(color * 1.22 + vec3(0.022, 0.030, 0.040), vec3(1.0)), glow);
}

vec3 aplicar_raios_mundo(vec3 color, vec2 screen_uv) {
    if (u_lightning <= 0.001) {
        return color;
    }

    float bolt_x = 0.18 + 0.52 * fract(sin(floor(u_time * 1.75) + 3.41) * 43758.5453);
    float branch = abs(screen_uv.x - (bolt_x + sin(screen_uv.y * 18.0 + u_time * 12.0) * 0.018));
    float bolt = smoothstep(0.030, 0.0, branch) * smoothstep(0.72, 0.10, screen_uv.y);
    color += vec3(0.42, 0.45, 0.52) * clamp(u_lightning, 0.0, 1.25);
    color += vec3(0.64, 0.66, 0.75) * bolt * clamp(u_lightning, 0.0, 1.25);
    return color;
}
