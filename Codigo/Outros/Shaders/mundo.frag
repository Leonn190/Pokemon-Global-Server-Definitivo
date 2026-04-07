#version 330

uniform sampler2D u_scene_tex;
uniform sampler2D u_hud_tex;
uniform vec2 u_resolution;
uniform vec2 u_player_uv;
uniform vec3 u_tint;
uniform float u_darkness;
uniform float u_rain_power;
uniform float u_lightning;
uniform float u_star_strength;
uniform float u_inside;
uniform float u_time;
uniform float u_biome_mode;
uniform float u_biome_power;
uniform float u_shader_enabled;

in vec2 v_uv;
out vec4 fragColor;

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 345.45));
    p += dot(p, p + 34.345);
    return fract(p.x * p.y);
}

float noise21(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    float a = hash21(i);
    float b = hash21(i + vec2(1.0, 0.0));
    float c = hash21(i + vec2(0.0, 1.0));
    float d = hash21(i + vec2(1.0, 1.0));
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
}

vec3 saturate_color(vec3 c, float amount) {
    float luma = dot(c, vec3(0.299, 0.587, 0.114));
    return mix(vec3(luma), c, amount);
}

vec3 scene_sample(vec2 uv) {
    return texture(u_scene_tex, clamp(uv, vec2(0.0), vec2(1.0))).rgb;
}

float star_field(vec2 screen_uv) {
    vec2 uv = screen_uv;
    uv.x *= u_resolution.x / u_resolution.y;
    uv *= 24.0;

    vec2 gv = fract(uv) - 0.5;
    vec2 id = floor(uv);
    float rnd = hash21(id);
    float mask = step(0.9925, rnd);
    float d = length(gv);
    float blink = 0.65 + 0.35 * sin(u_time * (2.0 + rnd * 4.0) + rnd * 30.0);
    return smoothstep(0.17, 0.0, d) * mask * blink;
}

void main() {
    vec2 screen_uv = gl_FragCoord.xy / u_resolution;
    vec4 hud = texture(u_hud_tex, v_uv);
    vec3 base_scene = scene_sample(v_uv);

    if (u_shader_enabled < 0.5) {
        fragColor = vec4(clamp(base_scene, 0.0, 1.0), 1.0);
        return;
    }

    float aspect = u_resolution.x / u_resolution.y;
    vec2 centered = screen_uv - vec2(0.5);
    centered.x *= aspect;

    vec3 color = base_scene;

    float dark = clamp(u_darkness, 0.0, 1.0);
    float rain = clamp(u_rain_power, 0.0, 1.0);
    float biome = clamp(u_biome_power, 0.0, 1.0);

    float vignette = smoothstep(1.16, 0.12, length(centered));
    vec3 tint_grade = mix(vec3(1.0), clamp(u_tint, 0.0, 1.0), dark * 0.66);
    color *= tint_grade;
    color *= (1.0 - dark * 0.72);
    color *= mix(0.95, 1.0, vignette);
    color = saturate_color(color, 1.04);

    if (rain > 0.001) {
        float ripple = noise21(vec2(screen_uv.x * 28.0 + u_time * 0.35, screen_uv.y * 36.0 - u_time * 3.8));
        vec2 wet_offset = vec2((ripple - 0.5) * 0.010 * rain, 0.0);
        vec3 rainy = scene_sample(v_uv + wet_offset);
        color = mix(color, rainy * vec3(0.92, 0.98, 1.03), rain * 0.20);

        float reflection_mask = smoothstep(0.40, 1.0, screen_uv.y) * (1.0 - u_inside * 0.55);
        float streak = smoothstep(0.56, 1.0, ripple);
        color += vec3(0.025, 0.045, 0.060) * reflection_mask * rain * (0.30 + 0.70 * streak);
        color = mix(color, color * vec3(0.84, 0.90, 0.98), rain * 0.22);
    }

    if (u_biome_mode > 0.5 && u_biome_mode < 1.5) {
        float edge = 1.0 - smoothstep(0.0, 0.16, min(min(screen_uv.x, 1.0 - screen_uv.x), min(screen_uv.y, 1.0 - screen_uv.y)));
        float frost_noise = noise21(screen_uv * vec2(26.0, 18.0) + u_time * 0.08);
        float frost = edge * smoothstep(0.40, 1.0, biome) * (0.60 + frost_noise * 0.40) * (1.0 - u_inside * 0.64);
        color = mix(color, min(color + vec3(0.10, 0.12, 0.14), vec3(1.0)), biome * 0.24);
        color = mix(color, vec3(0.88, 0.94, 1.0), frost * 0.58);
    }
    else if (u_biome_mode > 1.5 && u_biome_mode < 2.5) {
        float heat_n = noise21(vec2(screen_uv.x * 8.0 + u_time * 0.25, screen_uv.y * 26.0 + u_time * 1.3));
        vec2 heat_offset = vec2((heat_n - 0.5) * 0.012 * biome, 0.0);
        vec3 heated = scene_sample(v_uv + heat_offset);
        float ember = pow(noise21(screen_uv * 7.0 + vec2(u_time * 0.10, -u_time * 0.06)), 3.0);
        color = mix(color, heated * vec3(1.06, 0.96, 0.82), biome * 0.28);
        color += vec3(0.28, 0.09, 0.02) * ember * biome * (1.0 - u_inside * 0.50);
    }
    else if (u_biome_mode > 2.5 && u_biome_mode < 3.5) {
        float haze = noise21(vec2(screen_uv.x * 14.0 + u_time * 0.3, screen_uv.y * 20.0 + u_time * 1.1));
        vec2 heat_offset = vec2((haze - 0.5) * 0.009 * biome, 0.0);
        vec3 dry = scene_sample(v_uv + heat_offset);
        float dust = smoothstep(0.30, 1.0, haze) * smoothstep(0.10, 0.95, screen_uv.y);
        color = mix(color, dry * vec3(1.08, 1.00, 0.86), biome * 0.24);
        color += vec3(0.08, 0.06, 0.03) * dust * biome * 0.22;
    }
    else if (u_biome_mode > 3.5 && u_biome_mode < 4.5) {
        vec2 magic_shift = vec2(0.004 + biome * 0.006, 0.0) * (1.0 - u_inside * 0.35);
        vec3 magic_rgb = vec3(
            scene_sample(v_uv + magic_shift).r,
            scene_sample(v_uv).g,
            scene_sample(v_uv - magic_shift).b
        );
        float spark = pow(noise21(screen_uv * 22.0 + u_time * 0.24), 8.0);
        color = mix(color, saturate_color(magic_rgb, 1.26) * vec3(1.05, 0.94, 1.10), biome * 0.26);
        color += vec3(0.20, 0.08, 0.24) * biome * 0.16;
        color += vec3(0.22, 0.12, 0.28) * spark * biome;
    }
    else if (u_biome_mode > 4.5) {
        float murk = noise21(screen_uv * 8.5 + vec2(u_time * 0.05, -u_time * 0.03));
        float fog = smoothstep(0.22, 1.0, murk) * smoothstep(0.26, 1.0, screen_uv.y);
        color = saturate_color(color, 1.0 - biome * 0.24);
        color = mix(color, color * vec3(0.84, 0.90, 0.84), biome * 0.28);
        color = mix(color, vec3(0.48, 0.54, 0.48), fog * biome * 0.18 * (1.0 - u_inside * 0.40));
    }

    if (u_star_strength > 0.01 && u_inside < 0.5) {
        float top_mask = smoothstep(0.40, 0.82, screen_uv.y);
        float stars = star_field(screen_uv) * u_star_strength * top_mask;
        color += vec3(0.42, 0.46, 0.54) * stars;
    }

    vec2 light_delta = screen_uv - u_player_uv;
    light_delta.x *= aspect;
    float dist = length(light_delta);
    float inner_radius = mix(0.045, 0.085, dark);
    float outer_radius = mix(0.16, 0.24, dark);
    float glow_core = 1.0 - smoothstep(inner_radius, outer_radius, dist);
    float glow_soft = 1.0 - smoothstep(outer_radius, outer_radius * 1.65, dist);
    glow_core = pow(max(glow_core, 0.0), 1.45);
    glow_soft = pow(max(glow_soft, 0.0), 1.8);
    float glow = (glow_core * 0.82 + glow_soft * 0.18) * dark;
    glow *= mix(1.0, 0.88, rain * 0.45);
    color = mix(color, min(color * 1.22 + vec3(0.022, 0.030, 0.040), vec3(1.0)), glow);

    if (u_lightning > 0.001) {
        float bolt_x = 0.18 + 0.52 * fract(sin(floor(u_time * 1.75) + 3.41) * 43758.5453);
        float branch = abs(screen_uv.x - (bolt_x + sin(screen_uv.y * 18.0 + u_time * 12.0) * 0.018));
        float bolt = smoothstep(0.030, 0.0, branch) * smoothstep(0.72, 0.10, screen_uv.y);
        color += vec3(0.42, 0.45, 0.52) * clamp(u_lightning, 0.0, 1.25);
        color += vec3(0.64, 0.66, 0.75) * bolt * clamp(u_lightning, 0.0, 1.25);
    }

    color = clamp(color, 0.0, 1.0);
    color = mix(color, hud.rgb, hud.a);
    fragColor = vec4(color, 1.0);
}
