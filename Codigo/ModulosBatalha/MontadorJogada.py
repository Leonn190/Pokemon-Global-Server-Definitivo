from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class MontadorJogada:
    MAX_MOVIMENTOS = 5
    MAX_MOVIMENTOS_POR_POKEMON = 2

    def __init__(self, regras_batalha: Dict[str, object] | None = None) -> None:
        self._jogadas: List[Dict[str, object]] = []
        self._selecionado_id: Optional[int] = None
        self._proximo_id = 1
        self._regras_batalha = dict(regras_batalha or {})
        self._ataques_por_nome = self._carregar_propriedades_ataque()

    @classmethod
    def _carregar_propriedades_ataque(cls) -> Dict[str, Dict[str, object]]:
        caminho = Path("Dados") / "Pokemon Global Server - PropriedadesAtaque.json"
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except Exception:
            return {}
        ataques = dados.get("ataques") if isinstance(dados, dict) else {}
        if not isinstance(ataques, dict):
            return {}
        saida: Dict[str, Dict[str, object]] = {}
        for ataque in ataques.values():
            if not isinstance(ataque, dict):
                continue
            nome = str(ataque.get("nome") or ataque.get("Ataque") or "").strip()
            if not nome:
                continue
            saida[nome.casefold()] = dict(ataque)
        return saida

    @staticmethod
    def _normalizar_id(executor_id: object) -> str:
        return str(executor_id or "")

    @staticmethod
    def _nome_ataque(ataque: Dict[str, object] | None) -> str:
        if not isinstance(ataque, dict):
            return ""
        return str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()

    def estilo_ataque(self, ataque: Dict[str, object] | None) -> str:
        prop = self.obter_propriedades_ataque(ataque)
        nome = self._nome_ataque(ataque).casefold()
        if not nome:
            return "movimento"
        estilo = str(prop.get("estilo") or ataque.get("estilo") or "").strip().casefold()
        if estilo:
            return estilo
        return "ataque"

    def obter_propriedades_ataque(self, ataque: Dict[str, object] | None) -> Dict[str, object]:
        nome = self._nome_ataque(ataque).casefold()
        base = dict(self._ataques_por_nome.get(nome, {}))
        if isinstance(ataque, dict):
            for chave, valor in ataque.items():
                if chave not in base:
                    base[chave] = valor
        return base

    def ataque_eh_passiva(self, ataque: Dict[str, object] | None) -> bool:
        return self.estilo_ataque(ataque) == "passiva"

    def custo_base_ataque(self, ataque: Dict[str, object] | None, fallback: float = 0.0) -> float:
        prop = self.obter_propriedades_ataque(ataque)
        try:
            return max(0.0, float(prop.get("custo", ataque.get("custo", fallback) if isinstance(ataque, dict) else fallback) or 0.0))
        except (TypeError, ValueError):
            return max(0.0, float(fallback or 0.0))

    @staticmethod
    def validar_segundo_ponto_parede(ponto_a: tuple[float, float], ponto_b: tuple[float, float], distancia_max: float) -> bool:
        if not (isinstance(ponto_a, (tuple, list)) and len(ponto_a) == 2 and isinstance(ponto_b, (tuple, list)) and len(ponto_b) == 2):
            return False
        return math.dist((float(ponto_a[0]), float(ponto_a[1])), (float(ponto_b[0]), float(ponto_b[1]))) <= float(distancia_max)

    @staticmethod
    def atingiu_limiar_arrasto(inicio_px: tuple[float, float], fim_px: tuple[float, float], limiar_px: float = 12.0) -> bool:
        if not (isinstance(inicio_px, (tuple, list)) and len(inicio_px) == 2 and isinstance(fim_px, (tuple, list)) and len(fim_px) == 2):
            return False
        return math.dist((float(inicio_px[0]), float(inicio_px[1])), (float(fim_px[0]), float(fim_px[1]))) >= float(limiar_px)

    def resolver_arrasto_para_jogada(
        self,
        *,
        executor,
        executor_id: object,
        origem_mundo: tuple[float, float],
        destino_mundo: tuple[float, float],
        dentro_arena: bool,
        reserva_id: object | None,
        reserva_valida: bool,
    ) -> Dict[str, object] | None:
        if reserva_id is not None:
            if not bool(reserva_valida):
                return None
            return {
                "executor": executor,
                "executor_id": self._normalizar_id(executor_id),
                "troca_reserva_id": str(reserva_id),
                "destino_mundo": tuple(destino_mundo),
                "custo_base": 0.0,
                "estilo": "troca",
                "tipo_movimento": False,
            }
        if not bool(dentro_arena):
            return None
        return {
            "executor": executor,
            "executor_id": self._normalizar_id(executor_id),
            "destino_mundo": tuple(destino_mundo),
            "custo_base": self.custo_movimento(executor, origem_mundo, destino_mundo),
            "estilo": "movimento",
            "tipo_movimento": True,
        }

    @staticmethod
    def _nome_acao(jogada: Dict[str, object]) -> str:
        nome_manual = str(jogada.get("acao_chave_manual") or "").strip()
        if nome_manual:
            return nome_manual.casefold()
        if jogada.get("troca_reserva_id"):
            return "__troca__"
        ataque = jogada.get("ataque") if isinstance(jogada, dict) else None
        if isinstance(ataque, dict):
            nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()
            if nome:
                return nome.casefold()
        return "__movimento_nativo__"

    def _jogadas_executor(self, executor_id: object) -> List[Dict[str, object]]:
        chave = self._normalizar_id(executor_id)
        return [item for item in self._jogadas if self._normalizar_id(item.get("executor_id")) == chave]

    def _custo_total_para_executor(self, quantidade_previa: int, custo_base: float, jogada: Dict[str, object]) -> float:
        if quantidade_previa <= 0:
            return max(0.0, float(custo_base))
        if bool(jogada.get("tipo_movimento")) and not bool(jogada.get("ataque")):
            return max(0.0, float(custo_base))
        return max(0.0, float(custo_base) * 1.1)

    def _executor_bloqueado_por_troca(self, executor_id: object) -> bool:
        return any(item.get("troca_reserva_id") for item in self._jogadas_executor(executor_id))

    def pode_adicionar(self, jogada: Dict[str, object], energia_disponivel: float | None = None, ignorar_custo: bool = False) -> Tuple[bool, str, float]:
        if not isinstance(jogada, dict):
            return False, "Jogada inválida.", 0.0
        executor_id = self._normalizar_id(jogada.get("executor_id"))
        if not executor_id:
            return False, "Sem executor.", 0.0
        if self._executor_bloqueado_por_troca(executor_id):
            return False, "Pokémon já preparou troca.", 0.0
        if len(self._jogadas) >= self.MAX_MOVIMENTOS:
            return False, "A jogada já está cheia.", 0.0
        jogadas_executor = self._jogadas_executor(executor_id)
        if len(jogadas_executor) >= self.MAX_MOVIMENTOS_POR_POKEMON:
            return False, "Esse Pokémon já tem 2 movimentos.", 0.0

        nome_acao = self._nome_acao(jogada)
        if any(self._nome_acao(item) == nome_acao for item in jogadas_executor):
            return False, "Esse movimento já foi usado por esse Pokémon.", 0.0

        if bool(jogada.get("tipo_movimento")) and not bool(jogada.get("ataque")):
            if any(bool(item.get("tipo_movimento")) and not bool(item.get("ataque")) for item in jogadas_executor):
                return False, "Movimento já preparado para esse Pokémon.", 0.0

        ataque = jogada.get("ataque")
        if self.ataque_eh_passiva(ataque):
            return False, "Ataque passivo não pode ser preparado manualmente.", 0.0

        custo_base = float(jogada.get("custo_base") or jogada.get("custo") or 0.0)
        custo_total = self._custo_total_para_executor(len(jogadas_executor), custo_base, jogada)
        if energia_disponivel is not None and not bool(ignorar_custo):
            ja_reservado = self.custo_reservado(executor_id)
            if ja_reservado + custo_total > float(energia_disponivel) + 1e-6:
                return False, "Energia insuficiente.", custo_total
        return True, "", custo_total

    def adicionar(self, jogada: Dict[str, object], energia_disponivel: float | None = None, ignorar_custo: bool = False) -> Tuple[Optional[Dict[str, object]], str]:
        permitido, motivo, custo_total = self.pode_adicionar(jogada, energia_disponivel=energia_disponivel, ignorar_custo=ignorar_custo)
        if not permitido:
            return None, motivo

        item = dict(jogada)
        item["id"] = self._proximo_id
        item["executor_id"] = self._normalizar_id(item.get("executor_id"))
        item["acao_chave"] = self._nome_acao(item)
        item["custo_base"] = float(item.get("custo_base") or item.get("custo") or 0.0)
        item["custo"] = float(custo_total)

        self._proximo_id += 1
        self._jogadas.append(item)
        self._selecionado_id = None
        return dict(item), ""

    def calcular_previsao(self, executor_id: object, jogada: Dict[str, object], energia_disponivel: float | None, ignorar_custo: bool = False) -> Tuple[float, bool]:
        teste = dict(jogada)
        teste["executor_id"] = self._normalizar_id(executor_id)
        permitido, _, custo = self.pode_adicionar(teste, energia_disponivel=energia_disponivel, ignorar_custo=ignorar_custo)
        return float(custo), bool(permitido)

    @staticmethod
    def custo_movimento(pokemon, origem: tuple[float, float], destino: tuple[float, float]) -> float:
        try:
            peso = float(getattr(pokemon, "Peso", 0.0) or 0.0)
        except (TypeError, ValueError):
            peso = 0.0
        custo_por_tile = min(30, round(peso / 20.0)) + 5
        dist = math.dist((float(origem[0]), float(origem[1])), (float(destino[0]), float(destino[1])))
        return max(0.0, float(custo_por_tile) * float(dist))

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
            self._recalcular_custos()
            return dict(removido)
        return None

    def _recalcular_custos(self) -> None:
        por_executor: Dict[str, int] = {}
        for item in self._jogadas:
            ex = self._normalizar_id(item.get("executor_id"))
            qnt = por_executor.get(ex, 0)
            item["custo"] = self._custo_total_para_executor(qnt, float(item.get("custo_base") or 0.0), item)
            por_executor[ex] = qnt + 1

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
        _, construtos = self.resolver_visuais(pokemons_por_id)
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

            estilo = str(item.get("estilo") or "").casefold()
            if (
                (item.get("tipo_movimento") and not item.get("troca_reserva_id"))
                or estilo in {"dash", "impulso"}
            ) and isinstance(item.get("destino_mundo"), (tuple, list)) and len(item.get("destino_mundo")) == 2:
                destino = item.get("destino_mundo")
                posicoes[chave] = (float(destino[0]), float(destino[1]))
                construtos[chave] = posicoes[chave]

        return jogadas_visuais, construtos
