"""Representação de Pokémon no mundo com animações locais de captura."""

from __future__ import annotations

import math
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

from Codigo.ModulosGerais.Colisor import Colisor
from Codigo.ModulosGerais.Auxiliares import carregar_frames
from Codigo.ModulosGerais.Sonoridades import tocar
from Codigo.Visual.PokemonMundoAnimator import PokemonMundoAnimator
from Codigo.Visual.PokemonMundoEstado import PokemonMundoEstado

Vector2 = Tuple[float, float]
_PASTA_ANIMACOES = Path("Recursos") / "Visual" / "Pokemons" / "Animação"


class Pokemon:
    _cache_frames: Dict[str, List[pygame.Surface]] = {}
    _cache_frames_escalados: Dict[Tuple[str, int], List[pygame.Surface]] = {}
    _cache_rotacao_bola: Dict[Tuple[int, int], pygame.Surface] = {}
    _carregamento_em_andamento: set[str] = set()
    _INTERVALO_FRAME_ANIM_MS = 85
    _DIAMETRO_BASE_TILES = 0.6
    _INCREMENTO_DIAMETRO_POR_ESCALA = 0.1

    def __init__(self, snapshot: Dict[str, object]) -> None:
        pos = self._pos(snapshot.get("posicao"))
        self.Id = int(snapshot.get("id", 0) or 0)
        self.id_objeto = self.Id
        self.Posicao = (float(pos[0]), float(pos[1]))
        self.Destino: Vector2 = self.Posicao
        self.Colisor = Colisor(x=self.Posicao[0], y=self.Posicao[1], raio_colisao=max(0.2, self._f(snapshot.get("raio_colisao"), 0.45)), raio_interacao=1.2)
        self.Nome = "Pokemon"
        self.Especie = "Pokemon"
        self.Info: Dict[str, object] = {"stats": {}}
        self.FrutasAplicadas: List[Dict[str, object]] = []
        self.EstadoFrutificacao: Dict[str, object] = {"efeitos": {}}
        self.EstaIrritado = False
        self.DificuldadeCaptura = 20.0
        self.TamanhoBarraCaptura = 0.32
        self.VelocidadeBarraCaptura = 90.0
        self._inicio_barra_local_ms = pygame.time.get_ticks()
        self.AlvoLocalCaptura = False
        self._velocidade_interp_tiles_s = 2.5
        self._velocidade_recuperacao_tiles_s = 5.0
        self._recuperacao_restante_s = 0.0

        self.TempoAnimCapturaMs = 320
        self.TempoAnimChecagemMs = 220
        self.TempoIntervaloChecagemMs = 120
        self.TempoAnimFugaMs = 340
        self.TempoAnimVoltaMs = 420
        self.TempoEsperaConfirmacaoMs = 1500
        self.TempoRecuperacaoMovimentoMs = 180

        self.CapturaEstado: Dict[str, object] = {
            "fase": "normal",
            "fase_inicio_ms": 0,
            "bola_posicao": [self.Posicao[0], self.Posicao[1]],
            "retorno_inicio": None,
            "retorno_destino": None,
            "bola_nome": "pokeball",
            "token_arremesso": "",
            "checagens": [],
            "indice_checagem": 0,
            "resultado_final": None,
            "captura_pendente": False,
        }
        self._captura_local_token = ""
        self._captura_local_inicio_ms = 0
        self._captura_servidor_pendente: Optional[Dict[str, object]] = None
        self._captura_servidor_forcar_em_ms = 0
        self._captura_servidor_espera_colisao = False
        self._captura_autoritativa_aplicada = False
        self._ultima_assinatura_captura = ""
        self._ultima_assinatura_som_captura = ""
        self._despawn_pendente = False
        self._pronto_para_remover = False
        self._raio_colisao_padrao = max(0.2, self._f(snapshot.get("raio_colisao"), 0.45))
        self._diametro_tiles_visual = max(1.0, self._raio_colisao_padrao * 2.0)
        self.EstadoVisual = PokemonMundoEstado(self)
        self.Animator = PokemonMundoAnimator(self)
        self.aplicar_snapshot(snapshot)

    @staticmethod
    def _f(v, d=0.0) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return float(d)

    @staticmethod
    def _pos(v) -> Vector2:
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return (float(v[0]), float(v[1]))
        return (0.0, 0.0)

    @staticmethod
    def _diametro_por_escala(escala: object, default: float = 1.4) -> float:
        try:
            e = int(float(escala))
        except (TypeError, ValueError):
            e = 0
        if e < 0:
            return float(default)
        return float(Pokemon._DIAMETRO_BASE_TILES) + (e * float(Pokemon._INCREMENTO_DIAMETRO_POR_ESCALA))

    @classmethod
    def _precarregar_frames_async(cls, especie: str) -> None:
        chave = str(especie or "").strip().lower()
        if not chave:
            return
        if chave in cls._cache_frames or chave in cls._carregamento_em_andamento:
            return
        cls._carregamento_em_andamento.add(chave)

        def _worker() -> None:
            frames = carregar_frames(_PASTA_ANIMACOES / chave)
            cls._cache_frames[chave] = frames
            cls._carregamento_em_andamento.discard(chave)
            cls._cache_frames_escalados = {
                k: v for k, v in cls._cache_frames_escalados.items()
                if str(k[0]).strip().lower() != chave
            }

        thread = threading.Thread(
            target=_worker,
            name=f"PokemonFramesLoader-{chave}",
            daemon=True,
        )
        thread.start()

    @classmethod
    def _carregar_frames_nome(cls, especie: str) -> List[pygame.Surface]:
        chave = str(especie or "").strip().lower()
        if not chave:
            return []
        frames = cls._cache_frames.get(chave)
        if frames is not None:
            return frames
        cls._precarregar_frames_async(chave)
        return []

    @classmethod
    def _obter_frames_escalados(cls, especie: str, tamanho_px: int) -> List[pygame.Surface]:
        tamanho = max(8, int(tamanho_px))
        chave = (str(especie).lower(), tamanho)
        if chave in cls._cache_frames_escalados:
            return cls._cache_frames_escalados[chave]
        frames = cls._carregar_frames_nome(especie)
        escalados = []
        for frame in frames:
            w, h = frame.get_size()
            if w <= 0 or h <= 0:
                continue
            k = tamanho / max(w, h)
            escalados.append(pygame.transform.smoothscale(frame, (max(1, int(w * k)), max(1, int(h * k)))))
        cls._cache_frames_escalados[chave] = escalados
        return escalados

    def definir_alvo_local_captura(self, ativo: bool) -> None:
        self.AlvoLocalCaptura = bool(ativo)

    def calcular_captura_critica_local(self, pos_projetil: Vector2) -> bool:
        dx = float(pos_projetil[0]) - float(self.Posicao[0])
        dy = float(pos_projetil[1]) - float(self.Posicao[1])
        ang_impacto = (math.degrees(math.atan2(-dy, dx)) + 360.0) % 360.0
        inicio, fim, janela = self.EstadoVisual.estado_barra_critica()
        critica = self.EstadoVisual.captura_critica(pos_projetil)
        print(
            "[CAPTURA_CRITICA_CLIENT] "
            f"pokemon_id={self.Id} especie={self.Especie} pos_projetil=({float(pos_projetil[0]):.3f},{float(pos_projetil[1]):.3f}) "
            f"pos_pokemon=({float(self.Posicao[0]):.3f},{float(self.Posicao[1]):.3f}) ang_impacto={ang_impacto:.3f} "
            f"barra_inicio={inicio:.3f} barra_fim={fim:.3f} janela={janela:.3f} velocidade={self.VelocidadeBarraCaptura:.3f} "
            f"tamanho_barra={self.TamanhoBarraCaptura:.3f} critica={critica}"
        )
        return bool(critica)

    def _agora_ms(self) -> int:
        return pygame.time.get_ticks()

    def _fase(self) -> str:
        return str(self.CapturaEstado.get("fase", "normal") or "normal").strip().lower()

    def _fase_ms(self) -> int:
        return int(self.CapturaEstado.get("fase_inicio_ms", 0) or 0)

    def _tempo_fase_ms(self) -> int:
        return max(0, self._agora_ms() - self._fase_ms())

    def _trocar_fase(self, fase: str) -> None:
        self.CapturaEstado["fase"] = str(fase or "normal")
        self.CapturaEstado["fase_inicio_ms"] = self._agora_ms()

    def _normalizar_log_checagens(self, evento: Dict[str, object]) -> List[bool]:
        bruto = None
        for chave in ("checagens", "log_checagens", "tremidas", "log", "plano_tremidas"):
            valor = evento.get(chave)
            if isinstance(valor, list):
                bruto = valor
                break
        if bruto is None and isinstance(evento.get("tentativas_tremida"), list):
            bruto = [item.get("sucesso") for item in list(evento.get("tentativas_tremida") or []) if isinstance(item, dict)]
        resultado: List[bool] = []
        if isinstance(bruto, list):
            for item in bruto[:3]:
                if isinstance(item, dict):
                    v = item.get("capturou", item.get("sucesso", item.get("resultado", item.get("passou"))))
                else:
                    v = item
                resultado.append(bool(v))
        fim = evento.get("resultado_final")
        if fim is None:
            fim = evento.get("capturado", evento.get("sucesso", evento.get("capturou")))
        resultado_final = None if fim is None else bool(fim)
        if resultado_final is True and resultado and len(resultado) < 3:
            resultado.extend([True] * (3 - len(resultado)))
        if resultado_final is True and not resultado:
            resultado = [True, True, True]
        if resultado_final is False and not resultado:
            resultado = [False]
        return resultado[:3]

    def _resultado_final_evento(self, evento: Dict[str, object]) -> Optional[bool]:
        if "resultado" in evento:
            r = str(evento.get("resultado") or "").strip().lower()
            if r in {"sucesso", "capturado", "ok", "true"}:
                return True
            if r in {"falha", "falhou", "escape", "nao", "não", "false"}:
                return False
        for chave in ("resultado_final", "capturado", "sucesso", "capturou"):
            if chave in evento and evento.get(chave) is not None:
                return bool(evento.get(chave))
        return None

    def _assinatura_payload_captura(self, evento: Dict[str, object]) -> str:
        token = str(evento.get("token_arremesso") or "").strip()
        checagens = self._normalizar_log_checagens(evento)
        resultado = self._resultado_final_evento(evento)
        return f"{token}|{resultado}|{','.join('1' if bool(c) else '0' for c in checagens)}"

    def _snapshot_captura_autoritativo(self, captura: Dict[str, object]) -> bool:
        if not isinstance(captura, dict) or not captura:
            return False
        token = str(captura.get("token_arremesso") or "").strip()
        resultado = str(captura.get("resultado") or "").strip().lower()
        checagens = captura.get("checagens")
        pendente = bool(captura.get("captura_pendente", False))
        tem_resultado_bool = any(captura.get(k) is not None for k in ("resultado_final", "capturado", "sucesso", "capturou"))

        if not token and not pendente and resultado in {"", "pendente"} and not checagens and not tem_resultado_bool:
            return False

        return bool(token or pendente or resultado in {"sucesso", "falha", "falhou", "capturado", "escape"} or checagens or tem_resultado_bool)

    def _tocar_resultado_captura(self, resultado_final: Optional[bool], token: str) -> None:
        if resultado_final is None:
            return
        assinatura = f"{token}|{bool(resultado_final)}"
        if assinatura == self._ultima_assinatura_som_captura:
            return
        self._ultima_assinatura_som_captura = assinatura
        tocar("Conseguiu" if bool(resultado_final) else "Falhou")

    def _posicao_bola_mundo(self) -> Vector2:
        pos = self.CapturaEstado.get("bola_posicao")
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            return (float(pos[0]), float(pos[1]))
        return self.Posicao

    def _fixar_bola_na_posicao_atual(self) -> None:
        self.CapturaEstado["bola_posicao"] = [float(self.Posicao[0]), float(self.Posicao[1])]

    def capturar(self, evento_captura: Dict[str, object]) -> None:
        evento = dict(evento_captura or {})
        if not evento:
            return
        token_evento = str(evento.get("token_arremesso") or "").strip()
        resultado = str(evento.get("resultado") or "").strip().lower()
        tem_resultado = (
            resultado in {"sucesso", "falha", "falhou", "capturado", "escape"}
            or any(evento.get(k) is not None for k in ("resultado_final", "capturado", "sucesso", "capturou"))
            or bool(self._normalizar_log_checagens(evento))
        )
        if not token_evento and not tem_resultado and not bool(evento.get("captura_pendente", False)):
            return
        token = token_evento or str(self.CapturaEstado.get("token_arremesso") or self._captura_local_token or "")
        if token:
            self.CapturaEstado["token_arremesso"] = token
        if tem_resultado:
            self._captura_local_inicio_ms = 0
        if "bola_nome" in evento or not self.CapturaEstado.get("bola_nome"):
            self.CapturaEstado["bola_nome"] = str(evento.get("bola_nome") or self.CapturaEstado.get("bola_nome") or "pokeball")
        if isinstance(evento.get("bola_posicao"), (list, tuple)) and len(evento.get("bola_posicao")) == 2:
            self.CapturaEstado["bola_posicao"] = [float(evento["bola_posicao"][0]), float(evento["bola_posicao"][1])]
        if isinstance(evento.get("retorno_inicio"), (list, tuple)) and len(evento.get("retorno_inicio")) == 2:
            self.CapturaEstado["retorno_inicio"] = [float(evento["retorno_inicio"][0]), float(evento["retorno_inicio"][1])]
        if isinstance(evento.get("retorno_destino"), (list, tuple)) and len(evento.get("retorno_destino")) == 2:
            self.CapturaEstado["retorno_destino"] = [float(evento["retorno_destino"][0]), float(evento["retorno_destino"][1])]

        checagens = self._normalizar_log_checagens(evento)
        if checagens:
            self.CapturaEstado["checagens"] = checagens
        resultado_final = self._resultado_final_evento(evento)
        if resultado_final is not None:
            self.CapturaEstado["resultado_final"] = resultado_final
            if not self.CapturaEstado.get("checagens"):
                self.CapturaEstado["checagens"] = [True, True, True] if resultado_final else [False]
        if tem_resultado:
            self.CapturaEstado["captura_pendente"] = False
        elif "captura_pendente" in evento:
            self.CapturaEstado["captura_pendente"] = bool(evento.get("captura_pendente", False))

    def registrar_colisao_projetil_local(self, token: str, nome_bola: str = "pokeball", tempo_espera_confirmacao_ms: int = 1500) -> None:
        token = str(token or "")
        fase = self._fase()
        resultado_definido = self.CapturaEstado.get("resultado_final") is not None
        if self._captura_autoritativa_aplicada:
            return
        if fase in {"captura", "checagem", "fuga", "volta"} and resultado_definido:
            return
        token_atual = str(self.CapturaEstado.get("token_arremesso") or "")
        if token and token_atual and token != token_atual:
            self._captura_autoritativa_aplicada = False
        self._captura_local_token = token
        self._captura_local_inicio_ms = self._agora_ms()
        self.TempoEsperaConfirmacaoMs = max(200, int(tempo_espera_confirmacao_ms or self.TempoEsperaConfirmacaoMs))
        self.CapturaEstado["bola_nome"] = str(nome_bola or self.CapturaEstado.get("bola_nome") or "pokeball")
        self.CapturaEstado["token_arremesso"] = self._captura_local_token
        self.CapturaEstado["captura_pendente"] = True
        self.CapturaEstado["checagens"] = []
        self.CapturaEstado["indice_checagem"] = 0
        self.CapturaEstado["resultado_final"] = None
        self._fixar_bola_na_posicao_atual()
        self._trocar_fase("captura")

    def resultado_servidor_recebido_por_token(self, token: str, esperar_colisao: bool = False, atraso_ms: int = 0) -> None:
        token = str(token or "")
        if not token:
            return
        atual = self._captura_servidor_pendente if isinstance(self._captura_servidor_pendente, dict) else None
        if isinstance(atual, dict) and ("checagens" in atual or "resultado" in atual or "resultado_final" in atual):
            return
        payload = dict(atual or {})
        payload["token_arremesso"] = token
        self._captura_servidor_pendente = payload
        self._captura_servidor_espera_colisao = bool(esperar_colisao)
        base_espera = self.TempoEsperaConfirmacaoMs if bool(esperar_colisao) else 0
        self._captura_servidor_forcar_em_ms = int(self._agora_ms() + base_espera + max(0, int(atraso_ms or 0)))

    def aplicar_resultado_servidor_captura(self, captura_payload: Dict[str, object], esperar_colisao: bool = False) -> None:
        payload = dict(captura_payload or {})
        assinatura = self._assinatura_payload_captura(payload)
        if assinatura and assinatura == self._ultima_assinatura_captura and self._captura_autoritativa_aplicada:
            return
        token = str(payload.get("token_arremesso") or self.CapturaEstado.get("token_arremesso") or "")
        if token:
            payload["token_arremesso"] = token
            token_atual = str(self.CapturaEstado.get("token_arremesso") or "")
            if token_atual and token != token_atual:
                self._captura_autoritativa_aplicada = False
        self._captura_servidor_pendente = payload
        self._captura_servidor_espera_colisao = bool(esperar_colisao)
        self._captura_servidor_forcar_em_ms = int(self._agora_ms() + (self.TempoEsperaConfirmacaoMs if bool(esperar_colisao) else 0))

    def iniciar_animacao_captura_por_impacto_local(self, token: str) -> None:
        self.registrar_colisao_projetil_local(token)

    def _iniciar_fuga(self) -> None:
        if self._fase() == "fuga":
            return
        self.CapturaEstado["captura_pendente"] = False
        self.CapturaEstado["resultado_final"] = False
        self._tocar_resultado_captura(False, str(self.CapturaEstado.get("token_arremesso") or ""))
        self._trocar_fase("fuga")
        self._recuperacao_restante_s = max(self._recuperacao_restante_s, self.TempoRecuperacaoMovimentoMs / 1000.0)

    def _iniciar_volta(self) -> None:
        if self._fase() == "volta":
            return
        self.CapturaEstado["captura_pendente"] = False
        self.CapturaEstado["resultado_final"] = True
        self._tocar_resultado_captura(True, str(self.CapturaEstado.get("token_arremesso") or ""))
        if not isinstance(self.CapturaEstado.get("retorno_inicio"), (list, tuple)):
            bola = self._posicao_bola_mundo()
            self.CapturaEstado["retorno_inicio"] = [float(bola[0]), float(bola[1])]
        self._trocar_fase("volta")

    def _resolver_timeout_resultado_captura(self) -> None:
        if self._captura_local_inicio_ms <= 0:
            return
        if (self._agora_ms() - self._captura_local_inicio_ms) < self.TempoEsperaConfirmacaoMs:
            return
        if self._fase() in {"captura", "checagem"} and self.CapturaEstado.get("resultado_final") is None:
            self._iniciar_fuga()
        self._captura_local_inicio_ms = 0

    def _aplicar_confirmacao_servidor_pendente(self) -> None:
        payload = self._captura_servidor_pendente if isinstance(self._captura_servidor_pendente, dict) else None
        if not payload:
            return
        token = str(payload.get("token_arremesso") or "")
        token_local = str(self.CapturaEstado.get("token_arremesso") or "")
        agora = self._agora_ms()
        if self._fase() != "captura":
            if agora < int(self._captura_servidor_forcar_em_ms):
                return
            if self._captura_servidor_espera_colisao and self._fase() in {"fuga", "volta"}:
                return
            self.CapturaEstado["token_arremesso"] = token or token_local
            self.CapturaEstado["captura_pendente"] = True
            self.CapturaEstado["indice_checagem"] = 0
            self._fixar_bola_na_posicao_atual()
            self._trocar_fase("captura")
        self.capturar(payload)
        if ("resultado" in payload) or ("checagens" in payload) or ("resultado_final" in payload):
            self._captura_autoritativa_aplicada = True
            self._ultima_assinatura_captura = self._assinatura_payload_captura(payload)
        self._captura_servidor_pendente = None
        self._captura_servidor_forcar_em_ms = 0
        self._captura_servidor_espera_colisao = False

    def em_captura_pendente(self) -> bool:
        self._resolver_timeout_resultado_captura()
        fase = self._fase()
        if bool(self.CapturaEstado.get("captura_pendente", False)):
            return True
        return fase in {"captura", "checagem", "fuga", "volta"}

    def deve_adiar_despawn(self) -> bool:
        if isinstance(self._captura_servidor_pendente, dict):
            return True
        fase = self._fase()
        if fase == "volta":
            return True
        if bool(self.CapturaEstado.get("resultado_final") is True) and fase in {"captura", "checagem"}:
            return True
        return False

    def solicitar_despawn_apos_animacao(self) -> None:
        self._despawn_pendente = True

    def pronto_para_remover_local(self) -> bool:
        return bool(self._pronto_para_remover)

    def update(self, snapshot: Dict[str, object]) -> None:
        self.aplicar_snapshot(snapshot)

    def aplicar_snapshot(self, snapshot: Dict[str, object]) -> None:
        estado = snapshot.get("estado") if isinstance(snapshot.get("estado"), dict) else {}
        self.Especie = str(estado.get("especie") or snapshot.get("nome") or self.Especie)
        self._precarregar_frames_async(self.Especie)
        self.Nome = str(estado.get("nome") or snapshot.get("nome") or self.Especie)
        stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}
        stats_norm = {str(k): self._f(v) for k, v in stats.items()}
        self.Info = {"id": int(snapshot.get("id", self.Id)), "nome": self.Nome, "especie": self.Especie, "stats": stats_norm}
        self.DificuldadeCaptura = self._f(estado.get("dificuldade_captura", estado.get("dificuldade")), self._f(stats_norm.get("Poder"), 200.0) / 20.0 + 10.0)
        tamanho_barra = self._f(estado.get("tamanho_barra_captura"), 0.32)
        velocidade_barra = self._f(estado.get("velocidade_barra_captura"), 90.0)
        self.FrutasAplicadas = list(estado.get("frutas_aplicadas") or [])[:2]
        self.EstadoFrutificacao = dict(estado.get("estado_frutificacao") or {"efeitos": {}})
        bonus_barra = self._f(self.EstadoFrutificacao.get("bonus_tamanho_barra_captura_percentual"), 0.0)
        mult_velocidade = self._f(self.EstadoFrutificacao.get("multiplicador_velocidade_barra_captura"), 1.0)
        self.TamanhoBarraCaptura = max(0.06, min(0.45, tamanho_barra * (1.0 + bonus_barra / 100.0)))
        self.VelocidadeBarraCaptura = max(20.0, min(260.0, velocidade_barra * max(0.05, mult_velocidade)))
        self.EstaIrritado = bool(estado.get("esta_irritado", False))
        captura = estado.get("captura") if isinstance(estado.get("captura"), dict) else {}
        if self._snapshot_captura_autoritativo(captura):
            self.capturar(captura)

        diametro_estado = self._f(estado.get("tamanho_tiles"), 0.0)
        if diametro_estado <= 0.0:
            diametro_estado = self._f(snapshot.get("tamanho_tiles"), 0.0)
        if diametro_estado <= 0.0:
            diametro_estado = self._diametro_por_escala(
                estado.get("escala", snapshot.get("escala", estado.get("tamanho", snapshot.get("tamanho")))),
                default=self._diametro_tiles_visual,
            )
        self._diametro_tiles_visual = max(1.0, float(diametro_estado))
        raio_por_tamanho = self._diametro_tiles_visual * 0.5
        raio_snapshot = self._f(snapshot.get("raio_colisao"), -1.0)
        if raio_snapshot > 0.0:
            self._raio_colisao_padrao = max(0.2, raio_snapshot)
        else:
            self._raio_colisao_padrao = max(0.2, raio_por_tamanho)

        fase_local = self._fase()
        if fase_local in {"captura", "checagem", "fuga", "volta"} or bool(self.CapturaEstado.get("resultado_final") is True):
            self.Colisor.raio_colisao = 0.0
            self.Colisor.raio_interacao = 0.0
            return

        self.Colisor.raio_colisao = self._raio_colisao_padrao
        self.Colisor.raio_interacao = max(self.Colisor.raio_colisao, 1.2)

        destino = self._pos(snapshot.get("posicao"))
        if self._fase() in {"captura", "checagem"} and self.CapturaEstado.get("resultado_final") is None:
            dist_mov = math.hypot(float(destino[0]) - float(self.Posicao[0]), float(destino[1]) - float(self.Posicao[1]))
            if dist_mov > 0.12:
                self._captura_local_inicio_ms = min(self._captura_local_inicio_ms, self._agora_ms() - max(50, int(self.TempoEsperaConfirmacaoMs * 0.8)))
        self.Destino = destino
        if str(snapshot.get("movimento") or "").strip().lower() == "teleportar":
            self.definir_posicao(*destino)

    def definir_posicao(self, x: float, y: float) -> None:
        self.Posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.Posicao)

    def mover(self, dt: float) -> None:
        self.atualizar(dt)





    def atualizar(self, dt: float) -> None:
        dt = max(0.0, float(dt))
        self.EstadoVisual.atualizar(dt)
        self._resolver_timeout_resultado_captura()
        self._aplicar_confirmacao_servidor_pendente()
        fase = self._fase()
        if fase not in {"captura", "checagem", "fuga", "volta"}:
            px, py = self.Posicao
            dx, dy = self.Destino
            dist = math.hypot(dx - px, dy - py)
            if dist > 1e-4:
                vel = self._velocidade_interp_tiles_s
                if self._recuperacao_restante_s > 0.0:
                    vel = max(vel, self._velocidade_recuperacao_tiles_s)
                    self._recuperacao_restante_s = max(0.0, self._recuperacao_restante_s - dt)
                passo = min(dist, vel * dt)
                k = (passo / dist) if dist > 0 else 0.0
                self.definir_posicao(px + (dx - px) * k, py + (dy - py) * k)
        else:
            self._fixar_bola_na_posicao_atual()

        if fase == "captura":
            if self._tempo_fase_ms() >= self.TempoAnimCapturaMs and self.CapturaEstado.get("resultado_final") is not None:
                checagens = list(self.CapturaEstado.get("checagens") or [])
                if not checagens:
                    if self.CapturaEstado.get("resultado_final") is True:
                        checagens = [True, True, True]
                    else:
                        checagens = [False]
                    self.CapturaEstado["checagens"] = checagens
                self.CapturaEstado["indice_checagem"] = 0
                self._trocar_fase("checagem")
        elif fase == "checagem":
            total_ms = self.TempoAnimChecagemMs + self.TempoIntervaloChecagemMs
            checagens = list(self.CapturaEstado.get("checagens") or [])
            indice = max(0, int(self.CapturaEstado.get("indice_checagem", 0) or 0))
            if total_ms > 0 and self._tempo_fase_ms() >= total_ms:
                if indice < len(checagens) and not bool(checagens[indice]):
                    self._iniciar_fuga()
                elif indice + 1 < len(checagens):
                    self.CapturaEstado["indice_checagem"] = indice + 1
                    self._trocar_fase("checagem")
                elif self.CapturaEstado.get("resultado_final") is True:
                    self._iniciar_volta()
                else:
                    self._iniciar_fuga()
        elif fase == "fuga":
            if self._tempo_fase_ms() >= self.TempoAnimFugaMs:
                self.CapturaEstado["checagens"] = []
                self.CapturaEstado["indice_checagem"] = 0
                self.CapturaEstado["resultado_final"] = None
                self.CapturaEstado["captura_pendente"] = False
                self._trocar_fase("normal")
        elif fase == "volta":
            if self._tempo_fase_ms() >= self.TempoAnimVoltaMs:
                self.CapturaEstado["captura_pendente"] = False
                if self._despawn_pendente:
                    self._pronto_para_remover = True
                else:
                    self._trocar_fase("normal")

    def atualizar_visual(self, dt: float) -> None:
        self.Animator.atualizar_visual(dt)

    def render(self, tela, camera, dt: float = 0.0) -> None:
        self.Animator.render(tela, camera, dt)


Pokemon.desenhar = Pokemon.render
PokemonMundo = Pokemon
