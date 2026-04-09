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

    def __init__(self, dados: Dict[str, object], posicao: Vector2, lado: str, regras: Dict[str, object] | None = None) -> None:
        self.Dados = dict(dados or {})
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        self.Lado = str(lado or "jogador")
        self.Regras = dict(regras or {})

        estado = self.Dados.get("estado") if isinstance(self.Dados.get("estado"), dict) else self.Dados
        stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}

        self.Nome = str(estado.get("nome") or estado.get("especie") or self.Dados.get("nome") or "Pokemon")
        self.Especie = str(estado.get("especie") or self.Nome)
        self.Peso = float(estado.get("peso", 0.0) or 0.0)
        self.Escala = int(estado.get("escala", self.Dados.get("escala", 3)) or 3)
        self.CrC = float(stats.get("CrC", estado.get("CrC", 0.0)) or 0.0)
        self.CrD = float(stats.get("CrD", estado.get("CrD", 0.0)) or 0.0)
        base_tamanho = float(self.Regras.get("combate_pokemon_tamanho_diametro_base_tiles", 1.0) or 1.0)
        incremento = float(self.Regras.get("combate_pokemon_tamanho_incremento_por_escala", 0.1) or 0.1)
        self.DiametroTiles = max(0.4, base_tamanho + max(0.0, float(self.Escala)) * max(0.01, incremento))

        self.VidaMax = max(1.0, float(stats.get("Vida", estado.get("Vida", 1.0)) or 1.0))
        self.VidaAtual = max(0.0, min(self.VidaMax, float(estado.get("vida_atual", self.VidaMax) or self.VidaMax)))

        ene_base = max(1.0, float(stats.get("Ene", estado.get("Ene", 1.0)) or 1.0))
        self.EnergiaMax = ene_base * 3.0
        energia_padrao = max(0.0, min(self.EnergiaMax, float(estado.get("energia", ene_base) or ene_base)))
        self.Energia = energia_padrao
        self.Nivel = int(estado.get("nivel", estado.get("Nivel", self.Dados.get("nivel", 1))) or 1)
        self.Tipos = list(estado.get("tipos") or self.Dados.get("tipos") or ([] if not self.Dados.get("tipo") else [self.Dados.get("tipo")]))
        self.ListaAtaques = self._extrair_lista_ataques(estado)
        self.ItensBuild = list(estado.get("build") or estado.get("itens_build") or self.Dados.get("build") or [])
        self.Stats = dict(stats)
        for chave in ("Amplificacao", "Durabilidade", "Vamp", "Barreira"):
            self.Stats.setdefault(chave, 0.0)


    @staticmethod
    def _extrair_lista_ataques(estado: Dict[str, object]) -> List[Dict[str, object]]:
        candidatos = estado.get("ataques") or estado.get("moves") or estado.get("golpes") or []
        saida: List[Dict[str, object]] = []
        if isinstance(candidatos, (list, tuple)):
            for item in candidatos:
                if isinstance(item, dict):
                    saida.append(dict(item))
                elif item is not None:
                    saida.append({"nome": str(item), "tipo": "normal"})
        return saida

    def raio_px(self, camera) -> int:
        tile_px = max(16, int(getattr(camera, "TilePx", 40) or 40))
        return max(12, int(tile_px * (self.DiametroTiles * 0.5)))

    def centro_tela(self, camera) -> Tuple[int, int]:
        px, py = camera.mundo_para_tela_px(self.Posicao)
        return int(px), int(py)


    @staticmethod
    def _normalizar_chave_ficha(chave: str) -> str:
        return str(chave or "").strip().lower().replace("á", "a").replace("ã", "a").replace("ç", "c")

    def obter_valor_ficha(self, chave: str):
        c = self._normalizar_chave_ficha(chave)
        mapa_direto = {
            "peso": self.Peso,
            "escala": self.Escala,
            "energiamaxima": self.EnergiaMax,
            "energiamax": self.EnergiaMax,
            "crc": self.CrC,
            "crd": self.CrD,
            "vida": self.VidaMax,
        }
        if c in mapa_direto:
            return mapa_direto[c]

        for k, v in self.Stats.items():
            if self._normalizar_chave_ficha(k) == c:
                return v
        return 0.0

    def montar_dados_ficha(self) -> Dict[str, object]:
        return {
            "nome": self.Nome,
            "nivel": self.Nivel,
            "tipos": list(self.Tipos),
            "ataques": list(self.ListaAtaques),
            "itens": list(self.ItensBuild),
            "vida_atual": self.VidaAtual,
            "vida_max": self.VidaMax,
            "energia_atual": self.Energia,
            "energia_max": self.EnergiaMax,
        }

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

    def renderizar(self, tela: pygame.Surface, camera, selecionado: bool = False) -> None:
        centro = self.centro_tela(camera)
        tile_px = max(16, int(getattr(camera, "TilePx", 40) or 40))
        raio = self.raio_px(camera)

        cor_circulo = (56, 90, 145) if self.Lado == "jogador" else (144, 74, 74)
        pygame.draw.circle(tela, (0, 0, 0, 80), (centro[0], centro[1] + max(4, raio // 8)), int(raio * 0.96))
        pygame.draw.circle(tela, cor_circulo, centro, raio)
        pygame.draw.circle(tela, (22, 26, 34), centro, raio, max(2, int(tile_px * 0.06)))
        if selecionado:
            pulso = (pygame.time.get_ticks() % 900) / 900.0
            alpha = int(130 + 120 * abs(0.5 - pulso) * 2.0)
            brilho = pygame.Surface((raio * 3, raio * 3), pygame.SRCALPHA)
            pygame.draw.circle(brilho, (255, 255, 190, alpha), (brilho.get_width() // 2, brilho.get_height() // 2), raio + max(2, int(tile_px * 0.16)), 3)
            tela.blit(brilho, brilho.get_rect(center=centro))

        frame = self._frame_atual(int(raio * 1.40))
        if frame is not None:
            tela.blit(frame, frame.get_rect(center=(centro[0], centro[1] - int(raio * 0.08))))

        self._desenhar_barras(tela, centro, raio, tile_px)

    def _desenhar_barras(self, tela: pygame.Surface, centro: Tuple[int, int], raio: int, tile_px: int) -> None:
        largura = max(24, int(tile_px * self.DiametroTiles * 1.25))
        vida_h = max(7, int(tile_px * 0.18))
        ene_h = max(2, int(vida_h * 0.44))
        espaco = max(1, int(tile_px * 0.05))
        topo = int(centro[1] - raio - (tile_px * 0.38))
        x = int(centro[0] - largura * 0.5)

        rect_vida = pygame.Rect(x, topo, largura, vida_h)
        rect_ene = pygame.Rect(x, topo + vida_h + espaco, largura, ene_h)

        pygame.draw.rect(tela, (0, 0, 0), rect_vida, border_radius=max(2, vida_h // 3))
        inner_vida = rect_vida.inflate(-2, -2)
        pygame.draw.rect(tela, (34, 44, 34), inner_vida, border_radius=max(2, inner_vida.height // 3))
        vida_t = 0.0 if self.VidaMax <= 0 else max(0.0, min(1.0, self.VidaAtual / self.VidaMax))
        if vida_t > 0.001 and inner_vida.width > 2:
            fill_vida = pygame.Rect(inner_vida.x, inner_vida.y, max(1, int(inner_vida.width * vida_t)), inner_vida.height)
            pygame.draw.rect(tela, (52, 205, 72), fill_vida, border_radius=max(2, inner_vida.height // 3))

        blocos = max(1, int(math.ceil(self.VidaMax / 30.0)))
        for i in range(1, blocos):
            marca_x = inner_vida.x + int((inner_vida.width * i) / blocos)
            pygame.draw.line(tela, (0, 0, 0), (marca_x, inner_vida.y), (marca_x, inner_vida.y + inner_vida.height), 1)

        pygame.draw.rect(tela, (0, 0, 0), rect_ene, border_radius=max(1, ene_h // 2))
        inner_ene = rect_ene.inflate(-2, -2)
        pygame.draw.rect(tela, (20, 46, 80), inner_ene, border_radius=max(1, inner_ene.height // 2))
        ene_t = 0.0 if self.EnergiaMax <= 0 else max(0.0, min(1.0, self.Energia / self.EnergiaMax))
        if ene_t > 0.001 and inner_ene.width > 2:
            fill_ene = pygame.Rect(inner_ene.x, inner_ene.y, max(1, int(inner_ene.width * ene_t)), inner_ene.height)
            pygame.draw.rect(tela, (60, 150, 255), fill_ene, border_radius=max(1, inner_ene.height // 2))
