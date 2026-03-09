from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class GeradorBaus:
    TIPOS_ORDEM = ("Comum", "Incomum", "Raro", "Epico", "Lendario", "Mitico")

    def __init__(self, arquivo_baus: Optional[Path] = None, arquivo_itens: Optional[Path] = None, dia_fixo: int = 1) -> None:
        raiz = Path(__file__).resolve().parents[2]
        dados = raiz / "Dados"
        self._arquivo_baus = Path(arquivo_baus or (dados / "Global server - Baus.csv"))
        self._arquivo_itens = Path(arquivo_itens or (dados / "Global server - Itens.csv"))
        self._dia_fixo = max(1, int(dia_fixo))
        self._tabela_baus = self._carregar_tabela_baus()
        self._itens_validos = self._carregar_itens_validos()

    @staticmethod
    def _parse_percent(valor: str) -> float:
        texto = str(valor or "").strip().replace("%", "")
        if not texto:
            return 0.0
        try:
            return max(0.0, float(texto))
        except ValueError:
            return 0.0

    def _carregar_tabela_baus(self) -> Dict[int, Dict[str, object]]:
        tabela: Dict[int, Dict[str, object]] = {}
        dia_atual: Optional[int] = None
        with self._arquivo_baus.open("r", encoding="utf-8") as f:
            leitor = csv.reader(f)
            for linha in leitor:
                colunas = [str(c or "").strip() for c in linha]
                tokens = [c for c in colunas if c]
                if not tokens:
                    continue

                if tokens[0].lower().startswith("dia"):
                    try:
                        dia_atual = int(tokens[0].split(" ")[1])
                    except Exception:
                        dia_atual = None
                    if dia_atual is not None and dia_atual not in tabela:
                        tabela[dia_atual] = {"chance_tipos": {}, "chance_raridade_por_tipo": {}}
                    continue

                if dia_atual is None:
                    continue
                if tokens[0].lower() == "bau":
                    continue
                if tokens[0] not in self.TIPOS_ORDEM:
                    continue

                tipo = tokens[0]
                chance_tipo = self._parse_percent(tokens[1]) if len(tokens) > 1 else 0.0
                pesos_raridade = {}
                for idx in range(6):
                    col = tokens[2 + idx] if len(tokens) > (2 + idx) else "0"
                    pesos_raridade[idx + 1] = self._parse_percent(col)

                tabela[dia_atual]["chance_tipos"][tipo] = chance_tipo
                tabela[dia_atual]["chance_raridade_por_tipo"][tipo] = pesos_raridade

        return tabela

    def _carregar_itens_validos(self) -> Dict[int, List[Dict[str, object]]]:
        itens_por_raridade: Dict[int, List[Dict[str, object]]] = {k: [] for k in range(1, 7)}
        with self._arquivo_itens.open("r", encoding="utf-8") as f:
            leitor = csv.DictReader(f)
            for linha in leitor:
                if not isinstance(linha, dict):
                    continue
                raridade_raw = str(linha.get("Raridade", "")).strip()
                if not raridade_raw.isdigit():
                    continue
                raridade = int(raridade_raw)
                if raridade < 1 or raridade > 6:
                    continue
                itens_por_raridade[raridade].append(
                    {
                        "Nome": str(linha.get("Nome", "")).strip(),
                        "Descrição": str(linha.get("Descrição", "")).strip(),
                        "Raridade": raridade,
                        "Estilo": str(linha.get("Estilo", "")).strip(),
                        "Code": str(linha.get("Code", "")).strip(),
                    }
                )
        return itens_por_raridade

    def _dia_base(self) -> int:
        dias = sorted(self._tabela_baus.keys())
        if not dias:
            return 0
        idx = min(len(dias) - 1, self._dia_fixo - 1)
        return dias[idx]

    @staticmethod
    def _escolher_por_peso(rng: random.Random, pesos: Dict[object, float]):
        opcoes = [(k, max(0.0, float(v))) for k, v in pesos.items() if float(v) > 0.0]
        if not opcoes:
            return None
        total = sum(v for _, v in opcoes)
        alvo = rng.uniform(0.0, total)
        acumulado = 0.0
        for chave, peso in opcoes:
            acumulado += peso
            if acumulado >= alvo:
                return chave
        return opcoes[-1][0]

    def gerar_bau(self, rng: random.Random) -> Dict[str, object]:
        dia = self._dia_base()
        bloco = self._tabela_baus.get(dia, {})
        chance_tipos = bloco.get("chance_tipos", {}) if isinstance(bloco, dict) else {}
        tipo = self._escolher_por_peso(rng, chance_tipos) or "Comum"

        chance_raridade = {}
        if isinstance(bloco, dict):
            tabela_tipo = bloco.get("chance_raridade_por_tipo", {})
            if isinstance(tabela_tipo, dict):
                chance_raridade = tabela_tipo.get(tipo, {})

        qtd_itens = rng.randint(1, 3)
        usados = set()
        itens: List[Dict[str, object]] = []

        tentativas = 0
        while len(itens) < qtd_itens and tentativas < 50:
            tentativas += 1
            raridade = self._escolher_por_peso(rng, chance_raridade)
            if raridade is None:
                break
            pool = [item for item in self._itens_validos.get(int(raridade), []) if item.get("Code") not in usados]
            if not pool:
                continue
            escolhido = dict(rng.choice(pool))
            usados.add(escolhido.get("Code"))
            itens.append(escolhido)

        if not itens:
            for raridade in range(1, 7):
                pool = [item for item in self._itens_validos.get(raridade, []) if item.get("Code") not in usados]
                if pool:
                    escolhido = dict(rng.choice(pool))
                    itens.append(escolhido)
                    break

        return {"tipo_bau": str(tipo), "itens": itens[:3]}


GERADOR_BAUS_SERVER = GeradorBaus()
