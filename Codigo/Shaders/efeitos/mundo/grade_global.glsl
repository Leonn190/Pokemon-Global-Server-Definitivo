vec3 aplicar_grade_global(vec3 color, vec2 centered, float dark) {
    float vignette = smoothstep(1.16, 0.12, length(centered));
    vec3 tint_grade = mix(vec3(1.0), clamp(u_tint, 0.0, 1.0), dark * 0.66);
    color *= tint_grade;
    color *= (1.0 - dark * 0.72);
    color *= mix(0.95, 1.0, vignette);
    return saturate_color(color, 1.04);
}
