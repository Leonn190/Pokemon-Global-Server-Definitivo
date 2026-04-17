"""Gerenciador visual de tiles (base + transições)."""

from __future__ import annotations

import math
from typing import Callable, Dict, Iterable, Optional, Tuple

import pygame

Cor = Tuple[int, int, int]
Vizinhanca = Tuple[int | None, int | None, int | None, int | None, int | None, int | None, int | None, int | None, int | None]


class AparenciaBaseTiles:
    """Gera visual base dos tiles com variação leve e determinística."""

    def __init__(self, cores_blocos: Dict[int, Cor]) -> None:
        self.CoresBlocos = {int(k): tuple(v) for k, v in (cores_blocos or {}).items()}
        self.SeedMundo = 0
        self._cache_tiles: Dict[Tuple[int, int, int], pygame.Surface] = {}

    def definir_seed(self, seed_mundo: int) -> None:
        novo_seed = int(seed_mundo or 0)
        if novo_seed != self.SeedMundo:
            self.SeedMundo = novo_seed
            self.limpar_cache()

    def atualizar_cores(self, cores_blocos: Dict[int, Cor]) -> None:
        self.CoresBlocos = {int(k): tuple(v) for k, v in (cores_blocos or {}).items()}
        self.limpar_cache()

    def limpar_cache(self) -> None:
        self._cache_tiles.clear()

    @staticmethod
    def _mix64(valor: int) -> int:
        x = int(valor) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 30)
        x = (x * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 27)
        x = (x * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 31)
        return x & 0xFFFFFFFFFFFFFFFF

    def _variante_base(self, mundo_x: int, mundo_y: int, bloco: int) -> int:
        h = (
            int(self.SeedMundo)
            ^ (int(mundo_x) * 0x9E3779B185EBCA87)
            ^ (int(mundo_y) * 0xC2B2AE3D27D4EB4F)
            ^ (int(bloco) * 0x165667B19E3779F9)
        ) & 0xFFFFFFFFFFFFFFFF
        return int(self._mix64(h) % 8)

    @staticmethod
    def _clamp_cor(valor: float) -> int:
        return int(max(0, min(255, round(valor))))

    def _tile_base_cacheado(self, tile_px: int, bloco: int, variante: int) -> pygame.Surface:
        chave = (int(tile_px), int(bloco), int(variante))
        cache = self._cache_tiles.get(chave)
        if cache is not None:
            return cache

        base = tuple(self.CoresBlocos.get(int(bloco), (255, 0, 255)))
        superficie = pygame.Surface((tile_px, tile_px), pygame.SRCALPHA)

        ganho = (int(variante) - 3.5) * 1.6
        r0 = self._clamp_cor(base[0] + ganho)
        g0 = self._clamp_cor(base[1] + ganho)
        b0 = self._clamp_cor(base[2] + ganho)

        for py in range(tile_px):
            t = (py + 0.5) / max(1.0, float(tile_px))
            grad = (0.94 + (0.12 * (1.0 - t)))
            for px in range(tile_px):
                n = (((px + 3) * 73856093) ^ ((py + 5) * 19349663) ^ ((int(variante) + 11) * 83492791)) & 0xFFFFFFFF
                ruido = ((n % 17) - 8) * 0.005
                fator = max(0.80, min(1.20, grad + ruido))
                cor = (
                    self._clamp_cor(r0 * fator),
                    self._clamp_cor(g0 * fator),
                    self._clamp_cor(b0 * fator),
                    255,
                )
                superficie.set_at((px, py), cor)

        resultado = superficie.convert_alpha()
        self._cache_tiles[chave] = resultado
        return resultado

    def obter_tile_base(self, mundo_x: int, mundo_y: int, bloco: int, tile_px: int) -> pygame.Surface:
        variante = self._variante_base(mundo_x, mundo_y, bloco)
        return self._tile_base_cacheado(tile_px=max(1, int(tile_px)), bloco=int(bloco), variante=variante)


class TilesTransicionais:
    GRUPOS_PADRAO = {
        "agua": frozenset({0, 1}),
        "campo": frozenset({2, 3}),
        "areia": frozenset({4, 5}),
        "neve": frozenset({6, 10, 11}),
        "magico": frozenset({7}),
        "vulcanico": frozenset({8, 9}),
    }

    def __init__(
        self,
        cores_blocos: Dict[int, Cor],
        callback_bloco_global: Callable[[int, int], Optional[int]],
        grupos_bioma: Optional[Dict[str, Iterable[int]]] = None,
        largura_borda_ratio: float = 0.46,
        alpha_borda: int = 205,
        alpha_canto: int = 235,
        forca_ruido: float = 0.11,
    ) -> None:
        self.CoresBlocos = {int(k): tuple(v) for k, v in (cores_blocos or {}).items()}
        self.CallbackBlocoGlobal = callback_bloco_global
        self.LarguraBordaRatio = max(0.18, min(0.60, float(largura_borda_ratio)))
        self.AlphaBorda = max(24, min(255, int(alpha_borda)))
        self.AlphaCanto = max(24, min(255, int(alpha_canto)))
        self.ForcaRuido = max(0.0, min(0.30, float(forca_ruido)))

        grupos = grupos_bioma or self.GRUPOS_PADRAO
        self.GruposBioma: Dict[str, frozenset[int]] = {
            str(nome): frozenset(int(v) for v in valores)
            for nome, valores in grupos.items()
        }

        self._cache_tiles: Dict[Tuple[int, int, Tuple[bool, bool, bool, bool, bool, bool, bool, bool]], pygame.Surface] = {}
        self._mapa_grupos_por_bloco: Dict[int, str] = {}
        self.SeedMundo = 0
        for nome, valores in self.GruposBioma.items():
            for bloco in valores:
                self._mapa_grupos_por_bloco[int(bloco)] = nome

    def definir_seed(self, seed_mundo: int) -> None:
        novo_seed = int(seed_mundo or 0)
        if novo_seed != self.SeedMundo:
            self.SeedMundo = novo_seed
            self.limpar_cache()

    def atualizar_cores(self, cores_blocos: Dict[int, Cor]) -> None:
        self.CoresBlocos = {int(k): tuple(v) for k, v in (cores_blocos or {}).items()}
        self.limpar_cache()

    def limpar_cache(self) -> None:
        self._cache_tiles.clear()

    @staticmethod
    def _mix64(valor: int) -> int:
        x = int(valor) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 30)
        x = (x * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 27)
        x = (x * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 31)
        return x & 0xFFFFFFFFFFFFFFFF

    def _grupo_recebe_transicao(self, mundo_x: int, mundo_y: int, dx: int, dy: int, grupo_central: str, grupo_vizinho: str) -> bool:
        ax, ay = int(mundo_x), int(mundo_y)
        bx, by = int(mundo_x + dx), int(mundo_y + dy)
        if (bx, by) < (ax, ay):
            ax, ay, bx, by = bx, by, ax, ay
        g1, g2 = sorted((str(grupo_central), str(grupo_vizinho)))
        g1_hash = sum((idx + 1) * ord(ch) for idx, ch in enumerate(g1))
        g2_hash = sum((idx + 1) * ord(ch) for idx, ch in enumerate(g2))
        h = (
            int(self.SeedMundo)
            ^ (ax * 0x9E3779B185EBCA87)
            ^ (ay * 0xC2B2AE3D27D4EB4F)
            ^ (bx * 0x165667B19E3779F9)
            ^ (by * 0x85EBCA77C2B2AE63)
            ^ (g1_hash & 0xFFFFFFFFFFFFFFFF)
            ^ ((g2_hash << 1) & 0xFFFFFFFFFFFFFFFF)
        ) & 0xFFFFFFFFFFFFFFFF
        bit = self._mix64(h) & 1
        return str(grupo_central) == (g1 if bit == 0 else g2)

    def _cor_bloco(self, bloco: int) -> Cor:
        return tuple(self.CoresBlocos.get(int(bloco), (255, 0, 255)))

    def _grupo(self, bloco: int | None) -> Optional[str]:
        if bloco is None:
            return None
        return self._mapa_grupos_por_bloco.get(int(bloco), f"bloco_{int(bloco)}")

    def _mesmo_grupo(self, bloco_a: int | None, bloco_b: int | None) -> bool:
        return self._grupo(bloco_a) == self._grupo(bloco_b)

    def _coletar_vizinhanca(self, mundo_x: int, mundo_y: int) -> Vizinhanca:
        coords = (
            (mundo_x - 1, mundo_y - 1), (mundo_x, mundo_y - 1), (mundo_x + 1, mundo_y - 1),
            (mundo_x - 1, mundo_y),     (mundo_x, mundo_y),     (mundo_x + 1, mundo_y),
            (mundo_x - 1, mundo_y + 1), (mundo_x, mundo_y + 1), (mundo_x + 1, mundo_y + 1),
        )
        valores = []
        for x, y in coords:
            bloco = self.CallbackBlocoGlobal(int(x), int(y))
            valores.append(None if bloco is None else int(bloco))
        return tuple(valores)  # type: ignore[return-value]

    def _escolher_bloco_dominante(self, mundo_x: int, mundo_y: int, bloco_central: int, vizinhanca: Vizinhanca) -> Optional[int]:
        # considerar só cardinais para escolher quem domina a borda;
        # diagonais servem só para arredondar canto depois
        pesos = {1: 1.0, 3: 1.0, 5: 1.0, 7: 1.0}
        offsets = {1: (0, -1), 3: (-1, 0), 5: (1, 0), 7: (0, 1)}

        grupo_central = self._grupo(bloco_central)
        if grupo_central is None:
            return None

        score_por_grupo: Dict[str, float] = {}
        bloco_representante: Dict[str, int] = {}

        for indice, bloco in enumerate(vizinhanca):
            if indice not in offsets or bloco is None:
                continue
            grupo = self._grupo(bloco)
            if grupo is None or grupo == grupo_central:
                continue

            dx, dy = offsets[indice]
            if not self._grupo_recebe_transicao(mundo_x, mundo_y, dx, dy, grupo_central, grupo):
                continue

            score_por_grupo[grupo] = score_por_grupo.get(grupo, 0.0) + pesos[indice]
            bloco_representante.setdefault(grupo, int(bloco))

        if not score_por_grupo:
            return None

        grupo_vencedor = sorted(score_por_grupo.items(), key=lambda item: (-item[1], item[0]))[0][0]
        return bloco_representante.get(grupo_vencedor)

    def _construir_overlay(self, tile_px: int, cor_overlay: Cor, flags: Dict[str, bool]) -> Optional[pygame.Surface]:
        if not any(flags.values()):
            return None
        largura = max(1.0, float(tile_px) * self.LarguraBordaRatio)
        raio = max(largura * 1.15, float(tile_px) * 0.36)
        alpha_lado = self.AlphaBorda / 255.0
        alpha_canto = self.AlphaCanto / 255.0
        superficie = pygame.Surface((tile_px, tile_px), pygame.SRCALPHA)

        for py in range(tile_px):
            v = (py + 0.5) / float(tile_px)
            for px in range(tile_px):
                u = (px + 0.5) / float(tile_px)
                influencia = 0.0
                if flags["n"]:
                    influencia = max(influencia, self._gradiente_lado(v * tile_px, largura) * alpha_lado)
                if flags["s"]:
                    influencia = max(influencia, self._gradiente_lado((1.0 - v) * tile_px, largura) * alpha_lado)
                if flags["w"]:
                    influencia = max(influencia, self._gradiente_lado(u * tile_px, largura) * alpha_lado)
                if flags["e"]:
                    influencia = max(influencia, self._gradiente_lado((1.0 - u) * tile_px, largura) * alpha_lado)
                if flags["nw"] or (flags["n"] and flags["w"]):
                    influencia = max(influencia, self._gradiente_canto(math.hypot(u * tile_px, v * tile_px), raio) * alpha_canto)
                if flags["ne"] or (flags["n"] and flags["e"]):
                    influencia = max(influencia, self._gradiente_canto(math.hypot((1.0 - u) * tile_px, v * tile_px), raio) * alpha_canto)
                if flags["sw"] or (flags["s"] and flags["w"]):
                    influencia = max(influencia, self._gradiente_canto(math.hypot(u * tile_px, (1.0 - v) * tile_px), raio) * alpha_canto)
                if flags["se"] or (flags["s"] and flags["e"]):
                    influencia = max(influencia, self._gradiente_canto(math.hypot((1.0 - u) * tile_px, (1.0 - v) * tile_px), raio) * alpha_canto)
                if influencia <= 0.0:
                    continue
                ruido = self._ruido_contextual(px, py, flags)
                influencia = max(0.0, min(1.0, influencia + ((ruido - 0.5) * self.ForcaRuido)))
                if influencia <= 0.0:
                    continue
                superficie.set_at((px, py), (*cor_overlay, int(max(0, min(255, round(influencia * 255.0))))))

        return superficie

    @staticmethod
    def _gradiente_lado(distancia_px: float, largura_px: float) -> float:
        if distancia_px >= largura_px:
            return 0.0
        t = 1.0 - (distancia_px / max(1e-6, largura_px))
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _gradiente_canto(distancia_px: float, raio_px: float) -> float:
        if distancia_px >= raio_px:
            return 0.0
        t = 1.0 - (distancia_px / max(1e-6, raio_px))
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _ruido_contextual(px: int, py: int, flags: Dict[str, bool]) -> float:
        s = 0
        for i, chave in enumerate(("n", "ne", "e", "se", "s", "sw", "w", "nw"), start=1):
            if flags.get(chave):
                s += i * 97
        valor = (px * 73856093) ^ (py * 19349663) ^ (s * 83492791)
        return ((valor & 0xFFFFFFFF) % 1000) / 999.0

    def renderizar_overlay_tile(self, mundo_x: int, mundo_y: int, bloco_central: int, tile_px: int) -> pygame.Surface:
        vizinhanca = self._coletar_vizinhanca(mundo_x, mundo_y)
        bloco_dominante = self._escolher_bloco_dominante(mundo_x, mundo_y, bloco_central, vizinhanca)

        flags = (False, False, False, False, False, False, False, False)

        if bloco_dominante is not None:
            grupo_central = self._grupo(bloco_central)
            grupo_dominante = self._grupo(bloco_dominante)

            n, ne, e, se, s, sw, w, nw = (
                vizinhanca[1], vizinhanca[2], vizinhanca[5], vizinhanca[8],
                vizinhanca[7], vizinhanca[6], vizinhanca[3], vizinhanca[0],
            )

            recebe_n = (
                grupo_central is not None and grupo_dominante is not None
                and self._mesmo_grupo(bloco_dominante, n)
                and self._grupo_recebe_transicao(mundo_x, mundo_y, 0, -1, grupo_central, grupo_dominante)
            )
            recebe_e = (
                grupo_central is not None and grupo_dominante is not None
                and self._mesmo_grupo(bloco_dominante, e)
                and self._grupo_recebe_transicao(mundo_x, mundo_y, 1, 0, grupo_central, grupo_dominante)
            )
            recebe_s = (
                grupo_central is not None and grupo_dominante is not None
                and self._mesmo_grupo(bloco_dominante, s)
                and self._grupo_recebe_transicao(mundo_x, mundo_y, 0, 1, grupo_central, grupo_dominante)
            )
            recebe_w = (
                grupo_central is not None and grupo_dominante is not None
                and self._mesmo_grupo(bloco_dominante, w)
                and self._grupo_recebe_transicao(mundo_x, mundo_y, -1, 0, grupo_central, grupo_dominante)
            )

            flags = (
                recebe_n,
                recebe_n and recebe_e and self._mesmo_grupo(bloco_dominante, ne),
                recebe_e,
                recebe_e and recebe_s and self._mesmo_grupo(bloco_dominante, se),
                recebe_s,
                recebe_s and recebe_w and self._mesmo_grupo(bloco_dominante, sw),
                recebe_w,
                recebe_w and recebe_n and self._mesmo_grupo(bloco_dominante, nw),
            )

        chave = (int(tile_px), int(bloco_dominante or -1), flags)
        cache = self._cache_tiles.get(chave)
        if cache is not None:
            return cache

        superficie = pygame.Surface((tile_px, tile_px), pygame.SRCALPHA)
        if bloco_dominante is not None:
            flags_dict = {
                "n": flags[0],
                "ne": flags[1],
                "e": flags[2],
                "se": flags[3],
                "s": flags[4],
                "sw": flags[5],
                "w": flags[6],
                "nw": flags[7],
            }
            overlay = self._construir_overlay(tile_px, self._cor_bloco(bloco_dominante), flags_dict)
            if overlay is not None:
                superficie.blit(overlay, (0, 0))

        resultado = superficie.convert_alpha()
        self._cache_tiles[chave] = resultado
        return resultado


class GerenciadorTiles:
    """Compositor de aparência base + transição de bordas entre grupos."""

    def __init__(self, cores_blocos: Dict[int, Cor], callback_bloco_global: Callable[[int, int], Optional[int]], **kwargs) -> None:
        self._base = AparenciaBaseTiles(cores_blocos=cores_blocos)
        self._transicoes = TilesTransicionais(cores_blocos=cores_blocos, callback_bloco_global=callback_bloco_global, **kwargs)

    def definir_seed(self, seed_mundo: int) -> None:
        self._base.definir_seed(seed_mundo)
        self._transicoes.definir_seed(seed_mundo)

    def atualizar_cores(self, cores_blocos: Dict[int, Cor]) -> None:
        self._base.atualizar_cores(cores_blocos)
        self._transicoes.atualizar_cores(cores_blocos)

    def limpar_cache(self) -> None:
        self._base.limpar_cache()
        self._transicoes.limpar_cache()

    def renderizar_chunk(self, chave_chunk: Tuple[int, int], grid: list[list[int]], tile_px: int, tamanho_chunk: int) -> Optional[pygame.Surface]:
        if not grid:
            return None
        largura_chunk = max((len(linha) for linha in grid), default=0)
        altura_chunk = len(grid)
        if largura_chunk <= 0 or altura_chunk <= 0:
            return None

        tile_px = max(1, int(tile_px))
        tamanho_chunk = max(1, int(tamanho_chunk))
        superficie = pygame.Surface((largura_chunk * tile_px, altura_chunk * tile_px), pygame.SRCALPHA)

        base_x = int(chave_chunk[0]) * tamanho_chunk
        base_y = int(chave_chunk[1]) * tamanho_chunk
        for by, linha in enumerate(grid):
            for bx, bloco in enumerate(linha):
                mundo_x = base_x + bx
                mundo_y = base_y + by
                bloco_int = int(bloco)
                superficie.blit(self._base.obter_tile_base(mundo_x, mundo_y, bloco_int, tile_px), (bx * tile_px, by * tile_px))
                overlay = self._transicoes.renderizar_overlay_tile(mundo_x, mundo_y, bloco_int, tile_px)
                superficie.blit(overlay, (bx * tile_px, by * tile_px))

        return superficie.convert_alpha()
