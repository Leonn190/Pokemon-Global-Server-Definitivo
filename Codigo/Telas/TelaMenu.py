import pygame
from pathlib import Path
from Codigo.Prefabs.Botao import Botao

# =========================
# CONFIG / CACHE (sem convert aqui!)
# =========================
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

_FUNDO_OFFSET_X = 0.0
_FUNDO_DIRECAO = 1
_FUNDO_VELOCIDADE = 26.0


def TelaMenu(JOGO, EVENTOS, dt):
    global _MENU_CARREGADO
    global _FUNDO, _FUNDO_LARGURA, _FUNDO_ALTURA, _LOGO_ORIGINAL
    global _FRAMES_HOVER, _TEXTURA_BASE, _ESTILO_BOTAO, _BOTOES
    global _OVERLAY, _OVERLAY_SIZE
    global _FUNDO_OFFSET_X, _FUNDO_DIRECAO

    tela = JOGO.TELA
    largura_tela, altura_tela = tela.get_size()

    # -------------------------
    # CARREGA 1 VEZ (AGORA o display já existe, então pode convert)
    # -------------------------
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
            "radius": 22,
            "border_width": 2,
            "border": (22, 26, 40),
            "border_hover": (252, 234, 125),
            "bg": (18, 20, 30),
            "bg_hover": (38, 44, 66),
            "bg_pressed": (16, 19, 28),
            "bg_image": _TEXTURA_BASE,
            "bg_frames_hover": _FRAMES_HOVER,
            "bg_frames_fps": 12,
            "hover_scale": 1.08,
            "hover_speed": 14.0,
            "press_scale": 0.97,
            "text_style": {
                "size": 40,
                "color": (245, 246, 255),
                "hover_color": (255, 232, 80),
                "hover_speed": 28.0,
                "outline": True,
                "outline_color": (0, 0, 0),
                "outline_thickness": 2,
                "shadow": True,
                "shadow_color": (0, 0, 0, 170),
                "shadow_offset": (2, 2),
            },
        }

        # cria botões 1 vez (posição depende do tamanho atual da tela)
        largura_botao = 480
        altura_botao = 120
        espacamento = 28
        inicio_y = int(altura_tela * 0.58)
        x = (largura_tela - largura_botao) // 2

        _BOTOES = [
            Botao(pygame.Rect(x, inicio_y + (altura_botao + espacamento) * 0, largura_botao, altura_botao), "Jogar", style=_ESTILO_BOTAO),
            Botao(pygame.Rect(x, inicio_y + (altura_botao + espacamento) * 1, largura_botao, altura_botao), "Configurações", style=_ESTILO_BOTAO),
            Botao(pygame.Rect(x, inicio_y + (altura_botao + espacamento) * 2, largura_botao, altura_botao), "Sair", style=_ESTILO_BOTAO),
        ]

        _MENU_CARREGADO = True

    # -------------------------
    # FUNDO (pan) — leve
    # -------------------------
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

    # -------------------------
    # OVERLAY ESCURO (cache por tamanho)
    # -------------------------
    if _FUNDO_ALTURA != altura_tela:
        if _OVERLAY is None or _OVERLAY_SIZE != (largura_tela, altura_tela):
            _OVERLAY = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
            _OVERLAY.fill((0, 0, 0, 70))
            _OVERLAY_SIZE = (largura_tela, altura_tela)
        tela.blit(_OVERLAY, (0, 0))

    # -------------------------
    # LOGO (se sua resolução é fixa, dá pra cachear também; por enquanto ok)
    # -------------------------
    largura_logo = min(int(largura_tela * 0.36), _LOGO_ORIGINAL.get_width())
    altura_logo = int(_LOGO_ORIGINAL.get_height() * (largura_logo / _LOGO_ORIGINAL.get_width()))
    logo = pygame.transform.smoothscale(_LOGO_ORIGINAL, (largura_logo, altura_logo)).convert_alpha()
    logo_pos = (largura_tela // 2 - largura_logo // 2, int(altura_tela * 0.30) - altura_logo // 2)
    tela.blit(logo, logo_pos)

    # -------------------------
    # BOTÕES
    # -------------------------
    for botao in _BOTOES:
        botao.render(tela, EVENTOS, dt, JOGO=JOGO)