#version 330

#include "uniformes/globais.glsl"
#include "uniformes/mundo.glsl"
#include "uniformes/batalha.glsl"
#include "uniformes/ataques.glsl"
#include "uniformes/hud.glsl"
#include "comum/constantes.glsl"
#include "comum/ruido.glsl"
#include "comum/cores.glsl"
#include "comum/amostras.glsl"
#include "comum/geometria.glsl"
#include "efeitos/mundo/grade_global.glsl"
#include "efeitos/mundo/clima_mundo.glsl"
#include "efeitos/mundo/biomas_mundo.glsl"
#include "efeitos/mundo/dungeon_ambiente.glsl"
#include "efeitos/mundo/captura.glsl"
#include "efeitos/batalha/clima_batalha.glsl"
#include "efeitos/batalha/areas_batalha.glsl"
#include "efeitos/batalha/estados_batalha.glsl"
#include "efeitos/batalha/ataques_batalha.glsl"
#include "efeitos/hud/menu_logo.glsl"
#include "efeitos/hud/texto_cinematico.glsl"

void main() {
    vec2 screen_uv = gl_FragCoord.xy / u_resolution;
    vec4 hud = texture(u_hud_tex, v_uv);
    vec3 base_scene = scene_sample(v_uv);

    if (u_shader_enabled < 0.5) {
        fragColor = vec4(clamp(base_scene, 0.0, 1.0), 1.0);
        return;
    }

    if (abs(u_effect_mode - FX_MENU_LOGO) < 0.5 && u_menu_logo_power > 0.001) {
        vec3 menu_color = aplicar_menu_logo(base_scene, hud, screen_uv);
        menu_color = aplicar_texto_cinematico_hud(menu_color, hud, v_uv);
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

    color = aplicar_grade_global(color, centered, dark);
    color = aplicar_chuva_mundo(color, screen_uv, rain, battle_acid);
    color = aplicar_biomas_mundo(color, screen_uv, biome);
    color = aplicar_clima_batalha(color, screen_uv, aspect, battle_sun, battle_sand, battle_fog);
    color = aplicar_areas_batalha(color, v_uv, aspect);
    color = aplicar_estados_batalha(color, v_uv, aspect);
    color = aplicar_ataques_batalha(color, v_uv, aspect);
    color = aplicar_estrelas_luz_player(color, screen_uv, aspect, dark, rain);
    color = aplicar_raios_mundo(color, screen_uv);
    color = aplicar_dungeon_ambiente(color, screen_uv, centered);
    color = aplicar_captura(color, v_uv);

    color = clamp(color, 0.0, 1.0);
    color = mix(color, hud.rgb, hud.a);
    color = aplicar_texto_cinematico_hud(color, hud, v_uv);
    fragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
