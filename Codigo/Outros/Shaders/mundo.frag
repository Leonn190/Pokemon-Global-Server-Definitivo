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
uniform float u_battle_sun_power;
uniform float u_battle_sand_power;
uniform float u_battle_fog_power;
uniform float u_battle_acid_power;
uniform float u_shader_enabled;

// Menu principal: retangulo da logo em pixels (x, y, w, h) e forca do efeito.
uniform vec4 u_menu_logo_rect;
uniform float u_menu_logo_power;

in vec2 v_uv;
out vec4 fragColor;

const float PI = 3.14159265359;

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

float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.50;
    mat2 rot = mat2(0.80, -0.60, 0.60, 0.80);
    for (int i = 0; i < 4; i++) {
        v += a * noise21(p);
        p = rot * p * 2.03 + vec2(17.7, 9.2);
        a *= 0.52;
    }
    return v;
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

float hud_alpha_blur(vec2 uv, float px_radius) {
    vec2 p = vec2(px_radius) / u_resolution;
    float a = texture(u_hud_tex, uv).a * 0.22;
    a += texture(u_hud_tex, uv + vec2( p.x,  0.0)).a * 0.10;
    a += texture(u_hud_tex, uv + vec2(-p.x,  0.0)).a * 0.10;
    a += texture(u_hud_tex, uv + vec2( 0.0,  p.y)).a * 0.10;
    a += texture(u_hud_tex, uv + vec2( 0.0, -p.y)).a * 0.10;
    a += texture(u_hud_tex, uv + vec2( p.x,  p.y)).a * 0.07;
    a += texture(u_hud_tex, uv + vec2(-p.x,  p.y)).a * 0.07;
    a += texture(u_hud_tex, uv + vec2( p.x, -p.y)).a * 0.07;
    a += texture(u_hud_tex, uv + vec2(-p.x, -p.y)).a * 0.07;
    a += texture(u_hud_tex, uv + vec2( p.x * 1.8,  0.0)).a * 0.06;
    a += texture(u_hud_tex, uv + vec2(-p.x * 1.8,  0.0)).a * 0.06;
    a += texture(u_hud_tex, uv + vec2( 0.0,  p.y * 1.8)).a * 0.06;
    a += texture(u_hud_tex, uv + vec2( 0.0, -p.y * 1.8)).a * 0.06;
    return clamp(a, 0.0, 1.0);
}

vec2 rotate2d(vec2 p, float a) {
    float s = sin(a);
    float c = cos(a);
    return vec2(c * p.x - s * p.y, s * p.x + c * p.y);
}

float ellipse_orbit(vec2 rel, vec2 radius, float angle, float thickness, float dash_phase) {
    vec2 p = rotate2d(rel, angle) / max(radius, vec2(0.0001));
    float ring = 1.0 - smoothstep(thickness, thickness * 2.4, abs(length(p) - 1.0));
    float theta = atan(p.y, p.x);

    // Arcos, nao rabiscos completos: aparecem/desaparecem em trechos suaves.
    float dash = 0.58 + 0.42 * sin(theta * 2.0 + dash_phase);
    dash *= 0.66 + 0.34 * sin(theta * 4.0 - dash_phase * 0.7);
    dash = smoothstep(0.53, 0.96, dash);
    return ring * dash;
}

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

void main() {
    vec2 screen_uv = gl_FragCoord.xy / u_resolution;
    vec4 hud = texture(u_hud_tex, v_uv);
    vec3 base_scene = scene_sample(v_uv);

    if (u_shader_enabled < 0.5) {
        fragColor = vec4(clamp(base_scene, 0.0, 1.0), 1.0);
        return;
    }

    if (u_menu_logo_power > 0.001) {
        vec3 menu_color = aplicar_menu_logo(base_scene, hud, screen_uv);
        fragColor = vec4(clamp(menu_color, 0.0, 1.0), 1.0);
        return;
    }

    float aspect = u_resolution.x / u_resolution.y;
    vec2 centered = screen_uv - vec2(0.5);
    centered.x *= aspect;

    vec3 color = base_scene;

    float dark = clamp(u_darkness, 0.0, 1.0);
    float rain = clamp(u_rain_power, 0.0, 1.0);
    float biome = clamp(u_biome_power, 0.0, 1.0);
    float battle_sun = clamp(u_battle_sun_power, 0.0, 1.0);
    float battle_sand = clamp(u_battle_sand_power, 0.0, 1.0);
    float battle_fog = clamp(u_battle_fog_power, 0.0, 1.0);
    float battle_acid = clamp(u_battle_acid_power, 0.0, 1.0);

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
        vec3 rain_grade = mix(vec3(0.92, 0.98, 1.03), vec3(0.84, 1.07, 0.76), battle_acid);
        color = mix(color, rainy * rain_grade, rain * 0.20);

        float reflection_mask = smoothstep(0.40, 1.0, screen_uv.y) * (1.0 - u_inside * 0.55);
        float streak = smoothstep(0.56, 1.0, ripple);
        vec3 rain_glow = mix(vec3(0.025, 0.045, 0.060), vec3(0.025, 0.085, 0.018), battle_acid);
        color += rain_glow * reflection_mask * rain * (0.30 + 0.70 * streak);
        color = mix(color, color * mix(vec3(0.84, 0.90, 0.98), vec3(0.80, 0.98, 0.78), battle_acid), rain * 0.22);
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

    if (battle_sun > 0.001) {
        vec2 sun_pos = vec2(-0.10, 1.10);
        float sun_dist = length((screen_uv - sun_pos) * vec2(aspect, 1.0));
        float glare = 1.0 - smoothstep(0.15, 1.16, sun_dist);
        float ray_seed = screen_uv.x * 5.2 + screen_uv.y * 2.5 + sin(u_time * 0.18) * 0.18;
        float rays = pow(max(0.0, sin(ray_seed * PI) * 0.5 + 0.5), 5.0);
        rays *= smoothstep(1.04, 0.20, sun_dist);
        color = mix(color, min(color * vec3(1.12, 1.06, 0.90) + vec3(0.055, 0.044, 0.020), vec3(1.0)), battle_sun * 0.42);
        color += vec3(0.35, 0.28, 0.10) * (glare * 0.20 + rays * 0.16) * battle_sun;
    }

    if (battle_sand > 0.001) {
        float sand_n = noise21(vec2(screen_uv.x * 12.0 - u_time * 2.2, screen_uv.y * 28.0 + u_time * 0.32));
        vec2 sand_offset = vec2((sand_n - 0.5) * 0.012 * battle_sand, 0.0);
        vec3 sandy = scene_sample(v_uv + sand_offset);
        float sheet = smoothstep(0.42, 1.0, sand_n) * (0.35 + 0.65 * smoothstep(0.08, 0.92, screen_uv.y));
        color = mix(color, sandy * vec3(1.08, 1.01, 0.82), battle_sand * 0.30);
        color = mix(color, vec3(0.76, 0.66, 0.43), sheet * battle_sand * 0.16);
    }

    if (battle_fog > 0.001) {
        float fog_n = noise21(vec2(screen_uv.x * 5.5 - u_time * 0.12, screen_uv.y * 7.0 + u_time * 0.05));
        float veil = smoothstep(0.10, 0.92, fog_n) * (0.55 + 0.45 * smoothstep(0.04, 0.78, screen_uv.y));
        color = saturate_color(color, 1.0 - battle_fog * 0.34);
        color = mix(color, vec3(0.72, 0.76, 0.75), battle_fog * (0.18 + veil * 0.24));
        color = mix(vec3(0.5), color, 1.0 - battle_fog * 0.16);
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
