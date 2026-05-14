vec3 aplicar_biomas_mundo(vec3 color, vec2 screen_uv, float biome) {
    if (u_biome_mode > 0.5 && u_biome_mode < 1.5) {
        float edge = 1.0 - smoothstep(0.0, 0.16, min(min(screen_uv.x, 1.0 - screen_uv.x), min(screen_uv.y, 1.0 - screen_uv.y)));
        float frost_noise = noise21(screen_uv * vec2(26.0, 18.0) + u_time * 0.08);
        float frost = edge * smoothstep(0.40, 1.0, biome) * (0.60 + frost_noise * 0.40) * (1.0 - u_inside * 0.64);
        color = mix(color, min(color + vec3(0.10, 0.12, 0.14), vec3(1.0)), biome * 0.24);
        color = mix(color, vec3(0.88, 0.94, 1.0), frost * 0.58);
    }
    else if (u_biome_mode > 1.5 && u_biome_mode < 2.5) {
        float heat_n = noise21(vec2(screen_uv.x * 8.0 + u_time * 0.25, screen_uv.y * 26.0 + u_time * 1.3));
        vec2 heat_offset = vec2((heat_n - 0.5) * 0.012 * biome, 0.0);
        vec3 heated = scene_sample(v_uv + heat_offset);
        float ember = pow(noise21(screen_uv * 7.0 + vec2(u_time * 0.10, -u_time * 0.06)), 3.0);
        color = mix(color, heated * vec3(1.06, 0.96, 0.82), biome * 0.28);
        color += vec3(0.28, 0.09, 0.02) * ember * biome * (1.0 - u_inside * 0.50);
    }
    else if (u_biome_mode > 2.5 && u_biome_mode < 3.5) {
        float haze = noise21(vec2(screen_uv.x * 14.0 + u_time * 0.3, screen_uv.y * 20.0 + u_time * 1.1));
        vec2 heat_offset = vec2((haze - 0.5) * 0.009 * biome, 0.0);
        vec3 dry = scene_sample(v_uv + heat_offset);
        float dust = smoothstep(0.30, 1.0, haze) * smoothstep(0.10, 0.95, screen_uv.y);
        color = mix(color, dry * vec3(1.08, 1.00, 0.86), biome * 0.24);
        color += vec3(0.08, 0.06, 0.03) * dust * biome * 0.22;
    }
    else if (u_biome_mode > 3.5 && u_biome_mode < 4.5) {
        vec2 magic_shift = vec2(0.004 + biome * 0.006, 0.0) * (1.0 - u_inside * 0.35);
        vec3 magic_rgb = vec3(
            scene_sample(v_uv + magic_shift).r,
            scene_sample(v_uv).g,
            scene_sample(v_uv - magic_shift).b
        );
        float spark = pow(noise21(screen_uv * 22.0 + u_time * 0.24), 8.0);
        color = mix(color, saturate_color(magic_rgb, 1.26) * vec3(1.05, 0.94, 1.10), biome * 0.26);
        color += vec3(0.20, 0.08, 0.24) * biome * 0.16;
        color += vec3(0.22, 0.12, 0.28) * spark * biome;
    }
    else if (u_biome_mode > 4.5) {
        float murk = noise21(screen_uv * 8.5 + vec2(u_time * 0.05, -u_time * 0.03));
        float fog = smoothstep(0.22, 1.0, murk) * smoothstep(0.26, 1.0, screen_uv.y);
        color = saturate_color(color, 1.0 - biome * 0.24);
        color = mix(color, color * vec3(0.84, 0.90, 0.84), biome * 0.28);
        color = mix(color, vec3(0.48, 0.54, 0.48), fog * biome * 0.18 * (1.0 - u_inside * 0.40));
    }
    return color;
}
