import pygame
from pathlib import Path

from Codigo.Modulos.Sonoridades import VerificaSonoridade
from Codigo.Prefabs.Barra import Barra
from Codigo.Prefabs.Botao import Botao, BotaoAlavanca
from Codigo.Prefabs.Texto import Texto

_CONFIG_CARREGADA = False
_TAMANHO_CACHE = (0, 0)

_BARRAS = {}
_BOTOES_TOGGLE = {}
_BOTAO_SALVAR = None
_BOTAO_CANCELAR = None
_TITULO = None

_CONFIG_INICIAL = None


def _estilo_base():
    return {
        "radius": 18,
        "border_width": 2,
        "border": (18, 24, 44),
        "border_hover": (255, 220, 120),
        "bg": (40, 56, 98),
        "bg_hover": (58, 79, 136),
        "bg_pressed": (34, 47, 82),
        "hover_scale": 1.03,
        "hover_speed": 10.0,
        "press_scale": 0.97,
        "text_style": {
            "size": 28,
            "color": (245, 246, 255),
            "hover_color": (255, 235, 130),
            "hover_speed": 18.0,
            "align": "center",
            "outline": True,
            "outline_color": (0, 0, 0),
            "outline_thickness": 1,
            "shadow": True,
            "shadow_color": (0, 0, 0, 160),
            "shadow_offset": (2, 2),
        },
    }


def _salvar_config(config):
    caminho = Path("ConfigFixa.py")
    caminho.write_text("ConfigFixa = " + repr(config) + "\n", encoding="utf-8")


def _voltar_menu(Cena):
    Cena.DefinirTela("MenuPrincipal")


def _ao_toggle(chave, jogo, estado):
    jogo.CONFIG[chave] = estado
    if chave == "Mudo":
        VerificaSonoridade(jogo.CONFIG)


def _executar_cancelar(Cena, JOGO, botao):
    JOGO.CONFIG.clear()
    JOGO.CONFIG.update(_CONFIG_INICIAL)

    _BARRAS["FPS"].set_valor(JOGO.CONFIG["FPS"])
    _BARRAS["Claridade"].set_valor(JOGO.CONFIG["Claridade"])
    _BARRAS["Volume"].set_valor(JOGO.CONFIG["Volume"] * 100)

    for chave, botao_toggle in _BOTOES_TOGGLE.items():
        botao_toggle.set_estado(JOGO.CONFIG[chave])

    VerificaSonoridade(JOGO.CONFIG)
    _voltar_menu(Cena)


def _executar_salvar(Cena, JOGO, botao):
    _salvar_config(JOGO.CONFIG)
    _voltar_menu(Cena)


def _montar_layout(Cena, JOGO):
    global _CONFIG_CARREGADA, _TAMANHO_CACHE, _CONFIG_INICIAL
    global _BARRAS, _BOTOES_TOGGLE, _BOTAO_SALVAR, _BOTAO_CANCELAR, _TITULO

    largura_tela, altura_tela = JOGO.TELA.get_size()
    estilo = _estilo_base()

    _CONFIG_INICIAL = dict(JOGO.CONFIG)

    largura_barra = min(900, int(largura_tela * 0.68))
    x_barra = (largura_tela - largura_barra) // 2
    y_inicial = int(altura_tela * 0.20)
    espacamento = 110

    _BARRAS = {
        "FPS": Barra(pygame.Rect(x_barra, y_inicial + espacamento * 0, largura_barra, 26), "FPS", JOGO.CONFIG["FPS"], 30, 300, 0),
        "Claridade": Barra(pygame.Rect(x_barra, y_inicial + espacamento * 1, largura_barra, 26), "Claridade", JOGO.CONFIG["Claridade"], 0, 100, 0),
        "Volume": Barra(pygame.Rect(x_barra, y_inicial + espacamento * 2, largura_barra, 26), "Volume", JOGO.CONFIG["Volume"] * 100, 0, 100, 0),
    }

    largura_toggle = 320
    altura_toggle = 70
    espaco_x = 30
    y_toggles = y_inicial + espacamento * 3 + 20
    x_toggles = (largura_tela - (largura_toggle * 2 + espaco_x)) // 2

    chaves = ["Mudo", "FPS Visivel", "Cords Visiveis", "Ping Visivel"]
    _BOTOES_TOGGLE = {}
    for i, chave in enumerate(chaves):
        coluna = i % 2
        linha = i // 2
        x = x_toggles + coluna * (largura_toggle + espaco_x)
        y = y_toggles + linha * (altura_toggle + 18)

        estilo_toggle = dict(estilo)
        estilo_toggle["text_style"] = dict(estilo["text_style"])

        botao_toggle = BotaoAlavanca(
            pygame.Rect(x, y, largura_toggle, altura_toggle),
            chave,
            estado_inicial=JOGO.CONFIG[chave],
            execute=lambda jogo, estado, botao, chave=chave: _ao_toggle(chave, jogo, estado),
            style=estilo_toggle,
        )
        _BOTOES_TOGGLE[chave] = botao_toggle

    estilo_acao = dict(estilo)
    estilo_acao["text_style"] = dict(estilo["text_style"])
    estilo_acao["text_style"]["size"] = 34

    largura_acao = 260
    altura_acao = 80
    y_acao = int(altura_tela * 0.88)
    x_cancelar = largura_tela // 2 - largura_acao - 20
    x_salvar = largura_tela // 2 + 20

    _BOTAO_CANCELAR = Botao(
        pygame.Rect(x_cancelar, y_acao, largura_acao, altura_acao),
        "Cancelar",
        execute=lambda jogo, botao: _executar_cancelar(Cena, jogo, botao),
        style=estilo_acao,
    )
    _BOTAO_SALVAR = Botao(
        pygame.Rect(x_salvar, y_acao, largura_acao, altura_acao),
        "Salvar",
        execute=lambda jogo, botao: _executar_salvar(Cena, jogo, botao),
        style=estilo_acao,
    )

    _TITULO = Texto(
        "Configurações",
        pos=(largura_tela // 2, int(altura_tela * 0.08)),
        style={
            "size": 54,
            "align": "center",
            "outline": True,
            "outline_color": (0, 0, 0),
            "outline_thickness": 2,
            "shadow": True,
            "shadow_color": (0, 0, 0, 180),
            "shadow_offset": (2, 2),
        },
    )

    _TAMANHO_CACHE = (largura_tela, altura_tela)
    _CONFIG_CARREGADA = True


def ResetTelaConfig():
    global _CONFIG_CARREGADA
    _CONFIG_CARREGADA = False


def TelaConfig(Cena, JOGO, EVENTOS, dt):
    largura_tela, altura_tela = JOGO.TELA.get_size()
    if (not _CONFIG_CARREGADA) or _TAMANHO_CACHE != (largura_tela, altura_tela):
        _montar_layout(Cena, JOGO)

    JOGO.TELA.fill((10, 14, 28))
    _TITULO.draw(JOGO.TELA)

    alterou_fps = _BARRAS["FPS"].render(JOGO.TELA, EVENTOS)
    alterou_claridade = _BARRAS["Claridade"].render(JOGO.TELA, EVENTOS)
    alterou_volume = _BARRAS["Volume"].render(JOGO.TELA, EVENTOS)

    if alterou_fps:
        JOGO.CONFIG["FPS"] = int(round(_BARRAS["FPS"].valor))

    if alterou_claridade:
        JOGO.CONFIG["Claridade"] = int(round(_BARRAS["Claridade"].valor))

    if alterou_volume:
        JOGO.CONFIG["Volume"] = max(0.0, min(1.0, _BARRAS["Volume"].valor / 100.0))
        VerificaSonoridade(JOGO.CONFIG)

    for botao in _BOTOES_TOGGLE.values():
        botao.render(JOGO.TELA, EVENTOS, dt, JOGO=JOGO)

    _BOTAO_CANCELAR.render(JOGO.TELA, EVENTOS, dt, JOGO=JOGO)
    _BOTAO_SALVAR.render(JOGO.TELA, EVENTOS, dt, JOGO=JOGO)
