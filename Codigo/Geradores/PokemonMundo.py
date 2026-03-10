"""Representação de Pokémon no mundo com estados serializáveis de frutificação/captura."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from Codigo.Geradores.Entidade import Entidade
from Codigo.Geradores.Itens.ItemInventario import ItemInventario
from Codigo.Modulos.Auxiliares import carregar_frames

Vector2 = Tuple[float, float]
_PASTA_ANIMACOES = Path("Recursos") / "Visual" / "Pokemons" / "Animação"


class PokemonMundo(Entidade):
    _cache_frames: Dict[str, List[pygame.Surface]] = {}
    _cache_frames_escalados: Dict[Tuple[str, int], List[pygame.Surface]] = {}
    _cache_rotacao_bola: Dict[Tuple[int, int], pygame.Surface] = {}

    def __init__(self, snapshot: Dict[str, object]) -> None:
        pos = self._pos(snapshot.get("posicao"))
        super().__init__(posicao=pos, raio_colisao=max(0.2, self._f(snapshot.get("raio_colisao"), 0.45)), raio_interacao=1.2, id_objeto=int(snapshot.get("id", 0)))
        self.Destino: Vector2 = pos
        self.Nome = "Pokemon"
        self.Especie = "Pokemon"
        self.Info: Dict[str, object] = {"stats": {}}
        self.FrutasAplicadas: List[Dict[str, object]] = []
        self.EstadoFrutificacao: Dict[str, object] = {"efeitos": {}}
        self.CapturaEstado: Dict[str, object] = {"fase": "nenhuma", "fase_inicio_ms": 0, "bola_posicao": None, "retorno_inicio": None, "retorno_destino": None, "bola_nome": "pokeball"}
        self.AlvoLocalCaptura = False
        self._inicio_barra_local_ms = pygame.time.get_ticks()
        self.DificuldadeCaptura = 20.0
        self.TamanhoBarraCaptura = 0.32
        self.VelocidadeBarraCaptura = 90.0
        self._velocidade_interp_tiles_s = 2.5
        self._escala_visual = 1.0
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
    def _carregar_frames_nome(cls, especie: str) -> List[pygame.Surface]:
        chave = str(especie or "").strip().lower()
        if not chave:
            return []
        if chave in cls._cache_frames:
            return cls._cache_frames[chave]
        frames = carregar_frames(_PASTA_ANIMACOES / chave)
        cls._cache_frames[chave] = frames
        return frames

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

    def capturar(self, evento_captura: Dict[str, object]) -> None:
        evento = dict(evento_captura or {})
        self.CapturaEstado.update(evento)
        self.CapturaEstado.setdefault("fase", "nenhuma")
        self.CapturaEstado.setdefault("fase_inicio_ms", pygame.time.get_ticks())

    def aplicar_snapshot(self, snapshot: Dict[str, object]) -> None:
        estado = snapshot.get("estado") if isinstance(snapshot.get("estado"), dict) else {}
        self.Especie = str(estado.get("especie") or snapshot.get("nome") or self.Especie)
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
        if captura:
            self.capturar(captura)

        destino = self._pos(snapshot.get("posicao"))
        self.Destino = destino
        if str(snapshot.get("movimento") or "").strip().lower() == "teleportar":
            self.definir_posicao(*destino)

    def atualizar(self, dt: float) -> None:
        dt = max(0.0, float(dt))
        px, py = self.Posicao
        dx, dy = self.Destino
        dist = math.hypot(dx - px, dy - py)
        if dist > 1e-4:
            passo = min(dist, self._velocidade_interp_tiles_s * dt)
            k = (passo / dist) if dist > 0 else 0.0
            self.definir_posicao(px + (dx - px) * k, py + (dy - py) * k)

        fase = str(self.CapturaEstado.get("fase", "nenhuma"))
        if fase in {"iniciada", "absorcao"}:
            self._escala_visual = max(0.0, self._escala_visual - dt * 2.6)
        elif fase in {"escape_reaparecendo"}:
            self._escala_visual = min(1.0, self._escala_visual + dt * 2.3)
        elif fase in {"sucesso", "retorno_bola", "finalizada", "bola_no_chao", "tremida1", "tremida2", "tremida3"}:
            self._escala_visual = max(0.0, self._escala_visual - dt * 3.5)
        else:
            self._escala_visual += (1.0 - self._escala_visual) * min(1.0, dt * 6.5)

    def _desenhar_barra_local(self, tela, centro, raio):
        decorrido_s = max(0.0, (pygame.time.get_ticks() - int(self._inicio_barra_local_ms)) / 1000.0)
        ang = (decorrido_s * self.VelocidadeBarraCaptura) % 360.0
        jan = max(8.0, min(120.0, self.TamanhoBarraCaptura * 360.0))
        rect = pygame.Rect(0, 0, raio * 2, raio * 2)
        rect.center = centro
        ini = math.radians(-ang)
        fim = math.radians(-(ang + jan))
        pygame.draw.arc(tela, (255, 210, 76), rect, fim, ini, 4)
        pygame.draw.circle(tela, (36, 120, 255), centro, raio, 1)

    def _desenhar_pokemon_normal(self, tela, centro, raio_corpo):
        frames = self._obter_frames_escalados(self.Especie, max(12, int(raio_corpo * 1.8)))
        if frames and raio_corpo > 2:
            frame = frames[int((pygame.time.get_ticks() / 100) % len(frames))]
            tela.blit(frame, frame.get_rect(center=centro))
        else:
            pygame.draw.circle(tela, (70, 155, 245), centro, raio_corpo)
            pygame.draw.circle(tela, (24, 84, 190), centro, raio_corpo, 2)

    def _desenhar_efeito_absorcao(self, tela, centro, raio_base):
        t = (pygame.time.get_ticks() % 450) / 450.0
        rr = max(4, int(raio_base * (0.5 + t * 1.5)))
        pygame.draw.circle(tela, (78, 168, 255), centro, rr, 2)

    def _centro_bola_captura(self, camera, centro_padrao, usar_posicao_captura=True):
        if not usar_posicao_captura:
            return centro_padrao
        pos = self.CapturaEstado.get("bola_posicao")
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            bx, by = camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))
            return (int(bx), int(by))
        return centro_padrao

    def _surface_bola_captura(self, tile_px: int):
        nome_bola = str(self.CapturaEstado.get("bola_nome") or "pokeball")
        item = {"Nome": nome_bola, "Code": ""}
        return ItemInventario.surface_item(item, lado_px=max(12, int(tile_px * 0.45)))

    def _desenhar_bola_captura(self, tela, camera, centro, fase, tile_px, usar_posicao_captura=True):
        cx, cy = self._centro_bola_captura(camera, centro, usar_posicao_captura=usar_posicao_captura)
        ang = 0.0
        if fase.startswith("tremida"):
            k = int(fase.replace("tremida", "") or 1)
            cx += int(math.sin(pygame.time.get_ticks() * 0.024 * (1 + k * 0.3)) * (4 + k))
            ang = math.sin(pygame.time.get_ticks() * 0.05 * (1 + k * 0.2)) * (12.0 + 2.0 * k)

        base = self._surface_bola_captura(tile_px)
        if base is None:
            pygame.draw.circle(tela, (255, 180, 90), (int(cx), int(cy)), max(3, int(tile_px * 0.16)))
            return

        chave = (id(base), int(ang) % 360)
        rot = self._cache_rotacao_bola.get(chave)
        if rot is None:
            rot = pygame.transform.rotate(base, ang)
            self._cache_rotacao_bola[chave] = rot
            if len(self._cache_rotacao_bola) > 720:
                self._cache_rotacao_bola.clear()
        tela.blit(rot, rot.get_rect(center=(int(cx), int(cy))))

    def _desenhar_retorno_ou_escape(self, tela, camera, centro, fase, raio_corpo, tile_px):
        if fase == "retorno_bola":
            ini = self.CapturaEstado.get("retorno_inicio") if isinstance(self.CapturaEstado.get("retorno_inicio"), (list, tuple)) else [self.Posicao[0], self.Posicao[1]]
            fim = self.CapturaEstado.get("retorno_destino") if isinstance(self.CapturaEstado.get("retorno_destino"), (list, tuple)) else ini
            ini_t = camera.mundo_para_tela_px((float(ini[0]), float(ini[1])))
            fim_t = camera.mundo_para_tela_px((float(fim[0]), float(fim[1])))
            t = min(1.0, max(0.0, (pygame.time.get_ticks() - int(self.CapturaEstado.get("fase_inicio_ms", 0))) / 320.0))
            bx = int(ini_t[0] + (fim_t[0] - ini_t[0]) * t)
            by = int(ini_t[1] + (fim_t[1] - ini_t[1]) * t)
            self._desenhar_bola_captura(tela, camera, (bx, by), fase, tile_px, usar_posicao_captura=False)
            return

        if fase == "escape_reaparecendo":
            self._desenhar_pokemon_normal(tela, centro, max(3, int(raio_corpo * max(0.2, self._escala_visual))))

    def desenhar(self, tela, camera, dt: float) -> None:
        self.atualizar(dt)
        cx, cy = camera.mundo_para_tela_px(self.Posicao)
        centro = (int(cx), int(cy))
        tile_px = int(getattr(camera, "TilePx", 50))
        base = max(6, int(tile_px * self.Colisor.raio_colisao))
        pulso = 1.0 + math.sin(pygame.time.get_ticks() * 0.008) * 0.06
        raio_corpo = max(2, int(base * pulso * self._escala_visual))
        fase = str(self.CapturaEstado.get("fase", ""))

        if self.FrutasAplicadas:
            pygame.draw.circle(tela, (98, 212, 118), centro, raio_corpo + 8, 2)

        if self.AlvoLocalCaptura:
            self._desenhar_barra_local(tela, centro, base + 14)

        if fase in {"iniciada", "absorcao"}:
            self._desenhar_efeito_absorcao(tela, centro, base + 10)
            self._desenhar_pokemon_normal(tela, centro, raio_corpo)
        elif fase in {"bola_no_chao", "tremida1", "tremida2", "tremida3"}:
            self._desenhar_bola_captura(tela, camera, centro, fase, tile_px)
        elif fase in {"retorno_bola", "escape_reaparecendo"}:
            self._desenhar_retorno_ou_escape(tela, camera, centro, fase, raio_corpo, tile_px)
        elif fase in {"sucesso", "finalizada"}:
            self._desenhar_bola_captura(tela, camera, centro, fase, tile_px)
        else:
            self._desenhar_pokemon_normal(tela, centro, raio_corpo)
