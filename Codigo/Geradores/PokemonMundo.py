"""Representação de Pokémon no mundo com animações locais de captura."""

from __future__ import annotations

import math
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

from Codigo.Modulos.Colisor import Colisor
from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Modulos.Auxiliares import carregar_frames

Vector2 = Tuple[float, float]
_PASTA_ANIMACOES = Path("Recursos") / "Visual" / "Pokemons" / "Animação"


class Pokemon:
    _cache_frames: Dict[str, List[pygame.Surface]] = {}
    _cache_frames_escalados: Dict[Tuple[str, int], List[pygame.Surface]] = {}
    _cache_rotacao_bola: Dict[Tuple[int, int], pygame.Surface] = {}
    _carregamento_em_andamento: set[str] = set()
    _INTERVALO_FRAME_ANIM_MS = 85

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
        self.TempoEsperaForcarCapturaServidorMs = 700
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
        self._captura_fake_token = ""
        self._captura_fake_inicio_ms = 0
        self._captura_servidor_pendente: Optional[Dict[str, object]] = None
        self._captura_servidor_forcar_em_ms = 0
        self._captura_autoritativa_aplicada = False
        self._despawn_pendente = False
        self._pronto_para_remover = False
        self._raio_colisao_padrao = max(0.2, self._f(snapshot.get("raio_colisao"), 0.45))
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
        novo = bool(ativo)
        if novo and not self.AlvoLocalCaptura:
            self._inicio_barra_local_ms = pygame.time.get_ticks()
        self.AlvoLocalCaptura = novo

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
            if chave in evento:
                return bool(evento.get(chave))
        return None

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
        token = str(evento.get("token_arremesso") or self.CapturaEstado.get("token_arremesso") or self._captura_fake_token or "")
        if token:
            self.CapturaEstado["token_arremesso"] = token
            self._captura_fake_inicio_ms = 0
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
        self.CapturaEstado["captura_pendente"] = False

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
        self._captura_fake_token = token
        self._captura_fake_inicio_ms = self._agora_ms()
        self.TempoEsperaConfirmacaoMs = max(200, int(tempo_espera_confirmacao_ms or self.TempoEsperaConfirmacaoMs))
        self.CapturaEstado["bola_nome"] = str(nome_bola or self.CapturaEstado.get("bola_nome") or "pokeball")
        self.CapturaEstado["token_arremesso"] = self._captura_fake_token
        self.CapturaEstado["captura_pendente"] = True
        self.CapturaEstado["checagens"] = []
        self.CapturaEstado["indice_checagem"] = 0
        self.CapturaEstado["resultado_final"] = None
        self._fixar_bola_na_posicao_atual()
        self._trocar_fase("captura")

    def confirmar_captura_por_token(self, token: str, esperar_colisao: bool = False, atraso_ms: int = 0) -> None:
        token = str(token or "")
        if not token:
            return
        atual = self._captura_servidor_pendente if isinstance(self._captura_servidor_pendente, dict) else None
        if isinstance(atual, dict) and ("checagens" in atual or "resultado" in atual or "resultado_final" in atual):
            return
        payload = dict(atual or {})
        payload["token_arremesso"] = token
        self._captura_servidor_pendente = payload
        base_espera = self.TempoEsperaForcarCapturaServidorMs if bool(esperar_colisao) else 0
        self._captura_servidor_forcar_em_ms = int(self._agora_ms() + base_espera + max(0, int(atraso_ms or 0)))

    def aplicar_resultado_servidor_captura(self, captura_payload: Dict[str, object], esperar_colisao: bool = False) -> None:
        payload = dict(captura_payload or {})
        token = str(payload.get("token_arremesso") or self.CapturaEstado.get("token_arremesso") or "")
        if token:
            payload["token_arremesso"] = token
            token_atual = str(self.CapturaEstado.get("token_arremesso") or "")
            if token_atual and token != token_atual:
                self._captura_autoritativa_aplicada = False
        self._captura_servidor_pendente = payload
        self._captura_servidor_forcar_em_ms = int(self._agora_ms() + (self.TempoEsperaForcarCapturaServidorMs if bool(esperar_colisao) else 0))

    def iniciar_captura_fake(self, token: str) -> None:
        self.registrar_colisao_projetil_local(token)

    def _iniciar_fuga(self) -> None:
        if self._fase() == "fuga":
            return
        self.CapturaEstado["captura_pendente"] = False
        self.CapturaEstado["resultado_final"] = False
        self._trocar_fase("fuga")
        self._recuperacao_restante_s = max(self._recuperacao_restante_s, self.TempoRecuperacaoMovimentoMs / 1000.0)

    def _iniciar_volta(self) -> None:
        if self._fase() == "volta":
            return
        self.CapturaEstado["captura_pendente"] = False
        self.CapturaEstado["resultado_final"] = True
        if not isinstance(self.CapturaEstado.get("retorno_inicio"), (list, tuple)):
            bola = self._posicao_bola_mundo()
            self.CapturaEstado["retorno_inicio"] = [float(bola[0]), float(bola[1])]
        self._trocar_fase("volta")

    def _resolver_timeout_captura_fake(self) -> None:
        if self._captura_fake_inicio_ms <= 0:
            return
        if (self._agora_ms() - self._captura_fake_inicio_ms) < self.TempoEsperaConfirmacaoMs:
            return
        if self._fase() in {"captura", "checagem"} and self.CapturaEstado.get("resultado_final") is None:
            self._iniciar_fuga()
        self._captura_fake_inicio_ms = 0

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
            self.CapturaEstado["token_arremesso"] = token or token_local
            self.CapturaEstado["captura_pendente"] = True
            self.CapturaEstado["indice_checagem"] = 0
            self._fixar_bola_na_posicao_atual()
            self._trocar_fase("captura")
        self.capturar(payload)
        if ("resultado" in payload) or ("checagens" in payload) or ("resultado_final" in payload):
            self._captura_autoritativa_aplicada = True
        self._captura_servidor_pendente = None
        self._captura_servidor_forcar_em_ms = 0

    def em_captura_pendente(self) -> bool:
        self._resolver_timeout_captura_fake()
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
        self.TamanhoBarraCaptura = max(0.06, min(0.45, self._f(estado.get("tamanho_barra_captura"), 0.32)))
        self.VelocidadeBarraCaptura = max(20.0, min(260.0, self._f(estado.get("velocidade_barra_captura"), 90.0)))
        self.FrutasAplicadas = list(estado.get("frutas_aplicadas") or [])[:2]
        self.EstadoFrutificacao = dict(estado.get("estado_frutificacao") or {"efeitos": {}})
        captura = estado.get("captura") if isinstance(estado.get("captura"), dict) else {}
        fase_local = self._fase()
        token_local = str(self.CapturaEstado.get("token_arremesso") or "")
        token_captura = str(captura.get("token_arremesso") or "") if captura else ""
        if captura:
            if fase_local == "normal":
                self.aplicar_resultado_servidor_captura(captura, esperar_colisao=True)
            else:
                mesmo_token = bool(token_local and token_captura and token_local == token_captura)
                if not (fase_local == "volta" and bool(self.CapturaEstado.get("resultado_final") is True) and mesmo_token):
                    if mesmo_token:
                        if (not self.CapturaEstado.get("bola_nome")) and str(captura.get("bola_nome") or ""):
                            self.CapturaEstado["bola_nome"] = str(captura.get("bola_nome") or "")
                        if (self.CapturaEstado.get("retorno_inicio") is None) and isinstance(captura.get("retorno_inicio"), (list, tuple)) and len(captura.get("retorno_inicio")) == 2:
                            self.CapturaEstado["retorno_inicio"] = [float(captura["retorno_inicio"][0]), float(captura["retorno_inicio"][1])]
                        if (self.CapturaEstado.get("retorno_destino") is None) and isinstance(captura.get("retorno_destino"), (list, tuple)) and len(captura.get("retorno_destino")) == 2:
                            self.CapturaEstado["retorno_destino"] = [float(captura["retorno_destino"][0]), float(captura["retorno_destino"][1])]

        self._raio_colisao_padrao = max(0.2, self._f(snapshot.get("raio_colisao"), self._raio_colisao_padrao))
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
                self._captura_fake_inicio_ms = min(self._captura_fake_inicio_ms, self._agora_ms() - max(50, int(self.TempoEsperaConfirmacaoMs * 0.8)))
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
        self._resolver_timeout_captura_fake()
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
                self._trocar_fase("normal")
                if self._despawn_pendente:
                    self._pronto_para_remover = True

    def _desenhar_barra_local(self, tela, centro, raio):
        decorrido_s = max(0.0, (pygame.time.get_ticks() - int(self._inicio_barra_local_ms)) / 1000.0)
        ang = (decorrido_s * self.VelocidadeBarraCaptura) % 360.0
        jan = max(8.0, min(120.0, self.TamanhoBarraCaptura * 360.0))
        rect = pygame.Rect(0, 0, raio * 2, raio * 2)
        rect.center = centro
        ini = math.radians(-ang)
        fim = math.radians(-(ang + jan))
        pygame.draw.arc(tela, (255, 210, 76), rect, fim, ini, 4)

    def _desenhar_pokemon_normal(self, tela, centro, raio_corpo, escala_extra: float = 1.0, alpha: int = 255):
        raio = max(2, int(raio_corpo * max(0.05, float(escala_extra))))
        frames = self._obter_frames_escalados(self.Especie, max(12, int(raio * 1.8)))
        if frames and raio > 2:
            frame = frames[int((pygame.time.get_ticks() / self._INTERVALO_FRAME_ANIM_MS) % len(frames))].copy()
            if alpha < 255:
                frame.set_alpha(alpha)
            tela.blit(frame, frame.get_rect(center=centro))
        else:
            surf = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(surf, (70, 155, 245, alpha), (surf.get_width() // 2, surf.get_height() // 2), raio)
            pygame.draw.circle(surf, (24, 84, 190, alpha), (surf.get_width() // 2, surf.get_height() // 2), raio, 2)
            tela.blit(surf, surf.get_rect(center=centro))

    def _desenhar_circulo_base(self, tela, centro, raio_base):
        pulso = 1.0 + math.sin(pygame.time.get_ticks() * 0.008) * 0.06
        rr = max(3, int(raio_base * pulso))
        pygame.draw.circle(tela, (70, 155, 245), centro, rr)
        pygame.draw.circle(tela, (24, 84, 190), centro, rr, 2)
        return rr

    def _surface_bola_captura(self, tile_px: int):
        nome_bola = str(self.CapturaEstado.get("bola_nome") or "pokeball")
        item = {"Nome": nome_bola, "Code": ""}
        return ItemInventario.surface_item(item, lado_px=max(12, int(tile_px * 0.45)))

    def _desenhar_bola(self, tela, centro, tile_px: int, rotacao: float = 0.0, escala: float = 1.0, alpha: int = 255):
        base = self._surface_bola_captura(tile_px)
        if base is None:
            pygame.draw.circle(tela, (255, 180, 90), (int(centro[0]), int(centro[1])), max(3, int(tile_px * 0.16)))
            return
        sprite = base
        if abs(escala - 1.0) > 1e-3:
            w, h = base.get_size()
            sprite = pygame.transform.smoothscale(base, (max(1, int(w * escala)), max(1, int(h * escala))))
        ang_i = int(rotacao) % 360
        chave = (id(sprite), ang_i)
        rot = self._cache_rotacao_bola.get(chave)
        if rot is None:
            rot = pygame.transform.rotate(sprite, rotacao)
            self._cache_rotacao_bola[chave] = rot
            if len(self._cache_rotacao_bola) > 720:
                self._cache_rotacao_bola.clear()
        if alpha < 255:
            rot = rot.copy()
            rot.set_alpha(alpha)
        tela.blit(rot, rot.get_rect(center=(int(centro[0]), int(centro[1]))))

    def _desenhar_animacao_captura(self, tela, camera, centro, tile_px):
        t = min(1.0, max(0.0, self._tempo_fase_ms() / max(1.0, float(self.TempoAnimCapturaMs))))
        base = max(6, int(tile_px * max(self._raio_colisao_padrao, 0.42)))
        aura_r = max(base + 4, int(base * (1.1 + 0.55 * t)))
        aura = pygame.Surface((aura_r * 3, aura_r * 3), pygame.SRCALPHA)
        c = (150, 220, 255, int(120 * (1.0 - t * 0.35)))
        pygame.draw.circle(aura, c, (aura.get_width() // 2, aura.get_height() // 2), aura_r, max(2, int(base * 0.09)))
        tela.blit(aura, aura.get_rect(center=centro))
        for i in range(3):
            ang = (t * math.pi * 2.2) + (i * math.pi * 2.0 / 3.0)
            ox = int(math.cos(ang) * base * (0.5 + 0.2 * (1.0 - t)))
            oy = int(math.sin(ang) * base * (0.35 + 0.2 * (1.0 - t)))
            pygame.draw.circle(tela, (180, 235, 255), (centro[0] + ox, centro[1] + oy), max(2, int(base * 0.10)))
        poke_scale = max(0.0, 1.0 - (t ** 1.35))
        poke_y = int(centro[1] - tile_px * 0.12 * t)
        if poke_scale > 0.02:
            self._desenhar_pokemon_normal(tela, (centro[0], poke_y), max(2, int(base * 2.1)), escala_extra=poke_scale, alpha=max(20, int(255 * (1.0 - t * 0.55))))
        bola_y = int(centro[1] - tile_px * 0.24 * (1.0 - t) * (1.0 - t))
        bola_rot = -280.0 * (1.0 - t)
        bola_squash = 1.0 + 0.12 * math.sin(t * math.pi)
        self._desenhar_bola(tela, (centro[0], bola_y), tile_px, rotacao=bola_rot, escala=bola_squash)

    def _desenhar_animacao_checagem(self, tela, camera, centro, tile_px):
        base = max(6, int(tile_px * max(self._raio_colisao_padrao, 0.42)))
        indice = max(0, int(self.CapturaEstado.get("indice_checagem", 0) or 0))
        t = min(1.0, max(0.0, self._tempo_fase_ms() / max(1.0, float(self.TempoAnimChecagemMs))))
        amplitudes = [13.0, 9.0, 6.0]
        rotacoes = [18.0, 12.0, 7.0]
        amp = amplitudes[min(indice, len(amplitudes) - 1)]
        rot = rotacoes[min(indice, len(rotacoes) - 1)]
        onda = math.sin(t * math.pi)
        dx = int(math.sin(t * math.pi * 2.0) * amp * onda)
        ang = math.sin(t * math.pi * 2.0) * rot * onda
        sombra = pygame.Rect(0, 0, int(base * 1.8), max(4, int(base * 0.45)))
        sombra.center = (centro[0], centro[1] + int(base * 0.72))
        pygame.draw.ellipse(tela, (0, 0, 0, 90), sombra)
        self._desenhar_bola(tela, (centro[0] + dx, centro[1]), tile_px, rotacao=ang)

    def _desenhar_animacao_fuga(self, tela, centro, base):
        t = min(1.0, max(0.0, self._tempo_fase_ms() / max(1.0, float(self.TempoAnimFugaMs))))
        self._desenhar_circulo_base(tela, centro, base)
        for i in range(5):
            ang = (i / 5.0) * math.pi * 2.0 + (t * 2.4)
            ox = int(math.cos(ang) * base * (0.45 + t * 0.85))
            oy = int(math.sin(ang) * base * (0.25 + t * 0.65))
            pygame.draw.circle(tela, (255, 225, 170), (centro[0] + ox, centro[1] + oy), max(2, int(base * 0.08)))
        escala = min(1.0, 0.18 + (t ** 0.65) * 0.92)
        alpha = max(50, int(255 * min(1.0, 0.4 + t * 0.9)))
        self._desenhar_pokemon_normal(tela, centro, max(3, int(base * 2.1)), escala_extra=escala, alpha=alpha)

    def _desenhar_animacao_volta(self, tela, camera, tile_px):
        ini = self.CapturaEstado.get("retorno_inicio") if isinstance(self.CapturaEstado.get("retorno_inicio"), (list, tuple)) else list(self._posicao_bola_mundo())
        fim = self.CapturaEstado.get("retorno_destino") if isinstance(self.CapturaEstado.get("retorno_destino"), (list, tuple)) else ini
        t = min(1.0, max(0.0, self._tempo_fase_ms() / max(1.0, float(self.TempoAnimVoltaMs))))
        ini_t = camera.mundo_para_tela_px((float(ini[0]), float(ini[1])))
        fim_t = camera.mundo_para_tela_px((float(fim[0]), float(fim[1])))
        bx = ini_t[0] + (fim_t[0] - ini_t[0]) * t
        by = ini_t[1] + (fim_t[1] - ini_t[1]) * t - math.sin(t * math.pi) * max(18.0, tile_px * 0.55)
        rot = -540.0 * t
        self._desenhar_bola(tela, (int(bx), int(by)), tile_px, rotacao=rot)

    def render(self, tela, camera, dt: float) -> None:
        self.atualizar(dt)
        cx, cy = camera.mundo_para_tela_px(self.Posicao)
        centro = (int(cx), int(cy))
        tile_px = int(getattr(camera, "TilePx", 50))
        base = max(6, int(tile_px * max(float(getattr(self.Colisor, "raio_colisao", 0.0) or 0.0), self._raio_colisao_padrao, 0.42)))
        fase = self._fase()
        em_pendente = self.em_captura_pendente()

        if self.FrutasAplicadas and fase not in {"volta"} and not em_pendente:
            pygame.draw.circle(tela, (98, 212, 118), centro, base + 8, 2)

        if self.AlvoLocalCaptura and fase == "normal" and not em_pendente:
            self._desenhar_barra_local(tela, centro, base + 14)

        if fase == "captura":
            self._desenhar_animacao_captura(tela, camera, centro, tile_px)
        elif fase == "checagem":
            self._desenhar_animacao_checagem(tela, camera, centro, tile_px)
        elif fase == "fuga":
            self._desenhar_animacao_fuga(tela, centro, base)
        elif fase == "volta":
            self._desenhar_animacao_volta(tela, camera, tile_px)
        else:
            self._desenhar_circulo_base(tela, centro, int(base * 2))
            self._desenhar_pokemon_normal(tela, centro, max(2, int(base * 2.0)))


Pokemon.desenhar = Pokemon.render
PokemonMundo = Pokemon
