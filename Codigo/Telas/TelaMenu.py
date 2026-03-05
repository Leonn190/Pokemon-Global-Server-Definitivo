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


def TelaMenu(Cena, JOGO, EVENTOS, dt):
    global _MENU_CARREGADO
    global _FUNDO, _FUNDO_LARGURA, _FUNDO_ALTURA, _LOGO_ORIGINAL
    global _FRAMES_HOVER, _TEXTURA_BASE, _ESTILO_BOTAO, _BOTOES
    global _OVERLAY, _OVERLAY_SIZE
    global _LOGO_ESPECIAL, _LOGO_ESPECIAL_SIZE, _LOGO_ESPECIAL_CENTER, _TEMPO_LOGO
    global _FUNDO_OFFSET_X, _FUNDO_DIRECAO

    tela = JOGO.TELA
    largura_tela, altura_tela = tela.get_size()

    _TEMPO_LOGO += dt

    if not _MENU_CARREGADO:
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