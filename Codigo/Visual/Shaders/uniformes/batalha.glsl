uniform float u_battle_sun_power;
uniform float u_battle_sand_power;
uniform float u_battle_fog_power;
uniform float u_battle_acid_power;

// Estados visuais de batalha. Cada vec4 guarda: x, y, raio, codigo + intensidade * 0.1.
// Apenas estados que mudam visual/cor persistente do Pokemon entram aqui.
// Codigos: 1 envenenado, 2 queimado/cauterizado, 3 energizado,
// 4 intoxicado, 5 encharcado, 6 abencoado, 7 congelado,
// 8 amaldicoado, 9 encantado.
uniform vec4 u_estado_batalha_0;
uniform vec4 u_estado_batalha_1;
uniform vec4 u_estado_batalha_2;
uniform vec4 u_estado_batalha_3;
uniform vec4 u_estado_batalha_4;
uniform vec4 u_estado_batalha_5;
uniform vec4 u_estado_batalha_6;
uniform vec4 u_estado_batalha_7;
uniform vec4 u_estado_batalha_8;
uniform vec4 u_estado_batalha_9;
uniform vec4 u_estado_batalha_10;
uniform vec4 u_estado_batalha_11;
