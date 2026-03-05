import pygame

from Codigo.Modulos.Sonoridades import VerificaSonoridade
from Codigo.Prefabs.Barra import Barra
from Codigo.Prefabs.Botao import Botao, BotaoAlavanca
from Codigo.Prefabs.Texto import Texto
from Codigo.Telas.TelasGenericas import SubtelaConfirmacao

_CONFIG_CARREGADA = False
_TAMANHO_CACHE = (0, 0)

_BARRAS = {}
_BOTOES_TOGGLE = {}
_BOTAO_SALVAR = None
_BOTAO_CANCELAR = None
_BOTAO_DESLOGAR = None
_TITULO = None

_SUBTELA_ATIVA = None

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


def salvar_config_fixa(config):
    from pathlib import Path

    caminho = Path("Outros/ConfigFixa.py")
    caminho.write_text("ConfigFixa = " + repr(dict(config)) + "\n", encoding="utf-8")


def _voltar_menu(Cena, JOGO):
    retorno = JOGO.INFO.pop("ConfigRetorno", None)
    if isinstance(retorno, dict) and retorno.get("Cena") == "Mundo":
        JOGO.CenaAlvo = "Mundo"
        return
    if getattr(JOGO.Cena, "ID", "") == "Mundo":
        JOGO.Cena.TelaAtual = None
        return
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
    _voltar_menu(Cena, JOGO)


def _executar_salvar(Cena, JOGO, botao):
    salvar_config_fixa(JOGO.CONFIG)
    _voltar_menu(Cena, JOGO)


def _confirmar_deslogar(Cena, JOGO):
    JOGO.CONFIG["Usuario"] = None
    salvar_config_fixa(JOGO.CONFIG)
    Cena.DefinirTela("MenuPrincipal")
    JOGO.CenaAlvo = "Login"


def _abrir_confirmacao_deslogar(Cena, JOGO):
    global _SUBTELA_ATIVA
    _SUBTELA_ATIVA = SubtelaConfirmacao(
        JOGO.TELA.get_size(),
        "Você será desconectado da conta atual.",
        confirmar_callback=lambda: _confirmar_deslogar(Cena, JOGO),
        titulo="Confirmar logout",
    )


def _montar_layout(Cena, JOGO):
    global _CONFIG_CARREGADA, _TAMANHO_CACHE, _CONFIG_INICIAL
    global _BARRAS, _BOTOES_TOGGLE, _BOTAO_SALVAR, _BOTAO_CANCELAR, _BOTAO_DESLOGAR, _TITULO

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

    estilo_deslogar = dict(estilo_acao)
    estilo_deslogar["text_style"] = dict(estilo_acao["text_style"])
    estilo_deslogar["bg"] = (105, 38, 38)
    estilo_deslogar["bg_hover"] = (132, 48, 48)
    estilo_deslogar["bg_pressed"] = (86, 30, 30)

    _BOTAO_DESLOGAR = Botao(
        pygame.Rect(largura_tela // 2 - (largura_acao // 2), y_acao - 98, largura_acao, 78),
        "Deslogar",
        execute=lambda jogo, botao: _abrir_confirmacao_deslogar(Cena, jogo),
        style=estilo_deslogar,
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
    global _CONFIG_CARREGADA, _SUBTELA_ATIVA
    _CONFIG_CARREGADA = False
    _SUBTELA_ATIVA = None


def TelaConfig(Cena, JOGO, EVENTOS, dt):
    global _SUBTELA_ATIVA

    largura_tela, altura_tela = JOGO.TELA.get_size()
    if (not _CONFIG_CARREGADA) or _TAMANHO_CACHE != (largura_tela, altura_tela):
        _montar_layout(Cena, JOGO)

    JOGO.TELA.fill((10, 14, 28))
    _TITULO.draw(JOGO.TELA)

    eventos_ativos = [] if _SUBTELA_ATIVA else EVENTOS
    mouse_pos = (-99999, -99999) if _SUBTELA_ATIVA else None

    alterou_fps = _BARRAS["FPS"].render(JOGO.TELA, eventos_ativos)
    alterou_claridade = _BARRAS["Claridade"].render(JOGO.TELA, eventos_ativos)
    alterou_volume = _BARRAS["Volume"].render(JOGO.TELA, eventos_ativos)

    if alterou_fps:
        JOGO.CONFIG["FPS"] = int(round(_BARRAS["FPS"].valor))

    if alterou_claridade:
        JOGO.CONFIG["Claridade"] = int(round(_BARRAS["Claridade"].valor))

    if alterou_volume:
        JOGO.CONFIG["Volume"] = max(0.0, min(1.0, _BARRAS["Volume"].valor / 100.0))
        VerificaSonoridade(JOGO.CONFIG)

    for botao in _BOTOES_TOGGLE.values():
        botao.render(JOGO.TELA, eventos_ativos, dt, JOGO=JOGO, mouse_pos=mouse_pos)

    _BOTAO_DESLOGAR.render(JOGO.TELA, eventos_ativos, dt, JOGO=JOGO, mouse_pos=mouse_pos)
    _BOTAO_CANCELAR.render(JOGO.TELA, eventos_ativos, dt, JOGO=JOGO, mouse_pos=mouse_pos)
    _BOTAO_SALVAR.render(JOGO.TELA, eventos_ativos, dt, JOGO=JOGO, mouse_pos=mouse_pos)

    if _SUBTELA_ATIVA:
        _SUBTELA_ATIVA.render(JOGO.TELA, EVENTOS, dt, JOGO=JOGO)
        if _SUBTELA_ATIVA.encerrada:
            _SUBTELA_ATIVA = None
