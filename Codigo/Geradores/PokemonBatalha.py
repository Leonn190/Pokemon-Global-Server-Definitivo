from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from Codigo.ModulosGerais.Auxiliares import carregar_frames

Vector2 = Tuple[float, float]
_PASTA_ANIMACOES = Path("Recursos") / "Visual" / "Pokemons" / "Animação"


class PokemonBatalha:
    _cache_frames: Dict[str, List[pygame.Surface]] = {}

    def __init__(self, dados: Dict[str, object], posicao: Vector2, lado: str) -> None:
        self.Dados = dict(dados or {})
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        self.Lado = str(lado or "jogador")

        estado = self.Dados.get("estado") if isinstance(self.Dados.get("estado"), dict) else self.Dados
        stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}

        self.Nome = str(estado.get("nome") or estado.get("especie") or self.Dados.get("nome") or "Pokemon")
        self.Especie = str(estado.get("especie") or self.Nome)
        self.Peso = float(estado.get("peso", 0.0) or 0.0)
        self.Escala = int(estado.get("escala", self.Dados.get("escala", 3)) or 3)
        self.CrC = float(stats.get("CrC", estado.get("CrC", 0.0)) or 0.0)
        self.CrD = float(stats.get("CrD", estado.get("CrD", 0.0)) or 0.0)

        self.VidaMax = max(1.0, float(stats.get("Vida", estado.get("Vida", 1.0)) or 1.0))
        self.VidaAtual = max(0.0, min(self.VidaMax, float(estado.get("vida_atual", self.VidaMax) or self.VidaMax)))

        ene_base = max(1.0, float(stats.get("Ene", estado.get("Ene", 1.0)) or 1.0))
        self.EnergiaMax = ene_base * 3.0
        energia_padrao = max(0.0, min(self.EnergiaMax, float(estado.get("energia", self.EnergiaMax) or self.EnergiaMax)))
        self.Energia = energia_padrao

    @classmethod
    def _frames_especie(cls, especie: str) -> List[pygame.Surface]:
        chave = str(especie or "").strip().lower()
        if not chave:
            return []
        if chave in cls._cache_frames:
            return cls._cache_frames[chave]
        cls._cache_frames[chave] = carregar_frames(_PASTA_ANIMACOES / chave)
        return cls._cache_frames[chave]

    def _frame_atual(self, tamanho_px: int) -> pygame.Surface | None:
        frames = self._frames_especie(self.Especie)
        if not frames:
            return None
        idx = int((pygame.time.get_ticks() // 95) % max(1, len(frames)))
        base = frames[idx]
        w, h = base.get_size()
        if w <= 0 or h <= 0:
            return None
        k = float(tamanho_px) / float(max(w, h))
        return pygame.transform.smoothscale(base, (max(1, int(w * k)), max(1, int(h * k))))

    def renderizar(self, tela: pygame.Surface, camera) -> None:
        px, py = camera.mundo_para_tela_px(self.Posicao)
        centro = (int(px), int(py))
        tile_px = max(16, int(getattr(camera, "TilePx", 40) or 40))
        raio = max(18, int(tile_px * 0.78))

        cor_circulo = (56, 90, 145) if self.Lado == "jogador" else (144, 74, 74)
        pygame.draw.circle(tela, (0, 0, 0, 80), (centro[0], centro[1] + max(4, raio // 8)), int(raio * 0.96))
        pygame.draw.circle(tela, cor_circulo, centro, raio)
        pygame.draw.circle(tela, (22, 26, 34), centro, raio, max(2, int(tile_px * 0.06)))

        frame = self._frame_atual(int(raio * 1.40))
        if frame is not None:
            tela.blit(frame, frame.get_rect(center=(centro[0], centro[1] - int(raio * 0.08))))

        self._desenhar_barras(tela, centro, raio)

    def _desenhar_barras(self, tela: pygame.Surface, centro: Tuple[int, int], raio: int) -> None:
        largura_arco = max(7, int(raio * 0.16))
        energia_largura = max(2, int(largura_arco * 0.45))
        r_vida = max(10, int(raio * 1.16))
        r_energia = r_vida + max(3, int(largura_arco * 0.45))
        ang_ini = math.radians(200)
        ang_fim = math.radians(340)

        rect_vida = pygame.Rect(centro[0] - r_vida, centro[1] - r_vida, r_vida * 2, r_vida * 2)
        rect_ene = pygame.Rect(centro[0] - r_energia, centro[1] - r_energia, r_energia * 2, r_energia * 2)

        pygame.draw.arc(tela, (0, 0, 0), rect_vida, ang_ini, ang_fim, largura_arco)
        vida_t = 0.0 if self.VidaMax <= 0 else max(0.0, min(1.0, self.VidaAtual / self.VidaMax))
        if vida_t > 0.001:
            pygame.draw.arc(tela, (52, 205, 72), rect_vida, ang_ini, ang_ini + (ang_fim - ang_ini) * vida_t, max(1, largura_arco - 2))

        marcas = max(0, int(self.VidaMax // 30) - 1)
        if marcas > 0:
            blocos = marcas + 1
            for i in range(1, marcas + 1):
                frac = i / blocos
                ang = ang_ini + (ang_fim - ang_ini) * frac
                c = math.cos(ang); s = math.sin(ang)
                p1 = (int(centro[0] + c * (r_vida - largura_arco // 2)), int(centro[1] + s * (r_vida - largura_arco // 2)))
                p2 = (int(centro[0] + c * (r_vida + largura_arco // 2)), int(centro[1] + s * (r_vida + largura_arco // 2)))
                pygame.draw.line(tela, (0, 0, 0), p1, p2, 2)

        pygame.draw.arc(tela, (20, 46, 80), rect_ene, ang_ini, ang_fim, energia_largura)
        ene_t = 0.0 if self.EnergiaMax <= 0 else max(0.0, min(1.0, self.Energia / self.EnergiaMax))
        if ene_t > 0.001:
            pygame.draw.arc(tela, (60, 150, 255), rect_ene, ang_ini, ang_ini + (ang_fim - ang_ini) * ene_t, energia_largura)
