from __future__ import annotations

import csv
import unicodedata
from pathlib import Path


def _norm(valor: object) -> str:
    txt = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    return "".join(ch for ch in txt if not unicodedata.combining(ch)).replace(" ", "")


def _f(valor: object, default: float = 1.0) -> float:
    try:
        if isinstance(valor, str):
            return float(valor.replace(",", "."))
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


class FraquezasResistencia:
    def __init__(self):
        self._tabela: dict[str, dict[str, float]] = {}
        self._carregar()

    def _carregar(self):
        caminho = Path(__file__).resolve().parents[2] / "Dados" / "Pokemon Global Server - Sistema FR.csv"
        if not caminho.exists():
            return
        with caminho.open("r", encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.reader(f))
        if len(linhas) < 2:
            return
        cabecalho = [_norm(c) for c in linhas[0][1:]]
        for row in linhas[1:]:
            if not row:
                continue
            tipo_atk = _norm(row[0])
            if not tipo_atk:
                continue
            mapa: dict[str, float] = {}
            for idx, tipo_def in enumerate(cabecalho, start=1):
                if idx >= len(row):
                    continue
                mapa[tipo_def] = _f(row[idx], 1.0)
            self._tabela[tipo_atk] = mapa

    def obter_multiplicador(self, tipo_ataque: object, tipos_defensor: object) -> float:
        atk = _norm(tipo_ataque)
        if not atk:
            return 1.0
        tipos = tipos_defensor if isinstance(tipos_defensor, list) else [tipos_defensor]
        mult = 1.0
        for tipo in tipos:
            tipo_n = _norm(tipo)
            if not tipo_n:
                continue
            mult *= self._tabela.get(atk, {}).get(tipo_n, 1.0)
            if mult == 0:
                return 0.0
        return float(mult)

    def eh_fraco(self, tipo_ataque: object, tipos_defensor: object) -> bool:
        return self.obter_multiplicador(tipo_ataque, tipos_defensor) > 1.0

    def resiste(self, tipo_ataque: object, tipos_defensor: object) -> bool:
        mult = self.obter_multiplicador(tipo_ataque, tipos_defensor)
        return 0.0 < mult < 1.0

    def eh_imune(self, tipo_ataque: object, tipos_defensor: object) -> bool:
        return self.obter_multiplicador(tipo_ataque, tipos_defensor) == 0.0
