import pygame

from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.CaixaTexto import CaixaTexto
from Codigo.Prefabs.Texto import Texto
from Codigo.Server.Login import autenticar
from Codigo.Telas.Config import salvar_config_fixa


_TELA_CARREGADA = False
_TAMANHO_CACHE = (0, 0)

_TITULO = None
_MSG = None

_CAMPO_USUARIO = None
_CAMPO_SENHA = None

_BOTAO_ACESSAR = None
_BOTAO_SAIR = None


_ESTILO_BOTAO = {
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
        "size": 32,
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


def _definir_mensagem(texto, cor=(245, 246, 255)):
    if _MSG is None:
        return
    _MSG.set_text(texto)
    _MSG.set_style(color=cor)


def _acessar(jogo, botao):
    usuario = _CAMPO_USUARIO.texto.strip() if _CAMPO_USUARIO else ""
    senha = _CAMPO_SENHA.texto.strip() if _CAMPO_SENHA else ""

    resposta = autenticar(usuario, senha)
    if resposta.get("status") != "ok":
        _definir_mensagem(resposta.get("mensagem", "Falha no login"), (255, 140, 140))
        return

    usuario_login = resposta.get("usuario") or usuario
    jogo.CONFIG["Usuario"] = usuario_login
    salvar_config_fixa(jogo.CONFIG)

    _definir_mensagem("Login feito com sucesso!", (130, 255, 160))
    jogo.CenaAlvo = "Menu"


def _montar_layout(jogo):
    global _TELA_CARREGADA, _TAMANHO_CACHE
    global _TITULO, _MSG, _CAMPO_USUARIO, _CAMPO_SENHA, _BOTAO_ACESSAR, _BOTAO_SAIR

    largura, altura = jogo.TELA.get_size()

    _TITULO = Texto(
        "Login",
        (largura // 2, int(altura * 0.18)),
        style={"size": 72, "align": "center", "outline": True, "shadow": True},
    )

    _MSG = Texto(
        "Informe usuário e senha",
        (largura // 2, int(altura * 0.28)),
        style={"size": 30, "align": "center", "outline": False, "shadow": False},
    )

    largura_campo = min(760, int(largura * 0.62))
    altura_campo = 78
    x_campo = (largura - largura_campo) // 2

    _CAMPO_USUARIO = CaixaTexto(
        pygame.Rect(x_campo, int(altura * 0.36), largura_campo, altura_campo),
        texto_inicial="",
        placeholder="Usuário",
        max_chars=32,
        ativo=True,
    )

    _CAMPO_SENHA = CaixaTexto(
        pygame.Rect(x_campo, int(altura * 0.48), largura_campo, altura_campo),
        texto_inicial="",
        placeholder="Senha",
        max_chars=32,
        ativo=True,
    )

    largura_botao = 280
    altura_botao = 88
    y_botao = int(altura * 0.65)

    _BOTAO_ACESSAR = Botao(
        pygame.Rect(largura // 2 - largura_botao - 18, y_botao, largura_botao, altura_botao),
        "Acessar",
        execute=_acessar,
        style=_ESTILO_BOTAO,
    )

    # Otimização: remove função _sair e usa lambda direto
    _BOTAO_SAIR = Botao(
        pygame.Rect(largura // 2 + 18, y_botao, largura_botao, altura_botao),
        "Sair",
        execute=lambda jogo, botao: jogo.SolicitarSair(),
        style=_ESTILO_BOTAO,
    )

    _TAMANHO_CACHE = (largura, altura)
    _TELA_CARREGADA = True


def TelaLogin(Cena, JOGO, EVENTOS, dt):
    largura, altura = JOGO.TELA.get_size()

    if (not _TELA_CARREGADA) or _TAMANHO_CACHE != (largura, altura):
        _montar_layout(JOGO)

    JOGO.TELA.fill((9, 14, 30))

    _TITULO.draw(JOGO.TELA)
    _MSG.draw(JOGO.TELA)

    _CAMPO_USUARIO.render(JOGO.TELA, EVENTOS, dt)
    _CAMPO_SENHA.render(JOGO.TELA, EVENTOS, dt)

    _BOTAO_ACESSAR.render(JOGO.TELA, EVENTOS, dt, JOGO=JOGO)
    _BOTAO_SAIR.render(JOGO.TELA, EVENTOS, dt, JOGO=JOGO)