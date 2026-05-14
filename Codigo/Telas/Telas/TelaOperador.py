import threading

import pygame

from Codigo.Prefabs.Botao import Botao, BotaoAlavanca
from Codigo.Prefabs.Mensagem import Mensagem
from Codigo.ModulosGerais.Server import GerenciadorServerList as GERENCIADOR_SERVER_LIST
from Codigo.ModulosGerais.Server.ServerMenu import definir_mundo_server, definir_server_ligado, obter_status_operacao, operar_server
from Codigo.Telas.Telas.TelasGenericas import SubtelaCarregamento, SubtelaConfirmacao, SubtelaTexto

_TELA_CARREGADA = False
_TAMANHO_CACHE = (0, 0)

_MENSAGEM = None

_BOTAO_VOLTAR = None
_BOTAO_LIGAR = None
_BOTAO_MUNDO = None

_REQUISICAO_THREAD = None
_REQUISICAO_RESULTADO = None
_REQUISICAO_TIPO_ATUAL = None
_REQUISICAO_PENDENTE = None
_STATUS_TIMER = 0.0
_GERACAO_NOTIFICADA = False
_REMOCAO_NOTIFICADA = False
_AGUARDANDO_CRIACAO = False


def possui_subtela_carregamento_ativa(jogo=None):
    if jogo is None:
        return False
    return isinstance(jogo.GerenciadorSubtelas.obter_por_tipo(SubtelaCarregamento), SubtelaCarregamento)
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


def _estilo_alavanca_acao():
    estilo = dict(_ESTILO_BOTAO)
    estilo["text_style"] = dict(_ESTILO_BOTAO["text_style"])
    estilo["estilo_ativo"] = {
        "bg": (150, 32, 32),
        "bg_hover": (186, 42, 42),
        "bg_pressed": (118, 26, 26),
        "border": (70, 16, 16),
        "border_hover": (255, 180, 180),
    }
    estilo["estilo_desativado"] = {
        "bg": (24, 128, 42),
        "bg_hover": (35, 156, 54),
        "bg_pressed": (20, 102, 34),
        "border": (12, 60, 20),
        "border_hover": (180, 255, 180),
    }
    return estilo


def _emitir_feedback(texto, sucesso=False):
    if _MENSAGEM is None:
        return
    _MENSAGEM.emitir(texto, tipo="sucesso" if sucesso else "erro")


def _emitir_info(texto):
    if _MENSAGEM is None:
        return
    _MENSAGEM.emitir(texto, tipo="info")


def _get_server_id(cena):
    servidores = GERENCIADOR_SERVER_LIST.listar_servidores()
    indice = getattr(cena, "ServerOperadorIndice", None)
    if indice is None or indice >= len(servidores):
        return ""
    return servidores[indice].get("id", "")


def _worker(tipo, server_id, payload):
    global _REQUISICAO_RESULTADO

    if tipo == "ligado":
        resposta = definir_server_ligado(server_id, payload)
    elif tipo == "mundo":
        resposta = definir_mundo_server(server_id, payload)
    elif tipo == "status":
        resposta = obter_status_operacao(server_id)
    else:
        resposta = operar_server(server_id, payload)

    _REQUISICAO_RESULTADO = {"tipo": tipo, "resposta": resposta, "payload": payload}


def _iniciar_requisicao(tipo, server_id, payload=None, mensagem="Comunicando com Servidor..."):
    global _REQUISICAO_THREAD, _REQUISICAO_RESULTADO, _REQUISICAO_TIPO_ATUAL, _REQUISICAO_PENDENTE
    if _REQUISICAO_THREAD and _REQUISICAO_THREAD.is_alive():
        if _REQUISICAO_TIPO_ATUAL == "status" and tipo != "status":
            _REQUISICAO_PENDENTE = (tipo, server_id, payload, mensagem)
            return True
        return False

    _REQUISICAO_PENDENTE = None
    _REQUISICAO_RESULTADO = None
    _REQUISICAO_TIPO_ATUAL = tipo
    if mensagem:
        _emitir_info(mensagem)
    _REQUISICAO_THREAD = threading.Thread(target=_worker, args=(tipo, server_id, payload), daemon=True)
    _REQUISICAO_THREAD.start()
    return True


def _iniciar_requisicao_pendente():
    global _REQUISICAO_PENDENTE
    if _REQUISICAO_PENDENTE is None:
        return False
    tipo, server_id, payload, mensagem = _REQUISICAO_PENDENTE
    _REQUISICAO_PENDENTE = None
    return _iniciar_requisicao(tipo, server_id, payload, mensagem)


def _voltar(cena):
    global _TELA_CARREGADA
    _TELA_CARREGADA = False
    cena.DefinirTela("Servers")


def _pedir_confirmacao_apagar_mundo(jogo, estado, botao):
    global _AGUARDANDO_CRIACAO
    if estado:
        if _iniciar_requisicao("mundo", _get_server_id(jogo.Cena), True, "Iniciando criação de mundo..."):
            _AGUARDANDO_CRIACAO = True
            jogo.GerenciadorSubtelas.abrir(SubtelaCarregamento(jogo.TELA.get_size(), "Carregando"))
            modal = jogo.GerenciadorSubtelas.obter_por_tipo(SubtelaCarregamento)
            modal.set_progresso(0)
            modal.set_mensagem("Preparando geração do mundo")
        return

    jogo.GerenciadorSubtelas.abrir(SubtelaConfirmacao(
        jogo.TELA.get_size(),
        "Tem certeza que deseja apagar o mundo?",
        titulo="Decisão drástica",
        confirmar_callback=lambda: _abrir_subtela_chave_apagar(jogo),
    ))


def _abrir_subtela_chave_apagar(jogo):
    jogo.GerenciadorSubtelas.abrir(SubtelaTexto(
        jogo.TELA.get_size(),
        "Digite a chave de segurança novamente",
        "",
        enviar_callback=lambda chave: _validar_chave_apagar(jogo, chave),
        placeholders="Chave de 4 dígitos",
        max_chars=4,
    ))


def _validar_chave_apagar(jogo, chave):
    if not _iniciar_requisicao("validar_chave", _get_server_id(jogo.Cena), chave, "Validando chave de segurança..."):
        _emitir_feedback("Já existe uma operação em andamento")
        return False
    return True
def _toggle_ligado(jogo, estado, botao):
    _iniciar_requisicao("ligado", _get_server_id(jogo.Cena), estado, "Atualizando status do servidor...")


def _atualizar_rotulos_botoes():
    if _BOTAO_LIGAR is not None:
        _BOTAO_LIGAR.set_text("Desligar Server" if _BOTAO_LIGAR.estado else "Ligar Server")
    if _BOTAO_MUNDO is not None:
        _BOTAO_MUNDO.set_text("Apagar Mundo" if _BOTAO_MUNDO.estado else "Criar Mundo")


def _processar_status_geracao(jogo, resposta):
    global _GERACAO_NOTIFICADA, _REMOCAO_NOTIFICADA, _AGUARDANDO_CRIACAO
    operacao = str(resposta.get("operacao_geracao", "nenhuma") or "nenhuma")
    em_andamento = bool(resposta.get("mundo_em_geracao", False))

    modal_carregamento = jogo.GerenciadorSubtelas.obter_por_tipo(SubtelaCarregamento)
    if isinstance(modal_carregamento, SubtelaCarregamento):
        modal_carregamento.set_progresso(int(resposta.get("progresso_mundo", 0)))
        modal_carregamento.set_mensagem(resposta.get("mensagem_geracao", "Carregando mundo"))

    if em_andamento:
        return

    erro = str(resposta.get("erro_geracao", "")).strip()
    if erro:
        if isinstance(modal_carregamento, SubtelaCarregamento):
            modal_carregamento.encerrada = True
        if operacao == "remocao":
            if not _REMOCAO_NOTIFICADA:
                _emitir_feedback(f"Falha ao apagar mundo: {erro}")
                _REMOCAO_NOTIFICADA = True
        else:
            if not _GERACAO_NOTIFICADA:
                _emitir_feedback(f"Falha ao criar mundo: {erro}")
                _GERACAO_NOTIFICADA = True
        _AGUARDANDO_CRIACAO = False
        return

    if _AGUARDANDO_CRIACAO and not bool(resposta.get("mundo_existente", False)):
        if isinstance(modal_carregamento, SubtelaCarregamento):
            modal_carregamento.set_mensagem("Criando mundo...")
        return

    operacao_remocao = operacao == "remocao" or (
        operacao == "nenhuma"
        and isinstance(modal_carregamento, SubtelaCarregamento)
        and not bool(resposta.get("mundo_existente", True))
    )

    if operacao_remocao and not resposta.get("mundo_existente", True):
        if isinstance(modal_carregamento, SubtelaCarregamento):
            modal_carregamento.encerrada = True
        if not _REMOCAO_NOTIFICADA:
            _emitir_feedback("Mundo apagado", sucesso=True)
            _REMOCAO_NOTIFICADA = True
        return

    if resposta.get("mundo_existente", False):
        if isinstance(modal_carregamento, SubtelaCarregamento):
            modal_carregamento.encerrada = True
        _AGUARDANDO_CRIACAO = False
        if not _GERACAO_NOTIFICADA:
            _emitir_feedback("Mundo criado e pronto para uso", sucesso=True)
            _GERACAO_NOTIFICADA = True

        if not bool(resposta.get("ligado", False)) and not (_REQUISICAO_THREAD and _REQUISICAO_THREAD.is_alive()):
            _iniciar_requisicao("ligado", _get_server_id(jogo.Cena), True, "Ligando servidor automaticamente...")


def _processar_resposta(jogo):
    global _REQUISICAO_THREAD, _REQUISICAO_RESULTADO, _REQUISICAO_TIPO_ATUAL
    global _GERACAO_NOTIFICADA, _REMOCAO_NOTIFICADA, _AGUARDANDO_CRIACAO
    if not _REQUISICAO_RESULTADO:
        if not (_REQUISICAO_THREAD and _REQUISICAO_THREAD.is_alive()):
            _iniciar_requisicao_pendente()
        return

    payload = _REQUISICAO_RESULTADO
    _REQUISICAO_RESULTADO = None
    _REQUISICAO_THREAD = None
    _REQUISICAO_TIPO_ATUAL = None

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
            _BOTAO_MUNDO.set_estado(bool(resposta.get("mundo_existente", False)))
            if payload["payload"]:
                _GERACAO_NOTIFICADA = False
                _AGUARDANDO_CRIACAO = True
            else:
                _REMOCAO_NOTIFICADA = False
                _AGUARDANDO_CRIACAO = False
            _processar_status_geracao(jogo, resposta)
        else:
            _BOTAO_MUNDO.set_estado(not payload["payload"])
            _AGUARDANDO_CRIACAO = False

    elif tipo == "validar_chave":
        if sucesso:
            jogo.GerenciadorSubtelas.abrir(SubtelaCarregamento(jogo.TELA.get_size(), "Carregando"))
            modal = jogo.GerenciadorSubtelas.obter_por_tipo(SubtelaCarregamento)
            modal.set_progresso(0)
            modal.set_mensagem("Apagando mundo")
            _iniciar_requisicao("mundo", _get_server_id(jogo.Cena), False, "Apagando mundo do servidor...")
        else:
            _emitir_feedback(resposta.get("mensagem", "Chave inválida"))

    elif tipo == "status":
        if sucesso:
            _BOTAO_LIGAR.set_estado(bool(resposta.get("ligado", False)))
            _BOTAO_MUNDO.set_estado(bool(resposta.get("mundo_existente", False)))
            _processar_status_geracao(jogo, resposta)

    if tipo in ("ligado", "validar_chave") or not sucesso:
        _emitir_feedback(resposta.get("mensagem", "Falha de comunicação"), sucesso=sucesso)
    _atualizar_rotulos_botoes()
    _iniciar_requisicao_pendente()


def _montar_layout(jogo, tela_destino=None):
    global _TELA_CARREGADA, _TAMANHO_CACHE
    global _BOTAO_VOLTAR, _BOTAO_LIGAR, _BOTAO_MUNDO, _MENSAGEM
    global _GERACAO_NOTIFICADA, _REMOCAO_NOTIFICADA, _AGUARDANDO_CRIACAO

    tela = tela_destino if tela_destino is not None else jogo.TELA
    largura, altura = tela.get_size()

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
        style=_estilo_alavanca_acao(),
    )

    _BOTAO_MUNDO = BotaoAlavanca(
        pygame.Rect(x, int(altura * 0.48), largura_botao, altura_botao),
        "Mundo",
        estado_inicial=False,
        execute=_pedir_confirmacao_apagar_mundo,
        style=_estilo_alavanca_acao(),
    )

    _BOTAO_VOLTAR = Botao(
        pygame.Rect(x, int(altura * 0.72), largura_botao, 96),
        "Voltar",
        execute=lambda jogo_ref, botao: _voltar(jogo_ref.Cena),
        style=_ESTILO_BOTAO,
    )

    _GERACAO_NOTIFICADA = False
    _REMOCAO_NOTIFICADA = False
    _AGUARDANDO_CRIACAO = False
    _TAMANHO_CACHE = (largura, altura)
    _TELA_CARREGADA = True
    _atualizar_rotulos_botoes()
    _iniciar_requisicao("status", _get_server_id(jogo.Cena), None, "Carregando estado do servidor...")


def TelaOperador(cena, jogo, eventos, dt, tela_destino=None):
    global _STATUS_TIMER

    tela = tela_destino if tela_destino is not None else jogo.TELA
    largura, altura = tela.get_size()

    if (not _TELA_CARREGADA) or _TAMANHO_CACHE != (largura, altura):
        _montar_layout(jogo, tela_destino=tela)

    _processar_resposta(jogo)

    _STATUS_TIMER += max(0.0, float(dt))
    modal = jogo.GerenciadorSubtelas.topo
    pode_atualizar_status = (modal is None) or isinstance(modal, SubtelaCarregamento)
    if _STATUS_TIMER >= 0.12 and pode_atualizar_status and not (_REQUISICAO_THREAD and _REQUISICAO_THREAD.is_alive()):
        _STATUS_TIMER = 0.0
        _iniciar_requisicao("status", _get_server_id(jogo.Cena), None, "")

    tela.fill((7, 10, 20))

    eventos_ativos = [] if modal else eventos
    mouse_pos = (-99999, -99999) if modal else None

    requisicao_bloqueante = bool(_REQUISICAO_THREAD and _REQUISICAO_THREAD.is_alive() and _REQUISICAO_TIPO_ATUAL != "status")
    bloqueado = requisicao_bloqueante or isinstance(modal, SubtelaCarregamento)
    _BOTAO_LIGAR.set_habilitado((not bloqueado) and bool(_BOTAO_MUNDO.estado))
    _BOTAO_MUNDO.set_habilitado(not bloqueado)

    _BOTAO_LIGAR.render(tela, eventos_ativos, dt, JOGO=jogo, mouse_pos=mouse_pos)
    _BOTAO_MUNDO.render(tela, eventos_ativos, dt, JOGO=jogo, mouse_pos=mouse_pos)
    _BOTAO_VOLTAR.render(tela, eventos_ativos, dt, JOGO=jogo, mouse_pos=mouse_pos)


    _MENSAGEM.render(tela, dt)
