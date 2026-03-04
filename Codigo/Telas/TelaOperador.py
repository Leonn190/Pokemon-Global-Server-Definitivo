import threading

import pygame

from Codigo.Prefabs.Botao import Botao, BotaoAlavanca
from Codigo.Prefabs.Mensagem import Mensagem
from Codigo.Server.ServerMenu import definir_mundo_server, definir_server_ligado, operar_server
from Codigo.Telas.TelasGenericas import SubtelaConfirmacao, SubtelaTexto
from ServerList import SERVER_LIST

_TELA_CARREGADA = False
_TAMANHO_CACHE = (0, 0)

_MENSAGEM = None
_SUBTELA_ATIVA = None

_BOTAO_VOLTAR = None
_BOTAO_LIGAR = None
_BOTAO_MUNDO = None

_REQUISICAO_THREAD = None
_REQUISICAO_RESULTADO = None


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


def _emitir_feedback(texto, sucesso=False):
    if _MENSAGEM is None:
        return
    _MENSAGEM.emitir(texto, tipo="sucesso" if sucesso else "erro")


def _emitir_info(texto):
    if _MENSAGEM is None:
        return
    _MENSAGEM.emitir(texto, tipo="info")


def _get_server_ip(cena):
    indice = getattr(cena, "ServerOperadorIndice", None)
    if indice is None or indice >= len(SERVER_LIST):
        return ""
    return SERVER_LIST[indice].get("ip", "")


def _worker(tipo, ip, payload):
    global _REQUISICAO_RESULTADO

    if tipo == "ligado":
        resposta = definir_server_ligado(ip, payload)
    elif tipo == "mundo":
        resposta = definir_mundo_server(ip, payload)
    else:
        resposta = operar_server(ip, payload)

    _REQUISICAO_RESULTADO = {"tipo": tipo, "resposta": resposta, "payload": payload}


def _iniciar_requisicao(tipo, ip, payload=None, mensagem="Comunicando com SimuladorServerJogo..."):
    global _REQUISICAO_THREAD, _REQUISICAO_RESULTADO
    if _REQUISICAO_THREAD and _REQUISICAO_THREAD.is_alive():
        return False

    _REQUISICAO_RESULTADO = None
    _emitir_info(mensagem)
    _REQUISICAO_THREAD = threading.Thread(target=_worker, args=(tipo, ip, payload), daemon=True)
    _REQUISICAO_THREAD.start()
    return True


def _voltar(cena):
    global _TELA_CARREGADA
    _TELA_CARREGADA = False
    cena.DefinirTela("Servers")


def _pedir_confirmacao_apagar_mundo(jogo, estado, botao):
    global _SUBTELA_ATIVA
    if estado:
        _iniciar_requisicao("mundo", _get_server_ip(jogo.Cena), True, "Criando mundo no servidor...")
        return

    _SUBTELA_ATIVA = SubtelaConfirmacao(
        jogo.TELA.get_size(),
        "Tem certeza que deseja apagar o mundo?",
        titulo="Decisão drástica",
        confirmar_callback=lambda: _abrir_subtela_chave_apagar(jogo),
    )


def _abrir_subtela_chave_apagar(jogo):
    global _SUBTELA_ATIVA
    _SUBTELA_ATIVA = SubtelaTexto(
        jogo.TELA.get_size(),
        "Digite a chave de segurança novamente",
        "",
        enviar_callback=lambda chave: _validar_chave_apagar(jogo, chave),
        placeholders="Chave de 4 dígitos",
        max_chars=4,
    )


def _validar_chave_apagar(jogo, chave):
    _iniciar_requisicao("validar_chave", _get_server_ip(jogo.Cena), chave, "Validando chave de segurança...")


def _toggle_ligado(jogo, estado, botao):
    _iniciar_requisicao("ligado", _get_server_ip(jogo.Cena), estado, "Atualizando status do servidor...")


def _atualizar_rotulos_botoes():
    if _BOTAO_LIGAR is not None:
        _BOTAO_LIGAR.set_text("Desligar Server" if _BOTAO_LIGAR.estado else "Ligar Server")
    if _BOTAO_MUNDO is not None:
        _BOTAO_MUNDO.set_text("Apagar Mundo" if _BOTAO_MUNDO.estado else "Criar Mundo")


def _processar_resposta(jogo):
    global _REQUISICAO_THREAD, _REQUISICAO_RESULTADO
    if not _REQUISICAO_RESULTADO:
        return

    payload = _REQUISICAO_RESULTADO
    _REQUISICAO_RESULTADO = None
    _REQUISICAO_THREAD = None

    resposta = payload["resposta"]
    sucesso = resposta.get("status") == "ok"

    tipo = payload["tipo"]
    if tipo == "ligado":
        if sucesso:
            _BOTAO_LIGAR.set_estado(resposta.get("ligado", payload["payload"]))
        else:
            _BOTAO_LIGAR.set_estado(not payload["payload"])

    elif tipo == "mundo":
        if sucesso:
            _BOTAO_MUNDO.set_estado(resposta.get("mundo_existente", payload["payload"]))
        else:
            _BOTAO_MUNDO.set_estado(not payload["payload"])

    elif tipo == "validar_chave":
        if sucesso:
            _iniciar_requisicao("mundo", _get_server_ip(jogo.Cena), False, "Apagando mundo do servidor...")
        else:
            _BOTAO_MUNDO.set_estado(True)

    _emitir_feedback(resposta.get("mensagem", "Falha de comunicação"), sucesso=sucesso)
    _atualizar_rotulos_botoes()


def _montar_layout(jogo):
    global _TELA_CARREGADA, _TAMANHO_CACHE
    global _BOTAO_VOLTAR, _BOTAO_LIGAR, _BOTAO_MUNDO, _MENSAGEM

    largura, altura = jogo.TELA.get_size()

    if _MENSAGEM is None:
        _MENSAGEM = Mensagem(
            (largura, altura),
            fila_externa=jogo.FilaMensagensTecnicas,
            limite_fila=4,
        )
    else:
        _MENSAGEM.set_fila_externa(jogo.FilaMensagensTecnicas)
        _MENSAGEM.redimensionar((largura, altura))

    largura_botao = min(560, int(largura * 0.54))
    altura_botao = 92
    x = (largura - largura_botao) // 2

    _BOTAO_LIGAR = BotaoAlavanca(
        pygame.Rect(x, int(altura * 0.28), largura_botao, altura_botao),
        "Server",
        estado_inicial=False,
        execute=_toggle_ligado,
        style=_ESTILO_BOTAO,
    )

    _BOTAO_MUNDO = BotaoAlavanca(
        pygame.Rect(x, int(altura * 0.48), largura_botao, altura_botao),
        "Mundo",
        estado_inicial=False,
        execute=_pedir_confirmacao_apagar_mundo,
        style=_ESTILO_BOTAO,
    )

    _BOTAO_VOLTAR = Botao(
        pygame.Rect(x, int(altura * 0.72), largura_botao, 96),
        "Voltar",
        execute=lambda jogo_ref, botao: _voltar(jogo_ref.Cena),
        style=_ESTILO_BOTAO,
    )

    _TAMANHO_CACHE = (largura, altura)
    _TELA_CARREGADA = True
    _atualizar_rotulos_botoes()


def TelaOperador(cena, jogo, eventos, dt):
    global _SUBTELA_ATIVA

    largura, altura = jogo.TELA.get_size()

    if (not _TELA_CARREGADA) or _TAMANHO_CACHE != (largura, altura):
        _montar_layout(jogo)

    _processar_resposta(jogo)

    jogo.TELA.fill((7, 10, 20))

    eventos_ativos = [] if _SUBTELA_ATIVA else eventos
    mouse_pos = (-99999, -99999) if _SUBTELA_ATIVA else None

    _BOTAO_LIGAR.set_habilitado(not (_REQUISICAO_THREAD and _REQUISICAO_THREAD.is_alive()))
    _BOTAO_MUNDO.set_habilitado(not (_REQUISICAO_THREAD and _REQUISICAO_THREAD.is_alive()))

    _BOTAO_LIGAR.render(jogo.TELA, eventos_ativos, dt, JOGO=jogo, mouse_pos=mouse_pos)
    _BOTAO_MUNDO.render(jogo.TELA, eventos_ativos, dt, JOGO=jogo, mouse_pos=mouse_pos)
    _BOTAO_VOLTAR.render(jogo.TELA, eventos_ativos, dt, JOGO=jogo, mouse_pos=mouse_pos)

    if _SUBTELA_ATIVA:
        _SUBTELA_ATIVA.render(jogo.TELA, eventos, dt, JOGO=jogo)
        if _SUBTELA_ATIVA.encerrada:
            _SUBTELA_ATIVA = None

    _MENSAGEM.render(jogo.TELA, dt)
