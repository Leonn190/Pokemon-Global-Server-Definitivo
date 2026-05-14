vec3 aplicar_menu_logo(vec3 scene_color, vec4 hud, vec2 screen_uv) {
    float power = clamp(u_menu_logo_power, 0.0, 1.0);
    if (power <= 0.001 || u_menu_logo_rect.z <= 1.0 || u_menu_logo_rect.w <= 1.0) {
        return mix(scene_color, hud.rgb, hud.a);
    }

    float aspect = u_resolution.x / u_resolution.y;
    vec2 ui_uv = v_uv; // v_uv ja esta no mesmo sistema top-left do Pygame.
    vec2 rect_pos = u_menu_logo_rect.xy / u_resolution;
    vec2 rect_size = u_menu_logo_rect.zw / u_resolution;
    vec2 logo_center = rect_pos + rect_size * 0.5;

    vec2 rel = ui_uv - logo_center;
    rel.x *= aspect;
    vec2 logo_radius = vec2(max(rect_size.x * aspect * 0.58, 0.001), max(rect_size.y * 0.58, 0.001));
    vec2 local = clamp((ui_uv - rect_pos) / max(rect_size, vec2(0.0001)), vec2(0.0), vec2(1.0));

    vec3 blue = vec3(0.05, 0.45, 0.95);
    vec3 cyan = vec3(0.04, 0.85, 1.00);
    vec3 red = vec3(1.00, 0.12, 0.12);
    vec3 magenta = vec3(0.95, 0.14, 0.56);
    vec3 violet = vec3(0.48, 0.22, 1.00);
    vec3 side_color = mix(blue, red, smoothstep(0.32, 0.72, local.x));
    side_color = mix(side_color, violet, 0.20 * (1.0 - abs(local.x - 0.5) * 2.0));

    vec3 color = scene_color;

    // Fumaca/aurora atras da logo. Escura e atmosferica, sem estourar branco.
    float ellipse_d = length(rel / logo_radius);
    float outer = 1.0 - smoothstep(1.36, 2.18, ellipse_d);
    float inner_cut = smoothstep(0.55, 1.02, ellipse_d);
    float smoke_mask = outer * inner_cut;
    float smoke_noise = fbm(vec2(rel.x * 5.4 + u_time * 0.050, rel.y * 7.4 - u_time * 0.075));
    float smoke = smoke_mask * smoothstep(0.26, 0.92, smoke_noise);
    float smoke_pulse = 0.74 + 0.26 * sin(u_time * 1.15 + local.x * 2.2);
    color += side_color * smoke * smoke_pulse * 0.135 * power;

    // Bloom pela alpha real da logo, mas com intensidade baixa.
    float near_alpha = hud_alpha_blur(v_uv, 7.0);
    float mid_alpha = hud_alpha_blur(v_uv, 18.0);
    float far_alpha = hud_alpha_blur(v_uv, 36.0);
    float outside_logo = 1.0 - smoothstep(0.05, 0.38, hud.a);
    float bloom = (near_alpha * 0.50 + mid_alpha * 0.32 + far_alpha * 0.18) * outside_logo;
    color += side_color * bloom * 0.46 * power;

    // Aro suave de luz no contorno do globo, com vermelho/azul dos lados.
    float rim = 1.0 - smoothstep(0.010, 0.044, abs(ellipse_d - 1.0));
    rim *= smoothstep(0.18, 1.0, rect_size.y);
    rim *= 0.34 + 0.18 * sin(u_time * 1.7 + local.x * 6.0);
    color += side_color * rim * 0.12 * power;

    // Orbitas limpas e discretas. Elas ficam atras da logo porque a logo e aplicada no final.
    float o1 = ellipse_orbit(rel, logo_radius * vec2(1.36, 0.70), -0.16, 0.010, u_time * 0.70);
    float o2 = ellipse_orbit(rel, logo_radius * vec2(1.20, 0.55), 0.18, 0.009, -u_time * 0.58 + 1.7);
    float orbit_fade = (1.0 - smoothstep(2.20, 2.95, ellipse_d)) * smoothstep(0.62, 1.08, ellipse_d);
    color += mix(cyan, magenta, smoothstep(0.38, 0.68, local.x)) * o1 * orbit_fade * 0.145 * power;
    color += vec3(1.00, 0.78, 0.24) * o2 * orbit_fade * 0.055 * power;

    // Particulas raras ao redor, pequenas, para nao virar sujeira visual.
    vec2 particle_uv = rel / logo_radius;
    particle_uv.x *= 1.10;
    vec2 grid = particle_uv * 13.0;
    vec2 cell = floor(grid);
    vec2 gv = fract(grid) - 0.5;
    float rnd = hash21(cell + 19.0);
    float particle_zone = smoke_mask * step(0.972, rnd);
    float twinkle = 0.50 + 0.50 * sin(u_time * (1.8 + rnd * 3.0) + rnd * 20.0);
    float spark = smoothstep(0.13, 0.0, length(gv)) * particle_zone * twinkle;
    color += mix(cyan, red, smoothstep(0.45, 0.65, local.x)) * spark * 0.22 * power;

    // Pequeno tratamento interno na logo: so valoriza, nao lava as cores.
    vec3 logo_rgb = hud.rgb;
    float sweep = smoothstep(0.018, 0.0, abs(local.x - fract(u_time * 0.075 + 0.18)));
    float vertical_soft = smoothstep(0.05, 0.44, local.y) * (1.0 - smoothstep(0.92, 1.0, local.y));
    logo_rgb = mix(logo_rgb, min(logo_rgb * 1.05 + side_color * 0.035, vec3(1.0)), sweep * vertical_soft * hud.a * power);
    logo_rgb = saturate_color(logo_rgb, 1.035);

    color = clamp(color, 0.0, 1.0);
    return mix(color, logo_rgb, hud.a);
}
