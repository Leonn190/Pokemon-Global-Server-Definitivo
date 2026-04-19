from __future__ import annotations

import csv
import random
import time
from pathlib import Path
from typing import Dict, List

from SimuladorServerJogo.Batalha.GerenciadorBatalhas import GERENCIADOR_BATALHAS

_RAIZ = Path(__file__).resolve().parents[3]
_CACHE_ATAQUES: tuple[List[Dict[str, object]], Dict[str, Dict[str, object]], Dict[str, Dict[str, object]]] | None = None


def _normalizar(valor: object) -> str:
    return str(valor or "").strip().casefold()


def _carregar_ataques() -> tuple[List[Dict[str, object]], Dict[str, Dict[str, object]], Dict[str, Dict[str, object]]]:
    global _CACHE_ATAQUES
    if _CACHE_ATAQUES is not None:
        return _CACHE_ATAQUES
    lista: List[Dict[str, object]] = []
    por_code: Dict[str, Dict[str, object]] = {}
    por_nome: Dict[str, Dict[str, object]] = {}
    caminho = _RAIZ / "Dados" / "Pokemon Global Server - Ataques.csv"
    with caminho.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            nome = str(row.get("Ataque") or row.get("Nome") or "").strip()
            if not nome:
                continue
            code = str(row.get("Code") or "").strip()
            ataque = dict(row)
            ataque["Ataque"] = nome
            ataque["Nome"] = nome
            lista.append(ataque)
            por_nome[_normalizar(nome)] = ataque
            if code:
                por_code[str(code)] = ataque
    _CACHE_ATAQUES = (lista, por_code, por_nome)
    return _CACHE_ATAQUES


def _resolver_ataque(arg: str) -> Dict[str, object] | None:
    lista, por_code, por_nome = _carregar_ataques()
    chave = str(arg or "").strip()
    if not chave:
        return None
    if chave in por_code:
        return dict(por_code[chave])
    chave_nome = chave.replace("_", " ")
    por_nome_match = por_nome.get(_normalizar(chave_nome))
    if por_nome_match is not None:
        return dict(por_nome_match)
    if chave.isdigit():
        idx = int(chave)
        if 0 <= idx < len(lista):
            return dict(lista[idx])
    return None


def _listar_pokemons_lado(sistema, lado: str):
    ids = list((sistema.Lados.get(lado) or {}).get("todos") or [])
    return [p for p in [sistema.PokemonsPorId.get(uid) for uid in ids] if p is not None]


def _resolver_pokemon(sistema, arg: str | None):
    aliados = _listar_pokemons_lado(sistema, "jogador")
    inimigos = _listar_pokemons_lado(sistema, "inimigo")
    if not aliados and not inimigos:
        return None, "Nenhum Pokémon disponível na batalha."

    alvo = str(arg or "").strip()
    if not alvo:
        return (aliados[0] if aliados else None), None

    if alvo.isdigit():
        numero = int(alvo)
        if 1 <= numero <= 6:
            idx = numero - 1
            if idx < len(aliados):
                return aliados[idx], None
            return None, f"Pokémon aliado no slot {numero} não encontrado."
        if 7 <= numero <= 12:
            idx = numero - 7
            if idx < len(inimigos):
                return inimigos[idx], None
            return None, f"Pokémon inimigo no slot {numero} não encontrado."
        return None, "Número de Pokémon inválido. Use 1..6 (aliados) ou 7..12 (inimigos)."

    chave = _normalizar(alvo.replace("_", " "))
    for p in aliados + inimigos:
        if _normalizar(getattr(p, "Uid", "")) == chave:
            return p, None
    for p in aliados + inimigos:
        if _normalizar(getattr(p, "Nome", "")) == chave or _normalizar(getattr(p, "Especie", "")) == chave:
            return p, None
    return None, f"Pokémon alvo não encontrado: {alvo}"


def _resolver_slot_preferencial(arg: str | None):
    if arg is None:
        return None, None
    try:
        slot = int(str(arg).strip())
    except (TypeError, ValueError):
        return None, "Slot de ataque inválido. Use valores de 1 a 5."
    if slot < 1 or slot > 5:
        return None, "Slot de ataque inválido. Use valores de 1 a 5."
    return slot, None


def _aplicar_ataque_no_pokemon(pokemon, ataque: Dict[str, object], *, slot_preferencial: int | None = None) -> str:
    habilidades = [dict(item) for item in list(getattr(pokemon, "Habilidades", []) or []) if isinstance(item, dict)]
    nome_ataque = _normalizar(ataque.get("Ataque") or ataque.get("Nome"))
    idx_existente = -1
    for idx, atual in enumerate(habilidades):
        atual_nome = _normalizar(atual.get("Ataque") or atual.get("Nome"))
        atual_code = str(atual.get("Code") or "").strip()
        novo_code = str(ataque.get("Code") or "").strip()
        if (novo_code and atual_code == novo_code) or (nome_ataque and atual_nome == nome_ataque):
            idx_existente = idx
            break

    if idx_existente >= 0:
        return "mantido"

    ataque_final = dict(ataque)
    if len(habilidades) < 5:
        if slot_preferencial is None:
            habilidades.append(ataque_final)
            acao = "adicionado"
        else:
            idx_slot = max(0, int(slot_preferencial) - 1)
            if idx_slot < len(habilidades):
                habilidades[idx_slot] = ataque_final
                acao = "substituído_slot"
            else:
                habilidades.append(ataque_final)
                acao = "adicionado"
    else:
        if slot_preferencial is not None:
            idx_slot = max(0, int(slot_preferencial) - 1)
            habilidades[idx_slot] = ataque_final
            acao = "substituído_slot"
        else:
            idx = random.randrange(len(habilidades))
            habilidades[idx] = ataque_final
            acao = "substituído_aleatorio"

    pokemon.Habilidades = habilidades
    if isinstance(getattr(pokemon, "Estado", None), dict):
        pokemon.Estado["habilidades"] = [dict(item) for item in habilidades]
    if isinstance(getattr(pokemon, "Dados", None), dict):
        pokemon.Dados["habilidades"] = [dict(item) for item in habilidades]
    return acao


def _resolver_sistema_batalha(autor: str, meta: dict):
    batalha_id = str(meta.get("batalha_id") or "").strip()
    if batalha_id:
        sistema = GERENCIADOR_BATALHAS.obter_batalha(batalha_id)
        if sistema is not None:
            return sistema
    client_id = str(meta.get("client_id") or "").strip()
    if client_id:
        sistema = GERENCIADOR_BATALHAS.obter_batalha_ativa(client_id)
        if sistema is not None:
            return sistema
    return GERENCIADOR_BATALHAS.obter_batalha_ativa(autor)


def executar_comando_batalha(autor: str, texto: str, meta: dict | None = None) -> dict:
    bruto = str(texto or "").strip()
    if not bruto.startswith("/"):
        return {"ok": False, "feedback": ""}
    partes = bruto[1:].split()
    if not partes:
        return {"ok": True, "feedback": "Comando inexistente: /", "autor": "Servidor", "timestamp": time.time()}
    cmd = str(partes[0]).strip().lower()
    args = [str(item).strip() for item in partes[1:] if str(item).strip()]
    meta_dict = dict(meta or {})
    sistema = _resolver_sistema_batalha(autor, meta_dict)
    if sistema is None:
        return {"ok": True, "feedback": "Nenhuma batalha ativa para este jogador.", "autor": "Servidor", "timestamp": time.time()}

    if cmd != "atk":
        return {"ok": True, "feedback": f"Comando de batalha inexistente: /{cmd}", "autor": "Servidor", "timestamp": time.time(), "batalha_atualizacao": {"batalha": sistema.snapshot(), "motivo": "comando_desconhecido"}}

    if len(args) < 1 or len(args) > 3:
        return {"ok": True, "feedback": "Uso: /Atk <ataque_nome|ataque_code> [pokemon_nome|pokemon_numero] [slot_ataque]", "autor": "Servidor", "timestamp": time.time(), "batalha_atualizacao": {"batalha": sistema.snapshot(), "motivo": "uso_invalido"}}

    ataque = _resolver_ataque(args[0])
    if ataque is None:
        return {"ok": True, "feedback": f"Ataque não encontrado: {args[0]}", "autor": "Servidor", "timestamp": time.time(), "batalha_atualizacao": {"batalha": sistema.snapshot(), "motivo": "ataque_nao_encontrado"}}

    pokemon_arg = args[1] if len(args) >= 2 else None
    pokemon_alvo, erro_pokemon = _resolver_pokemon(sistema, pokemon_arg)
    if pokemon_alvo is None:
        return {"ok": True, "feedback": str(erro_pokemon or "Pokémon alvo não encontrado."), "autor": "Servidor", "timestamp": time.time(), "batalha_atualizacao": {"batalha": sistema.snapshot(), "motivo": "pokemon_nao_encontrado"}}

    slot_arg = args[2] if len(args) >= 3 else None
    slot_preferencial, erro_slot = _resolver_slot_preferencial(slot_arg)
    if erro_slot is not None:
        return {"ok": True, "feedback": str(erro_slot), "autor": "Servidor", "timestamp": time.time(), "batalha_atualizacao": {"batalha": sistema.snapshot(), "motivo": "slot_invalido"}}

    acao = _aplicar_ataque_no_pokemon(pokemon_alvo, ataque, slot_preferencial=slot_preferencial)
    if hasattr(sistema, "verificar_integridade"):
        try:
            sistema.verificar_integridade()
        except Exception as exc:
            snapshot_erro = sistema.snapshot() if hasattr(sistema, "snapshot") else {}
            return {
                "ok": True,
                "feedback": f"Erro ao validar batalha após /Atk: {exc}",
                "autor": "Servidor",
                "timestamp": time.time(),
                "batalha_atualizacao": {"batalha": snapshot_erro, "motivo": "erro_verificacao"},
            }
    snapshot = sistema.snapshot() if hasattr(sistema, "snapshot") else {}
    nome = str(ataque.get("Ataque") or ataque.get("Nome") or "Ataque")
    return {
        "ok": True,
        "feedback": f"/Atk aplicado: {nome} {acao} em {getattr(pokemon_alvo, 'Nome', 'Pokemon')}",
        "autor": "Servidor",
        "timestamp": time.time(),
        "batalha_atualizacao": {"batalha": snapshot, "motivo": "comando_atk"},
    }
