vec3 aplicar_dungeon_ambiente(vec3 color, vec2 screen_uv, vec2 centered) {
    float power = clamp(u_dungeon_power, 0.0, 1.0);
    if (power <= 0.001) {
        return color;
    }
    float darkness = clamp(u_dungeon_darkness, 0.0, 1.0) * power;
    float dist = length(centered);
    float vinheta = smoothstep(0.12, 0.92, dist);
    color *= 1.0 - darkness * (0.74 + 0.34 * vinheta);
    float luz_player = smoothstep(0.44, 0.05, dist) * power;
    color = mix(color, color + vec3(0.08, 0.075, 0.055), luz_player * 0.45);
    color = mix(color, color * vec3(0.76, 0.80, 0.92), power * 0.06);
    return color;
}
