from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Mapping

from .AvaliadorIA import AvaliadorIA
from .ConfigIA import ConfigIA
from .ContextoIA import ContextoIA
from .FallbackIA import FallbackIA
from .GeradorAcoesIA import GeradorAcoesIA
from .HackerIA import HackerIA
from .MacroSimulador import MacroSimulador
from .MemoriaIA import MemoriaIA
from .MetadadosIA import MetadadosIA
from .MicroSimulador import MicroSimulador
from .PlanejadorIA import PlanejadorIA
from SimuladorServerJogo.Batalha.PropriedadesAtaques import carregar_propriedades_ataques


class ControladorIA:
    """Entrada server-side da nova IA de batalha."""

    def __init__(
        self,
        seed_base=None,
        config: Mapping[str, Any] | ConfigIA | None = None,
        *,
        permitir_overrides: bool = False,
    ):
        self.seed_base = seed_base
        self.permitir_overrides = bool(permitir_overrides)
        self.propriedades_ataques = self._carregar_propriedades_ataques()
        self.metadados = MetadadosIA()
        self.config_padrao = config if isinstance(config, ConfigIA) else ConfigIA.padrao()

        self.memoria = MemoriaIA()
        self.gerador = GeradorAcoesIA(self.propriedades_ataques)
        self.avaliador = AvaliadorIA()
        self.micro = MicroSimulador()
        self.macro = MacroSimulador()
        self.planejador = PlanejadorIA(self.gerador, self.avaliador, self.micro, self.macro)
        self.hacker = HackerIA(self.gerador, self.avaliador, self.macro)
        self.fallback = FallbackIA(self.propriedades_ataques)

    def gerar_jogada(self, partida, lado_id, config_ia: Mapping[str, Any] | ConfigIA | None = None):
        jogada_base = self.gerar_jogada_base(partida, lado_id, config_ia=config_ia)
        return self.finalizar_jogada_com_hacker(partida, lado_id, jogada_base, config_ia=config_ia)

    def gerar_jogada_base(self, partida, lado_id, config_ia: Mapping[str, Any] | ConfigIA | None = None):
        lado_id = int(lado_id or 0)
        rodada = int(getattr(partida, "rodada_atual", 1) or 1)
        rng = random.Random(self._seed_rodada(partida, rodada, lado_id))
        config = self._resolver_config(config_ia)
        usou_fallback = False
        erro = None

        try:
            contexto = ContextoIA(
                partida=partida,
                lado_id=lado_id,
                config=config,
                rng=rng,
                propriedades_ataques=self.propriedades_ataques,
                metadados_ia=self.metadados,
                usar_leitura_player=False,
            )
            contexto.memoria_ia = self.memoria.obter(contexto)
            acoes = self.planejador.planejar(contexto)

            if not acoes:
                usou_fallback = True
                acoes = self.fallback.gerar(partida, lado_id, rodada, rng, motivo="sem_acoes_planejador")
        except Exception as exc:
            erro = str(exc)
            usou_fallback = True
            self._registrar_aviso(partida, {"motivo": "ia_fallback_exception", "erro": erro, "lado_id": lado_id})
            acoes = self.fallback.gerar(partida, lado_id, rodada, rng, motivo="exception")

        return self._montar_jogada(partida, lado_id, rodada, config, acoes, usou_fallback=usou_fallback, usou_hacker=False, erro=erro)

    def finalizar_jogada_com_hacker(self, partida, lado_id, jogada_base, config_ia: Mapping[str, Any] | ConfigIA | None = None):
        lado_id = int(lado_id or 0)
        rodada = int(getattr(partida, "rodada_atual", 1) or 1)
        rng = random.Random(self._seed_rodada(partida, rodada, lado_id))
        config = self._resolver_config(config_ia)
        jogada = dict(jogada_base or {})
        acoes = list(jogada.get("acoes") or [])
        usou_hacker = False

        try:
            contexto = ContextoIA(
                partida=partida,
                lado_id=lado_id,
                config=config,
                rng=rng,
                propriedades_ataques=self.propriedades_ataques,
                metadados_ia=self.metadados,
                usar_leitura_player=True,
            )
            contexto.memoria_ia = self.memoria.obter(contexto)
            if config.hacker.intuicao > 0.0:
                novas_acoes = self.hacker.refinar(contexto, acoes)
                usou_hacker = novas_acoes != acoes
                acoes = novas_acoes
            try:
                self.memoria.registrar_jogadas_player(contexto, contexto.acoes_player_recebidas())
            except Exception:
                pass
        except Exception as exc:
            self._registrar_aviso(partida, {"motivo": "ia_hacker_exception", "erro": str(exc), "lado_id": lado_id})

        meta = dict(jogada.get("meta_ia") or {})
        meta["usou_hacker"] = bool(usou_hacker)
        jogada.update(self._montar_jogada(partida, lado_id, rodada, config, acoes, usou_fallback=bool(meta.get("usou_fallback")), usou_hacker=usou_hacker, erro=meta.get("erro")))
        jogada["meta_ia"] = {**jogada["meta_ia"], **meta}
        return jogada

    def gerar_jogada_fallback(self, partida, lado_id, motivo: str = "fallback_ia"):
        lado_id = int(lado_id or 0)
        rodada = int(getattr(partida, "rodada_atual", 1) or 1)
        rng = random.Random(self._seed_rodada(partida, rodada, lado_id))
        config = self._resolver_config(None)
        acoes = self.fallback.gerar(partida, lado_id, rodada, rng, motivo=motivo)
        return self._montar_jogada(partida, lado_id, rodada, config, acoes, usou_fallback=True, usou_hacker=False, erro=None)

    def _montar_jogada(self, partida, lado_id, rodada, config: ConfigIA, acoes, *, usou_fallback: bool, usou_hacker: bool, erro):
        return {
            "id_partida": str(getattr(partida, "id_partida", "") or ""),
            "rodada": int(rodada or 1),
            "modo_teste": False,
            "lado_id": int(lado_id or 0),
            "acoes": list(acoes or [])[: int(config.max_acoes_por_lado or 5)],
            "meta_ia": {
                "arquitetura": "IA",
                "defaults_fixos": not self.permitir_overrides,
                "usou_fallback": bool(usou_fallback),
                "usou_hacker": bool(usou_hacker),
                "erro": erro,
                "criterios_dificuldade": config.dificuldade.as_dict(),
                "criterios_hacker": config.hacker.as_dict(),
                "criterios_personalidade": config.personalidade.as_dict(),
            },
        }

    def _resolver_config(self, config_ia: Mapping[str, Any] | ConfigIA | None) -> ConfigIA:
        if isinstance(config_ia, ConfigIA) and self.permitir_overrides:
            return config_ia
        if isinstance(config_ia, Mapping) and self.permitir_overrides:
            return self.config_padrao.mesclar(config_ia, permitir_override=True)
        return self.config_padrao

    def _carregar_propriedades_ataques(self):
        base = Path(__file__).resolve().parents[3]
        return carregar_propriedades_ataques(base)

    def _seed_rodada(self, partida, rodada, lado_id):
        seed = self.seed_base if self.seed_base is not None else getattr(partida, "seed_partida", 0)
        return f"{seed}:{rodada}:{lado_id}:ia_nova"

    @staticmethod
    def _registrar_aviso(partida, aviso: dict) -> None:
        try:
            getattr(partida, "avisos", []).append(dict(aviso))
        except Exception:
            pass
