import threading

from SimuladorServerJogo.GeradorMundo import carregar_ou_criar_estado_mundo, obter_posicao_spawn, salvar_estado_mundo

_CHAVE_SEGURANCA = "1900"
_ESTADO_MUNDO = carregar_ou_criar_estado_mundo()
_POSICAO_SPAWN = obter_posicao_spawn(_ESTADO_MUNDO)

_ESTADO = {
    "nome": "Servidor Indigo",
    "ip": "203.0.113.77:8123",
    "ligado": True,
    "mundo_existente": True,
    "banidos": {"JogadorBanido"},
    "jogadores_com_personagem": set(_ESTADO_MUNDO.get("players", {}).keys()),
    "personagens": dict(_ESTADO_MUNDO.get("players", {})),
}

_LOCK = threading.Lock()


def _persistir_personagens() -> None:
    _ESTADO_MUNDO["players"] = _ESTADO["personagens"]
    salvar_estado_mundo(_ESTADO_MUNDO)


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
        _ESTADO["mundo_existente"] = bool(ativo)


def adicionar_personagem(usuario, skin, pokemon_inicial):
    with _LOCK:
        if usuario in _ESTADO["jogadores_com_personagem"]:
            return False, "Sua conta já possui personagem neste servidor"

        _ESTADO["jogadores_com_personagem"].add(usuario)
        _ESTADO["personagens"][usuario] = {
            "nome": usuario,
            "skin": skin,
            "pokemon_inicial": pokemon_inicial,
            "posicao": [_POSICAO_SPAWN[0], _POSICAO_SPAWN[1]],
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

        personagem["posicao"] = [float(posicao[0]), float(posicao[1])]
        _persistir_personagens()
