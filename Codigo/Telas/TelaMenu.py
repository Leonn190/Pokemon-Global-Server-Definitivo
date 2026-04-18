import pygame
from pathlib import Path
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Imagem import Imagem

_CAMINHO_FUNDO = Path("Recursos/Visual/Fundos/FundoMenu.jpg")
_CAMINHO_LOGO = Path("Recursos/Visual/Icones/GlobalServer/Logo.png")
_PASTA_TEXTURA = Path("Recursos/Visual/Texturas/TexturaCosmica")

_MENU_CARREGADO = False

_FUNDO = None
_FUNDO_LARGURA = 0
_FUNDO_ALTURA = 0

_LOGO_ORIGINAL = None

_FRAMES_HOVER = None
_TEXTURA_BASE = None
_ESTILO_BOTAO = None
_BOTOES = None

_OVERLAY = None
_OVERLAY_SIZE = (0, 0)

# --- logo com efeito interno (cache)
_LOGO_ESPECIAL = None
_LOGO_ESPECIAL_SIZE = (0, 0)
_LOGO_ESPECIAL_CENTER = (0, 0)
_TEMPO_LOGO = 0.0

_FUNDO_OFFSET_X = 0.0
_FUNDO_DIRECAO = 1
_FUNDO_VELOCIDADE = 32.0

_SHADER_LOGO_MENU = """
    #version 330
    in vec2 v_uv;
    out vec4 f_color;
    uniform sampler2D u_texture;
    uniform float u_time;
    uniform float u_alpha;
    uniform vec2 u_rect_size;

    float clamp01(float v) { return clamp(v, 0.0, 1.0); }

    void main() {
        vec4 base = texture(u_texture, v_uv);
        if (base.a <= 0.001) {
            discard;
        }

        float yy = v_uv.y * 220.0;
        float t = u_time;
        float speed = 0.9;
        float u = 0.5 + 0.25 * sin(yy * (6.283185307 / 220.0) + t * speed)
                    + 0.25 * sin(yy * 0.02 - t * (speed * 1.2));
        u = clamp01(u);

        vec3 cA = vec3(70.0, 170.0, 255.0) / 255.0;
        vec3 cB = vec3(255.0, 70.0, 140.0) / 255.0;
        vec3 cC = vec3(140.0, 100.0, 255.0) / 255.0;
        vec3 grad = mix(cA, cB, u);

        float sh = 0.5 + 0.5 * sin(t * 2.4 + yy * 0.06);
        grad *= (0.92 + 0.16 * sh);
        float mixc = 0.18 * (0.5 + 0.5 * sin(t * 0.7 + yy * 0.01));
        grad = mix(grad, cC, mixc);

        float amp = 9.0;
        float dx = sin(yy * 0.04 + t * 2.0) * amp + sin(yy * 0.013 - t * 1.6) * (amp * 0.55);
        vec2 uv_warp = vec2(v_uv.x - (dx / max(1.0, u_rect_size.x)), v_uv.y);
        vec4 mask = texture(u_texture, uv_warp);

        float overlay_alpha = mask.a * clamp01(u_alpha);
        vec3 out_rgb = mix(base.rgb, grad, overlay_alpha);
        f_color = vec4(out_rgb, base.a);
    }
"""


def _garantir_menu_carregado(Cena, altura_tela, largura_tela):
    global _MENU_CARREGADO
    global _FUNDO, _FUNDO_LARGURA, _FUNDO_ALTURA, _LOGO_ORIGINAL
    global _FRAMES_HOVER, _TEXTURA_BASE, _ESTILO_BOTAO, _BOTOES
    if _MENU_CARREGADO:
        return

    _FUNDO = pygame.image.load(str(_CAMINHO_FUNDO)).convert()
    _FUNDO_LARGURA, _FUNDO_ALTURA = _FUNDO.get_size()
    _LOGO_ORIGINAL = pygame.image.load(str(_CAMINHO_LOGO)).convert_alpha()

    frames = sorted(
        _PASTA_TEXTURA.glob("gif_frame*.png"),
        key=lambda p: int(p.stem.replace("gif_frame", ""))
    )
    _FRAMES_HOVER = [pygame.image.load(str(f)).convert_alpha() for i, f in enumerate(frames) if i % 6 == 0]
    _TEXTURA_BASE = _FRAMES_HOVER[0] if _FRAMES_HOVER else None

    _ESTILO_BOTAO = {
        "radius": 26,
        "border_width": 2,
        "border": (14, 18, 32),
        "border_hover": (255, 220, 120),
        "bg": (12, 14, 22),
        "bg_hover": (22, 26, 44),
        "bg_pressed": (10, 12, 20),
        "bg_image": _TEXTURA_BASE,
        "bg_frames_hover": _FRAMES_HOVER,
        "bg_frames_mode": "ticks",
        "bg_frames_interval_ms": 65,
        "bg_frames_scale_mode": "fast",
        "hover_scale": 1.06,
        "hover_speed": 11.0,
        "press_scale": 0.965,
        "text_color_steps": 12,
        "text_update_on_change": True,
        "text_style": {
            "size": 42,
            "color": (245, 246, 255),
            "hover_color": (255, 226, 120),
            "hover_speed": 18.0,
            "align": "center",
            "outline": True,
            "outline_color": (0, 0, 0),
            "outline_thickness": 1,
            "shadow": True,
            "shadow_color": (0, 0, 0, 190),
            "shadow_offset": (2, 2),
            "highlight": False,
        },
    }

    largura_botao = 480
    altura_botao = 120
    espacamento = 28
    inicio_y = int(altura_tela * 0.58)
    x = (largura_tela - largura_botao) // 2

    _BOTOES = [
        Botao(
            pygame.Rect(x, inicio_y + (altura_botao + espacamento) * 0, largura_botao, altura_botao),
            "Jogar",
            execute=lambda jogo, botao: Cena.DefinirTela("Servers"),
            style=_ESTILO_BOTAO,
        ),
        Botao(
            pygame.Rect(x, inicio_y + (altura_botao + espacamento) * 1, largura_botao, altura_botao),
            "Configurações",
            execute=lambda jogo, botao: Cena.DefinirTela("Config"),
            style=_ESTILO_BOTAO,
        ),
        Botao(
            pygame.Rect(x, inicio_y + (altura_botao + espacamento) * 2, largura_botao, altura_botao),
            "Sair",
            execute=lambda jogo, botao: jogo.SolicitarSair(),
            style=_ESTILO_BOTAO,
        ),
    ]

    _MENU_CARREGADO = True


def TelaMenu(Cena, JOGO, EVENTOS, dt, tela_destino=None):
    global _MENU_CARREGADO
    global _FUNDO, _FUNDO_LARGURA, _FUNDO_ALTURA, _LOGO_ORIGINAL
    global _FRAMES_HOVER, _TEXTURA_BASE, _ESTILO_BOTAO, _BOTOES
    global _OVERLAY, _OVERLAY_SIZE
    global _LOGO_ESPECIAL, _LOGO_ESPECIAL_SIZE, _LOGO_ESPECIAL_CENTER, _TEMPO_LOGO
    global _FUNDO_OFFSET_X, _FUNDO_DIRECAO

    tela = tela_destino if tela_destino is not None else JOGO.TELA
    largura_tela, altura_tela = tela.get_size()

    _TEMPO_LOGO += dt

    _garantir_menu_carregado(Cena, altura_tela, largura_tela)

    # ===== fundo com pan =====
    max_offset = max(0, _FUNDO_LARGURA - largura_tela)
    if max_offset > 0:
        _FUNDO_OFFSET_X += _FUNDO_VELOCIDADE * dt * _FUNDO_DIRECAO
        if _FUNDO_OFFSET_X >= max_offset:
            _FUNDO_OFFSET_X = float(max_offset)
            _FUNDO_DIRECAO = -1
        elif _FUNDO_OFFSET_X <= 0:
            _FUNDO_OFFSET_X = 0.0
            _FUNDO_DIRECAO = 1

    tela.blit(_FUNDO, (-int(_FUNDO_OFFSET_X), 0))

    # overlay se precisar
    if _FUNDO_ALTURA != altura_tela:
        if _OVERLAY is None or _OVERLAY_SIZE != (largura_tela, altura_tela):
            _OVERLAY = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
            _OVERLAY.fill((0, 0, 0, 70))
            _OVERLAY_SIZE = (largura_tela, altura_tela)
        tela.blit(_OVERLAY, (0, 0))

    # ===== logo (somente efeito interno na própria imagem) =====
    largura_logo = min(int(largura_tela * 0.36), _LOGO_ORIGINAL.get_width())
    altura_logo = int(_LOGO_ORIGINAL.get_height() * (largura_logo / _LOGO_ORIGINAL.get_width()))
    alvo = (largura_logo, altura_logo)
    centro_logo = (largura_tela // 2, int(altura_tela * 0.30))

    if _LOGO_ESPECIAL is None or _LOGO_ESPECIAL_SIZE != alvo or _LOGO_ESPECIAL_CENTER != centro_logo:
        _LOGO_ESPECIAL = Imagem(
            str(_CAMINHO_LOGO),
            center=centro_logo,
            size=alvo,
            effect_alpha=160,
        )
        _LOGO_ESPECIAL_SIZE = alvo
        _LOGO_ESPECIAL_CENTER = centro_logo

    _LOGO_ESPECIAL.render(tela, _TEMPO_LOGO)

    # ===== botões =====
    for botao in _BOTOES:
        botao.render(tela, EVENTOS, dt, JOGO=JOGO)


def TelaMenuGL(Cena, JOGO, EVENTOS, dt, renderer):
    global _FUNDO_OFFSET_X, _FUNDO_DIRECAO, _TEMPO_LOGO

    tela_largura, tela_altura = JOGO.TELA.get_size()
    _garantir_menu_carregado(Cena, tela_altura, tela_largura)

    _TEMPO_LOGO += dt
    max_offset = max(0, _FUNDO_LARGURA - tela_largura)
    if max_offset > 0:
        _FUNDO_OFFSET_X += _FUNDO_VELOCIDADE * dt * _FUNDO_DIRECAO
        if _FUNDO_OFFSET_X >= max_offset:
            _FUNDO_OFFSET_X = float(max_offset)
            _FUNDO_DIRECAO = -1
        elif _FUNDO_OFFSET_X <= 0:
            _FUNDO_OFFSET_X = 0.0
            _FUNDO_DIRECAO = 1

    src_x = int(_FUNDO_OFFSET_X)
    uv_x0 = src_x / max(1, _FUNDO_LARGURA)
    uv_x1 = min(1.0, (src_x + tela_largura) / max(1, _FUNDO_LARGURA))
    vis_h = min(tela_altura, _FUNDO_ALTURA)
    uv_y1 = vis_h / max(1, _FUNDO_ALTURA)
    renderer.desenhar_surface_cacheada(
        "menu:fundo",
        _FUNDO,
        pygame.Rect(0, 0, tela_largura, vis_h),
        dirty=False,
        uv_rect=(uv_x0, 0.0, uv_x1, uv_y1),
    )

    if _FUNDO_ALTURA != tela_altura:
        renderer.desenhar_retangulo((0, 0, tela_largura, tela_altura), (0, 0, 0, 70))

    largura_logo = min(int(tela_largura * 0.36), _LOGO_ORIGINAL.get_width())
    altura_logo = int(_LOGO_ORIGINAL.get_height() * (largura_logo / _LOGO_ORIGINAL.get_width()))
    alvo = (largura_logo, altura_logo)
    centro_logo = (tela_largura // 2, int(tela_altura * 0.30))
    global _LOGO_ESPECIAL, _LOGO_ESPECIAL_SIZE, _LOGO_ESPECIAL_CENTER
    if _LOGO_ESPECIAL is None or _LOGO_ESPECIAL_SIZE != alvo or _LOGO_ESPECIAL_CENTER != centro_logo:
        _LOGO_ESPECIAL = Imagem(str(_CAMINHO_LOGO), center=centro_logo, size=alvo, effect_alpha=160)
        _LOGO_ESPECIAL_SIZE = alvo
        _LOGO_ESPECIAL_CENTER = centro_logo
    _LOGO_ESPECIAL._gl_efeito_habilitado = True
    _LOGO_ESPECIAL._gl_shader_key = "menu_logo_fx"
    if hasattr(renderer, "registrar_shader_textura") and not renderer.possui_shader("menu_logo_fx"):
        renderer.registrar_shader_textura("menu_logo_fx", _SHADER_LOGO_MENU)

    _LOGO_ESPECIAL.render_gl(renderer, _TEMPO_LOGO)
    for botao in _BOTOES:
        botao.render_gl(renderer, EVENTOS, dt, JOGO=JOGO)
