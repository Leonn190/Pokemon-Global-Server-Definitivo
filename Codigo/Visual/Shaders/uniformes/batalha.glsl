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

// Efeitos visuais de area da arena. Cada vec4 guarda:
// x, y, raio, codigo + power * 0.1.
// Codigos: 1 destruido, 2 queimado, 3 envenenado, 4 congelado,
// 5 eletrificado, 6 encharcado, 7 amaldicoado, 8 abencoado.
uniform vec4 u_area_batalha_0;
uniform vec4 u_area_batalha_1;
uniform vec4 u_area_batalha_2;
uniform vec4 u_area_batalha_3;
uniform vec4 u_area_batalha_4;
uniform vec4 u_area_batalha_5;
uniform vec4 u_area_batalha_6;
uniform vec4 u_area_batalha_7;
uniform vec4 u_area_batalha_8;
uniform vec4 u_area_batalha_9;
uniform vec4 u_area_batalha_10;
uniform vec4 u_area_batalha_11;
uniform vec4 u_area_batalha_12;
uniform vec4 u_area_batalha_13;
uniform vec4 u_area_batalha_14;
uniform vec4 u_area_batalha_15;
uniform vec4 u_area_batalha_16;
uniform vec4 u_area_batalha_17;
