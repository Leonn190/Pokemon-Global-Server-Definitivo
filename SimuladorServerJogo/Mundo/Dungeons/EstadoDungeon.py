from __future__ import annotations

import copy
import time
from typing import Iterable

from SimuladorServerJogo.Gerais.EstadoServidor import obter_personagem_para_entrada, atualizar_perfil_personagem
from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Mundo.DungeonGeometria import eh_dimensao_dungeon


def eh_dentro_dungeon(player) -> bool:
    estado = getattr(player, "estado_extra", {}) if isinstance(getattr(player, "estado_extra", {}), dict) else {}
    return eh_dimensao_dungeon(str(estado.get("dimensao") or "Mundo"))


def obter_estado_dungeon_player(player) -> dict:
    estado = getattr(player, "estado_extra", {}) if isinstance(getattr(player, "estado_extra", {}), dict) else {}
    atual = estado.get("estado_dungeon") if isinstance(estado.get("estado_dungeon"), dict) else {}
    if not isinstance(atual, dict):
        atual = {}
    estado["estado_dungeon"] = atual
    return atual


def _perfil_personagem(client_id: str) -> dict:
    dados = obter_personagem_para_entrada(str(client_id or "")) or {}
    perfil = dict(dados)
    perfil.pop("inventario", None)
    return perfil


def _normalizar_salas(salas: Iterable[object]) -> list[str]:
    return sorted({str(sala or "").strip() for sala in list(salas or []) if str(sala or "").strip()})


def carregar_exploracao_persistida(client_id: str, dungeon_code: str) -> list[str]:
    perfil = _perfil_personagem(client_id)
    dungeons = perfil.get("dungeons") if isinstance(perfil.get("dungeons"), dict) else {}
    exploracao = dungeons.get("exploracao") if isinstance(dungeons.get("exploracao"), dict) else {}
    dados = exploracao.get(str(dungeon_code)) if isinstance(exploracao.get(str(dungeon_code)), dict) else {}
    return _normalizar_salas(dados.get("salas_exploradas") or [])


def salvar_exploracao_persistida(client_id: str, dungeon_code: str, salas: Iterable[object]) -> bool:
    if not str(client_id or "").strip():
        return False
    perfil = _perfil_personagem(client_id)
    dungeons = copy.deepcopy(perfil.get("dungeons")) if isinstance(perfil.get("dungeons"), dict) else {}
    exploracao = dungeons.get("exploracao") if isinstance(dungeons.get("exploracao"), dict) else {}
    exploracao[str(dungeon_code)] = {
        "salas_exploradas": _normalizar_salas(salas),
        "ultima_atualizacao": int(time.time()),
    }
    dungeons["exploracao"] = exploracao
    perfil["dungeons"] = dungeons
    atualizar_perfil_personagem(str(client_id), perfil)
    return True


def criar_estado_entrada(player, client_id: str, dungeon_code: str, porta_idx: int, pedra_id: int, layout: dict, entrada: dict, regras: dict) -> dict:
    sala_entrada = str((entrada or {}).get("sala_id") or "")
    persistidas = set(carregar_exploracao_persistida(client_id, dungeon_code))
    if sala_entrada:
        persistidas.add(sala_entrada)
    salvar_exploracao_persistida(client_id, dungeon_code, persistidas)
    return {
        "dungeon_code": str(dungeon_code),
        "porta_idx": int(porta_idx or 1),
        "pedra_id": int(pedra_id or 0),
        "coracoes": int((regras or {}).get("coracoes_iniciais", 3) or 3),
        "coracoes_max": int((regras or {}).get("coracoes_maximos", 3) or 3),
        "entrada_mundo": list(getattr(player, "estado_extra", {}).get("ultima_pos_mundo", list(getattr(player, "posicao", [0.0, 0.0])))),
        "dimensao": (layout or {}).get("dimensao"),
        "invulneravel_dungeon_ate_tick": 0,
        "portas_destrancadas": [],
        "salas_exploradas": _normalizar_salas(persistidas),
        "sala_id": sala_entrada,
        "sala_posicao": list((entrada or {}).get("posicao_sala") or []),
    }


def registrar_sala_explorada(player, dungeon_code: str, sala_id: str, client_id: str = "", persistir: bool = True) -> bool:
    sala = str(sala_id or "").strip()
    if not sala:
        return False
    estado = obter_estado_dungeon_player(player)
    exploradas = estado.get("salas_exploradas") if isinstance(estado.get("salas_exploradas"), list) else []
    if sala in {str(x) for x in exploradas}:
        return False
    exploradas.append(sala)
    estado["salas_exploradas"] = _normalizar_salas(exploradas)
    if persistir:
        usuario = str(client_id or getattr(player, "estado_extra", {}).get("usuario") or "")
        salvar_exploracao_persistida(usuario, str(dungeon_code), estado["salas_exploradas"])
    return True


def resolver_posicao_saida_dungeon(player, estado_dungeon: dict) -> list[float]:
    pedra = BANCO_DADOS.obter_objeto(int((estado_dungeon or {}).get("pedra_id", 0) or 0))
    pos = list(getattr(pedra, "posicao", [])) if pedra is not None else []
    if isinstance(pos, list) and len(pos) == 2:
        return [float(pos[0]), float(pos[1])]
    estado = getattr(player, "estado_extra", {}) if isinstance(getattr(player, "estado_extra", {}), dict) else {}
    for chave in ("ultima_pos_mundo",):
        valor = estado.get(chave)
        if isinstance(valor, (list, tuple)) and len(valor) == 2:
            return [float(valor[0]), float(valor[1])]
    valor = (estado_dungeon or {}).get("entrada_mundo")
    if isinstance(valor, (list, tuple)) and len(valor) == 2:
        return [float(valor[0]), float(valor[1])]
    return [0.0, 0.0]


def limpar_estado_temporario(player) -> None:
    if not isinstance(getattr(player, "estado_extra", None), dict):
        return
    player.estado_extra["dimensao"] = "Mundo"
    player.estado_extra.pop("estado_dungeon", None)


def normalizar_personagem_login_dungeon(usuario: str, personagem: dict) -> dict:
    dados = dict(personagem or {})
    dimensao = str(dados.get("dimensao_atual") or dados.get("dimensao") or "Mundo")
    if not eh_dimensao_dungeon(dimensao):
        return dados
    pos_dim = dados.get("posicoes_por_dimensao") if isinstance(dados.get("posicoes_por_dimensao"), dict) else {}
    estado_dungeon = dados.get("estado_dungeon") if isinstance(dados.get("estado_dungeon"), dict) else {}
    pedra = BANCO_DADOS.obter_objeto(int(estado_dungeon.get("pedra_id", 0) or 0))
    pos_pedra = list(getattr(pedra, "posicao", [])) if pedra is not None else []
    pos = pos_pedra if isinstance(pos_pedra, list) and len(pos_pedra) == 2 else None
    if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
        pos = estado_dungeon.get("entrada_mundo") if isinstance(estado_dungeon.get("entrada_mundo"), (list, tuple)) else None
    if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
        pos = pos_dim.get("Mundo") if isinstance(pos_dim.get("Mundo"), (list, tuple)) and len(pos_dim.get("Mundo")) == 2 else None
    if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
        pos = dados.get("ultima_pos_mundo") if isinstance(dados.get("ultima_pos_mundo"), (list, tuple)) and len(dados.get("ultima_pos_mundo")) == 2 else None
    if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
        pos = [0.0, 0.0]
    pos = [float(pos[0]), float(pos[1])]
    dados["posicao"] = pos
    dados["dimensao_atual"] = "Mundo"
    dados.pop("estado_dungeon", None)
    pos_dim["Mundo"] = pos
    dados["posicoes_por_dimensao"] = pos_dim
    try:
        from SimuladorServerJogo.Gerais.EstadoServidor import atualizar_posicao_personagem

        atualizar_posicao_personagem(str(usuario), pos, dimensao="Mundo")
    except Exception:
        pass
    return dados
