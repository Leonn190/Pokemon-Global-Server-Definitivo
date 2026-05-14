vec3 aplicar_captura(vec3 color, vec2 ui_uv) {
    float power = clamp(u_capture_power, 0.0, 1.0);
    if (power <= 0.001) {
        return color;
    }

    float aspect = u_resolution.x / u_resolution.y;
    vec2 rel = ui_uv - clamp(u_capture_uv, vec2(0.0), vec2(1.0));
    rel.x *= aspect;
    float d = length(rel);
    vec2 dir = rel / max(d, 0.0001);

    float phase = clamp(u_capture_phase, 0.0, 4.0);
    float result = clamp(u_capture_result, -1.0, 1.0);
    float critical = clamp(u_capture_critical, 0.0, 1.0);
    float check_i = max(0.0, u_capture_check_index);
    float check_count = max(1.0, u_capture_check_count);

    vec3 azul = vec3(0.18, 0.54, 1.00);
    vec3 ciano = vec3(0.20, 0.95, 1.00);
    vec3 ouro = vec3(1.00, 0.78, 0.24);
    vec3 verde = vec3(0.32, 1.00, 0.48);
    vec3 vermelho = vec3(1.00, 0.20, 0.18);
    vec3 violeta = vec3(0.72, 0.30, 1.00);

    vec3 base_fx = mix(azul, ouro, critical);
    if (result > 0.25) {
        base_fx = mix(base_fx, verde, 0.72);
    } else if (result > -0.25 && phase > 1.5) {
        base_fx = mix(base_fx, ciano, 0.48);
    } else if (result < -0.25) {
        base_fx = mix(base_fx, vermelho, 0.74);
    }

    float t = u_time + u_capture_token_hash * 0.017;
    float fase_check = clamp(check_i / check_count, 0.0, 1.0);

    // Escurece discretamente o entorno e chama atenção para o centro da captura.
    float vignette = smoothstep(0.22, 0.86, d);
    color = mix(color, color * mix(vec3(0.88, 0.92, 1.02), vec3(0.72, 0.76, 0.88), power), vignette * power * 0.22);

    // Distorção curta: dá sensação de sucção/energia sem precisar redesenhar sprite.
    float warp_zone = (1.0 - smoothstep(0.00, 0.34, d)) * power;
    float wave = sin(d * 62.0 - t * 7.2 + phase * 1.7) * 0.0065 * warp_zone;
    vec2 warp_uv = ui_uv + dir * wave;
    vec3 warped = scene_sample(warp_uv);
    color = mix(color, warped, warp_zone * 0.22);

    // Aura central perto do Pokémon/bola.
    float core = 1.0 - smoothstep(0.00, 0.105, d);
    float soft = 1.0 - smoothstep(0.04, 0.34, d);
    float pulse = 0.72 + 0.28 * sin(t * 8.0 + phase * 2.0);
    color += base_fx * core * power * (0.30 + 0.22 * pulse);
    color += base_fx * soft * power * 0.105;

    // Onda expansiva da entrada na pokébola e das checagens.
    float cycle = fract(t * mix(0.48, 0.76, critical) + fase_check * 0.31);
    float ring_radius = mix(0.055, 0.315, cycle);
    float ring_width = mix(0.014, 0.025, cycle);
    float ring = 1.0 - smoothstep(ring_width, ring_width * 2.2, abs(d - ring_radius));
    ring *= 1.0 - smoothstep(0.52, 0.92, cycle);
    color += base_fx * ring * power * (0.20 + critical * 0.18);

    // Checagem: três marcas luminosas discretas ao redor do centro.
    float marks = 0.0;
    for (int i = 0; i < 3; i++) {
        float a = (float(i) / 3.0) * PI * 2.0 + t * 0.95;
        vec2 mark_pos = vec2(cos(a) / aspect, sin(a)) * 0.125;
        float md = length((ui_uv - clamp(u_capture_uv, vec2(0.0), vec2(1.0)) - mark_pos) * vec2(aspect, 1.0));
        float active_mark = step(float(i), check_i + 0.001);
        marks += (1.0 - smoothstep(0.00, 0.022, md)) * mix(0.35, 1.0, active_mark);
    }
    vec3 check_color = mix(violeta, base_fx, 0.70);
    color += check_color * marks * power * smoothstep(1.05, 2.10, phase) * 0.22;

    // Captura crítica: halo dourado extra, mas controlado para não estourar branco.
    float critical_ring = 1.0 - smoothstep(0.010, 0.036, abs(d - 0.185));
    color += ouro * critical_ring * critical * power * (0.18 + 0.10 * pulse);

    // Resultado final: verde se pegou, vermelho se escapou.
    float final_mask = smoothstep(2.70, 3.70, phase) * power;
    vec3 final_color = result > 0.25 ? verde : vermelho;
    float final_flash = (1.0 - smoothstep(0.00, 0.42, d)) * (0.55 + 0.45 * sin(t * 11.0));
    color += final_color * final_flash * final_mask * abs(result) * 0.16;

    return clamp(color, 0.0, 1.0);
}
