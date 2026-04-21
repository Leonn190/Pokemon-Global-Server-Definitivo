from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import unicodedata

from SimuladorServerJogo.Batalha.Combate.Esquemas import (
    AtaqueCombateSpec,
    ComponenteDanoSpec,
    EfeitoSpec,
    ExecucaoSpec,
    PreparoSpec,
)
from SimuladorServerJogo.Batalha.Combate.ValidadorAtaques import CAMINHO_PADRAO, validar_arquivo


_CACHE_CATALOGO: CatalogoAtaquesCombate | None = None


def normalizar_nome(valor: object) -> str:
    texto = str(valor or "").strip().casefold()
    sem_acentos = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sem_acentos if unicodedata.category(c) != "Mn")


def _to_float(valor: Any) -> float | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _to_int(valor: Any) -> int | None:
    numero = _to_float(valor)
    if numero is None:
        return None
    return int(numero)


def _parse_componentes(componentes: Any) -> list[ComponenteDanoSpec]:
    saida: list[ComponenteDanoSpec] = []
    if not isinstance(componentes, list):
        return saida
    for item in componentes:
        if not isinstance(item, dict):
            continue
        saida.append(
            ComponenteDanoSpec(
                atributo=str(item.get("atributo") or "").strip(),
                escala=float(item.get("escala") or 0.0),
                categoria=str(item.get("categoria") or "").strip(),
            )
        )
    return saida


def _parse_efeito(efeito: dict[str, Any]) -> EfeitoSpec:
    resto = {
        chave: valor
        for chave, valor in efeito.items()
        if chave not in {"tipo", "alvo", "valor", "status", "atributo", "componentes", "condicao"}
    }
    valor_num = _to_float(efeito.get("valor"))
    if valor_num is None:
        valor_saida = efeito.get("valor")
    elif valor_num.is_integer():
        valor_saida = int(valor_num)
    else:
        valor_saida = valor_num

    condicao = efeito.get("condicao") if isinstance(efeito.get("condicao"), dict) else {}
    return EfeitoSpec(
        tipo=str(efeito.get("tipo") or "").strip(),
        alvo=str(efeito.get("alvo") or "").strip(),
        valor=valor_saida,
        status=str(efeito.get("status") or "").strip(),
        atributo=str(efeito.get("atributo") or "").strip(),
        componentes=_parse_componentes(efeito.get("componentes")),
        condicao=dict(condicao),
        dados=resto,
    )


def _parse_preparo(preparo: dict[str, Any]) -> PreparoSpec:
    resto = {
        chave: valor
        for chave, valor in preparo.items()
        if chave
        not in {
            "tipo",
            "indicador",
            "alcance",
            "largura",
            "raio",
            "angulo",
            "intensidade_min",
            "intensidade_max",
        }
    }
    return PreparoSpec(
        tipo=str(preparo.get("tipo") or "").strip(),
        indicador=str(preparo.get("indicador") or "").strip(),
        alcance=_to_float(preparo.get("alcance") or preparo.get("alcance_max")),
        largura=_to_float(preparo.get("largura")),
        raio=_to_float(preparo.get("raio")),
        angulo=_to_float(preparo.get("angulo")),
        intensidade_min=_to_float(preparo.get("intensidade_min")),
        intensidade_max=_to_float(preparo.get("intensidade_max")),
        dados=resto,
    )


def _parse_execucao(execucao: dict[str, Any]) -> ExecucaoSpec:
    resto = {
        chave: valor
        for chave, valor in execucao.items()
        if chave
        not in {
            "forma",
            "alcance",
            "alcance_max",
            "largura",
            "raio",
            "angulo",
            "velocidade_pct",
            "velocidade_tiles_tick",
            "desaceleracao",
            "ricochetes_paredes",
            "ricochetes_pokemons",
            "atravessa_pokemons",
            "atravessa_paredes",
            "atinge",
            "instantaneo",
        }
    }
    return ExecucaoSpec(
        forma=str(execucao.get("forma") or "").strip(),
        alcance=_to_float(execucao.get("alcance") or execucao.get("alcance_max")),
        largura=_to_float(execucao.get("largura")),
        raio=_to_float(execucao.get("raio")),
        angulo=_to_float(execucao.get("angulo")),
        velocidade_pct=_to_float(execucao.get("velocidade_pct")),
        velocidade_tiles_tick=_to_float(execucao.get("velocidade_tiles_tick")),
        desaceleracao=_to_float(execucao.get("desaceleracao")),
        ricochetes_paredes=_to_int(execucao.get("ricochetes_paredes")),
        ricochetes_pokemons=_to_int(execucao.get("ricochetes_pokemons")),
        atravessa_pokemons=execucao.get("atravessa_pokemons") if isinstance(execucao.get("atravessa_pokemons"), bool) else None,
        atravessa_paredes=execucao.get("atravessa_paredes") if isinstance(execucao.get("atravessa_paredes"), bool) else None,
        atinge=str(execucao.get("atinge") or "").strip(),
        instantaneo=execucao.get("instantaneo") if isinstance(execucao.get("instantaneo"), bool) else None,
        dados=resto,
    )


def _dict_para_spec(nome: str, bruto: dict[str, Any]) -> AtaqueCombateSpec:
    preparo = bruto.get("preparo") if isinstance(bruto.get("preparo"), dict) else {}
    execucao = bruto.get("execucao") if isinstance(bruto.get("execucao"), dict) else {}
    efeitos_ao_acertar = bruto.get("efeitos_ao_acertar") if isinstance(bruto.get("efeitos_ao_acertar"), list) else []
    efeitos_ao_falhar = bruto.get("efeitos_ao_falhar") if isinstance(bruto.get("efeitos_ao_falhar"), list) else []
    tags = [str(item) for item in list(bruto.get("tags") or [])]

    return AtaqueCombateSpec(
        id=str(bruto.get("id") or normalizar_nome(nome)).strip(),
        nome=str(bruto.get("nome") or nome).strip(),
        preparo=_parse_preparo(preparo),
        execucao=_parse_execucao(execucao),
        efeitos_ao_acertar=[_parse_efeito(item) for item in efeitos_ao_acertar if isinstance(item, dict)],
        efeitos_ao_falhar=[_parse_efeito(item) for item in efeitos_ao_falhar if isinstance(item, dict)],
        tags=tags,
        bruto=dict(bruto),
    )


class CatalogoAtaquesCombate:
    def __init__(self, dados_brutos: dict[str, Any], caminho: str | Path | None = None) -> None:
        self.caminho = Path(caminho) if caminho else CAMINHO_PADRAO
        self.versao = int(dados_brutos.get("versao") or 1)
        self._ataques_por_nome_norm: dict[str, AtaqueCombateSpec] = {}

        ataques = dados_brutos.get("ataques") if isinstance(dados_brutos.get("ataques"), dict) else {}
        for nome, bruto in ataques.items():
            if not isinstance(bruto, dict):
                continue
            spec = _dict_para_spec(str(nome), bruto)
            self._ataques_por_nome_norm[normalizar_nome(spec.nome)] = spec

    def obter(self, nome: str) -> AtaqueCombateSpec | None:
        return self._ataques_por_nome_norm.get(normalizar_nome(nome))

    def existe(self, nome: str) -> bool:
        return self.obter(nome) is not None

    def listar(self) -> list[AtaqueCombateSpec]:
        return list(self._ataques_por_nome_norm.values())

    def validar(self) -> list[str]:
        return validar_arquivo(self.caminho)


def carregar_catalogo_ataques(caminho: str | Path | None = None) -> CatalogoAtaquesCombate:
    global _CACHE_CATALOGO
    caminho_arquivo = Path(caminho) if caminho else CAMINHO_PADRAO

    if caminho is None and _CACHE_CATALOGO is not None:
        return _CACHE_CATALOGO

    dados = json.loads(caminho_arquivo.read_text(encoding="utf-8-sig"))
    catalogo = CatalogoAtaquesCombate(dados, caminho=caminho_arquivo)

    if caminho is None:
        _CACHE_CATALOGO = catalogo

    return catalogo
