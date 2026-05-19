vec2 attack_aspect(vec2 p, float aspect) {
    p.x *= aspect;
    return p;
}

vec3 attack_type_color(float tipo) {
    if (tipo < 1.5) return vec3(0.78, 0.76, 0.68);
    if (tipo < 2.5) return vec3(1.00, 0.34, 0.12);
    if (tipo < 3.5) return vec3(0.16, 0.54, 1.00);
    if (tipo < 4.5) return vec3(0.25, 0.80, 0.32);
    if (tipo < 5.5) return vec3(1.00, 0.88, 0.22);
    if (tipo < 6.5) return vec3(0.62, 0.90, 1.00);
    if (tipo < 7.5) return vec3(0.88, 0.36, 0.24);
    if (tipo < 8.5) return vec3(0.62, 0.22, 0.82);
    if (tipo < 9.5) return vec3(0.70, 0.48, 0.24);
    if (tipo < 10.5) return vec3(0.62, 0.82, 1.00);
    if (tipo < 11.5) return vec3(0.92, 0.36, 1.00);
    if (tipo < 12.5) return vec3(0.56, 0.78, 0.24);
    if (tipo < 13.5) return vec3(0.72, 0.62, 0.44);
    if (tipo < 14.5) return vec3(0.42, 0.28, 0.70);
    if (tipo < 15.5) return vec3(0.42, 0.48, 1.00);
    if (tipo < 16.5) return vec3(0.22, 0.18, 0.30);
    if (tipo < 17.5) return vec3(0.62, 0.70, 0.76);
    if (tipo < 18.5) return vec3(1.00, 0.48, 0.78);
    if (tipo < 19.5) return vec3(0.46, 0.74, 1.00);
    return vec3(0.78, 0.62, 1.00);
}

float attack_segment_info(vec2 uv, vec2 a, vec2 b, float aspect, out float t) {
    vec2 p = attack_aspect(uv, aspect);
    vec2 pa = attack_aspect(a, aspect);
    vec2 pb = attack_aspect(b, aspect);
    vec2 ab = pb - pa;
    float l2 = max(dot(ab, ab), 0.00001);
    t = clamp(dot(p - pa, ab) / l2, 0.0, 1.0);
    return length(p - (pa + ab * t));
}

float attack_ring(vec2 uv, vec2 centro, float aspect, float raio, float espessura) {
    vec2 rel = attack_aspect(uv - centro, aspect);
    return 1.0 - smoothstep(espessura, espessura * 2.2, abs(length(rel) - raio));
}

float attack_disc(vec2 uv, vec2 centro, float aspect, float raio) {
    vec2 rel = attack_aspect(uv - centro, aspect);
    return 1.0 - smoothstep(raio * 0.30, raio, length(rel));
}

float attack_jagged_line(vec2 uv, vec2 a, vec2 b, float aspect, float fase, float seed, float largura, out float t) {
    float dist = attack_segment_info(uv, a, b, aspect, t);
    float jag = (noise21(vec2(floor(t * 18.0 + seed * 9.0), seed * 31.0 + floor(u_time * 18.0))) - 0.5) * largura * 3.4;
    float pulse = smoothstep(fase - 0.24, fase + 0.12, t) * (1.0 - smoothstep(fase + 0.12, fase + 0.48, t));
    return (1.0 - smoothstep(largura * 0.30, largura * 1.45, abs(dist + jag))) * pulse;
}

vec3 aplicar_tipo_ataque(vec3 color, vec2 uv, vec2 a, vec2 b, float aspect, float tipo, float power, float raio, float seed, vec3 cor) {
    float t_seg = 0.0;
    float dist = attack_segment_info(uv, a, b, aspect, t_seg);
    float linha = 1.0 - smoothstep(raio * 0.18, raio * 1.25, dist);
    vec2 rel_alvo = attack_aspect(uv - b, aspect);
    float d_alvo = length(rel_alvo);
    float local = 1.0 - smoothstep(raio * 0.35, raio * 2.0, d_alvo);
    float n = noise21(uv * vec2(72.0, 54.0) + vec2(seed * 17.0, u_time * 0.55));

    if (tipo > 1.5 && tipo < 2.5) {
        float heat = linha * smoothstep(0.35, 0.95, n);
        color = mix(color, scene_sample(uv + vec2((n - 0.5) * 0.010, sin(u_time * 4.0 + n) * 0.004) * heat * power), heat * 0.18 * power);
        color += cor * heat * 0.10 * power;
    } else if (tipo > 2.5 && tipo < 3.5) {
        float onda = sin(d_alvo * 86.0 - u_time * 7.0 + seed) * 0.5 + 0.5;
        color = mix(color, scene_sample(uv + normalize(rel_alvo + vec2(0.0001)) * 0.006 * local * power), local * 0.16 * power);
        color += cor * linha * onda * 0.045 * power;
    } else if (tipo > 4.5 && tipo < 5.5) {
        float arco_t = 0.0;
        float arco = attack_jagged_line(uv, a, b, aspect, fract(u_time * 0.95 + seed), seed, raio * 0.20, arco_t);
        color += vec3(1.0, 0.92, 0.42) * arco * 0.22 * power;
    } else if (tipo > 5.5 && tipo < 6.5) {
        float cristal = smoothstep(0.86, 1.0, sin((uv.x + uv.y) * 95.0 + seed * 11.0));
        color = mix(color, vec3(0.68, 0.90, 1.0), linha * cristal * 0.10 * power);
        color += cor * linha * cristal * 0.06 * power;
    } else if (tipo > 7.5 && tipo < 8.5) {
        float bolha = step(0.78, n) * local * (0.6 + 0.4 * sin(u_time * 5.0 + n * 12.0));
        color = mix(color, color * vec3(0.92, 0.82, 1.04), local * 0.16 * power);
        color += cor * bolha * 0.12 * power;
    } else if (tipo > 10.5 && tipo < 11.5) {
        color = mix(color, scene_sample(uv + normalize(rel_alvo + vec2(0.0001)) * sin(d_alvo * 42.0 - u_time * 5.0) * 0.004 * local * power), local * 0.18 * power);
        color += cor * attack_ring(uv, b, aspect, raio * 1.35, raio * 0.10) * 0.08 * power;
    } else if (tipo > 12.5 && tipo < 13.5 || tipo > 8.5 && tipo < 9.5) {
        float poeira = smoothstep(0.45, 0.95, fbm((uv - b) * 18.0 + vec2(seed, -u_time * 0.8))) * local;
        color = mix(color, color * vec3(1.06, 0.96, 0.82), poeira * 0.12 * power);
    } else if (tipo > 15.5 && tipo < 16.5) {
        color = mix(color, color * vec3(0.62, 0.58, 0.74), local * 0.28 * power);
        color += cor * attack_ring(uv, b, aspect, raio * 1.15, raio * 0.14) * 0.06 * power;
    } else if (tipo > 18.5 && tipo < 19.5) {
        float estrela = step(0.985, hash21(floor((uv + seed) * vec2(80.0, 54.0)))) * local;
        color += vec3(0.74, 0.88, 1.0) * estrela * 0.55 * power;
        color = mix(color, scene_sample(uv + normalize(rel_alvo + vec2(0.0001)) * 0.004 * local * power), local * 0.12 * power);
    } else if (tipo > 19.5 && tipo < 20.5) {
        float ondas = attack_ring(uv, b, aspect, raio * (0.7 + fract(u_time * 1.8 + seed) * 1.6), raio * 0.08);
        color += cor * ondas * 0.11 * power;
    }

    return color;
}

vec3 aplicar_ataque_batalha_individual(vec3 color, vec2 screen_uv, float aspect, vec4 pos, vec4 data, vec4 extra, vec4 cor_data) {
    float modelo = floor(data.x + 0.01);
    float tipo = floor(data.y + 0.01);
    float fase = clamp(data.z, 0.0, 1.0);
    float power = clamp(data.w, 0.0, 1.0);
    if (modelo < 0.5 || power <= 0.001) {
        return color;
    }

    vec2 origem = pos.xy;
    vec2 alvo = pos.zw;
    float raio = max(0.006, extra.x);
    float largura = max(0.20, extra.y);
    float seed = extra.z;
    float impacto = clamp(extra.w, 0.0, 1.0);
    vec3 cor = mix(attack_type_color(tipo), clamp(cor_data.rgb, 0.0, 1.0), step(0.5, cor_data.a));

    float t = 0.0;
    float dist_linha = attack_segment_info(screen_uv, origem, alvo, aspect, t);
    vec2 ponto_fase = mix(origem, alvo, fase);
    float d_fase = length(attack_aspect(screen_uv - ponto_fase, aspect));
    float d_alvo = length(attack_aspect(screen_uv - alvo, aspect));
    float r = raio * largura;
    float brilho = 0.0;
    float mascara = 0.0;

    if (modelo < 1.5) {
        float trilha = (1.0 - smoothstep(r * 0.28, r * 1.12, dist_linha));
        trilha *= smoothstep(fase - 0.38, fase - 0.03, t) * (1.0 - smoothstep(fase + 0.02, fase + 0.25, t));
        float nucleo = 1.0 - smoothstep(r * 0.15, r * 0.78, d_fase);
        float pulso = attack_ring(screen_uv, alvo, aspect, raio * (0.50 + impacto * 1.10), raio * 0.12) * impacto;
        brilho = trilha * 0.38 + nucleo * 0.42 + pulso * 0.32;
        mascara = max(trilha, max(nucleo, pulso));
    } else if (modelo < 2.5) {
        float abre = 0.65 + 0.35 * sin(fase * 3.14159);
        float nucleo = 1.0 - smoothstep(r * 0.12 * abre, r * 0.34 * abre, dist_linha);
        float glow = 1.0 - smoothstep(r * 0.28, r * 1.65, dist_linha);
        brilho = nucleo * 0.55 + glow * 0.22;
        mascara = glow;
    } else if (modelo < 3.5) {
        float arco = attack_jagged_line(screen_uv, origem, alvo, aspect, fase, seed, r * 0.18, t);
        float flash = (1.0 - smoothstep(r * 0.12, r * 1.0, dist_linha)) * (0.45 + 0.55 * sin(u_time * 38.0 + seed * 17.0));
        brilho = arco * 0.62 + flash * 0.18;
        mascara = max(arco, flash * 0.45);
    } else if (modelo < 4.5) {
        float fluxo = 1.0 - smoothstep(r * 0.40, r * 1.95, dist_linha);
        float ruido = smoothstep(0.34, 0.92, fbm(vec2(t * 8.0 - u_time * 2.0, dist_linha * 38.0 + seed)));
        float ponta = smoothstep(fase - 0.25, fase + 0.05, t) * (1.0 - smoothstep(fase + 0.18, fase + 0.42, t));
        color = mix(color, scene_sample(screen_uv + vec2(0.0, (ruido - 0.5) * 0.006) * fluxo * power), fluxo * 0.14 * power);
        brilho = fluxo * (0.12 + ruido * 0.18) + ponta * fluxo * 0.16;
        mascara = fluxo;
    } else if (modelo < 5.5) {
        float onda = attack_ring(screen_uv, alvo, aspect, raio * mix(0.25, 2.35, fase), raio * (0.10 + 0.10 * largura));
        float centro = attack_disc(screen_uv, alvo, aspect, raio * (0.60 + impacto * 0.45));
        color = mix(color, scene_sample(screen_uv + normalize(attack_aspect(screen_uv - alvo, aspect) + vec2(0.0001)) * 0.006 * onda * power), onda * 0.16 * power);
        brilho = onda * 0.42 + centro * (0.15 + impacto * 0.30);
        mascara = max(onda, centro);
    } else if (modelo < 6.5) {
        float anel = attack_ring(screen_uv, alvo, aspect, raio * (0.55 + impacto * 1.2), raio * 0.13);
        float flash = attack_disc(screen_uv, alvo, aspect, raio * 0.95) * impacto;
        color = mix(color, scene_sample(screen_uv + normalize(attack_aspect(screen_uv - alvo, aspect) + vec2(0.0001)) * 0.004 * flash * power), flash * 0.18 * power);
        brilho = anel * 0.34 + flash * 0.28;
        mascara = max(anel, flash);
    } else {
        float aura = attack_disc(screen_uv, alvo, aspect, raio * 1.45);
        float borda = attack_ring(screen_uv, alvo, aspect, raio * (0.85 + 0.08 * sin(u_time * 2.0 + seed)), raio * 0.15);
        float pulso = 0.72 + 0.28 * sin(u_time * 4.2 + seed * 19.0);
        brilho = aura * 0.15 * pulso + borda * 0.18;
        mascara = max(aura * 0.55, borda);
    }

    color = aplicar_tipo_ataque(color, screen_uv, origem, alvo, aspect, tipo, power * mascara, raio, seed, cor);
    color = mix(color, min(color + cor * brilho * power, vec3(1.0)), clamp(mascara * power * 0.34, 0.0, 0.55));
    color += cor * brilho * power * 0.34;
    return clamp(color, 0.0, 1.0);
}

vec3 aplicar_ataques_batalha(vec3 color, vec2 screen_uv, float aspect) {
    color = aplicar_ataque_batalha_individual(color, screen_uv, aspect, u_attack_fx_0_pos, u_attack_fx_0_data, u_attack_fx_0_extra, u_attack_fx_0_color);
    color = aplicar_ataque_batalha_individual(color, screen_uv, aspect, u_attack_fx_1_pos, u_attack_fx_1_data, u_attack_fx_1_extra, u_attack_fx_1_color);
    color = aplicar_ataque_batalha_individual(color, screen_uv, aspect, u_attack_fx_2_pos, u_attack_fx_2_data, u_attack_fx_2_extra, u_attack_fx_2_color);
    color = aplicar_ataque_batalha_individual(color, screen_uv, aspect, u_attack_fx_3_pos, u_attack_fx_3_data, u_attack_fx_3_extra, u_attack_fx_3_color);
    color = aplicar_ataque_batalha_individual(color, screen_uv, aspect, u_attack_fx_4_pos, u_attack_fx_4_data, u_attack_fx_4_extra, u_attack_fx_4_color);
    color = aplicar_ataque_batalha_individual(color, screen_uv, aspect, u_attack_fx_5_pos, u_attack_fx_5_data, u_attack_fx_5_extra, u_attack_fx_5_color);
    color = aplicar_ataque_batalha_individual(color, screen_uv, aspect, u_attack_fx_6_pos, u_attack_fx_6_data, u_attack_fx_6_extra, u_attack_fx_6_color);
    color = aplicar_ataque_batalha_individual(color, screen_uv, aspect, u_attack_fx_7_pos, u_attack_fx_7_data, u_attack_fx_7_extra, u_attack_fx_7_color);
    return color;
}
