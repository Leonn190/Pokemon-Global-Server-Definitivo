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
uniform float u_effect_mode;

// Captura no mundo: efeito radial em torno do Pokémon/bola.
uniform vec2 u_capture_uv;
uniform float u_capture_power;
uniform float u_capture_phase;
uniform float u_capture_result;
uniform float u_capture_critical;
uniform float u_capture_check_index;
uniform float u_capture_check_count;
uniform float u_capture_token_hash;

// Menu principal: retangulo da logo em pixels (x, y, w, h) e forca do efeito.
uniform vec4 u_menu_logo_rect;
uniform float u_menu_logo_power;

in vec2 v_uv;
out vec4 fragColor;

const float PI = 3.14159265359;
const float FX_NONE = 0.0;
const float FX_MUNDO = 1.0;
const float FX_MENU_LOGO = 2.0;
const float FX_BATALHA = 3.0;
const float FX_MAPA = 4.0;
const float FX_PAINEL = 5.0;

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
