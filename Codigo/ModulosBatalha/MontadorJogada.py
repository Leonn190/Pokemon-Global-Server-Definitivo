from __future__ import annotations

from typing import Dict, List, Optional, Tuple


class MontadorJogada:
    MAX_MOVIMENTOS = 5
    MAX_MOVIMENTOS_POR_POKEMON = 2

    def __init__(self, regras_batalha: Dict[str, object] | None = None) -> None:
        self._jogadas: List[Dict[str, object]] = []
        self._selecionado_id: Optional[int] = None
        self._proximo_id = 1
        self._regras_batalha = dict(regras_batalha or {})

    @staticmethod
    def _normalizar_id(executor_id: object) -> str:
        return str(executor_id or "")

    @staticmethod
    def _nome_acao(jogada: Dict[str, object]) -> str:
        nome_manual = str(jogada.get("acao_chave_manual") or "").strip()
        if nome_manual:
            return nome_manual.casefold()
        ataque = jogada.get("ataque") if isinstance(jogada, dict) else None
        if isinstance(ataque, dict):
            nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()
            if nome:
                return nome.casefold()
        return "__movimento_nativo__"

    def _jogadas_executor(self, executor_id: object) -> List[Dict[str, object]]:
        chave = self._normalizar_id(executor_id)
        return [item for item in self._jogadas if self._normalizar_id(item.get("executor_id")) == chave]

    def _multiplicador_multiplas_acoes(self, quantidade_previa: int) -> float:
        regras = self._regras_batalha.get("multiplas_acoes") if isinstance(self._regras_batalha.get("multiplas_acoes"), dict) else {}
        try:
            multiplicador_base = float(regras.get("multiplicador_base", 1.0))
        except (TypeError, ValueError):
            multiplicador_base = 1.0
        try:
            acrescimo = float(regras.get("acrescimo_multiplicador_por_acao_extra", 0.2))
        except (TypeError, ValueError):
            acrescimo = 0.2
        return max(0.0, multiplicador_base + max(0, int(quantidade_previa)) * acrescimo)

    def _custo_total_para_executor(self, executor_id: object, custo_base: float) -> float:
        quantidade = len(self._jogadas_executor(executor_id))
        multiplicador = self._multiplicador_multiplas_acoes(quantidade)
        return max(0.0, float(custo_base) * multiplicador)

    def pode_adicionar(self, jogada: Dict[str, object]) -> Tuple[bool, str, float]:
        if not isinstance(jogada, dict):
            return False, "Jogada inválida.", 0.0
        executor_id = self._normalizar_id(jogada.get("executor_id"))
        if not executor_id:
            return False, "Sem executor.", 0.0
        if len(self._jogadas) >= self.MAX_MOVIMENTOS:
            return False, "A jogada já está cheia.", 0.0
        jogadas_executor = self._jogadas_executor(executor_id)
        if len(jogadas_executor) >= self.MAX_MOVIMENTOS_POR_POKEMON:
            return False, "Esse Pokémon já tem 2 movimentos.", 0.0

        nome_acao = self._nome_acao(jogada)
        if any(self._nome_acao(item) == nome_acao for item in jogadas_executor):
            return False, "Esse movimento já foi usado por esse Pokémon.", 0.0

        custo_base = float(jogada.get("custo_base") or jogada.get("custo") or 0.0)
        return True, "", self._custo_total_para_executor(executor_id, custo_base)

    def adicionar(self, jogada: Dict[str, object]) -> Tuple[Optional[Dict[str, object]], str]:
        permitido, motivo, custo_total = self.pode_adicionar(jogada)
        if not permitido:
            return None, motivo

        item = dict(jogada)
        item["id"] = self._proximo_id
        item["executor_id"] = self._normalizar_id(item.get("executor_id"))
        item["acao_chave"] = self._nome_acao(item)
        item["custo_base"] = float(item.get("custo_base") or item.get("custo") or 0.0)
        item["custo"] = custo_total

        self._proximo_id += 1
        self._jogadas.append(item)
        self._selecionado_id = None
        return dict(item), ""

    def listar(self) -> List[Dict[str, object]]:
        return [dict(item) for item in self._jogadas]

    def listar_referencias(self) -> List[Dict[str, object]]:
        return list(self._jogadas)

    def limpar(self) -> None:
        self._jogadas.clear()
        self._selecionado_id = None

    def remover(self, jogada_id: object) -> Optional[Dict[str, object]]:
        try:
            alvo = int(jogada_id)
        except (TypeError, ValueError):
            return None
        for indice, item in enumerate(self._jogadas):
            if int(item.get("id") or 0) != alvo:
                continue
            removido = self._jogadas.pop(indice)
            if self._selecionado_id == alvo:
                self._selecionado_id = None
            return dict(removido)
        return None

    def selecionar(self, jogada_id: object | None) -> Optional[int]:
        if jogada_id in (None, "", 0):
            self._selecionado_id = None
            return None
        try:
            alvo = int(jogada_id)
        except (TypeError, ValueError):
            return self._selecionado_id
        if any(int(item.get("id") or 0) == alvo for item in self._jogadas):
            self._selecionado_id = alvo
        return self._selecionado_id

    def selecionado_id(self) -> Optional[int]:
        return self._selecionado_id

    def custo_reservado(self, combatente_id: object) -> float:
        chave = self._normalizar_id(combatente_id)
        total = 0.0
        for item in self._jogadas:
            if self._normalizar_id(item.get("executor_id")) != chave:
                continue
            try:
                total += float(item.get("custo") or 0.0)
            except (TypeError, ValueError):
                continue
        return total

    def quantidade_executor(self, combatente_id: object) -> int:
        return len(self._jogadas_executor(combatente_id))

    def possui_acao_executor(self, combatente_id: object, nome_acao: str) -> bool:
        chave = self._normalizar_id(combatente_id)
        nome = str(nome_acao or "").casefold()
        return any(
            self._normalizar_id(item.get("executor_id")) == chave and str(item.get("acao_chave") or "").casefold() == nome
            for item in self._jogadas
        )

    def posicao_virtual_executor(self, executor_id: object, pokemons_por_id: Dict[str, object]) -> Optional[tuple[float, float]]:
        visuais, construtos = self.resolver_visuais(pokemons_por_id)
        _ = visuais
        chave = self._normalizar_id(executor_id)
        if chave in construtos:
            return tuple(construtos[chave])
        pokemon = pokemons_por_id.get(chave)
        if pokemon is None:
            return None
        posicao = getattr(pokemon, "Posicao", None)
        if isinstance(posicao, (tuple, list)) and len(posicao) == 2:
            return float(posicao[0]), float(posicao[1])
        return None

    def resolver_visuais(self, pokemons_por_id: Dict[str, object]) -> Tuple[List[Dict[str, object]], Dict[str, tuple[float, float]]]:
        posicoes: Dict[str, tuple[float, float]] = {}
        for chave, pokemon in (pokemons_por_id or {}).items():
            pos = getattr(pokemon, "Posicao", None)
            if isinstance(pos, (tuple, list)) and len(pos) == 2:
                posicoes[str(chave)] = (float(pos[0]), float(pos[1]))

        jogadas_visuais: List[Dict[str, object]] = []
        construtos: Dict[str, tuple[float, float]] = {}
        for item in self._jogadas:
            chave = self._normalizar_id(item.get("executor_id"))
            origem = posicoes.get(chave)
            if origem is None:
                continue
            visual = dict(item)
            visual["origem_mundo"] = origem
            jogadas_visuais.append(visual)

            if item.get("tipo_movimento") and not item.get("troca_reserva_id") and isinstance(item.get("destino_mundo"), (tuple, list)) and len(item.get("destino_mundo")) == 2:
                destino = item.get("destino_mundo")
                posicoes[chave] = (float(destino[0]), float(destino[1]))
                construtos[chave] = posicoes[chave]

        return jogadas_visuais, construtos
