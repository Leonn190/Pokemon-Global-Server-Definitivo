import pygame
from Codigo.Prefabs.Botao import Botao
from ServerList import SERVER_LIST

_TELA_CARREGADA = False
_TAMANHO_CACHE = (0, 0)

_ESTILO_BOTAO = None
_ESTILO_BOTAO_DESTAQUE = None

_BOTAO_ADICIONAR = None
_BOTOES_SERVERS = []
_BOTOES_ACOES = []


def _gerar_estilos():
    estilo_base = {
        "radius": 22,
        "border_width": 2,
        "border": (20, 26, 50),
        "border_hover": (255, 220, 120),
        "bg": (18, 24, 44),
        "bg_hover": (30, 40, 70),
        "bg_pressed": (14, 18, 34),
        "hover_scale": 1.04,
        "hover_speed": 10.0,
        "press_scale": 0.97,
        "text_style": {
            "size": 34,
            "color": (245, 246, 255),
            "hover_color": (255, 226, 120),
            "hover_speed": 18.0,
            "align": "center",
            "outline": True,
            "outline_color": (0, 0, 0),
            "outline_thickness": 1,
            "shadow": True,
            "shadow_color": (0, 0, 0, 180),
            "shadow_offset": (2, 2),
        },
    }

    estilo_destaque = dict(estilo_base)
    estilo_destaque["text_style"] = dict(estilo_base["text_style"])
    estilo_destaque["text_style"]["size"] = 38
    estilo_destaque["hover_scale"] = 1.06

    return estilo_base, estilo_destaque


def _montar_layout(Cena, JOGO):
    global _TELA_CARREGADA, _TAMANHO_CACHE
    global _ESTILO_BOTAO, _ESTILO_BOTAO_DESTAQUE
    global _BOTAO_ADICIONAR, _BOTOES_SERVERS, _BOTOES_ACOES

    largura_tela, altura_tela = JOGO.TELA.get_size()

    _ESTILO_BOTAO, _ESTILO_BOTAO_DESTAQUE = _gerar_estilos()

    largura_adicionar = min(760, int(largura_tela * 0.72))
    altura_adicionar = 110
    x_adicionar = (largura_tela - largura_adicionar) // 2
    y_adicionar = int(altura_tela * 0.12)

    _BOTAO_ADICIONAR = Botao(
        pygame.Rect(x_adicionar, y_adicionar, largura_adicionar, altura_adicionar),
        "Adicionar novo server",
        style=_ESTILO_BOTAO_DESTAQUE,
    )

    _BOTOES_SERVERS = []
    largura_server = min(640, int(largura_tela * 0.62))
    altura_server = 80
    espacamento_server = 14
    y_base_servers = y_adicionar + altura_adicionar + 36

    for i, server in enumerate(SERVER_LIST[:5]):
        nome_server = server.get("nome", f"Server {i + 1}")
        x_server = (largura_tela - largura_server) // 2
        y_server = y_base_servers + i * (altura_server + espacamento_server)
        _BOTOES_SERVERS.append(
            Botao(
                pygame.Rect(x_server, y_server, largura_server, altura_server),
                nome_server,
                style=_ESTILO_BOTAO,
            )
        )

    nomes_acoes = ["Voltar", "Renomear", "Entrar", "Apagar", "Operar"]
    _BOTOES_ACOES = []

    altura_acao = 95
    largura_acao = 220
    largura_entrar = 290
    espacamento_acao = 22

    largura_total = largura_acao * 4 + largura_entrar + espacamento_acao * 4
    x_inicio = (largura_tela - largura_total) // 2
    y_acoes = int(altura_tela * 0.82)

    x_cursor = x_inicio
    for nome in nomes_acoes:
        largura_atual = largura_entrar if nome == "Entrar" else largura_acao
        estilo_atual = _ESTILO_BOTAO_DESTAQUE if nome == "Entrar" else _ESTILO_BOTAO
        execute = (lambda jogo, botao: Cena.DefinirTela("MenuPrincipal")) if nome == "Voltar" else None

        _BOTOES_ACOES.append(
            Botao(
                pygame.Rect(x_cursor, y_acoes, largura_atual, altura_acao),
                nome,
                execute=execute,
                style=estilo_atual,
            )
        )
        x_cursor += largura_atual + espacamento_acao

    _TAMANHO_CACHE = (largura_tela, altura_tela)
    _TELA_CARREGADA = True


def TelaServers(Cena, JOGO, EVENTOS, dt):
    largura_tela, altura_tela = JOGO.TELA.get_size()

    if (not _TELA_CARREGADA) or _TAMANHO_CACHE != (largura_tela, altura_tela):
        _montar_layout(Cena, JOGO)

    JOGO.TELA.fill((8, 12, 24))

    for botao in [_BOTAO_ADICIONAR, *_BOTOES_SERVERS, *_BOTOES_ACOES]:
        botao.render(JOGO.TELA, EVENTOS, dt, JOGO=JOGO)
