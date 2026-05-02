vec3 aplicar_captura(vec3 color, vec2 ui_uv) {
    float power = clamp(u_capture_power, 0.0, 1.0);
    if (power <= 0.001) {
        return color;
    }

    float aspect = u_resolution.x / u_resolution.y;
    vec2 centro = clamp(u_capture_uv, vec2(0.0), vec2(1.0));
    vec2 rel = ui_uv - centro;
    rel.x *= aspect;
    float d = length(rel);
    vec2 dir = rel / max(d, 0.0001);

    float phase = clamp(u_capture_phase, 0.0, 4.0);
    float critical = clamp(u_capture_critical, 0.0, 1.0);
    float check_i = max(0.0, u_capture_check_index);
    float check_count = max(1.0, u_capture_check_count);
    float t = u_time + u_capture_token_hash * 0.017;
    float fase_check = clamp(check_i / check_count, 0.0, 1.0);

    vec3 azul = vec3(0.18, 0.54, 1.00);
    vec3 ciano = vec3(0.20, 0.88, 1.00);
    vec3 ouro = vec3(1.00, 0.76, 0.24);
    vec3 violeta = vec3(0.58, 0.32, 1.00);
    vec3 base_fx = mix(mix(azul, ciano, 0.42), ouro, critical * 0.72);

    // O shader de captura deve acompanhar a animação, não contar o resultado.
    // Por isso ele não usa verde/vermelho de sucesso/falha.
    float vignette = smoothstep(0.24, 0.82, d);
    color = mix(color, color * vec3(0.90, 0.94, 1.03), vignette * power * 0.105);

    float warp_zone = (1.0 - smoothstep(0.00, 0.29, d)) * power;
    float wave = sin(d * 54.0 - t * 5.8 + phase * 1.35) * 0.0038 * warp_zone;
    vec3 warped = scene_sample(ui_uv + dir * wave);
    color = mix(color, warped, warp_zone * 0.115);

    float pulse = 0.72 + 0.28 * sin(t * 6.6 + phase * 1.7);
    float core = 1.0 - smoothstep(0.00, 0.080, d);
    float soft = 1.0 - smoothstep(0.04, 0.275, d);
    color += base_fx * core * power * (0.105 + 0.060 * pulse);
    color += base_fx * soft * power * 0.038;

    // Onda curta de entrada e checagem: discreta, sem explosão de tela.
    float velocidade = mix(0.38, 0.55, critical);
    float cycle = fract(t * velocidade + fase_check * 0.29);
    float ring_radius = mix(0.052, 0.245, cycle);
    float ring_width = mix(0.010, 0.020, cycle);
    float ring = 1.0 - smoothstep(ring_width, ring_width * 2.15, abs(d - ring_radius));
    ring *= 1.0 - smoothstep(0.48, 0.88, cycle);
    float ring_phase_mask = mix(0.80, 1.0, smoothstep(1.0, 2.0, phase));
    color += base_fx * ring * power * ring_phase_mask * (0.080 + critical * 0.045);

    // Pequenas marcas de checagem: neutras, só reforçam que a bola está ativa.
    float marks = 0.0;
    for (int i = 0; i < 3; i++) {
        float a = (float(i) / 3.0) * PI * 2.0 + t * 0.76;
        vec2 mark_pos = vec2(cos(a) / aspect, sin(a)) * 0.112;
        float md = length((ui_uv - centro - mark_pos) * vec2(aspect, 1.0));
        float active_mark = step(float(i), check_i + 0.001);
        marks += (1.0 - smoothstep(0.00, 0.018, md)) * mix(0.22, 0.78, active_mark);
    }
    vec3 check_color = mix(violeta, ciano, 0.58);
    color += check_color * marks * power * smoothstep(1.05, 2.10, phase) * 0.095;

    float critical_ring = 1.0 - smoothstep(0.008, 0.028, abs(d - 0.165));
    color += ouro * critical_ring * critical * power * (0.105 + 0.050 * pulse);

    // Saída/finalização neutra: fade suave, sem indicar sucesso ou falha.
    float saida = smoothstep(2.70, 4.00, phase);
    float final_glow = (1.0 - smoothstep(0.00, 0.30, d)) * (0.50 + 0.50 * sin(t * 8.5));
    color += mix(ciano, ouro, critical * 0.65) * final_glow * saida * power * 0.038;

    return clamp(color, 0.0, 1.0);
}
