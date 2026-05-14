from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .ConfigIA import clamp01
from .ContextoIA import normalizar


class MetadadosIA:
    """Consulta metadados estratégicos dos ataques.

    Metadado orienta a IA. Ele não executa ataque e não substitui execute real.
    O critério conhecimento define quantos campos são liberados para a análise.
    """

    CAMPOS_BAIXO = ("papeis",)
    CAMPOS_MEDIO = ("papeis", "alvos_preferidos", "prioridade_simulacao")
    CAMPOS_ALTO = ("papeis", "alvos_preferidos", "riscos", "efeitos_relevantes", "condicoes", "prioridade_simulacao")

    def __init__(self, caminho: str | Path | None = None, dados: Mapping[str, Any] | None = None):
        self.caminho = (
            Path(caminho)
            if caminho is not None
            else Path(__file__).resolve().parents[3] / "Dados" / "Ataques" / "MetaDadosAtaques"
        )
        self._dados_brutos = dict(dados or self._carregar_arquivo())
        self._por_nome: dict[str, dict[str, Any]] = {}
        self._por_code: dict[str, dict[str, Any]] = {}
        self._indexar()

    def _carregar_arquivo(self) -> dict[str, Any]:
        if self.caminho.is_dir():
            dados_agregados: dict[str, Any] = {}
            for arquivo in sorted(self.caminho.glob("MetaDados*.json")):
                try:
                    dados = json.loads(arquivo.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if isinstance(dados, dict):
                    dados_agregados.update(dados)
            return dados_agregados
        if not self.caminho.exists():
            return {}
        try:
            dados = json.loads(self.caminho.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return dados if isinstance(dados, dict) else {}

    def _indexar(self) -> None:
        for chave, valor in self._dados_brutos.items():
            if not isinstance(valor, dict):
                continue
            item = dict(valor)
            nome = str(item.get("nome") or chave or "").strip()
            if nome:
                self._por_nome[normalizar(nome)] = item
            codigo = item.get("codigo", item.get("Code", item.get("ID")))
            if codigo is not None:
                try:
                    codigo = str(int(float(codigo)))
                except (TypeError, ValueError):
                    codigo = str(codigo)
                self._por_code[codigo] = item

    def consultar(self, ataque: Mapping[str, Any] | None, conhecimento: float = 1.0) -> dict[str, Any]:
        item = self._buscar_bruto(ataque)
        if not item:
            return self.fallback(ataque, conhecimento)
        return self._filtrar_por_conhecimento(item, conhecimento)

    def _buscar_bruto(self, ataque: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(ataque, Mapping):
            return None
        code = ataque.get("Code", ataque.get("ID", ataque.get("code")))
        if code is not None:
            try:
                code = str(int(float(code)))
            except (TypeError, ValueError):
                code = str(code)
            if code in self._por_code:
                return dict(self._por_code[code])
        nome = normalizar(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome"))
        if nome and nome in self._por_nome:
            return dict(self._por_nome[nome])
        return None

    def fallback(self, ataque: Mapping[str, Any] | None, conhecimento: float = 1.0) -> dict[str, Any]:
        nome = ""
        if isinstance(ataque, Mapping):
            nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or ataque.get("Code") or ataque.get("ID") or "").strip()
        item = {
            "nome": nome,
            "papeis": ["dano"],
            "alvos_preferidos": ["inimigo_ferido"],
            "riscos": {},
            "efeitos_relevantes": [],
            "condicoes": [],
            "prioridade_simulacao": 0.35,
            "fallback": True,
        }
        return self._filtrar_por_conhecimento(item, conhecimento)

    def _filtrar_por_conhecimento(self, item: Mapping[str, Any], conhecimento: float) -> dict[str, Any]:
        conhecimento = clamp01(conhecimento, 0.55)
        if conhecimento < 0.35:
            campos = self.CAMPOS_BAIXO
        elif conhecimento < 0.75:
            campos = self.CAMPOS_MEDIO
        else:
            campos = self.CAMPOS_ALTO

        saida: dict[str, Any] = {
            "nome": item.get("nome"),
            "codigo": item.get("codigo", item.get("Code", item.get("ID"))),
        }
        for campo in campos:
            valor = item.get(campo)
            if isinstance(valor, (list, tuple)):
                saida[campo] = list(valor)
            elif isinstance(valor, dict):
                saida[campo] = dict(valor)
            elif valor is not None:
                saida[campo] = valor
        saida["nivel_conhecimento"] = conhecimento
        return saida
