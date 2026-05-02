vec3 cor_estado_batalha(float tipo) {
    if (tipo < 1.5) return vec3(0.58, 0.23, 0.78); // envenenado
    if (tipo < 2.5) return vec3(1.00, 0.38, 0.12); // queimado
    if (tipo < 3.5) return vec3(1.00, 0.82, 0.18); // energizado
    if (tipo < 4.5) return vec3(0.48, 0.12, 0.68); // intoxicado
    if (tipo < 5.5) return vec3(0.16, 0.48, 0.96); // encharcado
    return vec3(1.00, 0.93, 0.62);                 // abençoado
}

vec3 aplicar_estado_batalha_individual(vec3 color, vec2 screen_uv, float aspect, vec4 dados, float deslocamento_tempo) {
    float tipo = floor(dados.w + 0.01);
    float power = clamp((dados.w - tipo) * 10.0, 0.0, 1.0);
    if (tipo < 0.5 || power <= 0.001 || dados.z <= 0.001) {
        return color;
    }

    vec2 rel = screen_uv - dados.xy;
    rel.x *= aspect;
    float d = length(rel);
    float raio = max(0.001, dados.z);
    float t = u_time + deslocamento_tempo;
    vec3 cor = cor_estado_batalha(tipo);

    float corpo = 1.0 - smoothstep(raio * 0.10, raio * 0.95, d);
    float aura = 1.0 - smoothstep(raio * 0.58, raio * 1.72, d);
    float anel = 1.0 - smoothstep(0.006, 0.030, abs(d - raio * (1.02 + 0.035 * sin(t * 2.6))));
    float n = noise21(screen_uv * vec2(34.0, 25.0) + vec2(t * 0.23, -t * 0.17));

    if (tipo < 1.5) {
        // Envenenado: névoa roxa leve, sem cobrir o sprite.
        float fumaca = aura * smoothstep(0.38, 1.0, n);
        color = mix(color, color * vec3(0.94, 0.88, 1.02), aura * power * 0.10);
        color += cor * (fumaca * 0.095 + anel * 0.050) * power;
    } else if (tipo < 2.5) {
        // Queimado: calor local e pequenas brasas subindo.
        float heat = aura * smoothstep(0.34, 1.0, n);
        vec2 offset = vec2((n - 0.5) * 0.006 * power * aura, 0.0);
        color = mix(color, scene_sample(v_uv + offset), heat * 0.10 * power);
        color += cor * (corpo * 0.050 + heat * 0.115 + anel * 0.040) * power;
    } else if (tipo < 3.5) {
        // Energizado: pulso elétrico curto e controlado.
        float raio_pulso = raio * mix(0.55, 1.45, fract(t * 0.85));
        float pulso = 1.0 - smoothstep(0.005, 0.026, abs(d - raio_pulso));
        float faisca = step(0.965, n) * aura;
        color += cor * (pulso * 0.090 + faisca * 0.130 + corpo * 0.030) * power;
        color = mix(color, min(color * vec3(1.03, 1.025, 0.94), vec3(1.0)), aura * power * 0.055);
    } else if (tipo < 4.5) {
        // Intoxicado: veneno mais pesado, com bolhas discretas.
        float bolha = step(0.952, n) * aura;
        float camada = aura * smoothstep(0.20, 0.82, n);
        color = saturate_color(color, 1.0 - camada * power * 0.08);
        color += cor * (camada * 0.135 + bolha * 0.160 + anel * 0.055) * power;
    } else if (tipo < 5.5) {
        // Encharcado: brilho frio e gotículas descendo.
        float gota = step(0.962, noise21(screen_uv * vec2(42.0, 58.0) + vec2(0.0, t * 1.35))) * aura;
        color = mix(color, color * vec3(0.90, 0.96, 1.08), aura * power * 0.14);
        color += cor * (gota * 0.125 + anel * 0.038) * power;
    } else {
        // Abençoado: halo quente/branco, mais limpo do que chamativo.
        float halo = aura * (0.70 + 0.30 * sin(t * 2.0));
        float brilho = step(0.975, n) * aura;
        color = mix(color, min(color * 1.035 + vec3(0.012, 0.010, 0.004), vec3(1.0)), halo * power * 0.10);
        color += cor * (halo * 0.070 + brilho * 0.145 + anel * 0.040) * power;
    }

    return clamp(color, 0.0, 1.0);
}

vec3 aplicar_estados_batalha(vec3 color, vec2 screen_uv, float aspect) {
    color = aplicar_estado_batalha_individual(color, screen_uv, aspect, u_estado_batalha_0, 0.00);
    color = aplicar_estado_batalha_individual(color, screen_uv, aspect, u_estado_batalha_1, 0.23);
    color = aplicar_estado_batalha_individual(color, screen_uv, aspect, u_estado_batalha_2, 0.46);
    color = aplicar_estado_batalha_individual(color, screen_uv, aspect, u_estado_batalha_3, 0.69);
    color = aplicar_estado_batalha_individual(color, screen_uv, aspect, u_estado_batalha_4, 0.92);
    color = aplicar_estado_batalha_individual(color, screen_uv, aspect, u_estado_batalha_5, 1.15);
    color = aplicar_estado_batalha_individual(color, screen_uv, aspect, u_estado_batalha_6, 1.38);
    color = aplicar_estado_batalha_individual(color, screen_uv, aspect, u_estado_batalha_7, 1.61);
    color = aplicar_estado_batalha_individual(color, screen_uv, aspect, u_estado_batalha_8, 1.84);
    color = aplicar_estado_batalha_individual(color, screen_uv, aspect, u_estado_batalha_9, 2.07);
    color = aplicar_estado_batalha_individual(color, screen_uv, aspect, u_estado_batalha_10, 2.30);
    color = aplicar_estado_batalha_individual(color, screen_uv, aspect, u_estado_batalha_11, 2.53);
    return color;
}
