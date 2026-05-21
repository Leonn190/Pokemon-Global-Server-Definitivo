from __future__ import annotations

import copy

from Servidor.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    dados_ataque_contexto,
    fnum,
    normalizar,
    registrar_log_execute,
)


def efeito_eh_negativo(efeito, lista_negativos=None):
    nome = normalizar((efeito or {}).get("nome") or (efeito or {}).get("code"))
    tipo = str((efeito or {}).get("tipo") or "").strip().lower()
    negativos = {normalizar(item) for item in list(lista_negativos or [])}
    return tipo == "negativo" or nome in negativos

def efeito_eh_positivo(efeito):
    return str((efeito or {}).get("tipo") or "").strip().lower() == "positivo"

def passos_positivos_efeito(efeito):
    if bool((efeito or {}).get("permanente")):
        return 0
    return max(0, int(fnum((efeito or {}).get("passos_restantes"), 0.0)))

def adicionar_efeito_formal_preservado(ctx, alvo, efeito, origem=None):
    if alvo is None or not isinstance(efeito, dict):
        return {"aplicado": False, "motivo": "efeito_invalido"}
    formal = copy.deepcopy(efeito)
    alvo.efeitos_formais.append(formal)
    if hasattr(alvo, "recalcular_atributos"):
        alvo.recalcular_atributos()
    registrar_log_execute(
        ctx,
        "pokemon_recebeu_efeito",
        {
            "pokemon_id": getattr(alvo, "id_batalha", None),
            "pokemon_nome": getattr(alvo, "nome", None),
            "efeito_nome": formal.get("nome"),
            "efeito_code": formal.get("code"),
            "tipo": formal.get("tipo"),
            "passos_restantes": formal.get("passos_restantes"),
            "passos_totais": formal.get("passos_totais"),
            "stacks": formal.get("stacks", 1),
            "origem_id": getattr(origem, "id_batalha", None),
            "origem_nome": getattr(origem, "nome", None),
            "efeito": copy.deepcopy(formal),
        },
    )
    return {"aplicado": True, "efeito": formal}

def remover_efeito_formal(ctx, alvo, efeito, origem=None, motivo=None):
    if alvo is None or not isinstance(efeito, dict):
        return False
    removido = False
    restantes = []
    for atual in list(getattr(alvo, "efeitos_formais", []) or []):
        if not removido and atual is efeito:
            removido = True
            continue
        restantes.append(atual)
    if not removido:
        chave = normalizar(efeito.get("code") or efeito.get("nome"))
        restantes = []
        for atual in list(getattr(alvo, "efeitos_formais", []) or []):
            if not removido and normalizar((atual or {}).get("code") or (atual or {}).get("nome")) == chave:
                removido = True
                continue
            restantes.append(atual)
    if not removido:
        return False
    alvo.efeitos_formais = restantes
    if hasattr(alvo, "recalcular_atributos"):
        alvo.recalcular_atributos()
    registrar_log_execute(
        ctx,
        "pokemon_removeu_efeito",
        {
            "pokemon_id": getattr(alvo, "id_batalha", None),
            "pokemon_nome": getattr(alvo, "nome", None),
            "efeito_nome": efeito.get("nome") or efeito.get("code"),
            "passos_removidos": passos_positivos_efeito(efeito),
            "origem_id": getattr(origem, "id_batalha", None),
            "origem_nome": getattr(origem, "nome", None),
            "motivo": motivo,
            **dados_ataque_contexto(ctx, motivo or "Ataque"),
        },
    )
    return True

def remover_efeitos_negativos(ctx, alvo, lista_negativos, origem=None, motivo=None):
    removidos = []
    restantes = []
    passos = 0
    for efeito in list(getattr(alvo, "efeitos_formais", []) or []):
        if efeito_eh_negativo(efeito, lista_negativos):
            removidos.append(copy.deepcopy(efeito))
            passos += passos_positivos_efeito(efeito)
        else:
            restantes.append(efeito)
    alvo.efeitos_formais = restantes
    if removidos and hasattr(alvo, "recalcular_atributos"):
        alvo.recalcular_atributos()
    for efeito in removidos:
        registrar_log_execute(
            ctx,
            "pokemon_removeu_efeito",
            {
                "pokemon_id": getattr(alvo, "id_batalha", None),
                "pokemon_nome": getattr(alvo, "nome", None),
                "efeito_nome": efeito.get("nome") or efeito.get("code"),
                "passos_removidos": passos_positivos_efeito(efeito),
                "origem_id": getattr(origem, "id_batalha", None),
                "origem_nome": getattr(origem, "nome", None),
                "motivo": motivo,
                **dados_ataque_contexto(ctx, motivo or "Ataque"),
            },
        )
    return {"removidos": len(removidos), "passos": passos, "efeitos": removidos}

def aplicar_efeito(usuario, alvo, nome, duracao=3, dados=None, valor=0.0, negativo=None):
    efeito = {"nome": nome, "duracao": duracao, "valor": valor}
    if negativo is not None:
        efeito["negativo"] = bool(negativo)
    return usuario.AplicarEfeito(alvo, efeito, dados=dados or {})


_AREAS_BATALHA = {
    "A1": (0, 0), "A2": (0, 1), "A3": (0, 2),
    "A4": (1, 0), "A5": (1, 1), "A6": (1, 2),
    "A7": (2, 0), "A8": (2, 1), "A9": (2, 2),
    "I1": (0, 0), "I2": (0, 1), "I3": (0, 2),
    "I4": (1, 0), "I5": (1, 1), "I6": (1, 2),
    "I7": (2, 0), "I8": (2, 1), "I9": (2, 2),
}

def obter_passos_efeito(pokemon, nome):
    alvo = normalizar(nome)
    for efeito in list(getattr(pokemon, "efeitos_formais", []) or []):
        if normalizar((efeito or {}).get("nome") or (efeito or {}).get("code")) == alvo:
            dados = (efeito or {}).get("dados") if isinstance((efeito or {}).get("dados"), dict) else {}
            if bool((efeito or {}).get("permanente")):
                return max(
                    0,
                    int(
                        fnum(
                            dados.get("passos_equivalentes", dados.get("queimado_passos_equivalentes", (efeito or {}).get("passos_equivalentes"))),
                            0.0,
                        )
                    ),
                )
            return max(0, int(fnum((efeito or {}).get("passos_restantes"), 0.0)))
    return 0

def efeito_formal(pokemon, nome):
    alvo = normalizar(nome)
    for efeito in list(getattr(pokemon, "efeitos_formais", []) or []):
        if normalizar((efeito or {}).get("nome") or (efeito or {}).get("code")) == alvo:
            return efeito
    return None

def remover_efeitos_contando_passos(pokemon, nomes, origem=None, dados=None):
    if pokemon is None:
        return {"removidos": 0, "passos": 0, "efeitos": []}
    alvos = {normalizar(nome) for nome in list(nomes or [])}
    removidos = []
    restantes = []
    passos = 0
    for efeito in list(getattr(pokemon, "efeitos_formais", []) or []):
        nome_norm = normalizar((efeito or {}).get("nome") or (efeito or {}).get("code"))
        if nome_norm in alvos:
            removidos.append(efeito)
            passos += max(0, int(fnum((efeito or {}).get("passos_restantes"), 0.0)))
        else:
            restantes.append(efeito)
    pokemon.efeitos_formais = restantes
    if removidos and hasattr(pokemon, "recalcular_atributos"):
        pokemon.recalcular_atributos()
    partida = getattr(pokemon, "partida", None)
    if removidos and partida is not None and hasattr(partida, "registrar_evento_log"):
        for efeito in removidos:
            partida.registrar_evento_log(
                "pokemon_removeu_efeito",
                {
                    "pokemon_id": getattr(pokemon, "id_batalha", None),
                    "pokemon_nome": getattr(pokemon, "nome", None),
                    "efeito_nome": (efeito or {}).get("nome") or (efeito or {}).get("code"),
                    "passos_removidos": max(0, int(fnum((efeito or {}).get("passos_restantes"), 0.0))),
                    "origem_id": getattr(origem, "id_batalha", None),
                    "origem_nome": getattr(origem, "nome", None),
                    **dict(dados or {}),
                },
            )
    return {"removidos": len(removidos), "passos": passos, "efeitos": removidos}
