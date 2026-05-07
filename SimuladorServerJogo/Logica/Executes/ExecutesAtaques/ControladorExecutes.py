from __future__ import annotations

import importlib

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesAgua import (
    obter_aliases_executes_agua,
    obter_executes_agua,
    obter_passivas_ataques_agua,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesCosmico import (
    obter_aliases_executes_cosmicos,
    obter_executes_cosmicos,
    obter_passivas_ataques_cosmicas,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesDragao import (
    obter_aliases_executes_dragao,
    obter_executes_dragao,
    obter_passivas_ataques_dragao,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesEletrico import (
    obter_aliases_executes_eletricos,
    obter_executes_eletricos,
    obter_passivas_ataques_eletricas,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesFada import (
    obter_aliases_executes_fada,
    obter_executes_fada,
    obter_passivas_ataques_fada,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesFantasma import (
    obter_aliases_executes_fantasma,
    obter_executes_fantasma,
    obter_passivas_ataques_fantasma,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesFogo import (
    obter_aliases_executes_fogo,
    obter_executes_fogo,
    obter_passivas_ataques_fogo,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesGelo import (
    obter_aliases_executes_gelo,
    obter_executes_gelo,
    obter_passivas_ataques_gelo,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesInseto import (
    obter_aliases_executes_inseto,
    obter_executes_inseto,
    obter_passivas_ataques_inseto,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesLutador import (
    obter_aliases_executes_lutador,
    obter_executes_lutador,
    obter_passivas_ataques_lutador,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesMetal import (
    obter_aliases_executes_metal,
    obter_executes_metal,
    obter_passivas_ataques_metal,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesNormal import (
    obter_aliases_executes_normais,
    obter_executes_normais,
    obter_executes_reativos_normais,
    obter_passivas_ataques_normais,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesPedra import (
    obter_aliases_executes_pedra,
    obter_executes_pedra,
    obter_passivas_ataques_pedra,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesPlanta import (
    obter_aliases_executes_planta,
    obter_executes_planta,
    obter_passivas_ataques_planta,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesPsiquico import (
    obter_aliases_executes_psiquicos,
    obter_executes_psiquicos,
    obter_passivas_ataques_psiquicas,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesSombrio import (
    obter_aliases_executes_sombrio,
    obter_executes_sombrio,
    obter_passivas_ataques_sombrio,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesSonoro import (
    obter_aliases_executes_sonoro,
    obter_executes_sonoro,
    obter_passivas_ataques_sonoro,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesTerra import (
    obter_aliases_executes_terra,
    obter_executes_terra,
    obter_passivas_ataques_terra,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesVeneno import (
    obter_aliases_executes_veneno,
    obter_executes_veneno,
    obter_passivas_ataques_veneno,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ExecutesVoador import (
    obter_aliases_executes_voador,
    obter_executes_voador,
    obter_passivas_ataques_voador,
)
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import normalizar
from SimuladorServerJogo.Batalha.ResolvedorFlags import ExecuteReativo


_FONTES_EXECUTES = (
    (obter_executes_normais, obter_passivas_ataques_normais, obter_aliases_executes_normais),
    (obter_executes_agua, obter_passivas_ataques_agua, obter_aliases_executes_agua),
    (obter_executes_cosmicos, obter_passivas_ataques_cosmicas, obter_aliases_executes_cosmicos),
    (obter_executes_dragao, obter_passivas_ataques_dragao, obter_aliases_executes_dragao),
    (obter_executes_eletricos, obter_passivas_ataques_eletricas, obter_aliases_executes_eletricos),
    (obter_executes_fada, obter_passivas_ataques_fada, obter_aliases_executes_fada),
    (obter_executes_fantasma, obter_passivas_ataques_fantasma, obter_aliases_executes_fantasma),
    (obter_executes_fogo, obter_passivas_ataques_fogo, obter_aliases_executes_fogo),
    (obter_executes_gelo, obter_passivas_ataques_gelo, obter_aliases_executes_gelo),
    (obter_executes_inseto, obter_passivas_ataques_inseto, obter_aliases_executes_inseto),
    (obter_executes_lutador, obter_passivas_ataques_lutador, obter_aliases_executes_lutador),
    (obter_executes_metal, obter_passivas_ataques_metal, obter_aliases_executes_metal),
    (obter_executes_pedra, obter_passivas_ataques_pedra, obter_aliases_executes_pedra),
    (obter_executes_planta, obter_passivas_ataques_planta, obter_aliases_executes_planta),
    (obter_executes_psiquicos, obter_passivas_ataques_psiquicas, obter_aliases_executes_psiquicos),
    (obter_executes_sombrio, obter_passivas_ataques_sombrio, obter_aliases_executes_sombrio),
    (obter_executes_sonoro, obter_passivas_ataques_sonoro, obter_aliases_executes_sonoro),
    (obter_executes_terra, obter_passivas_ataques_terra, obter_aliases_executes_terra),
    (obter_executes_veneno, obter_passivas_ataques_veneno, obter_aliases_executes_veneno),
    (obter_executes_voador, obter_passivas_ataques_voador, obter_aliases_executes_voador),
)

_MODULOS_TIPOS = (
    "ExecutesNormal",
    "ExecutesAgua",
    "ExecutesCosmico",
    "ExecutesDragao",
    "ExecutesEletrico",
    "ExecutesFada",
    "ExecutesFantasma",
    "ExecutesFogo",
    "ExecutesGelo",
    "ExecutesInseto",
    "ExecutesLutador",
    "ExecutesMetal",
    "ExecutesPedra",
    "ExecutesPlanta",
    "ExecutesPsiquico",
    "ExecutesSombrio",
    "ExecutesSonoro",
    "ExecutesTerra",
    "ExecutesVeneno",
    "ExecutesVoador",
)


def _montar_executes():
    saida = {}
    for obter_executes, _, _ in _FONTES_EXECUTES:
        saida.update(obter_executes())
    return saida


def _montar_passivas():
    saida = []
    for _, obter_passivas, _ in _FONTES_EXECUTES:
        saida.extend(obter_passivas())
    return sorted(saida, key=lambda item: int(str(item.get("code") or 0)))


def _montar_aliases():
    saida = {}
    for _, _, obter_aliases in _FONTES_EXECUTES:
        saida.update(obter_aliases())
    return saida


def _montar_reativos():
    saida = []
    base = "SimuladorServerJogo.Logica.Executes.ExecutesAtaques"
    for nome_modulo in _MODULOS_TIPOS:
        try:
            modulo = importlib.import_module(f"{base}.{nome_modulo}")
        except Exception:
            continue
        for nome_funcao in dir(modulo):
            if not nome_funcao.startswith("obter_executes_reativos_"):
                continue
            func = getattr(modulo, nome_funcao, None)
            if not callable(func):
                continue
            try:
                saida.extend(list(func() or []))
            except Exception:
                continue
    for idx, reativo in enumerate(saida, start=1):
        if not getattr(reativo, "ordem", 0):
            reativo.ordem = idx
    return saida


_EXECUTES = _montar_executes()
_REATIVOS = _montar_reativos()
_PASSIVAS = _montar_passivas()
_ALIASES = _montar_aliases()


def resolver_chave(nome_ou_code):
    bruto = str(nome_ou_code or "").strip()
    if bruto in _ALIASES:
        return _ALIASES.get(bruto)
    chave = normalizar(bruto)
    chave_sem_prefixo = chave[6:] if chave.startswith("ataque") else chave
    if chave in _ALIASES:
        return _ALIASES.get(chave)
    if chave_sem_prefixo in _ALIASES:
        return _ALIASES.get(chave_sem_prefixo)
    return chave_sem_prefixo


def obter_execute_principal(nome_ou_code):
    return _EXECUTES.get(resolver_chave(nome_ou_code))


def executar_execute_principal(nome_ou_code, contexto, alvo=None):
    func = obter_execute_principal(nome_ou_code)
    if not callable(func):
        return {"falha": True, "motivo": "execute_nao_encontrado"}
    return dict(func(dict(contexto or {}), alvo) or {})


def _areas_afetadas_por_alvificacao(area_id, props, lado_usuario):
    area_id = str(area_id or "").upper()
    if not area_id:
        return []
    alvo_cfg = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
    tipo = str(alvo_cfg.get("tipo") or "area").strip().lower()
    if tipo in {"arena", "campo", "arena_inimiga", "campo_inimigo", "todos_inimigos"}:
        return [area_id]
    try:
        idx = int(area_id[1:]) - 1
    except (TypeError, ValueError, IndexError):
        return [area_id]
    if idx < 0 or idx > 8:
        return [area_id]
    prefixo = area_id[:1]
    row, col = idx // 3, idx % 3
    if tipo in {"linha", "fileira", "row", "line"}:
        colunas = range(3)
        try:
            if int(lado_usuario) == 51:
                colunas = range(2, -1, -1)
        except (TypeError, ValueError):
            pass
        return [f"{prefixo}{row * 3 + c + 1}" for c in colunas]
    if tipo in {"coluna", "column"}:
        return [f"{prefixo}{r * 3 + col + 1}" for r in range(3)]
    return [area_id]


def executar_alvificacao(nome_ou_code, contexto):
    props = (contexto or {}).get("propriedades") if isinstance((contexto or {}).get("propriedades"), dict) else {}
    estilo = str(props.get("estilo_logico") or "").strip().lower()
    if estilo == "ativo":
        return []
    partida = (contexto or {}).get("partida")
    acao = (contexto or {}).get("acao") if isinstance((contexto or {}).get("acao"), dict) else {}
    alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
    if str(alvo.get("tipo") or "").strip().lower() == "pokemon" and alvo.get("pokemon_id"):
        pokemon = partida.obter_pokemon(alvo.get("pokemon_id"))
        return [pokemon] if pokemon is not None else []
    area_id = alvo.get("area_id")
    if partida is None or not area_id:
        return []
    usuario = (contexto or {}).get("usuario")
    lado_usuario = getattr(usuario, "lado_id", None)
    alvos = []
    vistos = set()
    alvo_cfg = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
    tipo_alvo = str(alvo_cfg.get("tipo") or "area").strip().lower()
    if tipo_alvo in {"arena", "campo", "arena_inimiga", "campo_inimigo", "todos_inimigos"}:
        area_base = partida.areas.get(str(area_id or ""))
        lado_area = int((area_base or {}).get("lado_id", -999))
        areas = [aid for aid, area in partida.areas.items() if int((area or {}).get("lado_id", -998)) == lado_area]
    else:
        areas = _areas_afetadas_por_alvificacao(area_id, props, lado_usuario)
    for area_afetada in areas:
        ocupante = partida.pokemon_na_area(area_afetada)
        if ocupante is None:
            continue
        chave = getattr(ocupante, "id_batalha", id(ocupante))
        if chave in vistos:
            continue
        vistos.add(chave)
        alvos.append(ocupante)
    return alvos


def registrar_execute_reativo(nome, flag, func, origem_ataque=None, code=None, grupo=None):
    _REATIVOS.append(
        ExecuteReativo(
            nome=str(nome),
            flag=str(flag),
            func=func,
            origem_ataque=origem_ataque,
            code=code,
            grupo=grupo,
            ordem=len(_REATIVOS) + 1,
        )
    )


def obter_executes_reativos(nome_ou_code, flag=None):
    chave = resolver_chave(nome_ou_code)
    origem = str(nome_ou_code or "").strip()
    candidatos = {origem.lower(), chave, normalizar(origem)}
    try:
        candidatos.add(str(int(float(origem))))
    except (TypeError, ValueError):
        pass
    saida = []
    for reativo in _REATIVOS:
        chaves_reativo = {
            str(getattr(reativo, "code", "") or "").strip().lower(),
            str(getattr(reativo, "origem_ataque", "") or "").strip().lower(),
            normalizar(getattr(reativo, "origem_ataque", "")),
            resolver_chave(getattr(reativo, "code", None) or getattr(reativo, "origem_ataque", None)),
        }
        if candidatos & {c for c in chaves_reativo if c}:
            saida.append(reativo)
    if flag:
        saida = [r for r in saida if str(r.flag) == str(flag)]
    return saida


def obter_passivas_ataque():
    return list(_PASSIVAS)
