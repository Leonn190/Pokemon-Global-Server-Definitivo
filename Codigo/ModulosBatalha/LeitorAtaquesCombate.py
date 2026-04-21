from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable

_CAMPOS_EXECUCAO_VISUAL = {"forma", "alcance", "alcance_max", "largura", "raio", "angulo", "velocidade_pct", "ricochetes", "ricochetes_paredes", "ricochetes_pokemons"}


def normalizar_nome(valor: Any) -> str:
    texto = str(valor or "").strip().casefold()
    sem_acentos = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sem_acentos if unicodedata.category(c) != "Mn")


def _caminho_padrao() -> Path:
    return Path(__file__).resolve().parents[2] / "Dados" / "Pokemon Global Server - AtaquesCombate.json"


def _nome_ataque_de_dict(ataque: Dict[str, Any]) -> str:
    for chave in ("Ataque", "Nome", "nome", "ataque"):
        nome = str(ataque.get(chave) or "").strip()
        if nome:
            return nome
    return ""


def _normalizar_ataque_bruto(chave: str, ataque: Dict[str, Any]) -> Dict[str, Any]:
    preparo = dict(ataque.get("preparo") or {})
    execucao_bruta = dict(ataque.get("execucao") or {})
    execucao = {campo: execucao_bruta[campo] for campo in _CAMPOS_EXECUCAO_VISUAL if campo in execucao_bruta}

    return {
        "id": ataque.get("id"),
        "nome": str(ataque.get("nome") or chave or "").strip(),
        "preparo": preparo,
        "execucao": execucao,
        "tags": list(ataque.get("tags") or []),
    }


def carregar_ataques_combate(caminho: str | Path | None = None) -> Dict[str, Dict[str, Any]]:
    arquivo = Path(caminho) if caminho is not None else _caminho_padrao()
    if not arquivo.exists():
        return {}

    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    ataques = dados.get("ataques") if isinstance(dados, dict) else {}
    if not isinstance(ataques, dict):
        return {}

    catalogo: Dict[str, Dict[str, Any]] = {}
    for chave, ataque in ataques.items():
        if not isinstance(ataque, dict):
            continue
        item = _normalizar_ataque_bruto(str(chave), ataque)
        nome_norm = normalizar_nome(item.get("nome"))
        if not nome_norm:
            continue
        catalogo[nome_norm] = item
    return catalogo


class LeitorAtaquesCombate:
    def __init__(self, caminho: str | Path | None = None) -> None:
        self._caminho = Path(caminho) if caminho is not None else _caminho_padrao()
        self._catalogo: Dict[str, Dict[str, Any]] = {}
        self.recarregar()

    def recarregar(self) -> None:
        self._catalogo = carregar_ataques_combate(self._caminho)

    def _nome_entrada(self, ataque_ou_nome: Any) -> str:
        if isinstance(ataque_ou_nome, str):
            return ataque_ou_nome
        if isinstance(ataque_ou_nome, dict):
            return _nome_ataque_de_dict(ataque_ou_nome)
        return ""

    def obter(self, nome_ataque: Any) -> Dict[str, Any]:
        nome = self._nome_entrada(nome_ataque)
        if not nome:
            return {}
        return dict(self._catalogo.get(normalizar_nome(nome)) or {})

    def existe(self, nome_ataque: Any) -> bool:
        return bool(self.obter(nome_ataque))

    def listar(self) -> Iterable[Dict[str, Any]]:
        return [dict(item) for item in self._catalogo.values()]

    def preparo_de(self, ataque_ou_nome: Any) -> Dict[str, Any]:
        ataque = self.obter(ataque_ou_nome)
        return dict(ataque.get("preparo") or {}) if ataque else {}

    def execucao_de(self, ataque_ou_nome: Any) -> Dict[str, Any]:
        ataque = self.obter(ataque_ou_nome)
        return dict(ataque.get("execucao") or {}) if ataque else {}
