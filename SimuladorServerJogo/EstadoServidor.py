import threading

from SimuladorServerJogo.GeradorMundo import (
    ALTURA_BLOCOS,
    ARQUIVO_MUNDO,
    LARGURA_BLOCOS,
    carregar_ou_criar_estado_mundo,
    gerar_novo_estado_mundo,
    obter_posicao_spawn,
    salvar_estado_mundo,
)

_CHAVE_SEGURANCA = "1900"
_ESTADO_MUNDO = carregar_ou_criar_estado_mundo()

_ESTADO = {
    "nome": "Servidor Indigo",
    "ip": "203.0.113.77:8123",
    "ligado": True,
    "mundo_existente": ARQUIVO_MUNDO.exists(),
    "banidos": {"JogadorBanido"},
    "jogadores_com_personagem": set(_ESTADO_MUNDO.get("players", {}).keys()),
    "personagens": dict(_ESTADO_MUNDO.get("players", {})),
}

_LOCK = threading.Lock()


def _clamp_posicao(posicao):
    try:
        x = float(posicao[0])
        y = float(posicao[1])
    except (TypeError, ValueError, IndexError):
        return (0.0, 0.0)

    x = max(0.0, min(x, float(LARGURA_BLOCOS - 1)))
    y = max(0.0, min(y, float(ALTURA_BLOCOS - 1)))
    return (x, y)


def _recarregar_mundo():
    global _ESTADO_MUNDO
    _ESTADO_MUNDO = carregar_ou_criar_estado_mundo()


def _criar_novo_mundo():
    global _ESTADO_MUNDO
    players = dict(_ESTADO.get("personagens", {}))
    _ESTADO_MUNDO = gerar_novo_estado_mundo(players=players)
    salvar_estado_mundo(_ESTADO_MUNDO)


def _apagar_mundo():
    global _ESTADO_MUNDO
    if ARQUIVO_MUNDO.exists():
        ARQUIVO_MUNDO.unlink()
    _ESTADO_MUNDO = {"meta": {}, "grid": [], "players": {}, "spawn": [0.0, 0.0]}


def _sync_personagens_mundo():
    _ESTADO_MUNDO["players"] = _ESTADO["personagens"]
    salvar_estado_mundo(_ESTADO_MUNDO)


def _persistir_personagens() -> None:
    _sync_personagens_mundo()


def chave_seguranca():
    return _CHAVE_SEGURANCA


def snapshot_estado():
    with _LOCK:
        return {
            "nome": _ESTADO["nome"],
            "ip": _ESTADO["ip"],
            "ligado": _ESTADO["ligado"],
            "mundo_existente": _ESTADO["mundo_existente"],
            "banidos": set(_ESTADO["banidos"]),
            "jogadores_com_personagem": set(_ESTADO["jogadores_com_personagem"]),
            "personagens": {k: dict(v) for k, v in _ESTADO["personagens"].items()},
        }


def definir_ligado(ativo):
    with _LOCK:
        _ESTADO["ligado"] = bool(ativo)


def definir_mundo_existente(ativo):
    with _LOCK:
        ativo = bool(ativo)
        if ativo:
            _criar_novo_mundo()
            _ESTADO["mundo_existente"] = True
            return

        _apagar_mundo()
        _ESTADO["mundo_existente"] = False


def adicionar_personagem(usuario, skin, pokemon_inicial):
    with _LOCK:
        if usuario in _ESTADO["jogadores_com_personagem"]:
            return False, "Sua conta já possui personagem neste servidor"

        _ESTADO["jogadores_com_personagem"].add(usuario)
        _recarregar_mundo()
        spawn = obter_posicao_spawn(_ESTADO_MUNDO)

        _ESTADO["personagens"][usuario] = {
            "nome": usuario,
            "skin": skin,
            "pokemon_inicial": pokemon_inicial,
            "posicao": [spawn[0], spawn[1]],
        }
        _persistir_personagens()

    return True, "Personagem criado com sucesso"


def atualizar_posicao_personagem(usuario, posicao):
    if not usuario:
        return

    with _LOCK:
        personagem = _ESTADO["personagens"].get(usuario)
        if personagem is None:
            return

        x, y = _clamp_posicao(posicao)
        personagem["posicao"] = [x, y]
        _persistir_personagens()
