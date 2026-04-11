from __future__ import annotations

from typing import Dict


class PokemonBatalha:
    def __init__(self, dados: Dict[str, object] | None = None, lado: str = "") -> None:
        bruto = dict(dados or {})
        self.Dados = bruto
        self.Uid = str(bruto.get("uid") or bruto.get("id") or bruto.get("ID") or "")
        self.Nome = str(bruto.get("nome") or bruto.get("Nome") or bruto.get("especie") or "Pokemon")
        self.Lado = str(lado or bruto.get("lado") or "")

    def serializar(self) -> Dict[str, object]:
        return {
            "uid": self.Uid,
            "nome": self.Nome,
            "lado": self.Lado,
        }
