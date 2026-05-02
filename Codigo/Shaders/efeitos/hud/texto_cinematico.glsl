vec3 aplicar_texto_cinematico_hud(vec3 color, vec4 hud, vec2 screen_uv) {
    float power = clamp(u_texto_cinematico_power, 0.0, 1.0);
    if (power <= 0.001 || u_texto_cinematico_rect.z <= 1.0 || u_texto_cinematico_rect.w <= 1.0) {
        return color;
    }

    vec2 rect_pos = u_texto_cinematico_rect.xy / u_resolution;
    vec2 rect_size = u_texto_cinematico_rect.zw / u_resolution;
    vec2 inflate = vec2(34.0, 26.0) / u_resolution;
    vec2 minp = rect_pos - inflate;
    vec2 maxp = rect_pos + rect_size + inflate;
    float dentro = step(minp.x, screen_uv.x) * step(screen_uv.x, maxp.x) * step(minp.y, screen_uv.y) * step(screen_uv.y, maxp.y);
    if (dentro <= 0.0) {
        return color;
    }

    vec2 local = clamp((screen_uv - rect_pos) / max(rect_size, vec2(0.0001)), vec2(0.0), vec2(1.0));
    float alpha_perto = hud_alpha_blur(v_uv, 9.0);
    float alpha_longe = hud_alpha_blur(v_uv, 24.0);
    float texto_alpha = clamp(hud.a + alpha_perto * 0.62 + alpha_longe * 0.34, 0.0, 1.0);

    vec3 frio = vec3(0.62, 0.74, 1.00);
    vec3 ouro = vec3(1.00, 0.78, 0.26);
    vec3 branco = vec3(1.00, 0.96, 0.86);
    vec3 cor = mix(frio, ouro, smoothstep(0.35, 0.85, u_texto_cinematico_modo));
    cor = mix(cor, branco, 0.22);

    float sweep_x = fract(u_time * 0.145 + 0.18);
    float sweep = smoothstep(0.050, 0.0, abs(local.x - sweep_x));
    float pulso = 0.74 + 0.26 * sin(u_time * 2.2);
    float borda = alpha_longe * (1.0 - hud.a);

    color += cor * borda * power * (0.18 + 0.08 * pulso);
    color = mix(color, min(color * 1.035 + cor * 0.030, vec3(1.0)), texto_alpha * power * 0.11);
    color += branco * sweep * texto_alpha * power * 0.045;

    return clamp(color, 0.0, 1.0);
}
