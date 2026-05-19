// Efeitos de area da arena, separados dos estados formais dos Pokemon.
// Entrada: vec4(x_uv, y_uv, raio_uv, codigo + power * 0.1).

vec3 cor_area_batalha(float tipo) {
    if (tipo < 1.5) return vec3(0.18, 0.15, 0.12); // destruido
    if (tipo < 2.5) return vec3(1.00, 0.30, 0.08); // queimado
    if (tipo < 3.5) return vec3(0.56, 0.18, 0.76); // envenenado
    if (tipo < 4.5) return vec3(0.58, 0.88, 1.00); // congelado
    if (tipo < 5.5) return vec3(1.00, 0.90, 0.22); // eletrificado
    if (tipo < 6.5) return vec3(0.18, 0.55, 1.00); // encharcado
    if (tipo < 7.5) return vec3(0.18, 0.06, 0.30); // amaldicoado
    return vec3(1.00, 0.90, 0.48);                 // abencoado
}

float area_disc(vec2 rel, float raio) {
    float d = length(rel);
    return 1.0 - smoothstep(raio * 0.20, raio, d);
}

float area_ring(float dist_norm, float fase) {
    return 1.0 - smoothstep(0.018, 0.075, abs(dist_norm - fase));
}

float area_linha_ruido(vec2 local, float seed, float densidade) {
    vec2 p = local * densidade;
    float a = abs(fract(p.x + p.y * (0.34 + seed * 0.42)) - 0.5);
    float b = abs(fract(p.x * (0.52 + seed * 0.25) - p.y * 0.78 + seed) - 0.5);
    return max(1.0 - smoothstep(0.010, 0.046, a), 1.0 - smoothstep(0.012, 0.052, b));
}

float area_faisca(vec2 local, float tempo, float densidade) {
    vec2 cel = floor((local + vec2(1.0)) * densidade);
    float h = hash21(cel);
    float pulso = smoothstep(0.64, 1.0, sin(tempo * (8.0 + h * 10.0) + h * 18.0) * 0.5 + 0.5);
    return step(0.82, h) * pulso;
}

float area_bolha(vec2 local, float tempo, float densidade) {
    vec2 cel = floor((local + vec2(1.0)) * densidade);
    vec2 p = fract((local + vec2(1.0)) * densidade) - 0.5;
    float h = hash21(cel);
    float r = 0.08 + h * 0.16;
    float d = length(p + vec2(sin(tempo + h * 17.0), cos(tempo * 0.7 + h * 11.0)) * 0.06);
    return (1.0 - smoothstep(r, r + 0.035, d)) * step(0.72, h);
}

float area_arco_eletrico(vec2 local, float tempo, float seed) {
    float alvo = (noise21(vec2(floor((local.y + 1.0) * 10.0), seed + floor(tempo * 8.0))) - 0.5) * 0.60;
    float x = local.x + sin(local.y * 18.0 + tempo * 12.0 + seed) * 0.035;
    float corpo = 1.0 - smoothstep(0.018, 0.060, abs(x - alvo));
    float corte = smoothstep(-0.92, -0.25, local.y) * (1.0 - smoothstep(0.20, 0.92, local.y));
    return corpo * corte;
}

vec3 aplicar_area_batalha_individual(vec3 color, vec2 screen_uv, float aspect, vec4 dados, float offset_tempo) {
    float tipo = floor(dados.w + 0.01);
    float power = clamp((dados.w - tipo) * 10.0, 0.0, 1.0);
    if (tipo < 0.5 || power <= 0.001 || dados.z <= 0.001) {
        return color;
    }

    vec2 rel = screen_uv - dados.xy;
    rel.x *= aspect;
    float raio = max(0.001, dados.z);
    float d = length(rel);
    float dist_norm = d / raio;
    if (dist_norm > 2.10) {
        return color;
    }

    float t = u_time + offset_tempo;
    vec2 local = rel / raio;
    vec3 cor = cor_area_batalha(tipo);
    float corpo = 1.0 - smoothstep(0.18, 1.00, dist_norm);
    float aura = 1.0 - smoothstep(0.72, 1.85, dist_norm);
    float n = fbm(local * 2.4 + vec2(t * 0.08, -t * 0.10));
    float n2 = noise21(screen_uv * vec2(76.0, 52.0) + vec2(t * 0.35, -t * 0.22));

    if (tipo < 1.5) {
        float rachadura = area_linha_ruido(local, dados.x + dados.y, 4.8) * corpo;
        float sujeira = smoothstep(0.25, 0.88, n) * aura;
        color = mix(color, color * vec3(0.55, 0.52, 0.48), (corpo * 0.28 + sujeira * 0.18) * power);
        color += vec3(0.02, 0.018, 0.014) * rachadura * 0.36 * power;
    } else if (tipo < 2.5) {
        float calor = smoothstep(0.34, 0.92, n) * aura;
        vec2 offset = vec2((n2 - 0.5) * 0.008, sin(t * 3.0 + n2) * 0.003) * calor * power;
        vec3 distorcido = scene_sample(screen_uv + offset);
        float brasas = area_faisca(local, t, 7.5) * aura;
        color = mix(color, distorcido, calor * 0.15 * power);
        color = mix(color, color * vec3(1.08, 0.90, 0.74), corpo * 0.15 * power);
        color += cor * (calor * 0.11 + brasas * 0.26) * power;
    } else if (tipo < 3.5) {
        float veneno = smoothstep(0.28, 0.82, fbm(local * vec2(3.4, 2.6) + vec2(t * 0.08, -t * 0.20))) * aura;
        float bolhas = area_bolha(local + vec2(0.0, -t * 0.10), t, 5.2) * aura;
        color = mix(color, color * vec3(0.88, 0.78, 1.03), corpo * 0.20 * power);
        color += cor * (veneno * 0.14 + bolhas * 0.22) * power;
    } else if (tipo < 4.5) {
        float gelo = smoothstep(0.24, 0.76, n) * aura;
        float cristal = area_linha_ruido(local, 0.41, 5.7) * corpo;
        color = mix(color, vec3(0.62, 0.84, 1.0), (gelo * 0.19 + corpo * 0.08) * power);
        color += cor * cristal * 0.18 * power;
    } else if (tipo < 5.5) {
        float arco_a = area_arco_eletrico(local + vec2(0.20, 0.0), t, 2.3);
        float arco_b = area_arco_eletrico(vec2(-local.x, local.y) + vec2(0.12, 0.0), t + 0.31, 8.7);
        float pulso = area_ring(dist_norm, mix(0.25, 1.55, fract(t * 0.90))) * aura;
        color += vec3(1.0, 0.92, 0.35) * max(arco_a, arco_b) * 0.26 * power;
        color += cor * pulso * 0.10 * power;
    } else if (tipo < 6.5) {
        float ondas = area_ring(dist_norm, 0.42 + fract(t * 0.42) * 0.65) * aura;
        color = mix(color, color * vec3(0.88, 0.97, 1.11), corpo * 0.15 * power);
        color += cor * ondas * 0.060 * power;
    } else if (tipo < 7.5) {
        float sombra = smoothstep(0.28, 0.84, fbm(local * 2.9 + vec2(-t * 0.08, -t * 0.18))) * aura;
        color = mix(color, color * vec3(0.58, 0.50, 0.70), (corpo * 0.24 + sombra * 0.18) * power);
        color += cor * sombra * 0.09 * power;
    } else {
        float brilho = area_faisca(local + vec2(t * 0.018, -t * 0.028), t, 8.4) * aura;
        float halo = aura * (0.55 + 0.45 * sin(t * 2.2 + n));
        color = mix(color, min(color * 1.06 + vec3(0.018, 0.014, 0.004), vec3(1.0)), halo * 0.12 * power);
        color += cor * (brilho * 0.24 + halo * 0.055) * power;
    }

    return clamp(color, 0.0, 1.0);
}

vec3 aplicar_areas_batalha(vec3 color, vec2 screen_uv, float aspect) {
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_0, 0.00);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_1, 0.17);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_2, 0.34);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_3, 0.51);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_4, 0.68);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_5, 0.85);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_6, 1.02);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_7, 1.19);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_8, 1.36);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_9, 1.53);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_10, 1.70);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_11, 1.87);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_12, 2.04);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_13, 2.21);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_14, 2.38);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_15, 2.55);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_16, 2.72);
    color = aplicar_area_batalha_individual(color, screen_uv, aspect, u_area_batalha_17, 2.89);
    return color;
}
