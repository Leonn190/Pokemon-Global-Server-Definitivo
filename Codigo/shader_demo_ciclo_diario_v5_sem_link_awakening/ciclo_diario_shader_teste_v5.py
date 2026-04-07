from pathlib import Path
import math
import random
import sys

import pygame

try:
    import moderngl
except ImportError:
    print("Esta demo com shader precisa do moderngl.")
    print("Instale com: pip install moderngl pygame")
    raise SystemExit(1)

pygame.init()

# =========================
# CONFIG
# =========================
W, H = 1920, 1080
FPS = 500
TILE = 48
SPEED = 260

DAY_DURATION_SECONDS = 120.0
TIME_SPEED_NORMAL = 1.0
TIME_SPEED_FAST = 8.0
START_TIME01 = 0.26

RAIN_MAX = 1.0
RAIN_STEP = 0.05
BIOME_MAX = 1.0
BIOME_STEP = 0.05
RAIN_LEVELS = int(round(RAIN_MAX / RAIN_STEP))
BIOME_LEVELS = int(round(BIOME_MAX / BIOME_STEP))

BASE_DIR = Path(__file__).resolve().parent
VERT_PATH = BASE_DIR / "ciclo_diario_shader_teste_v5.vert"
FRAG_PATH = BASE_DIR / "ciclo_diario_shader_teste_v5.frag"

if not VERT_PATH.exists() or not FRAG_PATH.exists():
    print("Arquivos de shader não encontrados na mesma pasta do .py")
    print("Esperado:")
    print(f" - {VERT_PATH.name}")
    print(f" - {FRAG_PATH.name}")
    raise SystemExit(1)

pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
pygame.display.gl_set_attribute(
    pygame.GL_CONTEXT_PROFILE_MASK,
    pygame.GL_CONTEXT_PROFILE_CORE,
)
pygame.display.set_mode((W, H), pygame.OPENGL | pygame.DOUBLEBUF)
pygame.display.set_caption("Top-down shader: ciclo diário + chuva + biomas v4")
clock = pygame.time.Clock()

ctx = moderngl.create_context()
ctx.disable(moderngl.DEPTH_TEST)
ctx.disable(moderngl.CULL_FACE)
ctx.disable(moderngl.BLEND)

program = ctx.program(
    vertex_shader=VERT_PATH.read_text(encoding="utf-8"),
    fragment_shader=FRAG_PATH.read_text(encoding="utf-8"),
)

quad = ctx.buffer(
    data=(
        b"\x00\x00\x80\xbf\x00\x00\x80\xbf\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x80\x3f\x00\x00\x80\xbf\x00\x00\x80\x3f\x00\x00\x00\x00"
        b"\x00\x00\x80\xbf\x00\x00\x80\x3f\x00\x00\x00\x00\x00\x00\x80\x3f"
        b"\x00\x00\x80\x3f\x00\x00\x80\xbf\x00\x00\x80\x3f\x00\x00\x00\x00"
        b"\x00\x00\x80\x3f\x00\x00\x80\x3f\x00\x00\x80\x3f\x00\x00\x80\x3f"
        b"\x00\x00\x80\xbf\x00\x00\x80\x3f\x00\x00\x00\x00\x00\x00\x80\x3f"
    )
)
vao = ctx.vertex_array(program, [(quad, "2f 2f", "in_pos", "in_uv")])

scene_surface = pygame.Surface((W, H), pygame.SRCALPHA)
hud_surface = pygame.Surface((W, H), pygame.SRCALPHA)
scene_tex = ctx.texture((W, H), 4)
hud_tex = ctx.texture((W, H), 4)
scene_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
hud_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
scene_tex.repeat_x = False
scene_tex.repeat_y = False
hud_tex.repeat_x = False
hud_tex.repeat_y = False
program["u_scene_tex"] = 0
program["u_hud_tex"] = 1
program["u_resolution"].value = (float(W), float(H))

# =========================
# CORES / FONTES
# =========================
BG = (14, 16, 22)
WHITE = (245, 245, 248)
OUTLINE = (25, 30, 45)
PLAYER = (255, 230, 120)
HUD_DARK = (12, 16, 24)
HUD_SOFT = (175, 185, 205)
HUD_TEXT = (205, 212, 225)

font = pygame.font.SysFont("Segoe UI", 18)
font_small = pygame.font.SysFont("Segoe UI", 15)
font_big = pygame.font.SysFont("Segoe UI", 22)

random.seed(7)

# =========================
# HELPERS
# =========================
def clamp(v, a, b):
    return a if v < a else b if v > b else v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )


def color_scale(c, s):
    return (
        int(clamp(c[0] * s, 0, 255)),
        int(clamp(c[1] * s, 0, 255)),
        int(clamp(c[2] * s, 0, 255)),
    )


def soften(c, add):
    return (
        int(clamp(c[0] + add, 0, 255)),
        int(clamp(c[1] + add, 0, 255)),
        int(clamp(c[2] + add, 0, 255)),
    )


# =========================
# MAPAS
# =========================
MAP_W, MAP_H = 30, 18
WORLD = [[0 for _ in range(MAP_W)] for _ in range(MAP_H)]
for y in range(MAP_H):
    WORLD[y][12] = 1
for x in range(6, 25):
    WORLD[10][x] = 1
for y in range(3, 7):
    for x in range(3, 6):
        WORLD[y][x] = 2

IN_W, IN_H = 20, 14
INSIDE = [[0 for _ in range(IN_W)] for _ in range(IN_H)]
for x in range(2, IN_W - 2):
    INSIDE[IN_H // 2][x] = 1

# =========================
# ESTÁDIO
# =========================
stadium_center_tile = (20, 10)
stadium_radius_px = (220, 150)


def stadium_center_world_px():
    cx = stadium_center_tile[0] * TILE + TILE // 2
    cy = stadium_center_tile[1] * TILE + TILE // 2
    return cx, cy


def stadium_door_rect_world():
    cx, cy = stadium_center_world_px()
    door_w, door_h = 70, 30
    return pygame.Rect(cx - door_w // 2, cy + stadium_radius_px[1] - 18, door_w, door_h)


def inside_exit_rect_world():
    cx = (IN_W * TILE) // 2
    cy = IN_H * TILE - 40
    return pygame.Rect(cx - 60, cy, 120, 28)


# =========================
# PLAYER + CAMERA
# =========================
scene = "world"
shader_enabled = True
time_speed = TIME_SPEED_NORMAL
day_time_seconds = START_TIME01 * DAY_DURATION_SECONDS
player_x = 12 * TILE
player_y = 15 * TILE
cam_x = 0.0
cam_y = 0.0


def world_bounds():
    if scene == "world":
        return MAP_W * TILE, MAP_H * TILE
    return IN_W * TILE, IN_H * TILE


def world_to_screen(wx, wy):
    return int(wx - cam_x), int(wy - cam_y)


def player_rect():
    return pygame.Rect(int(player_x - 14), int(player_y - 18), 28, 34)


def player_screen_center():
    pr = player_rect()
    return world_to_screen(pr.centerx, pr.centery)


# =========================
# CICLO DIÁRIO CERTO
# 00:30 = ponto mais escuro
# 12:30 = ponto mais claro
# =========================
def get_cycle_state(time01):
    t = time01 % 1.0
    sun = 0.5 - 0.5 * math.cos(math.tau * t)
    darkness = (1.0 - sun) ** 1.58 * 0.80

    dawn = max(0.0, 1.0 - abs(t - 0.25) / 0.16)
    dusk = max(0.0, 1.0 - abs(t - 0.75) / 0.16)
    warm = max(dawn, dusk)
    warm = warm * 0.65 + dawn * 0.18
    cool = (1.0 - sun) ** 1.15

    tint = (255, 255, 255)
    tint = lerp_color(tint, (255, 230, 206), warm * 0.55)
    tint = lerp_color(tint, (106, 124, 168), cool * 0.82)

    hour = (int((t * 24.0 + 0.5) % 24.0))
    if 5 <= hour < 8:
        label = "Amanhecer"
    elif 8 <= hour < 17:
        label = "Dia"
    elif 17 <= hour < 20:
        label = "Entardecer"
    else:
        label = "Noite"

    star_strength = clamp(((1.0 - sun) - 0.36) / 0.64, 0.0, 1.0)
    return {
        "label": label,
        "tint": tint,
        "darkness": darkness,
        "star_strength": star_strength,
        "time01": t,
        "sun": sun,
    }


def format_clock(time01):
    total_minutes = int(((time01 % 1.0) * 24.0 * 60.0 + 30.0) % (24 * 60))
    hh = total_minutes // 60
    mm = total_minutes % 60
    return f"{hh:02d}:{mm:02d}"


# =========================
# CHUVA
# =========================
rain_power = 0.0
rain_particles = []
lightning_flash = 0.0


def get_rain_level():
    return int(round(clamp(rain_power, 0.0, 1.0) * RAIN_LEVELS))


def set_rain(enabled):
    global rain_power
    if enabled:
        rain_power = 0.38 if rain_power <= 0.01 else rain_power
    else:
        rain_power = 0.0


def change_rain(delta):
    global rain_power
    rain_power = clamp(rain_power + delta, 0.0, RAIN_MAX)


def rain_label():
    p = rain_power
    if p <= 0.0:
        return "Sem chuva"
    if p < 0.18:
        return "Garoa"
    if p < 0.38:
        return "Chuva leve"
    if p < 0.60:
        return "Chuva"
    if p < 0.80:
        return "Chuva forte"
    return "Tempestade"


def rain_profile():
    p = rain_power
    if p <= 0.0:
        return {"target": 0, "speed": 0.0, "length": 0, "thickness": 0}
    return {
        "target": int(lerp(45, 680, p)),
        "speed": lerp(380.0, 1800.0, p),
        "length": int(lerp(10, 46, p)),
        "thickness": 2 if p < 0.35 else 3 if p < 0.76 else 4,
    }


def make_rain_particle():
    return {
        "x": random.uniform(-180, W + 180),
        "y": random.uniform(-H, H),
        "dx": random.uniform(165.0, 320.0),
        "dy": random.uniform(0.92, 1.10),
    }


def ensure_rain_population(target):
    while len(rain_particles) < target:
        rain_particles.append(make_rain_particle())
    if len(rain_particles) > target:
        del rain_particles[target:]


def update_rain(dt):
    global lightning_flash
    profile = rain_profile()
    ensure_rain_population(profile["target"])

    if profile["target"] <= 0:
        lightning_flash = max(0.0, lightning_flash - dt * 2.3)
        return

    for drop in rain_particles:
        drop["x"] += drop["dx"] * dt
        drop["y"] += profile["speed"] * drop["dy"] * dt
        if drop["y"] > H + profile["length"] or drop["x"] > W + 220:
            drop.update(make_rain_particle())
            drop["x"] = random.uniform(-220, W)
            drop["y"] = random.uniform(-220, -20)

    if rain_power >= 0.64:
        lightning_flash = max(0.0, lightning_flash - dt * 2.0)
        chance = lerp(0.12, 1.55, (rain_power - 0.64) / 0.36)
        if lightning_flash <= 0.0 and random.random() < dt * chance:
            lightning_flash = random.uniform(0.55, 1.25)
    else:
        lightning_flash = max(0.0, lightning_flash - dt * 2.6)


# =========================
# BIOMAS
# =========================
BIOMES = [
    "normal",
    "snow",
    "volcanic",
    "desert",
    "magic",
    "swamp",
]
BIOME_LABELS = {
    "normal": "Normal",
    "snow": "Neve",
    "volcanic": "Vulcânico",
    "desert": "Deserto",
    "magic": "Mágico",
    "swamp": "Pântano",
}
BIOME_KEYS = {
    pygame.K_1: "normal",
    pygame.K_2: "snow",
    pygame.K_3: "volcanic",
    pygame.K_4: "desert",
    pygame.K_5: "magic",
    pygame.K_6: "swamp",
}

biome_type = "snow"
biome_power = 0.70
fx_particles = []
biome_buttons = {}
rain_buttons = {}
shader_button = None


def get_biome_level():
    return int(round(clamp(biome_power, 0.0, 1.0) * BIOME_LEVELS))


def change_biome_power(delta):
    global biome_power
    biome_power = clamp(biome_power + delta, 0.0, BIOME_MAX)


def set_biome(new_biome):
    global biome_type
    biome_type = new_biome


def get_palette_for_biome(mode, power):
    del mode, power
    return {
        "grass1": (110, 200, 130),
        "grass2": (95, 185, 118),
        "path1": (190, 170, 120),
        "path2": (170, 150, 105),
        "water": (70, 140, 210),
        "water_border": (35, 75, 120),
        "water_high": (120, 190, 255),
        "wall": (70, 78, 95),
        "wall_dark": (52, 58, 72),
        "stadium_field": (95, 200, 120),
        "arena": (70, 175, 115),
    }


def make_fx_particle(mode):
    if mode == "snow":
        return {
            "x": random.uniform(-30, W + 30),
            "y": random.uniform(-H, H),
            "sx": random.uniform(1.8, 4.8),
            "sy": random.uniform(36.0, 160.0),
            "phase": random.uniform(0.0, math.tau),
            "size": random.uniform(1.4, 4.6),
        }
    if mode == "volcanic":
        return {
            "x": random.uniform(-40, W + 40),
            "y": random.uniform(H * 0.52, H + 40),
            "sx": random.uniform(-22.0, 22.0),
            "sy": random.uniform(-120.0, -44.0),
            "phase": random.uniform(0.0, math.tau),
            "size": random.uniform(1.4, 3.8),
        }
    if mode == "desert":
        return {
            "x": random.uniform(-60, W + 60),
            "y": random.uniform(40, H - 20),
            "sx": random.uniform(30.0, 96.0),
            "sy": random.uniform(-6.0, 12.0),
            "phase": random.uniform(0.0, math.tau),
            "size": random.uniform(1.2, 3.0),
        }
    if mode == "magic":
        return {
            "x": random.uniform(-20, W + 20),
            "y": random.uniform(30, H + 20),
            "sx": random.uniform(-22.0, 22.0),
            "sy": random.uniform(-18.0, 18.0),
            "phase": random.uniform(0.0, math.tau),
            "size": random.uniform(1.4, 3.5),
        }
    if mode == "swamp":
        return {
            "x": random.uniform(-40, W + 40),
            "y": random.uniform(H * 0.30, H + 20),
            "sx": random.uniform(-10.0, 10.0),
            "sy": random.uniform(-22.0, 10.0),
            "phase": random.uniform(0.0, math.tau),
            "size": random.uniform(6.0, 18.0),
        }
    return {
        "x": random.uniform(-20, W + 20),
        "y": random.uniform(-20, H + 20),
        "sx": 0.0,
        "sy": 0.0,
        "phase": 0.0,
        "size": 0.0,
    }


def biome_particle_target():
    p = biome_power
    if biome_type == "normal" or p <= 0.0:
        return 0
    if biome_type == "snow":
        return int(lerp(35, 260, p))
    if biome_type == "volcanic":
        return int(lerp(16, 150, p))
    if biome_type == "desert":
        return int(lerp(24, 180, p))
    if biome_type == "magic":
        return int(lerp(18, 120, p))
    return int(lerp(12, 84, p))


def ensure_fx_population(target):
    while len(fx_particles) < target:
        fx_particles.append(make_fx_particle(biome_type))
    if len(fx_particles) > target:
        del fx_particles[target:]


def update_biome_fx(dt):
    if scene != "world":
        return

    target = biome_particle_target()
    ensure_fx_population(target)
    ticks = pygame.time.get_ticks() * 0.001

    if biome_type == "normal" or target <= 0:
        return

    for p in fx_particles:
        if biome_type == "snow":
            p["phase"] += dt * 2.2
            p["x"] += (math.sin(ticks * 1.7 + p["phase"]) * 18.0 + p["sx"]) * dt
            p["y"] += p["sy"] * dt
            if p["y"] > H + 18 or p["x"] < -60 or p["x"] > W + 60:
                p.update(make_fx_particle("snow"))
                p["x"] = random.uniform(-20, W + 20)
                p["y"] = random.uniform(-140, -12)
        elif biome_type == "volcanic":
            p["phase"] += dt * 4.0
            p["x"] += (p["sx"] + math.sin(ticks * 3.2 + p["phase"]) * 12.0) * dt
            p["y"] += p["sy"] * dt
            if p["y"] < -20 or p["x"] < -60 or p["x"] > W + 60:
                p.update(make_fx_particle("volcanic"))
        elif biome_type == "desert":
            p["phase"] += dt * 2.4
            p["x"] += (p["sx"] + math.sin(ticks * 2.0 + p["phase"]) * 20.0) * dt
            p["y"] += (p["sy"] + math.sin(ticks * 1.7 + p["phase"]) * 5.0) * dt
            if p["x"] > W + 80 or p["y"] < -30 or p["y"] > H + 30:
                p.update(make_fx_particle("desert"))
                p["x"] = random.uniform(-100, -10)
        elif biome_type == "magic":
            p["phase"] += dt * 2.8
            p["x"] += math.sin(ticks * 1.4 + p["phase"]) * 16.0 * dt + p["sx"] * dt
            p["y"] += math.cos(ticks * 1.9 + p["phase"]) * 10.0 * dt + p["sy"] * dt
            if p["x"] < -30 or p["x"] > W + 30 or p["y"] < -30 or p["y"] > H + 30:
                p.update(make_fx_particle("magic"))
        elif biome_type == "swamp":
            p["phase"] += dt * 1.2
            p["x"] += math.sin(ticks * 0.9 + p["phase"]) * 7.0 * dt + p["sx"] * dt
            p["y"] += math.cos(ticks * 1.1 + p["phase"]) * 4.0 * dt + p["sy"] * dt
            if p["x"] < -80 or p["x"] > W + 80 or p["y"] < H * 0.20 or p["y"] > H + 50:
                p.update(make_fx_particle("swamp"))


# =========================
# DESENHO BASE 2D
# =========================
def draw_tile(surface, tx, ty, tile_id, palette):
    x = tx * TILE
    y = ty * TILE
    sx, sy = world_to_screen(x, y)
    r = pygame.Rect(sx, sy, TILE, TILE)

    if tile_id == 0:
        col = palette["grass1"] if (tx + ty) % 2 == 0 else palette["grass2"]
        pygame.draw.rect(surface, col, r)
    elif tile_id == 1:
        col = palette["path1"] if (tx + ty) % 2 == 0 else palette["path2"]
        pygame.draw.rect(surface, col, r, border_radius=10)
        pygame.draw.rect(surface, color_scale(col, 0.76), r, 1, border_radius=10)
    else:
        pygame.draw.rect(surface, palette["water"], r, border_radius=12)
        pygame.draw.rect(surface, palette["water_border"], r, 2, border_radius=12)
        if biome_type == "volcanic":
            pygame.draw.line(surface, palette["water_high"], (r.x + 8, r.y + 12), (r.x + 26, r.y + 12), 3)
            pygame.draw.line(surface, soften(palette["water_high"], -24), (r.x + 12, r.y + 24), (r.x + 34, r.y + 18), 2)
        elif biome_type == "magic":
            pygame.draw.line(surface, palette["water_high"], (r.x + 8, r.y + 12), (r.x + 30, r.y + 12), 2)
            pygame.draw.circle(surface, palette["water_high"], (r.x + 30, r.y + 28), 3)
        else:
            pygame.draw.line(surface, palette["water_high"], (r.x + 8, r.y + 14), (r.x + 28, r.y + 14), 2)


def draw_stadium(surface, palette):
    cx, cy = stadium_center_world_px()
    cx_s, cy_s = world_to_screen(cx, cy)

    rx, ry = stadium_radius_px
    outer = pygame.Rect(0, 0, rx * 2, ry * 2)
    outer.center = (cx_s, cy_s)

    shadow = pygame.Surface((outer.w + 24, outer.h + 24), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
    surface.blit(shadow, (outer.x - 12, outer.y - 8))

    pygame.draw.ellipse(surface, palette["wall"], outer)
    pygame.draw.ellipse(surface, OUTLINE, outer, 3)

    inner1 = outer.inflate(-60, -60)
    pygame.draw.ellipse(surface, lerp_color(palette["wall"], palette["wall_dark"], 0.45), inner1)
    pygame.draw.ellipse(surface, OUTLINE, inner1, 2)

    field = outer.inflate(-130, -130)
    pygame.draw.ellipse(surface, palette["stadium_field"], field)
    pygame.draw.ellipse(surface, color_scale(palette["stadium_field"], 0.70), field, 2)

    pygame.draw.ellipse(surface, (235, 235, 240), field.inflate(-field.w * 0.55, -field.h * 0.55), 2)
    pygame.draw.line(surface, (235, 235, 240), (field.centerx, field.top + 10), (field.centerx, field.bottom - 10), 2)

    for k in range(1, 6):
        rr = outer.inflate(-60 - k * 8, -60 - k * 8)
        pygame.draw.ellipse(surface, (0, 0, 0), rr, 1)

    door = stadium_door_rect_world()
    door_s = pygame.Rect(*world_to_screen(door.x, door.y), door.w, door.h)
    pygame.draw.rect(surface, (210, 200, 175), door_s, border_radius=8)
    pygame.draw.rect(surface, OUTLINE, door_s, 2, border_radius=8)
    pygame.draw.line(surface, (150, 130, 95), (door_s.left + 10, door_s.centery), (door_s.right - 10, door_s.centery), 2)


def draw_inside_stadium(surface, palette):
    surface.fill((18, 20, 28))

    for ty in range(IN_H):
        for tx in range(IN_W):
            draw_tile(surface, tx, ty, INSIDE[ty][tx], palette)

    arena = pygame.Rect(0, 0, 520, 300)
    arena.center = world_to_screen((IN_W * TILE) // 2, (IN_H * TILE) // 2 - 30)

    sh = pygame.Surface((arena.w + 24, arena.h + 24), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 100), sh.get_rect(), border_radius=28)
    surface.blit(sh, (arena.x - 12, arena.y - 8))

    pygame.draw.rect(surface, palette["arena"], arena, border_radius=28)
    pygame.draw.rect(surface, color_scale(palette["arena"], 0.54), arena, 3, border_radius=28)

    pygame.draw.circle(surface, (235, 235, 240), arena.center, 60, 3)
    pygame.draw.line(surface, (235, 235, 240), (arena.centerx, arena.top + 18), (arena.centerx, arena.bottom - 18), 3)

    stand_col = lerp_color(palette["wall"], palette["wall_dark"], 0.38)
    stands_top = pygame.Rect(arena.left - 70, arena.top - 90, arena.w + 140, 70)
    pygame.draw.rect(surface, stand_col, stands_top, border_radius=18)
    pygame.draw.rect(surface, OUTLINE, stands_top, 2, border_radius=18)
    for i in range(6):
        pygame.draw.line(
            surface,
            palette["wall_dark"],
            (stands_top.left + 18, stands_top.top + 12 + i * 9),
            (stands_top.right - 18, stands_top.top + 12 + i * 9),
            2,
        )

    stands_bot = pygame.Rect(arena.left - 70, arena.bottom + 20, arena.w + 140, 70)
    pygame.draw.rect(surface, stand_col, stands_bot, border_radius=18)
    pygame.draw.rect(surface, OUTLINE, stands_bot, 2, border_radius=18)
    for i in range(6):
        pygame.draw.line(
            surface,
            palette["wall_dark"],
            (stands_bot.left + 18, stands_bot.top + 12 + i * 9),
            (stands_bot.right - 18, stands_bot.top + 12 + i * 9),
            2,
        )

    bounds = pygame.Rect(*world_to_screen(0, 0), IN_W * TILE, IN_H * TILE)
    pygame.draw.rect(surface, palette["wall_dark"], bounds, 8)

    exit_r = inside_exit_rect_world()
    ex_s = pygame.Rect(*world_to_screen(exit_r.x, exit_r.y), exit_r.w, exit_r.h)
    pygame.draw.rect(surface, (210, 200, 175), ex_s, border_radius=10)
    pygame.draw.rect(surface, OUTLINE, ex_s, 2, border_radius=10)

    tip = font.render("E: sair", True, WHITE)
    surface.blit(tip, (ex_s.centerx - tip.get_width() // 2, ex_s.y - 26))


def draw_player(surface):
    pr = player_rect()
    sx, sy = world_to_screen(pr.x, pr.y)
    pr_s = pygame.Rect(sx, sy, pr.w, pr.h)

    sh = pygame.Surface((pr.w + 16, 16), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 90), sh.get_rect())
    surface.blit(sh, (pr_s.centerx - sh.get_width() // 2, pr_s.bottom - 8))

    pygame.draw.circle(surface, PLAYER, (pr_s.centerx, pr_s.centery), 16)
    pygame.draw.circle(surface, OUTLINE, (pr_s.centerx, pr_s.centery), 16, 2)
    pygame.draw.circle(surface, (40, 40, 55), (pr_s.centerx - 6, pr_s.centery - 2), 2)
    pygame.draw.circle(surface, (40, 40, 55), (pr_s.centerx + 6, pr_s.centery - 2), 2)


def draw_rain(surface):
    if scene != "world" or rain_power <= 0.0:
        return

    profile = rain_profile()
    alpha = int(lerp(66, 190, rain_power))
    layer = pygame.Surface((W, H), pygame.SRCALPHA)
    col = (205, 223, 255)
    for drop in rain_particles:
        x1 = int(drop["x"])
        y1 = int(drop["y"])
        x2 = int(drop["x"] - profile["length"] * 0.40)
        y2 = int(drop["y"] - profile["length"])
        pygame.draw.line(layer, (col[0], col[1], col[2], alpha), (x1, y1), (x2, y2), profile["thickness"])
    surface.blit(layer, (0, 0))


def draw_biome_particles(surface):
    if scene != "world" or biome_type == "normal" or biome_power <= 0.0:
        return

    layer = pygame.Surface((W, H), pygame.SRCALPHA)
    if biome_type == "snow":
        alpha = int(lerp(80, 210, biome_power))
        for p in fx_particles:
            radius = max(1, int(p["size"] + biome_power * 1.2))
            pygame.draw.circle(layer, (245, 248, 255, alpha), (int(p["x"]), int(p["y"])), radius)
    elif biome_type == "volcanic":
        alpha = int(lerp(90, 195, biome_power))
        for p in fx_particles:
            radius = max(1, int(p["size"]))
            pygame.draw.circle(layer, (255, 165, 70, alpha), (int(p["x"]), int(p["y"])), radius)
            if radius >= 2:
                pygame.draw.circle(layer, (255, 232, 150, max(40, alpha - 50)), (int(p["x"]), int(p["y"])), max(1, radius - 1))
    elif biome_type == "desert":
        alpha = int(lerp(28, 108, biome_power))
        for p in fx_particles:
            pygame.draw.circle(layer, (220, 200, 150, alpha), (int(p["x"]), int(p["y"])), max(1, int(p["size"])))
    elif biome_type == "magic":
        alpha = int(lerp(55, 165, biome_power))
        for p in fx_particles:
            radius = max(1, int(p["size"]))
            pygame.draw.circle(layer, (225, 170, 255, alpha), (int(p["x"]), int(p["y"])), radius)
            pygame.draw.circle(layer, (180, 220, 255, max(30, alpha - 45)), (int(p["x"]), int(p["y"])), max(1, radius - 1))
    elif biome_type == "swamp":
        alpha = int(lerp(20, 80, biome_power))
        for p in fx_particles:
            rect = pygame.Rect(0, 0, int(p["size"] * 2.2), int(p["size"]))
            rect.center = (int(p["x"]), int(p["y"]))
            pygame.draw.ellipse(layer, (160, 170, 156, alpha), rect)
    surface.blit(layer, (0, 0))


# =========================
# HUD
# =========================
def draw_button(surface, rect, label, active=False, accent=False):
    if active:
        fill = (68, 110, 164)
        border = (210, 224, 255)
    elif accent:
        fill = (48, 56, 78)
        border = (168, 182, 214)
    else:
        fill = (30, 36, 50)
        border = (120, 130, 152)
    pygame.draw.rect(surface, fill, rect, border_radius=10)
    pygame.draw.rect(surface, border, rect, 2, border_radius=10)
    text = font_small.render(label, True, WHITE)
    surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


def draw_cycle_hud(surface, state):
    global biome_buttons, rain_buttons, shader_button

    panel = pygame.Rect(14, 12, W - 28, 154)
    pygame.draw.rect(surface, (*HUD_DARK, 234), panel, border_radius=14)
    pygame.draw.rect(surface, (180, 190, 210, 255), panel, 1, border_radius=14)

    shader_status = "ON" if shader_enabled else "OFF"
    rain_pct = int(rain_power * 100)
    biome_pct = int(biome_power * 100)

    title = font_big.render(
        f"{state['label']}  {format_clock(state['time01'])}  |  Shader: {shader_status}",
        True,
        WHITE,
    )
    hint1 = font_small.render(
        "WASD mover | E entrar/sair | T acelerar | Y normal | H shader | R chuva on/off",
        True,
        HUD_TEXT,
    )
    hint2 = font_small.render(
        "1 normal | 2 neve | 3 vulcânico | 4 deserto | 5 mágico | 6 pântano | [ ] chuva | - + bioma",
        True,
        HUD_TEXT,
    )
    info = font_small.render(
        f"Escuridão: {int(state['darkness'] * 100)}% | Chuva: {rain_label()} {rain_pct}% ({get_rain_level()}/{RAIN_LEVELS}) | Bioma: {BIOME_LABELS[biome_type]} {biome_pct}% ({get_biome_level()}/{BIOME_LEVELS})",
        True,
        HUD_SOFT,
    )

    surface.blit(title, (panel.x + 12, panel.y + 10))
    surface.blit(hint1, (panel.x + 12, panel.y + 42))
    surface.blit(hint2, (panel.x + 12, panel.y + 62))
    surface.blit(info, (panel.x + 12, panel.y + 84))

    row_y = panel.y + 112
    shader_button = pygame.Rect(panel.x + 12, row_y, 90, 30)
    draw_button(surface, shader_button, f"Shader {shader_status}", active=shader_enabled, accent=not shader_enabled)

    rain_buttons = {
        "toggle": pygame.Rect(shader_button.right + 12, row_y, 92, 30),
        "dec": pygame.Rect(shader_button.right + 110, row_y, 36, 30),
        "inc": pygame.Rect(shader_button.right + 152, row_y, 36, 30),
    }
    draw_button(surface, rain_buttons["toggle"], "Chuva", active=rain_power > 0.0)
    draw_button(surface, rain_buttons["dec"], "[", accent=True)
    draw_button(surface, rain_buttons["inc"], "]", accent=True)

    bx = rain_buttons["inc"].right + 16
    biome_buttons = {
        "dec": pygame.Rect(bx, row_y, 36, 30),
        "inc": pygame.Rect(bx + 42, row_y, 36, 30),
    }
    draw_button(surface, biome_buttons["dec"], "-", accent=True)
    draw_button(surface, biome_buttons["inc"], "+", accent=True)

    x = biome_buttons["inc"].right + 10
    widths = {
        "normal": 78,
        "snow": 68,
        "volcanic": 92,
        "desert": 82,
        "magic": 82,
        "swamp": 82,
    }
    for mode in BIOMES:
        rect = pygame.Rect(x, row_y, widths[mode], 30)
        biome_buttons[mode] = rect
        draw_button(surface, rect, BIOME_LABELS[mode], active=(biome_type == mode))
        x = rect.right + 8


# =========================
# SHADER
# =========================
def biome_mode_value():
    return {
        "normal": 0.0,
        "snow": 1.0,
        "volcanic": 2.0,
        "desert": 3.0,
        "magic": 4.0,
        "swamp": 5.0,
    }[biome_type]


def upload_surface(texture, surface):
    texture.write(pygame.image.tobytes(surface, "RGBA", True))


def render_shader(cycle_state):
    px, py = player_screen_center()
    program["u_player_uv"].value = (clamp(px / W, 0.0, 1.0), clamp(py / H, 0.0, 1.0))
    program["u_tint"].value = tuple(v / 255.0 for v in cycle_state["tint"])

    dark = cycle_state["darkness"]
    if scene == "inside":
        dark *= 0.50
    dark += rain_power * 0.08
    program["u_darkness"].value = float(clamp(dark, 0.0, 0.88))
    program["u_rain_power"].value = float(rain_power)
    program["u_lightning"].value = float(clamp(lightning_flash, 0.0, 1.25))
    program["u_star_strength"].value = float(cycle_state["star_strength"] if scene == "world" else 0.0)
    program["u_inside"].value = 1.0 if scene == "inside" else 0.0
    program["u_time"].value = pygame.time.get_ticks() * 0.001
    program["u_biome_mode"].value = biome_mode_value()
    program["u_biome_power"].value = float(biome_power)
    program["u_shader_enabled"].value = 1.0 if shader_enabled else 0.0

    upload_surface(scene_tex, scene_surface)
    upload_surface(hud_tex, hud_surface)

    ctx.clear(0.0, 0.0, 0.0, 1.0)
    scene_tex.use(0)
    hud_tex.use(1)
    vao.render(moderngl.TRIANGLES)
    pygame.display.flip()


# =========================
# LOOP
# =========================
running = True
while running:
    dt = clock.tick(FPS) / 1000.0
    day_time_seconds = (day_time_seconds + dt * time_speed) % DAY_DURATION_SECONDS
    time01 = day_time_seconds / DAY_DURATION_SECONDS
    cycle_state = get_cycle_state(time01)
    update_rain(dt)
    update_biome_fx(dt)

    pressed_e = False
    mouse_clicked = False
    mouse_pos = (0, 0)

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_e:
                pressed_e = True
            elif e.key == pygame.K_t:
                time_speed = TIME_SPEED_FAST
            elif e.key == pygame.K_y:
                time_speed = TIME_SPEED_NORMAL
            elif e.key == pygame.K_h:
                shader_enabled = not shader_enabled
            elif e.key == pygame.K_r:
                set_rain(rain_power <= 0.0)
            elif e.key in BIOME_KEYS:
                set_biome(BIOME_KEYS[e.key])
            elif e.key in (pygame.K_LEFTBRACKET, pygame.K_KP_MINUS):
                change_rain(-RAIN_STEP)
            elif e.key in (pygame.K_RIGHTBRACKET, pygame.K_KP_PLUS):
                change_rain(RAIN_STEP)
            elif e.key == pygame.K_MINUS:
                change_biome_power(-BIOME_STEP)
            elif e.key in (pygame.K_EQUALS, pygame.K_PLUS):
                change_biome_power(BIOME_STEP)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            mouse_clicked = True
            mouse_pos = e.pos

    if mouse_clicked:
        if shader_button and shader_button.collidepoint(mouse_pos):
            shader_enabled = not shader_enabled
        elif rain_buttons.get("toggle") and rain_buttons["toggle"].collidepoint(mouse_pos):
            set_rain(rain_power <= 0.0)
        elif rain_buttons.get("dec") and rain_buttons["dec"].collidepoint(mouse_pos):
            change_rain(-RAIN_STEP)
        elif rain_buttons.get("inc") and rain_buttons["inc"].collidepoint(mouse_pos):
            change_rain(RAIN_STEP)
        elif biome_buttons.get("dec") and biome_buttons["dec"].collidepoint(mouse_pos):
            change_biome_power(-BIOME_STEP)
        elif biome_buttons.get("inc") and biome_buttons["inc"].collidepoint(mouse_pos):
            change_biome_power(BIOME_STEP)
        else:
            for mode in BIOMES:
                rect = biome_buttons.get(mode)
                if rect and rect.collidepoint(mouse_pos):
                    set_biome(mode)
                    break

    keys = pygame.key.get_pressed()
    vx = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
    vy = (1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0)
    if vx != 0 and vy != 0:
        vx *= 0.7071
        vy *= 0.7071

    player_x += vx * SPEED * dt
    player_y += vy * SPEED * dt

    bw, bh = world_bounds()
    player_x = clamp(player_x, 18, bw - 18)
    player_y = clamp(player_y, 18, bh - 18)

    target_cam_x = player_x - W * 0.5
    target_cam_y = player_y - H * 0.55
    cam_x += (target_cam_x - cam_x) * min(1.0, dt * 7.0)
    cam_y += (target_cam_y - cam_y) * min(1.0, dt * 7.0)

    if pressed_e:
        if scene == "world":
            door = stadium_door_rect_world()
            if player_rect().colliderect(door):
                scene = "inside"
                player_x = (IN_W * TILE) // 2
                player_y = (IN_H * TILE) - 90
                cam_x, cam_y = 0, 0
        else:
            exit_r = inside_exit_rect_world()
            if player_rect().colliderect(exit_r):
                scene = "world"
                d = stadium_door_rect_world()
                player_x = d.centerx
                player_y = d.centery + 60
                cam_x, cam_y = 0, 0
    
    palette = get_palette_for_biome(biome_type, biome_power)
    scene_surface.fill(BG)
    hud_surface.fill((0, 0, 0, 0))

    if scene == "world":
        for ty in range(MAP_H):
            for tx in range(MAP_W):
                draw_tile(scene_surface, tx, ty, WORLD[ty][tx], palette)
        draw_stadium(scene_surface, palette)

        door = stadium_door_rect_world()
        if player_rect().colliderect(door):
            tip = font.render("E: entrar no estádio", True, WHITE)
            sx, sy = world_to_screen(door.centerx, door.y - 18)
            scene_surface.blit(tip, (sx - tip.get_width() // 2, sy))

        draw_player(scene_surface)
        draw_biome_particles(scene_surface)
        draw_rain(scene_surface)
        draw_cycle_hud(hud_surface, cycle_state)
        hud = f"Cena: mundo | Rain shader + bioma shader | tempo {time_speed:.0f}x e FPS: {clock.get_fps():.1f}"
        hud_surface.blit(font.render(hud, True, WHITE), (16, H - 32))
    else:
        draw_inside_stadium(scene_surface, palette)
        draw_player(scene_surface)
        draw_cycle_hud(hud_surface, cycle_state)
        hud = f"Cena: estádio | E na saída para voltar | tempo {time_speed:.0f}x"
        hud_surface.blit(font.render(hud, True, WHITE), (16, H - 32))

    render_shader(cycle_state)

pygame.quit()
scene_tex.release()
hud_tex.release()
quad.release()
vao.release()
program.release()
ctx.release()
sys.exit()
