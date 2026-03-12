"""Representação de Pokémon no mundo com estados serializáveis de frutificação/captura."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from Codigo.Modulos.Colisor import Colisor
from Codigo.Geradores.Itens.ItemInventario import ItemInventario
from Codigo.Modulos.Auxiliares import carregar_frames

Vector2 = Tuple[float, float]
_PASTA_ANIMACOES = Path("Recursos") / "Visual" / "Pokemons" / "Animação"


class Pokemon:
    _cache_frames: Dict[str, List[pygame.Surface]] = {}
    _cache_frames_escalados: Dict[Tuple[str, int], List[pygame.Surface]] = {}
    _cache_rotacao_bola: Dict[Tuple[int, int], pygame.Surface] = {}

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
        self.CapturaEstado: Dict[str, object] = {"fase": "nenhuma", "fase_inicio_ms": 0, "bola_posicao": None, "retorno_inicio": None, "retorno_destino": None, "bola_nome": "pokeball"}
        self._captura_aguardando_token = ""
        self._captura_confirmada_token = ""
        self._captura_confirmada_desde_ms = 0
        self._captura_confirmada_espera_colisao = False
        self._captura_confirmada_atraso_ms = 0
        self.AlvoLocalCaptura = False
        self._inicio_barra_local_ms = pygame.time.get_ticks()
        self.DificuldadeCaptura = 20.0
        self.TamanhoBarraCaptura = 0.32
        self.VelocidadeBarraCaptura = 90.0
        self._velocidade_interp_tiles_s = 2.5
        self._escala_visual = 1.0
        self._captura_fake_token = ""
        self._captura_fake_inicio_ms = 0
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
        token_evento = str(evento.get("token_arremesso") or "")
        if token_evento and self._captura_aguardando_token and token_evento == self._captura_aguardando_token:
            self.confirmar_captura_por_token(token_evento, esperar_colisao=False, atraso_ms=0)

        fase_evento = str(evento.get("fase", "nenhuma") or "nenhuma").strip().lower()
        if self._captura_confirmada_token and token_evento and token_evento == self._captura_confirmada_token and self._captura_confirmada_espera_colisao:
            return
        if self._captura_confirmada_token and token_evento and token_evento == self._captura_confirmada_token and self._captura_confirmada_atraso_ms > 0:
            agora = pygame.time.get_ticks()
            if (agora - self._captura_confirmada_desde_ms) < self._captura_confirmada_atraso_ms and fase_evento in {"iniciada", "absorcao", "bola_no_chao", "tremida1", "tremida2", "tremida3"}:
                return

        self.CapturaEstado.update(evento)
        self.CapturaEstado.setdefault("fase", "nenhuma")
        self.CapturaEstado.setdefault("fase_inicio_ms", pygame.time.get_ticks())
        if token_evento:
            self._captura_fake_token = token_evento
        if fase_evento == "finalizada":
            self.CapturaEstado["fase"] = "nenhuma"
            self.CapturaEstado["captura_pendente"] = False
            self._escala_visual = 1.0
            self._captura_aguardando_token = ""
            self._captura_confirmada_token = ""
            self._captura_confirmada_desde_ms = 0
            self._captura_confirmada_espera_colisao = False
            self._captura_confirmada_atraso_ms = 0

    def registrar_colisao_projetil_local(self, token: str, nome_bola: str = "pokeball", tempo_espera_confirmacao_ms: int = 1500) -> None:
        self._captura_aguardando_token = str(token or "")
        self._captura_fake_token = self._captura_aguardando_token
        self._captura_fake_inicio_ms = pygame.time.get_ticks()
        self.CapturaEstado["bola_nome"] = str(nome_bola or self.CapturaEstado.get("bola_nome") or "pokeball")
        self.CapturaEstado["token_arremesso"] = self._captura_aguardando_token
        self.CapturaEstado["captura_pendente"] = True
        self.CapturaEstado["fase"] = "iniciada"
        self.CapturaEstado["fase_inicio_ms"] = self._captura_fake_inicio_ms
        self.CapturaEstado["tempo_espera_confirmacao_ms"] = int(tempo_espera_confirmacao_ms)
        self._captura_confirmada_espera_colisao = False
        if self._captura_confirmada_token == self._captura_aguardando_token:
            self.confirmar_captura_por_token(self._captura_aguardando_token, esperar_colisao=False, atraso_ms=0)

    def confirmar_captura_por_token(self, token: str, esperar_colisao: bool = False, atraso_ms: int = 0) -> None:
        token = str(token or "")
        if not token:
            return
        self._captura_confirmada_token = token
        self._captura_confirmada_desde_ms = pygame.time.get_ticks()
        self._captura_confirmada_espera_colisao = bool(esperar_colisao)
        self._captura_confirmada_atraso_ms = max(0, int(atraso_ms or 0))

    def iniciar_captura_fake(self, token: str) -> None:
        self.registrar_colisao_projetil_local(token)

    def _resolver_timeout_captura_fake(self) -> None:
        if self._captura_fake_inicio_ms <= 0:
            return
        tempo_limite = int(self.CapturaEstado.get("tempo_espera_confirmacao_ms", 1500) or 1500)
        if (pygame.time.get_ticks() - self._captura_fake_inicio_ms) < tempo_limite:
            return
        fase = str(self.CapturaEstado.get("fase", "nenhuma") or "nenhuma")
        if fase in {"bola_no_chao", "iniciada", "absorcao", "tremida1", "tremida2", "tremida3"}:
            self.CapturaEstado["fase"] = "escape_reaparecendo"
            self.CapturaEstado["captura_pendente"] = False
        self._captura_fake_inicio_ms = 0

    def em_captura_pendente(self) -> bool:
        self._resolver_timeout_captura_fake()
        agora_ms = pygame.time.get_ticks()
        if self._captura_confirmada_token:
            token_atual = str(self.CapturaEstado.get("token_arremesso") or self._captura_fake_token or "")
            pronto_por_tempo = (agora_ms - self._captura_confirmada_desde_ms) >= self._captura_confirmada_atraso_ms
            if token_atual == self._captura_confirmada_token and (not self._captura_confirmada_espera_colisao) and pronto_por_tempo:
                self._captura_confirmada_atraso_ms = 0
        fase = str(self.CapturaEstado.get("fase", "nenhuma") or "nenhuma")
        if bool(self.CapturaEstado.get("captura_pendente", False)):
            return True
        return fase in {"iniciada", "absorcao", "bola_no_chao", "tremida1", "tremida2", "tremida3", "retorno_bola", "sucesso"}

    def update(self, snapshot: Dict[str, object]) -> None:
        self.aplicar_snapshot(snapshot)

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
            self._captura_fake_inicio_ms = 0
            self.capturar(captura)

        if self.em_captura_pendente():
            self.Colisor.raio_colisao = 0.0
            self.Colisor.raio_interacao = 0.0
        else:
            self.Colisor.raio_colisao = max(0.2, self._f(snapshot.get("raio_colisao"), 0.45))
            self.Colisor.raio_interacao = max(self.Colisor.raio_colisao, 1.2)

        destino = self._pos(snapshot.get("posicao"))
        self.Destino = destino
        if str(snapshot.get("movimento") or "").strip().lower() == "teleportar":
            self.definir_posicao(*destino)

    def definir_posicao(self, x: float, y: float) -> None:
        self.Posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.Posicao)

    def mover(self, dt: float) -> None:
        self.atualizar(dt)

    def animacaptura(self, tela, camera, centro, tile_px):
        self._desenhar_pokebola_no_chao(tela, camera, centro, "absorcao", tile_px)

    def animachecagem(self, tela, camera, centro, fase, tile_px):
        self._desenhar_tremida(tela, camera, centro, fase, tile_px)

    def animafuga(self, tela, centro, base):
        self._desenhar_escape(tela, centro, base)

    def animavolta(self, tela, camera, centro, tile_px):
        self._desenhar_retorno_ao_player(tela, camera, centro, "retorno_bola", tile_px)

    def atualizar(self, dt: float) -> None:
        dt = max(0.0, float(dt))
        px, py = self.Posicao
        dx, dy = self.Destino
        dist = math.hypot(dx - px, dy - py)
        if dist > 1e-4:
            passo = min(dist, self._velocidade_interp_tiles_s * dt)
            k = (passo / dist) if dist > 0 else 0.0
            self.definir_posicao(px + (dx - px) * k, py + (dy - py) * k)

        self._resolver_timeout_captura_fake()
        agora_ms = pygame.time.get_ticks()
        if self._captura_confirmada_token:
            token_atual = str(self.CapturaEstado.get("token_arremesso") or self._captura_fake_token or "")
            pronto_por_tempo = (agora_ms - self._captura_confirmada_desde_ms) >= self._captura_confirmada_atraso_ms
            if token_atual == self._captura_confirmada_token and (not self._captura_confirmada_espera_colisao) and pronto_por_tempo:
                self._captura_confirmada_atraso_ms = 0
        fase = str(self.CapturaEstado.get("fase", "nenhuma") or "nenhuma")
        if fase in {"iniciada", "absorcao"}:
            self._escala_visual = max(0.0, self._escala_visual - dt * 2.6)
        elif fase == "escape_reaparecendo":
            self._escala_visual = min(1.0, self._escala_visual + dt * 2.4)
        elif fase in {"sucesso", "retorno_bola", "finalizada", "bola_no_chao", "tremida1", "tremida2", "tremida3", "escape"}:
            self._escala_visual = max(0.0, self._escala_visual - dt * 3.2)
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

    def _desenhar_circulo_base(self, tela, centro, raio_base, fase):
        escala = max(0.08, self._escala_visual)
        pulso = 1.0 + math.sin(pygame.time.get_ticks() * 0.008) * 0.06
        rr = max(3, int(raio_base * pulso * escala))
        if fase in {"iniciada", "absorcao"}:
            t = (pygame.time.get_ticks() % 420) / 420.0
            rr = max(rr, int(raio_base * (0.7 + t * 1.5) * escala))
            pygame.draw.circle(tela, (78, 168, 255), centro, rr, 2)
            pygame.draw.circle(tela, (60, 130, 255), centro, max(2, rr - 2), 1)
            return rr
        pygame.draw.circle(tela, (70, 155, 245), centro, rr)
        pygame.draw.circle(tela, (24, 84, 190), centro, rr, 2)
        return rr

    def _desenhar_absorcao(self, tela, camera, centro, raio_base, tile_px, fase):
        tempo = max(0.0, (pygame.time.get_ticks() - int(self.CapturaEstado.get("fase_inicio_ms", 0))) / 1000.0)
        if fase == "iniciada":
            prog = min(1.0, tempo / 0.22)
        elif fase == "absorcao":
            prog = 1.0 - min(1.0, tempo / 0.28)
        else:
            prog = 0.0
        prog = max(0.0, min(1.0, prog))
        raio_circulo = max(4, int(raio_base * (0.2 + 0.9 * prog)))
        cor = (170, 225, 255)
        aura = pygame.Surface((raio_circulo * 4, raio_circulo * 4), pygame.SRCALPHA)
        pygame.draw.circle(aura, (cor[0], cor[1], cor[2], 78), (aura.get_width() // 2, aura.get_height() // 2), raio_circulo)
        pygame.draw.circle(aura, (cor[0], cor[1], cor[2], 168), (aura.get_width() // 2, aura.get_height() // 2), raio_circulo, max(2, int(raio_base * 0.08)))
        tela.blit(aura, aura.get_rect(center=centro))
        raio_corpo = max(0, int(raio_base * (1.0 - prog)))
        if raio_corpo > 1:
            self._desenhar_pokemon_normal(tela, centro, raio_corpo)
        self._desenhar_bola_captura(tela, camera, centro, "bola_no_chao", tile_px)

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
            amplitudes = {1: 11, 2: 7, 3: 4}
            angulos = {1: 16.0, 2: 10.0, 3: 6.0}
            cx += int(math.sin(pygame.time.get_ticks() * 0.026 * (1 + k * 0.18)) * amplitudes.get(k, 4))
            ang = math.sin(pygame.time.get_ticks() * 0.05 * (1 + k * 0.12)) * angulos.get(k, 6.0)

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

    def _desenhar_escape(self, tela, centro, base):
        self._desenhar_circulo_base(tela, centro, base, "escape_reaparecendo")
        self._desenhar_pokemon_normal(tela, centro, max(3, int(base * max(0.18, self._escala_visual))))

    def _desenhar_retorno_ao_player(self, tela, camera, centro, fase, tile_px):
        ini = self.CapturaEstado.get("retorno_inicio") if isinstance(self.CapturaEstado.get("retorno_inicio"), (list, tuple)) else [self.Posicao[0], self.Posicao[1]]
        fim = self.CapturaEstado.get("retorno_destino") if isinstance(self.CapturaEstado.get("retorno_destino"), (list, tuple)) else ini
        ini_t = camera.mundo_para_tela_px((float(ini[0]), float(ini[1])))
        fim_t = camera.mundo_para_tela_px((float(fim[0]), float(fim[1])))
        t = min(1.0, max(0.0, (pygame.time.get_ticks() - int(self.CapturaEstado.get("fase_inicio_ms", 0))) / 340.0))
        bx = int(ini_t[0] + (fim_t[0] - ini_t[0]) * t)
        by = int(ini_t[1] + (fim_t[1] - ini_t[1]) * t)
        self._desenhar_bola_captura(tela, camera, (bx, by), fase, tile_px, usar_posicao_captura=False)

    def _desenhar_pokebola_no_chao(self, tela, camera, centro, fase, tile_px):
        self._desenhar_bola_captura(tela, camera, centro, fase, tile_px)

    def _desenhar_tremida(self, tela, camera, centro, fase, tile_px):
        self._desenhar_bola_captura(tela, camera, centro, fase, tile_px)

    def render(self, tela, camera, dt: float) -> None:
        self.atualizar(dt)
        cx, cy = camera.mundo_para_tela_px(self.Posicao)
        centro = (int(cx), int(cy))
        tile_px = int(getattr(camera, "TilePx", 50))
        base = max(6, int(tile_px * max(float(getattr(self.Colisor, "raio_colisao", 0.0) or 0.0), 0.42)))
        self._resolver_timeout_captura_fake()
        agora_ms = pygame.time.get_ticks()
        if self._captura_confirmada_token:
            token_atual = str(self.CapturaEstado.get("token_arremesso") or self._captura_fake_token or "")
            pronto_por_tempo = (agora_ms - self._captura_confirmada_desde_ms) >= self._captura_confirmada_atraso_ms
            if token_atual == self._captura_confirmada_token and (not self._captura_confirmada_espera_colisao) and pronto_por_tempo:
                self._captura_confirmada_atraso_ms = 0
        fase = str(self.CapturaEstado.get("fase", "nenhuma") or "nenhuma")

        em_pendente = self.em_captura_pendente()
        if self.FrutasAplicadas and fase not in {"sucesso", "finalizada", "retorno_bola"} and not em_pendente:
            pygame.draw.circle(tela, (98, 212, 118), centro, base + 8, 2)

        if self.AlvoLocalCaptura and fase in {"nenhuma", "escape_reaparecendo", "escape"} and not em_pendente:
            self._desenhar_barra_local(tela, centro, base + 14)

        if fase in {"iniciada", "absorcao"}:
            self._desenhar_absorcao(tela, camera, centro, max(base, int(tile_px * 0.50)), tile_px, fase)
        elif fase == "bola_no_chao":
            self._desenhar_pokebola_no_chao(tela, camera, centro, fase, tile_px)
        elif fase in {"tremida1", "tremida2", "tremida3"}:
            self._desenhar_tremida(tela, camera, centro, fase, tile_px)
        elif fase == "retorno_bola":
            self._desenhar_retorno_ao_player(tela, camera, centro, fase, tile_px)
        elif fase in {"escape", "escape_reaparecendo"}:
            self._desenhar_escape(tela, centro, base)
        elif fase in {"sucesso", "finalizada"}:
            self._desenhar_bola_captura(tela, camera, centro, fase, tile_px)
        else:
            self._desenhar_circulo_base(tela, centro, base, fase)
            self._desenhar_pokemon_normal(tela, centro, max(2, int(base * self._escala_visual)))


Pokemon.desenhar = Pokemon.render
PokemonMundo = Pokemon
