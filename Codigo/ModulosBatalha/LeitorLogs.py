from __future__ import annotations

from typing import Callable, Dict, List

class LeitorLogs:
    _FASES = ("inicializacao", "segmentacao", "passiva", "finalizacao")

    def __init__(self, controlador) -> None:
        self._controlador = controlador
        self.cancelar()

    @staticmethod
    def _numero(valor, default: float = 0.0) -> float:
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _posicao(valor) -> tuple[float, float] | None:
        if isinstance(valor, (list, tuple)) and len(valor) == 2:
            try:
                return (float(valor[0]), float(valor[1]))
            except (TypeError, ValueError):
                return None
        return None

    def cancelar(self) -> None:
        self._ativo = False
        self._historico: List[Dict[str, object]] = []
        self._log_atual: Dict[str, object] = {}
        self._resultado: Dict[str, object] = {}
        self._indice_bloco = 0
        self._tempo_decorrido = 0.0
        self._tick_final = 0
        self._tick_atual = 0
        self._turno_atual = 0
        self._eventos_processados = 0
        self._total_eventos = 0
        self._tick_segundos = 0.2
        self._ao_finalizar: Callable[[Dict[str, object]], None] | None = None

    def esta_ativo(self) -> bool:
        return bool(self._ativo)

    @classmethod
    def _contar_eventos_historico(cls, historico: List[Dict[str, object]]) -> int:
        total = 0
        for bloco in list(historico or []):
            if not isinstance(bloco, dict):
                continue
            for fase in cls._FASES:
                total += len([item for item in list(bloco.get(fase) or []) if isinstance(item, dict)])
        return int(total)

    def estado_visualizacao(self) -> Dict[str, object]:
        return {
            "ativo": bool(self._ativo),
            "turno_atual": int(self._turno_atual or 0),
            "tick_atual": int(self._tick_atual or 0),
            "tick_final": int(self._tick_final or 0),
            "eventos_processados": int(self._eventos_processados or 0),
            "eventos_totais": int(self._total_eventos or 0),
            "tick_segundos": float(self._tick_segundos or 0.2),
            "log": dict(self._log_atual or {}),
        }

    def reproduzir(
        self,
        log: Dict[str, object] | None,
        *,
        resultado: Dict[str, object] | None = None,
        ao_finalizar: Callable[[Dict[str, object]], None] | None = None,
    ) -> bool:
        historico = [dict(item) for item in list((log or {}).get("historico") or []) if isinstance(item, dict)]
        self.cancelar()
        self._log_atual = dict(log or {})
        self._resultado = dict(resultado or {})
        self._ao_finalizar = ao_finalizar
        self._turno_atual = max(1, int((log or {}).get("turno_atual", getattr(self._controlador, "_rodada_atual", 1)) or getattr(self._controlador, "_rodada_atual", 1)))
        regras_batalha = dict((log or {}).get("regras_batalha") or {}) if isinstance((log or {}).get("regras_batalha"), dict) else {}
        if not regras_batalha and hasattr(self._controlador, "obter_regras_batalha"):
            regras_batalha = dict(self._controlador.obter_regras_batalha() or {})
        self._tick_segundos = max(0.01, self._numero(regras_batalha.get("tick_segundos"), 0.2))
        snapshot_inicial = (log or {}).get("snapshot_inicial") if isinstance((log or {}).get("snapshot_inicial"), dict) else {}
        if snapshot_inicial and hasattr(self._controlador, "aplicar_snapshot_replay"):
            self._controlador.aplicar_snapshot_replay(snapshot_inicial)
        self._historico = historico
        self._total_eventos = self._contar_eventos_historico(historico)
        self._tick_final = max([int(item.get("tick", 0) or 0) for item in historico], default=0)
        if not historico:
            self._finalizar()
            return False
        self._ativo = True
        self._processar_blocos_ate_tick(0)
        return True

    def atualizar(self, dt: float) -> None:
        if not self._ativo:
            return
        self._tempo_decorrido += max(0.0, float(dt))
        tick_atual = int(self._tempo_decorrido / self._tick_segundos)
        self._processar_blocos_ate_tick(tick_atual)
        if self._indice_bloco >= len(self._historico) and self._tempo_decorrido >= (self._tick_final + 1) * self._tick_segundos:
            self._finalizar()

    def _finalizar(self) -> None:
        callback = self._ao_finalizar
        resultado = dict(self._resultado)
        self.cancelar()
        if callable(callback):
            callback(resultado)

    def _processar_blocos_ate_tick(self, tick_atual: int) -> None:
        self._tick_atual = max(0, int(tick_atual))
        while self._indice_bloco < len(self._historico):
            bloco = self._historico[self._indice_bloco]
            if int(bloco.get("tick", 0) or 0) > int(tick_atual):
                break
            self._processar_bloco(bloco)
            self._indice_bloco += 1

    def _processar_bloco(self, bloco: Dict[str, object]) -> None:
        self._tick_atual = max(self._tick_atual, int(bloco.get("tick", 0) or 0))
        for fase in self._FASES:
            for evento in [dict(item) for item in list(bloco.get(fase) or []) if isinstance(item, dict)]:
                self._processar_evento(evento)
                self._eventos_processados += 1

    def _mapa_pokemons(self) -> Dict[str, object]:
        return self._controlador.mapa_pokemons()

    def _pokemon(self, uid: object):
        return self._mapa_pokemons().get(str(uid or ""))

    def _animador(self, pokemon):
        return getattr(pokemon, "Animador", None) if pokemon is not None else None

    def _velocidade_tiles_segundo(self, valor_tick: object) -> float:
        return max(0.01, self._numero(valor_tick, 0.0) / max(0.01, self._tick_segundos))

    def _sincronizar_movimento(self, pokemon, origem, destino, velocidade_tick) -> None:
        if pokemon is None:
            return
        origem_pos = self._posicao(origem)
        destino_pos = self._posicao(destino)
        if origem_pos is not None:
            pokemon.PosicaoAnterior = origem_pos
            pokemon.Posicao = origem_pos
        if destino_pos is None:
            return
        animador = self._animador(pokemon)
        if animador is not None:
            animador.mover(destino_pos, self._velocidade_tiles_segundo(velocidade_tick))
        else:
            pokemon.Posicao = destino_pos

    def _ajustar_vida(self, pokemon, antes: object, depois: object, delta: object | None = None) -> None:
        if pokemon is None:
            return
        if antes not in (None, ""):
            pokemon.VidaAtual = max(0.0, min(float(pokemon.VidaMax), self._numero(antes, pokemon.VidaAtual)))
        if depois not in (None, ""):
            pokemon.VidaAtual = max(0.0, min(float(pokemon.VidaMax), self._numero(depois, pokemon.VidaAtual)))
        elif delta not in (None, ""):
            pokemon.VidaAtual = max(0.0, min(float(pokemon.VidaMax), pokemon.VidaAtual + self._numero(delta, 0.0)))

    def _ajustar_barreira(self, pokemon, antes: object, depois: object) -> None:
        if pokemon is None:
            return
        if antes not in (None, ""):
            pokemon.Barreira = max(0.0, self._numero(antes, pokemon.Barreira))
        if depois not in (None, ""):
            pokemon.Barreira = max(0.0, self._numero(depois, pokemon.Barreira))

    def _registrar_efeito(self, pokemon, nome: str, positivo: bool) -> None:
        if pokemon is None or not nome:
            return
        pokemon.Efeitos = [dict(item) for item in list(getattr(pokemon, "Efeitos", []) or []) if isinstance(item, dict)]
        pokemon.Efeitos.append({"nome": str(nome), "positivo": bool(positivo)})

    def _remover_efeito(self, pokemon, nome: str) -> None:
        if pokemon is None or not nome:
            return
        alvo = str(nome).strip().casefold()
        pokemon.Efeitos = [
            dict(item)
            for item in list(getattr(pokemon, "Efeitos", []) or [])
            if isinstance(item, dict) and str(item.get("nome") or "").strip().casefold() != alvo
        ]

    def _processar_evento(self, evento: Dict[str, object]) -> None:
        tipo = str(evento.get("tipo") or "").strip().casefold()
        if tipo == "acao":
            self._processar_acao(evento)
        elif tipo == "movimento":
            self._processar_movimento(evento)
        elif tipo == "dano":
            self._processar_dano(evento)
        elif tipo == "cura":
            self._processar_cura(evento)
        elif tipo == "barreira":
            self._processar_barreira(evento)
        elif tipo == "energia":
            self._processar_energia(evento)
        elif tipo == "efeito":
            self._processar_efeito(evento)
        elif tipo == "objeto":
            self._processar_objeto(evento)
        elif tipo == "fim_turno":
            self._processar_fim_turno(evento)

    def _processar_acao(self, evento: Dict[str, object]) -> None:
        executor = self._pokemon(evento.get("executor_id"))
        if executor is None:
            return
        if "energia_restante" in evento:
            executor.Energia = max(0.0, min(float(executor.EnergiaMax), self._numero(evento.get("energia_restante"), executor.Energia)))
        ataque = str(evento.get("ataque") or "").strip()
        animador = self._animador(executor)
        if animador is not None and ataque and str(evento.get("estilo") or "").strip().casefold() != "movimento":
            animador.sofrer_ataque_efeito(ataque, escala=1.35, loops=1)

    def _processar_movimento(self, evento: Dict[str, object]) -> None:
        pokemon = self._pokemon(evento.get("pokemon_id"))
        self._sincronizar_movimento(pokemon, evento.get("origem"), evento.get("posicao"), evento.get("velocidade"))

    def _processar_dano(self, evento: Dict[str, object]) -> None:
        alvo = self._pokemon(evento.get("alvo_id"))
        if alvo is None:
            return
        self._ajustar_barreira(alvo, evento.get("barreira_antes"), evento.get("barreira_depois"))
        self._ajustar_vida(alvo, evento.get("vida_antes"), evento.get("vida_depois"))
        animador = self._animador(alvo)
        if animador is not None:
            animador.tomar_dano(self._numero(evento.get("dano"), 0.0), bool(evento.get("critico", False)))
            if bool(evento.get("morto", False)):
                animador.animar_morte()

    def _processar_cura(self, evento: Dict[str, object]) -> None:
        alvo = self._pokemon(evento.get("alvo_id"))
        if alvo is None:
            return
        self._ajustar_vida(alvo, evento.get("vida_antes"), evento.get("vida_depois"), evento.get("valor"))
        animador = self._animador(alvo)
        if animador is not None:
            animador.tomar_cura(self._numero(evento.get("valor"), 0.0))

    def _processar_barreira(self, evento: Dict[str, object]) -> None:
        alvo = self._pokemon(evento.get("alvo_id"))
        if alvo is None:
            return
        alvo.Barreira = max(0.0, self._numero(evento.get("barreira_total"), alvo.Barreira))

    def _processar_energia(self, evento: Dict[str, object]) -> None:
        pokemon = self._pokemon(evento.get("pokemon_id"))
        if pokemon is None:
            return
        pokemon.Energia = max(0.0, min(float(pokemon.EnergiaMax), self._numero(evento.get("energia"), pokemon.Energia)))

    def _processar_efeito(self, evento: Dict[str, object]) -> None:
        alvo = self._pokemon(evento.get("alvo_id"))
        if alvo is None:
            return
        nome = str(evento.get("efeito") or "").strip()
        positivo = bool(evento.get("positivo", False))
        fase_efeito = str(evento.get("fase_efeito") or "aplicado").strip().casefold()
        if fase_efeito == "expirado":
            self._remover_efeito(alvo, nome)
            return
        if str(evento.get("status") or "ok").strip().casefold() != "ok":
            return
        self._registrar_efeito(alvo, nome, positivo)
        animador = self._animador(alvo)
        if animador is not None:
            if positivo:
                animador.buffar()
            else:
                animador.nerfar()

    def _processar_objeto(self, evento: Dict[str, object]) -> None:
        fase_objeto = str(evento.get("fase_objeto") or "").strip().casefold()
        if fase_objeto != "criado":
            return
        executor = self._pokemon(evento.get("executor_id"))
        animador = self._animador(executor)
        if animador is None:
            return

        subtipo = str(evento.get("subtipo") or "").strip().casefold()
        origem = self._posicao(evento.get("origem_execucao")) or self._posicao(evento.get("origem")) or self._posicao(evento.get("posicao"))
        destino = self._posicao(evento.get("destino")) or self._posicao(evento.get("posicao")) or origem
        if origem is None or destino is None:
            return

        duracao_s = max(self._tick_segundos, int(evento.get("duracao_ticks", 1) or 1) * self._tick_segundos)
        if subtipo == "tiro":
            animador.lancar_projetil(
                origem,
                destino,
                self._velocidade_tiles_segundo(evento.get("velocidade")),
                raio_tiles=max(0.08, self._numero(evento.get("raio_max"), 0.22)),
            )
            return
        if subtipo == "area":
            animador.aplicar_fluxo(
                origem,
                destino,
                alcance_tiles=max(self._numero(evento.get("alcance"), 0.0), self._numero(evento.get("alcance_max"), 0.0)),
                largura_graus=max(5.0, self._numero(evento.get("largura"), 50.0)),
                duracao_s=duracao_s,
                modo='area',
            )
            return
        if subtipo == "zona":
            animador.aplicar_fluxo(
                origem,
                destino,
                raio_tiles=max(self._numero(evento.get("raio"), 0.0), self._numero(evento.get("raio_max"), 0.0)),
                duracao_s=duracao_s,
                modo='zona',
            )

    def _processar_fim_turno(self, evento: Dict[str, object]) -> None:
        pokemon = self._pokemon(evento.get("pokemon_id"))
        if pokemon is None:
            return
        if "energia_total" in evento:
            pokemon.Energia = max(0.0, min(float(pokemon.EnergiaMax), self._numero(evento.get("energia_total"), pokemon.Energia)))
        elif "energia" in evento:
            pokemon.Energia = max(0.0, min(float(pokemon.EnergiaMax), pokemon.Energia + self._numero(evento.get("energia"), 0.0)))

        if "dano" in evento:
            self._ajustar_vida(pokemon, evento.get("vida_antes"), evento.get("vida_depois"))
            animador = self._animador(pokemon)
            if animador is not None:
                animador.tomar_dano(self._numero(evento.get("dano"), 0.0), False)
        elif "cura" in evento:
            self._ajustar_vida(pokemon, evento.get("vida_antes"), evento.get("vida_depois"))
            animador = self._animador(pokemon)
            if animador is not None:
                animador.tomar_cura(self._numero(evento.get("cura"), 0.0))
