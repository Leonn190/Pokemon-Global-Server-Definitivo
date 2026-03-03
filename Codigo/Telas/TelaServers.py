import pygame
from Codigo.Prefabs.Botao import Botao, BotaoSelecao
from Codigo.Prefabs.Mensagem import Mensagem
from Codigo.Server.ServerMenu import entrar_server, operar_server
from Codigo.Telas.TelasGenericas import SubtelaConfirmacao, SubtelaTexto
from ServerList import SERVER_LIST, salvar_server_list

_TELA_CARREGADA = False
_TAMANHO_CACHE = (0, 0)

_ESTILO_BOTAO = None
_ESTILO_BOTAO_DESTAQUE = None

_BOTAO_ADICIONAR = None
_BOTOES_SERVERS = []
_BOTOES_ACOES = {}

_SERVER_SELECIONADO = None
_SUBTELA_ATIVA = None
_MENSAGEM = None


def _persistir_servers():
    salvar_server_list()


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


def _emitir_feedback(texto, sucesso=False):
    if _MENSAGEM is None:
        return
    _MENSAGEM.emitir(texto, tipo="sucesso" if sucesso else "erro")


def _limpar_selecao():
    global _SERVER_SELECIONADO
    _SERVER_SELECIONADO = None
    for botao in _BOTOES_SERVERS:
        botao.set_selecionado(False)


def _alternar_server_selecionado(indice):
    global _SERVER_SELECIONADO
    _SERVER_SELECIONADO = None if _SERVER_SELECIONADO == indice else indice
    for i, botao in enumerate(_BOTOES_SERVERS):
        botao.set_selecionado(i == _SERVER_SELECIONADO)


def _renomear_server(novo_nome):
    if _SERVER_SELECIONADO is None:
        return

    novo_nome = novo_nome.strip()
    if not novo_nome:
        return

    SERVER_LIST[_SERVER_SELECIONADO]["nome"] = novo_nome
    _persistir_servers()
    _BOTOES_SERVERS[_SERVER_SELECIONADO].set_text(novo_nome)


def _adicionar_server(nome, link):
    nome = nome.strip()
    link = link.strip()
    if not nome or not link:
        return
    SERVER_LIST.append({"nome": nome, "ip": link})
    _persistir_servers()


def _apagar_server():
    if _SERVER_SELECIONADO is None:
        return
    SERVER_LIST.pop(_SERVER_SELECIONADO)
    _persistir_servers()
    _limpar_selecao()


def _entrar_server(jogo):
    if _SERVER_SELECIONADO is None:
        return

    server = SERVER_LIST[_SERVER_SELECIONADO]
    usuario = (jogo.CONFIG.get("Usuario") or "Visitante").strip()
    resposta = entrar_server(server.get("ip", ""), usuario)

    sucesso = resposta.get("status") == "ok"
    _emitir_feedback(resposta.get("mensagem", "Falha de comunicação com servidor"), sucesso=sucesso)


def _enviar_chave_operacao(chave):
    if _SERVER_SELECIONADO is None:
        return

    server = SERVER_LIST[_SERVER_SELECIONADO]
    resposta = operar_server(server.get("ip", ""), chave)
    sucesso = resposta.get("status") == "ok"
    _emitir_feedback(resposta.get("mensagem", "Falha de comunicação com servidor"), sucesso=sucesso)


def _abrir_subtela_renomear(JOGO):
    global _SUBTELA_ATIVA
    if _SERVER_SELECIONADO is None:
        return
    nome_atual = SERVER_LIST[_SERVER_SELECIONADO].get("nome", "")
    _SUBTELA_ATIVA = SubtelaTexto(
        JOGO.TELA.get_size(),
        "Renomear Servidor",
        nome_atual,
        enviar_callback=_renomear_server,
    )


def _abrir_subtela_adicionar(JOGO):
    global _SUBTELA_ATIVA
    _SUBTELA_ATIVA = SubtelaTexto(
        JOGO.TELA.get_size(),
        "Adicionar novo server",
        ["", ""],
        enviar_callback=_adicionar_server,
        placeholders=["Nome do servidor", "Link do servidor"],
        max_chars=[28, 50],
    )


def _abrir_subtela_apagar(JOGO):
    global _SUBTELA_ATIVA
    if _SERVER_SELECIONADO is None:
        return
    nome_server = SERVER_LIST[_SERVER_SELECIONADO].get("nome", "servidor")
    _SUBTELA_ATIVA = SubtelaConfirmacao(
        JOGO.TELA.get_size(),
        f"Deseja apagar servidor {nome_server}?",
        confirmar_callback=_apagar_server,
        titulo="Deseja apagar servidor",
    )


def _abrir_subtela_operar(JOGO):
    global _SUBTELA_ATIVA
    if _SERVER_SELECIONADO is None:
        return

    _SUBTELA_ATIVA = SubtelaTexto(
        JOGO.TELA.get_size(),
        "Digite a chave de segurança",
        "",
        enviar_callback=_enviar_chave_operacao,
        placeholders="Chave de 4 dígitos",
        max_chars=4,
    )


def _voltar_menu(Cena):
    global _SUBTELA_ATIVA, _TELA_CARREGADA
    _SUBTELA_ATIVA = None
    _limpar_selecao()
    _TELA_CARREGADA = False
    Cena.DefinirTela("MenuPrincipal")


def _montar_layout(Cena, JOGO):
    global _TELA_CARREGADA, _TAMANHO_CACHE
    global _ESTILO_BOTAO, _ESTILO_BOTAO_DESTAQUE
    global _BOTAO_ADICIONAR, _BOTOES_SERVERS, _BOTOES_ACOES, _MENSAGEM

    largura_tela, altura_tela = JOGO.TELA.get_size()

    _ESTILO_BOTAO, _ESTILO_BOTAO_DESTAQUE = _gerar_estilos()

    if _MENSAGEM is None:
        _MENSAGEM = Mensagem((largura_tela, altura_tela))
    else:
        _MENSAGEM.redimensionar((largura_tela, altura_tela))

    largura_adicionar = min(760, int(largura_tela * 0.72))
    altura_adicionar = 110
    x_adicionar = (largura_tela - largura_adicionar) // 2
    y_adicionar = int(altura_tela * 0.12)

    _BOTAO_ADICIONAR = Botao(
        pygame.Rect(x_adicionar, y_adicionar, largura_adicionar, altura_adicionar),
        "Adicionar novo server",
        execute=lambda jogo, botao: _abrir_subtela_adicionar(jogo),
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
            BotaoSelecao(
                pygame.Rect(x_server, y_server, largura_server, altura_server),
                nome_server,
                execute=lambda jogo, botao, indice=i: _alternar_server_selecionado(indice),
                style=_ESTILO_BOTAO,
                selecionado=(i == _SERVER_SELECIONADO),
            )
        )

    altura_acao = 95
    largura_acao = 220
    largura_entrar = 290
    espacamento_acao = 22

    nomes = ["Voltar", "Renomear", "Entrar", "Apagar", "Operar"]
    largura_total = largura_acao * 4 + largura_entrar + espacamento_acao * 4
    x_inicio = (largura_tela - largura_total) // 2
    y_acoes = int(altura_tela * 0.82)

    _BOTOES_ACOES = {}
    x_cursor = x_inicio
    for nome in nomes:
        largura_atual = largura_entrar if nome == "Entrar" else largura_acao
        estilo_atual = _ESTILO_BOTAO_DESTAQUE if nome == "Entrar" else _ESTILO_BOTAO

        execute = None
        if nome == "Voltar":
            execute = lambda jogo, botao: _voltar_menu(Cena)
        elif nome == "Renomear":
            execute = lambda jogo, botao: _abrir_subtela_renomear(jogo)
        elif nome == "Apagar":
            execute = lambda jogo, botao: _abrir_subtela_apagar(jogo)
        elif nome == "Entrar":
            execute = lambda jogo, botao: _entrar_server(jogo)
        elif nome == "Operar":
            execute = lambda jogo, botao: _abrir_subtela_operar(jogo)

        _BOTOES_ACOES[nome] = Botao(
            pygame.Rect(x_cursor, y_acoes, largura_atual, altura_acao),
            nome,
            execute=execute,
            style=estilo_atual,
        )
        x_cursor += largura_atual + espacamento_acao

    _TAMANHO_CACHE = (largura_tela, altura_tela)
    _TELA_CARREGADA = True


def _render_acao(nome, tela, eventos, dt, JOGO, mouse_pos=None):
    botao = _BOTOES_ACOES[nome]
    requer_selecao = nome in ("Renomear", "Apagar", "Entrar", "Operar")
    habilitado = (not requer_selecao) or (_SERVER_SELECIONADO is not None)

    botao.set_habilitado(habilitado)

    if habilitado:
        botao.set_style(
            bg=(18, 24, 44),
            bg_hover=(30, 40, 70),
            border=(20, 26, 50),
            border_hover=(255, 220, 120),
            text_style={"color": (245, 246, 255)},
        )
        botao.render(tela, eventos, dt, JOGO=JOGO, mouse_pos=mouse_pos)
        return

    botao.set_style(
        bg=(34, 34, 38),
        bg_hover=(34, 34, 38),
        bg_pressed=(34, 34, 38),
        border=(70, 70, 78),
        border_hover=(70, 70, 78),
        text_style={"color": (140, 140, 150), "hover_color": (140, 140, 150)},
    )
    botao.render(tela, eventos, dt, JOGO=JOGO, mouse_pos=mouse_pos)


def TelaServers(Cena, JOGO, EVENTOS, dt):
    global _SUBTELA_ATIVA, _TELA_CARREGADA

    largura_tela, altura_tela = JOGO.TELA.get_size()

    if (not _TELA_CARREGADA) or _TAMANHO_CACHE != (largura_tela, altura_tela):
        _montar_layout(Cena, JOGO)

    JOGO.TELA.fill((8, 12, 24))

    eventos_ativos = [] if _SUBTELA_ATIVA else EVENTOS
    mouse_pos = (-99999, -99999) if _SUBTELA_ATIVA else None

    _BOTAO_ADICIONAR.render(JOGO.TELA, eventos_ativos, dt, JOGO=JOGO, mouse_pos=mouse_pos)

    if len(SERVER_LIST) != len(_BOTOES_SERVERS):
        _montar_layout(Cena, JOGO)

    for botao in _BOTOES_SERVERS:
        botao.render(JOGO.TELA, eventos_ativos, dt, JOGO=JOGO, mouse_pos=mouse_pos)

    for nome in ("Voltar", "Renomear", "Entrar", "Apagar", "Operar"):
        _render_acao(nome, JOGO.TELA, eventos_ativos, dt, JOGO, mouse_pos=mouse_pos)

    if _SUBTELA_ATIVA:
        _SUBTELA_ATIVA.render(JOGO.TELA, EVENTOS, dt, JOGO=JOGO)
        if _SUBTELA_ATIVA.encerrada:
            _SUBTELA_ATIVA = None
            _TELA_CARREGADA = False

    _MENSAGEM.render(JOGO.TELA, dt)
