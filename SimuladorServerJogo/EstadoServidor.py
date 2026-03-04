import threading

_CHAVE_SEGURANCA = "1900"

_ESTADO = {
    "nome": "Servidor Indigo",
    "ip": "203.0.113.77:8123",
    "ligado": True,
    "mundo_existente": True,
    "banidos": {"JogadorBanido"},
    "jogadores_com_personagem": set(),
    "personagens": {
    },
}

_LOCK = threading.Lock()


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
            "skin": skin,
            "pokemon_inicial": pokemon_inicial,
        }

    return True, "Personagem criado com sucesso"
