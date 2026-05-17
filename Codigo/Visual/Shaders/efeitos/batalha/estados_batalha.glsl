// Shaders localizados para estados que mudam a cor/visual do Pokemon.
// Entrada por alvo: vec4(x_uv, y_uv, raio_uv, codigo + intensidade * 0.1).
// Codigos: 1 envenenado, 2 queimado/cauterizado, 3 energizado,
// 4 intoxicado, 5 encharcado, 6 abencoado, 7 congelado,
// 8 amaldicoado, 9 encantado.

vec3 cor_estado_batalha(float tipo) {
    if (tipo < 1.5) return vec3(0.62, 0.22, 0.82); // envenenado
    if (tipo < 2.5) return vec3(1.00, 0.36, 0.10); // queimado/cauterizado
    if (tipo < 3.5) return vec3(1.00, 0.86, 0.20); // energizado
    if (tipo < 4.5) return vec3(0.56, 0.10, 0.72); // intoxicado
    if (tipo < 5.5) return vec3(0.14, 0.50, 1.00); // encharcado
    if (tipo < 6.5) return vec3(1.00, 0.94, 0.55); // abencoado
    if (tipo < 7.5) return vec3(0.62, 0.90, 1.00); // congelado
    if (tipo < 8.5) return vec3(0.20, 0.06, 0.34); // amaldicoado
    return vec3(1.00, 0.36, 0.78);                 // encantado
}

float estado_faixa_vertical(vec2 local, float tempo, float escala, float velocidade) {
    float linha = sin((local.x * escala + tempo * velocidade) * 6.2831853);
    return smoothstep(0.72, 0.98, linha);
}

float estado_faisca(vec2 p, float tempo, float densidade) {
    vec2 cel = floor(p * densidade);
    float h = hash21(cel);
    float pulso = smoothstep(0.70, 1.0, sin(tempo * (8.0 + h * 8.0) + h * 22.0) * 0.5 + 0.5);
    return step(0.84, h) * pulso;
}

float estado_bolha(vec2 p, float tempo, float densidade) {
    vec2 cel = floor(p * densidade);
    vec2 local = fract(p * densidade) - 0.5;
    float h = hash21(cel + vec2(tempo * 0.07, -tempo * 0.03));
    float r = 0.08 + 0.22 * h;
    float d = length(local + vec2(sin(tempo + h * 17.0), cos(tempo * 0.7 + h * 11.0)) * 0.08);
    return (1.0 - smoothstep(r, r + 0.030, d)) * step(0.70, h);
}

float estado_cristal(vec2 local, float tempo) {
    vec2 p = local * vec2(13.0, 9.0);
    float linhas = 0.0;
    linhas += 1.0 - smoothstep(0.010, 0.055, abs(fract(p.x + p.y * 0.42) - 0.5));
    linhas += 1.0 - smoothstep(0.010, 0.050, abs(fract(p.x * 0.55 - p.y * 0.82 + 0.17) - 0.5));
    return clamp(linhas * (0.22 + 0.10 * sin(tempo * 1.3)), 0.0, 1.0);
}

float estado_raio_jagged(vec2 local, float tempo, float seed) {
    float x = local.x + sin(local.y * 18.0 + tempo * 10.0 + seed) * 0.025;
    float alvo = (noise21(vec2(floor((local.y + 1.0) * 12.0), seed)) - 0.5) * 0.52;
    float zig = abs(x - alvo);
    float corpo = 1.0 - smoothstep(0.012, 0.036, zig);
    float corte = smoothstep(-0.82, -0.18, local.y) * (1.0 - smoothstep(0.20, 0.85, local.y));
    return corpo * corte;
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
    vec2 local = rel / raio;

    float dist_norm = d / raio;
    float corpo = 1.0 - smoothstep(0.12, 0.92, dist_norm);
    float aura = 1.0 - smoothstep(0.70, 1.82, dist_norm);
    float borda = 1.0 - smoothstep(0.018, 0.095, abs(dist_norm - (1.02 + 0.040 * sin(t * 2.2))));
    float n = fbm(screen_uv * vec2(32.0, 24.0) + vec2(t * 0.16, -t * 0.21));
    float n2 = noise21(screen_uv * vec2(68.0, 53.0) + vec2(t * 0.37, t * 0.19));

    if (tipo < 1.5) {
        // Envenenado: fumaça roxa subindo, sem virar uma bolha gigante.
        float fumaca = aura * smoothstep(0.38, 0.86, fbm(local * vec2(2.8, 3.6) + vec2(t * 0.10, -t * 0.42)));
        float vapor = estado_faixa_vertical(local + vec2(n * 0.13, 0.0), t, 1.8, 0.36) * aura;
        color = mix(color, saturate_color(color, 0.86) * vec3(0.94, 0.88, 1.02), corpo * power * 0.18);
        color += cor * (fumaca * 0.135 + vapor * 0.045 + borda * 0.050) * power;
    } else if (tipo < 2.5) {
        // Queimado/cauterizado: calor, distorção e brasas subindo.
        float heat = aura * smoothstep(0.32, 0.90, n);
        vec2 offset = vec2((n2 - 0.5) * 0.010 * power * aura, (n - 0.5) * 0.004 * power * aura);
        vec3 distorcido = scene_sample(screen_uv + offset);
        float brasa = estado_faisca(local + vec2(0.0, -t * 0.18), t, 8.0) * aura;
        float chamas = smoothstep(0.30, 0.96, sin(local.y * 4.8 - t * 2.4 + n * 2.2)) * (1.0 - smoothstep(-0.35, 0.95, local.y)) * aura;
        color = mix(color, distorcido, heat * 0.16 * power);
        color = mix(color, color * vec3(1.10, 0.92, 0.78), corpo * power * 0.12);
        color += cor * (heat * 0.12 + chamas * 0.12 + brasa * 0.22 + borda * 0.035) * power;
    } else if (tipo < 3.5) {
        // Energizado: arcos eletricos e pulsos curtos.
        float fase = fract(t * 0.90);
        float pulso = 1.0 - smoothstep(0.018, 0.070, abs(dist_norm - mix(0.28, 1.55, fase)));
        float raio_a = estado_raio_jagged(local + vec2(0.18, 0.0), t, 2.7);
        float raio_b = estado_raio_jagged(vec2(-local.x, local.y) + vec2(0.12, 0.0), t + 0.32, 8.1);
        float faisca = estado_faisca(local + vec2(t * 0.02), t, 10.0) * aura;
        color = mix(color, min(color * vec3(1.06, 1.05, 0.86), vec3(1.0)), aura * power * 0.10);
        color += cor * (pulso * 0.115 + max(raio_a, raio_b) * 0.22 + faisca * 0.16) * power;
    } else if (tipo < 4.5) {
        // Intoxicado: veneno mais denso, bolhas e saturação roxa.
        float lama = aura * smoothstep(0.22, 0.78, fbm(local * 3.4 + vec2(t * 0.09, -t * 0.18)));
        float bolhas = estado_bolha(local + vec2(0.0, -t * 0.13), t, 6.5) * aura;
        color = saturate_color(color, 1.0 - lama * power * 0.18);
        color = mix(color, color * vec3(0.88, 0.78, 1.02), corpo * power * 0.22);
        color += cor * (lama * 0.18 + bolhas * 0.26 + borda * 0.060) * power;
    } else if (tipo < 5.5) {
        // Encharcado: goticulas descendo, brilho frio e pequenas ondas.
        float gotas = estado_faixa_vertical(local + vec2(n * 0.10, -t * 0.34), t, 2.9, 0.48) * aura;
        float gota_ponto = estado_faisca(vec2(local.x, local.y - t * 0.20), t, 13.0) * aura;
        float ondas = (1.0 - smoothstep(0.010, 0.052, abs(sin(dist_norm * 18.0 - t * 3.4)) * 0.055)) * aura;
        color = mix(color, color * vec3(0.86, 0.96, 1.12), aura * power * 0.19);
        color += cor * (gotas * 0.105 + gota_ponto * 0.14 + ondas * 0.030 + borda * 0.038) * power;
    } else if (tipo < 6.5) {
        // Abençoado: halo limpo, quente e brilhante.
        float halo = aura * (0.68 + 0.32 * sin(t * 2.0));
        float brilho = estado_faisca(local + vec2(t * 0.025, -t * 0.035), t, 10.0) * aura;
        float anel = 1.0 - smoothstep(0.018, 0.060, abs(dist_norm - (1.20 + 0.06 * sin(t * 1.6))));
        color = mix(color, min(color * 1.075 + vec3(0.018, 0.015, 0.004), vec3(1.0)), halo * power * 0.14);
        color += cor * (halo * 0.070 + brilho * 0.24 + anel * 0.050) * power;
    } else if (tipo < 7.5) {
        // Congelado: camada fria, geada e rachaduras/cristais discretos.
        float gelo = aura * smoothstep(0.26, 0.72, n);
        float cristal = estado_cristal(local, t) * corpo;
        float geada = smoothstep(0.50, 1.0, abs(local.x) + abs(local.y)) * aura;
        color = mix(color, vec3(0.64, 0.86, 1.0), (gelo * 0.20 + geada * 0.10) * power);
        color = mix(color, saturate_color(color, 0.78), corpo * power * 0.10);
        color += cor * (cristal * 0.18 + borda * 0.060) * power;
    } else if (tipo < 8.5) {
        // Amaldiçoado: sombra roxa/negra e vinheta local.
        float sombra = aura * smoothstep(0.30, 0.88, fbm(local * vec2(3.1, 3.9) + vec2(-t * 0.08, -t * 0.24)));
        float rasgo = estado_faixa_vertical(vec2(local.x + n * 0.25, local.y), t, 2.2, -0.25) * aura;
        color = mix(color, color * vec3(0.56, 0.48, 0.70), (corpo * 0.22 + sombra * 0.25) * power);
        color += cor * (sombra * 0.10 + rasgo * 0.075 + borda * 0.055) * power;
    } else {
        // Encantado: brilho rosa, particulas suaves e leitura magica.
        float brilho = estado_faisca(local + vec2(sin(t) * 0.02, -t * 0.04), t, 9.0) * aura;
        float aura_rosa = aura * (0.55 + 0.45 * sin(t * 2.4 + n * 2.0));
        color = mix(color, color * vec3(1.08, 0.90, 1.08), corpo * power * 0.14);
        color += cor * (aura_rosa * 0.070 + brilho * 0.24 + borda * 0.035) * power;
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
