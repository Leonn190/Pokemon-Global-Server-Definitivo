vec3 aplicar_dungeon_ambiente(vec3 color, vec2 screen_uv, vec2 centered) {
    float power = clamp(u_dungeon_power, 0.0, 1.0);
    if (power <= 0.001) {
        return color;
    }
    float darkness = clamp(u_dungeon_darkness, 0.0, 1.0) * power;
    float vinheta = smoothstep(0.18, 0.95, length(centered));
    color *= 1.0 - darkness * (0.56 + 0.28 * vinheta);
    color = mix(color, color * vec3(0.82, 0.86, 1.0), power * 0.08);
    return color;
}
