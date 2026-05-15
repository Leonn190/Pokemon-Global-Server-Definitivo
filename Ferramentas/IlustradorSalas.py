from __future__ import annotations

"""
IlustradorSalas.py

Ferramenta offline para gerar imagens das salas de dungeon em:
    Recursos/Visual/Salas

Uso normal, a partir da raiz do projeto:
    python Ferramentas/IlustradorSalas.py

Comportamento padrão:
- lê os modelos de salas do catálogo oficial de dungeon em Dados/Catalogos/Dungeon.json;
- usa as funções reais do gerador de dungeon para converter armadilhas/configurações;
- desenha piso, água, buraco, portas, portal e armadilhas seguindo as mesmas regras/cores/sprites do jogo;
- NÃO sobrescreve imagem já existente, a menos que use --forcar.

Modos extras:
    python Ferramentas/IlustradorSalas.py --modo catalogo
    python Ferramentas/IlustradorSalas.py --modo dungeons
    python Ferramentas/IlustradorSalas.py --modo ambos
"""

import argparse
import csv
import math
import os
import random
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable


DIRECOES_VALIDAS = {"N", "S", "L", "O"}


def _descobrir_raiz_projeto() -> Path:
    """Encontra a raiz do projeto mesmo se o script for chamado de outra pasta."""
    arquivo = Path(__file__).resolve()
    candidatos = [arquivo.parent, *arquivo.parents, Path.cwd().resolve(), *Path.cwd().resolve().parents]
    vistos: set[Path] = set()
    for candidato in candidatos:
        if candidato in vistos:
            continue
        vistos.add(candidato)
        if (candidato / "Dados").exists() and (candidato / "Recursos").exists():
            return candidato
    return Path.cwd().resolve()


def _configurar_imports(raiz: Path) -> None:
    raiz_txt = str(raiz)
    if raiz_txt not in sys.path:
        sys.path.insert(0, raiz_txt)


def _preparar_pygame():
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    import pygame

    pygame.init()
    pygame.display.init()
    try:
        pygame.display.set_mode((1, 1), pygame.HIDDEN)
    except Exception:
        pygame.display.set_mode((1, 1))
    return pygame


def _slug(texto: str, fallback: str = "sala") -> str:
    bruto = unicodedata.normalize("NFKD", str(texto or ""))
    bruto = "".join(c for c in bruto if not unicodedata.combining(c))
    bruto = re.sub(r"[^a-zA-Z0-9]+", "_", bruto).strip("_").lower()
    return bruto or fallback


def _int_seguro(valor: Any, padrao: int = 0) -> int:
    try:
        return int(float(valor))
    except Exception:
        return int(padrao)


def _float_seguro(valor: Any, padrao: float = 0.0) -> float:
    try:
        return float(valor)
    except Exception:
        return float(padrao)


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(float(minimo), min(float(maximo), float(valor)))


def _cor_somar(cor: tuple[int, int, int], delta: int) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c) + int(delta))) for c in cor)  # type: ignore[return-value]


def _parse_direcoes(texto: str) -> list[str]:
    if str(texto or "").strip().lower() in {"", "nenhuma", "none", "0"}:
        return []
    saida: list[str] = []
    for parte in re.split(r"[,;/| ]+", str(texto or "")):
        direcao = parte.strip().upper()
        if direcao in DIRECOES_VALIDAS and direcao not in saida:
            saida.append(direcao)
    return saida


class IlustradorSalas:
    def __init__(self, pygame_mod, raiz: Path, tile_px: int = 24, tick_preview: int = 0, aplicar_claridade: bool = True) -> None:
        self.pygame = pygame_mod
        self.raiz = Path(raiz)
        self.tile_px = max(8, int(tile_px or 24))
        self.tick_preview = int(tick_preview or 0)
        self.aplicar_claridade = bool(aplicar_claridade)
        self._sprites: dict[str, Any] = {}
        self._tile_sprites: dict[int, Any] = {}

    # ------------------------------------------------------------------
    # Recursos
    # ------------------------------------------------------------------
    def _sprite(self, nome: str):
        chave = str(nome or "")
        if chave in self._sprites:
            return self._sprites[chave]
        caminho = self.raiz / "Recursos" / "Visual" / "Mundo" / "Outros" / chave
        try:
            sprite = self.pygame.image.load(str(caminho)).convert_alpha() if caminho.exists() else None
        except Exception:
            sprite = None
        self._sprites[chave] = sprite
        return sprite

    def _sprite_tile(self, tile_id: int):
        """Tenta usar sprite real de tile quando existir; senão cai no desenho procedural."""
        tile_id = int(tile_id)
        if tile_id in self._tile_sprites:
            return self._tile_sprites[tile_id]

        nomes = [
            f"{tile_id}.png",
            f"{tile_id}.webp",
            f"Tile {tile_id}.png",
            f"Tile_{tile_id}.png",
            f"tile_{tile_id}.png",
            f"tile{tile_id}.png",
        ]
        pastas = [
            self.raiz / "Recursos" / "Visual" / "Mundo" / "Tiles",
            self.raiz / "Recursos" / "Visual" / "Mundo" / "Terrenos",
            self.raiz / "Recursos" / "Visual" / "Tiles",
            self.raiz / "Recursos" / "Visual" / "Terrenos",
        ]
        sprite = None
        for pasta in pastas:
            if not pasta.exists():
                continue
            for nome in nomes:
                caminho = pasta / nome
                if not caminho.exists():
                    continue
                try:
                    sprite = self.pygame.image.load(str(caminho)).convert_alpha()
                    break
                except Exception:
                    sprite = None
            if sprite is not None:
                break
        self._tile_sprites[tile_id] = sprite
        return sprite

    # ------------------------------------------------------------------
    # Conversão de coordenadas
    # ------------------------------------------------------------------
    def _origem_sala_tiles(self, sala: dict, layout: dict) -> tuple[float, float, int, int]:
        pos = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else [0, 0]
        bloco_w = _int_seguro(layout.get("largura_bloco_sala_tiles", layout.get("tamanho_bloco_sala_tiles", 32)), 32)
        bloco_h = _int_seguro(layout.get("altura_bloco_sala_tiles", layout.get("tamanho_bloco_sala_tiles", 18)), 18)
        origem_x = float(_int_seguro(pos[0], 0) * bloco_w)
        origem_y = float(_int_seguro(pos[1], 0) * bloco_h)
        return origem_x, origem_y, bloco_w, bloco_h

    def _mundo_para_px(self, pos: Iterable[float], origem_x: float, origem_y: float) -> tuple[int, int]:
        vals = list(pos or [0.0, 0.0])[:2]
        while len(vals) < 2:
            vals.append(0.0)
        x = (float(vals[0]) - float(origem_x)) * self.tile_px
        y = (float(vals[1]) - float(origem_y)) * self.tile_px
        return int(round(x)), int(round(y))

    # ------------------------------------------------------------------
    # Tiles e base da sala
    # ------------------------------------------------------------------
    def _desenhar_tile(self, tela, rect, tile: int, lx: int, ly: int, layout: dict) -> None:
        pg = self.pygame
        tile = int(tile)
        tile_vazio = _int_seguro(layout.get("tile_vazio_dungeon", 9), 9)
        tile_chao = _int_seguro(layout.get("tile_chao_dungeon", 8), 8)
        tile_agua = _int_seguro(layout.get("tile_agua_funda", 0), 0)
        tile_agua_rasa = _int_seguro(layout.get("tile_agua_rasa", 1), 1)
        tile_buraco = _int_seguro(layout.get("tile_buraco", 10), 10)
        tile_quebradinho = _int_seguro(layout.get("tile_quebradinho", tile_chao), tile_chao)

        sprite = self._sprite_tile(tile)
        if sprite is not None:
            tela.blit(pg.transform.smoothscale(sprite, (rect.width, rect.height)), rect)
            return

        ruido = ((lx * 37 + ly * 19 + tile * 11) % 9) - 4
        if tile == tile_vazio:
            cor = _cor_somar((18, 18, 22), ruido)
            pg.draw.rect(tela, cor, rect)
            if self.tile_px >= 16:
                pg.draw.rect(tela, _cor_somar((10, 10, 13), ruido), rect, 1)
            return

        if tile == tile_agua:
            cor = _cor_somar((30, 83, 158), ruido)
            pg.draw.rect(tela, cor, rect)
            if (lx + ly) % 3 == 0:
                y = rect.top + max(2, rect.height // 3)
                pg.draw.line(tela, (86, 148, 218), (rect.left + 3, y), (rect.right - 3, y), max(1, self.tile_px // 18))
            return

        if tile == tile_agua_rasa:
            cor = _cor_somar((46, 119, 178), ruido)
            pg.draw.rect(tela, cor, rect)
            return

        if tile == tile_buraco:
            pg.draw.rect(tela, (3, 3, 6), rect)
            if self.tile_px >= 14:
                pg.draw.rect(tela, (22, 22, 28), rect.inflate(-2, -2), max(1, self.tile_px // 12))
            return

        cor_chao = _cor_somar((62, 63, 70), ruido)
        pg.draw.rect(tela, cor_chao, rect)
        if self.tile_px >= 14:
            pg.draw.rect(tela, _cor_somar((49, 50, 56), ruido), rect, 1)
            brilho = rect.inflate(-max(2, self.tile_px // 5), -max(2, self.tile_px // 5))
            if brilho.width > 2 and brilho.height > 2:
                pg.draw.rect(tela, _cor_somar((69, 70, 78), ruido // 2), brilho, 1)

        if tile == tile_quebradinho and tile_quebradinho != tile_chao:
            pg.draw.line(tela, (20, 20, 24), rect.midtop, rect.center, max(1, self.tile_px // 16))
            pg.draw.line(tela, (20, 20, 24), rect.center, rect.bottomright, max(1, self.tile_px // 16))
            pg.draw.line(tela, (20, 20, 24), rect.center, rect.midleft, max(1, self.tile_px // 16))

    def _desenhar_grid_sala(self, tela, sala: dict, layout: dict) -> None:
        origem_x, origem_y, bloco_w, bloco_h = self._origem_sala_tiles(sala, layout)
        grid = layout.get("grid_tiles") if isinstance(layout.get("grid_tiles"), list) else []
        tile_vazio = _int_seguro(layout.get("tile_vazio_dungeon", 9), 9)
        parede = max(1, _int_seguro(layout.get("parede_largura_tiles", 2), 2))
        tile_chao = _int_seguro(layout.get("tile_chao_dungeon", 8), 8)

        for ly in range(bloco_h):
            gy = int(origem_y) + ly
            for lx in range(bloco_w):
                gx = int(origem_x) + lx
                tile = tile_vazio
                if 0 <= gy < len(grid) and isinstance(grid[gy], list) and 0 <= gx < len(grid[gy]):
                    tile = _int_seguro(grid[gy][gx], tile_vazio)
                else:
                    if parede <= lx < bloco_w - parede and parede <= ly < bloco_h - parede:
                        tile = tile_chao
                rect = self.pygame.Rect(lx * self.tile_px, ly * self.tile_px, self.tile_px, self.tile_px)
                self._desenhar_tile(tela, rect, tile, lx, ly, layout)

        # Moldura leve da sala/corte. Não existe como objeto no mundo, mas ajuda a imagem exportada a não ficar solta.
        self.pygame.draw.rect(tela, (8, 8, 10), tela.get_rect(), max(1, self.tile_px // 16))

    # ------------------------------------------------------------------
    # Portas, portal e extras fixos
    # ------------------------------------------------------------------
    def _porta_rect_local(self, direcao: str, layout: dict) -> Any:
        pg = self.pygame
        bloco_w = _int_seguro(layout.get("largura_bloco_sala_tiles", layout.get("tamanho_bloco_sala_tiles", 32)), 32)
        bloco_h = _int_seguro(layout.get("altura_bloco_sala_tiles", layout.get("tamanho_bloco_sala_tiles", 18)), 18)
        porta_w = max(1, _int_seguro(layout.get("porta_largura_tiles", 4), 4))
        parede = max(1, _int_seguro(layout.get("parede_largura_tiles", 2), 2))
        direcao = str(direcao or "").upper()
        if direcao in {"N", "S"}:
            px = int(round((bloco_w - porta_w) * 0.5 * self.tile_px))
            py = 0 if direcao == "N" else int((bloco_h - parede) * self.tile_px)
            return pg.Rect(px, py, max(2, int(porta_w * self.tile_px)), max(2, int(parede * self.tile_px)))
        px = 0 if direcao == "O" else int((bloco_w - parede) * self.tile_px)
        py = int(round((bloco_h - porta_w) * 0.5 * self.tile_px))
        return pg.Rect(px, py, max(2, int(parede * self.tile_px)), max(2, int(porta_w * self.tile_px)))

    def _desenhar_portas(self, tela, sala: dict, layout: dict) -> None:
        pg = self.pygame
        for info in list(sala.get("portas_info") or []):
            if not isinstance(info, dict):
                continue
            direcao = str(info.get("direcao") or "").upper()
            if direcao not in DIRECOES_VALIDAS:
                continue
            rect = self._porta_rect_local(direcao, layout)
            if bool(info.get("trancada", False)):
                # Mesmo padrão de ConstrutorDungeon.renderizar_dungeon.
                pg.draw.rect(tela, (58, 52, 48), rect)
                pg.draw.rect(tela, (246, 196, 64), rect, max(1, int(self.tile_px * 0.06)))
            else:
                # A abertura real já vem do grid_tiles; isto só marca a soleira para a imagem ficar legível.
                pg.draw.rect(tela, (70, 70, 76), rect, max(1, self.tile_px // 18))

    def _desenhar_portais(self, tela, sala: dict, layout: dict) -> None:
        pg = self.pygame
        origem_x, origem_y, _, _ = self._origem_sala_tiles(sala, layout)
        sala_id = str(sala.get("id") or "")
        for entrada in list(layout.get("entradas") or []):
            if not isinstance(entrada, dict) or str(entrada.get("sala_id") or "") != sala_id:
                continue
            pos = entrada.get("saida") if isinstance(entrada.get("saida"), (list, tuple)) else entrada.get("saida_pos")
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            x, y = self._mundo_para_px(pos, origem_x, origem_y)
            raio = max(9, int(self.tile_px * 0.68))
            pg.draw.circle(tela, (8, 8, 8), (int(x), int(y)), raio)
            pg.draw.circle(tela, (70, 70, 70), (int(x), int(y)), raio, 2)

    # ------------------------------------------------------------------
    # Armadilhas - espelha Codigo/ModulosMundo/Geradores/Armadilhas.py
    # ------------------------------------------------------------------
    @staticmethod
    def _config(trap: dict) -> dict:
        return trap.get("config") if isinstance(trap.get("config"), dict) else {}

    def _desenhar_espeto(self, tela, pos, origem_x: float, origem_y: float, movel: bool = False, escala: float = 1.0) -> None:
        pg = self.pygame
        sprite = self._sprite("Espetos Movel.png" if movel else "Espetos.png")
        cx, cy = self._mundo_para_px(pos, origem_x, origem_y)
        lado = max(12, int(self.tile_px * float(escala or 1.0)))
        if sprite is not None:
            img = pg.transform.smoothscale(sprite, (lado, lado))
            tela.blit(img, img.get_rect(center=(int(cx), int(cy))))
            return
        cor = (190, 180, 210) if movel else (150, 150, 162)
        pts = [
            (int(cx), int(cy - lado * 0.45)),
            (int(cx - lado * 0.36), int(cy + lado * 0.32)),
            (int(cx + lado * 0.36), int(cy + lado * 0.32)),
        ]
        pg.draw.polygon(tela, cor, pts)
        pg.draw.polygon(tela, (44, 44, 52), pts, 2)

    def _desenhar_quebradinho(self, tela, pos, origem_x: float, origem_y: float, fase: str = "inteiro") -> None:
        pg = self.pygame
        cx, cy = self._mundo_para_px(pos, origem_x, origem_y)
        rect = pg.Rect(0, 0, max(6, int(self.tile_px * 0.86)), max(6, int(self.tile_px * 0.86)))
        rect.center = (int(cx), int(cy))
        cor = (0, 0, 0) if str(fase or "") == "buraco" else (64, 64, 70)
        pg.draw.rect(tela, cor, rect, border_radius=max(1, self.tile_px // 18))
        if str(fase or "") != "buraco":
            pg.draw.line(tela, (20, 20, 24), rect.midtop, rect.center, 2)
            pg.draw.line(tela, (20, 20, 24), rect.center, rect.bottomright, 2)
            pg.draw.line(tela, (20, 20, 24), rect.center, rect.midleft, 2)

    def _bolas_barra_fogo(self, trap: dict) -> list[list[float]]:
        cfg = self._config(trap)
        centro = trap.get("posicao") if isinstance(trap.get("posicao"), (list, tuple)) else [0.0, 0.0]
        bolas = max(1, _int_seguro(cfg.get("bolas", cfg.get("numero_bolas", 4)), 4))
        barras = max(1, _int_seguro(cfg.get("barras", cfg.get("numero_cabos", 1)), 1))
        vel = _float_seguro(cfg.get("velocidade_giro", 1.1), 1.1)
        comp = _float_seguro(cfg.get("comprimento", 2.0), 2.0)
        ang_base = (float(self.tick_preview) / 30.0) * vel
        out: list[list[float]] = []
        for barra in range(barras):
            offset = (math.tau / barras) * barra
            for i in range(1, bolas + 1):
                r = comp * (i / bolas)
                ang = ang_base + offset
                out.append([float(centro[0]) + math.cos(ang) * r, float(centro[1]) + math.sin(ang) * r])
        return out

    def _desenhar_barra_fogo(self, tela, trap: dict, origem_x: float, origem_y: float) -> None:
        pg = self.pygame
        pos = trap.get("posicao", [0, 0])
        cx, cy = self._mundo_para_px(pos, origem_x, origem_y)
        rect = pg.Rect(0, 0, int(self.tile_px), int(self.tile_px))
        rect.center = (int(cx), int(cy))
        pg.draw.rect(tela, (48, 42, 42), rect)
        pg.draw.rect(tela, (190, 190, 170), rect, max(2, int(self.tile_px * 0.05)))
        pg.draw.circle(tela, (95, 82, 72), rect.center, max(4, int(self.tile_px * 0.20)))

        raio_bola = max(6, int(self.tile_px * _float_seguro(self._config(trap).get("raio_bola", 0.34), 0.34)))
        for bola in self._bolas_barra_fogo(trap):
            bx, by = self._mundo_para_px(bola, origem_x, origem_y)
            pg.draw.circle(tela, (255, 92, 24), (int(bx), int(by)), raio_bola)
            pg.draw.circle(tela, (255, 220, 74), (int(bx), int(by)), max(3, int(raio_bola * 0.55)))
            pg.draw.circle(tela, (255, 245, 174), (int(bx - raio_bola * 0.18), int(by - raio_bola * 0.18)), max(2, int(raio_bola * 0.22)))

    def _desenhar_torreta(self, tela, pos, origem_x: float, origem_y: float) -> None:
        pg = self.pygame
        cx, cy = self._mundo_para_px(pos, origem_x, origem_y)
        rect = pg.Rect(0, 0, int(self.tile_px), int(self.tile_px))
        rect.center = (int(cx), int(cy))
        pg.draw.rect(tela, (52, 58, 66), rect)
        pg.draw.rect(tela, (180, 190, 205), rect, max(2, int(self.tile_px * 0.05)))
        pg.draw.circle(tela, (25, 28, 34), rect.center, max(5, int(self.tile_px * 0.22)))

    def _desenhar_armadilhas(self, tela, sala: dict, layout: dict) -> None:
        origem_x, origem_y, _, _ = self._origem_sala_tiles(sala, layout)
        cfg_sala = sala.get("config") if isinstance(sala.get("config"), dict) else {}
        for trap in list(cfg_sala.get("armadilhas") or []):
            if not isinstance(trap, dict):
                continue
            tipo = str(trap.get("tipo") or "")
            pos = trap.get("posicao", [0.0, 0.0])
            cfg = self._config(trap)
            if tipo == "espeto":
                self._desenhar_espeto(tela, pos, origem_x, origem_y, movel=False, escala=_float_seguro(cfg.get("escala", 1.0), 1.0))
            elif tipo in {"espeto_movel", "espeto_ricochete"}:
                self._desenhar_espeto(tela, pos, origem_x, origem_y, movel=True, escala=_float_seguro(cfg.get("escala", 1.0), 1.0))
            elif tipo == "quebradinho":
                self._desenhar_quebradinho(tela, pos, origem_x, origem_y, fase="inteiro")
            elif tipo == "barra_fogo":
                self._desenhar_barra_fogo(tela, trap, origem_x, origem_y)
            elif tipo == "torreta":
                self._desenhar_torreta(tela, pos, origem_x, origem_y)

    # ------------------------------------------------------------------
    # Render público
    # ------------------------------------------------------------------
    def renderizar_sala(self, sala: dict, layout: dict):
        origem_x, origem_y, bloco_w, bloco_h = self._origem_sala_tiles(sala, layout)
        _ = (origem_x, origem_y)
        tela = self.pygame.Surface((bloco_w * self.tile_px, bloco_h * self.tile_px), self.pygame.SRCALPHA)
        self._desenhar_grid_sala(tela, sala, layout)
        self._desenhar_portas(tela, sala, layout)
        self._desenhar_portais(tela, sala, layout)
        self._desenhar_armadilhas(tela, sala, layout)

        if self.aplicar_claridade:
            cfg = sala.get("config") if isinstance(sala.get("config"), dict) else {}
            claridade = _clamp(_float_seguro(cfg.get("claridade", 10), 10), 0, 10)
            alpha = int(round((10.0 - claridade) * 10.0))
            if alpha > 0:
                sombra = self.pygame.Surface(tela.get_size(), self.pygame.SRCALPHA)
                sombra.fill((0, 0, 0, max(0, min(105, alpha))))
                tela.blit(sombra, (0, 0))
        return tela

    def salvar_sala(self, sala: dict, layout: dict, destino: Path, forcar: bool = False) -> str:
        if destino.exists() and not forcar:
            return "pulada"
        destino.parent.mkdir(parents=True, exist_ok=True)
        imagem = self.renderizar_sala(sala, layout)
        self.pygame.image.save(imagem, str(destino))
        return "gerada"


def _carregar_gerador_dungeons():
    from Servidor.Gerais.Geradores import GeradorDungeons as GD

    return GD


def _intervalo_modelo(modelo: dict, chave: str, padrao_min: float, padrao_max: float) -> tuple[float, float]:
    item = modelo.get(chave) if isinstance(modelo.get(chave), dict) else {}
    mn = _float_seguro(item.get("min", padrao_min), padrao_min)
    mx = _float_seguro(item.get("max", padrao_max), padrao_max)
    if mx < mn:
        mn, mx = mx, mn
    return mn, mx


def _montar_layout_modelo(GD, catalogo: dict, modelo: dict, fator: float, portas_modelo: list[str]) -> dict:
    pos = (0, 0)
    modelo_id = str(modelo.get("modelo_id") or modelo.get("id") or "sala")
    sala = GD._criar_sala(
        pos,
        catalogo,
        str(modelo.get("tipo") or "servos"),
        f"modelo_{_slug(modelo_id)}",
        _int_seguro(modelo.get("id", 0), 0),
        nome=str(modelo.get("nome") or modelo_id),
        modelo=modelo,
    )

    sala["portas"] = list(portas_modelo)
    sala["portas_bloqueadas"] = []
    sala["portas_info"] = [
        {"id": f"porta_modelo_{direcao}", "direcao": direcao, "destino_sala_id": "", "trancada": False}
        for direcao in portas_modelo
    ]

    cfg = sala.setdefault("config", GD._config_sala_vazia())
    cfg.update({"servos": [], "armadilhas": [], "piscina": None, "buracao": None, "inundada": None})

    tipo_publico = str(sala.get("tipo") or "")
    if tipo_publico == "entrada":
        cfg["claridade"] = 10
    elif tipo_publico == "boss":
        mn, mx = _intervalo_modelo(modelo, "claridade", 8, 10)
        cfg["claridade"] = int(round(mx))
    else:
        mn, mx = _intervalo_modelo(modelo, "claridade", 10, 10)
        cfg["claridade"] = int(round(mx + (mn - mx) * _clamp(fator, 0.0, 1.0)))
        cfg["armadilhas"] = GD._converter_armadilhas_modelo(sala, modelo, _clamp(fator, 0.0, 1.0))

    GD._aplicar_especial_modelo(sala, modelo)

    regras = getattr(GD, "_REGRAS", {}) if isinstance(getattr(GD, "_REGRAS", {}), dict) else {}
    bloco_w = _int_seguro(getattr(GD, "LARGURA_BLOCO_SALA_TILES", regras.get("largura_bloco_sala_tiles", 32)), 32)
    bloco_h = _int_seguro(getattr(GD, "ALTURA_BLOCO_SALA_TILES", regras.get("altura_bloco_sala_tiles", 18)), 18)
    bloco = _int_seguro(getattr(GD, "TAMANHO_BLOCO_SALA_TILES", regras.get("tamanho_bloco_sala_tiles", 32)), 32)

    ocupadas = {pos: sala}
    grid = GD._grid_tiles(ocupadas, 1, 1)
    entradas = []
    conteudo_especial = modelo.get("conteudo_especial") if isinstance(modelo.get("conteudo_especial"), dict) else {}
    if tipo_publico == "entrada" or bool(conteudo_especial.get("portal", False)):
        centro = [bloco_w / 2.0, bloco_h / 2.0]
        entradas.append({"porta_idx": 1, "sala_id": sala["id"], "posicao_sala": [0, 0], "spawn": centro, "saida": centro, "saida_pos": centro, "ativa": True, "pedra_id": 0})

    return {
        "dimensao": "Ilustracao_Modelo_Dungeon",
        "dungeon_code": "catalogo",
        "dungeon_nome": "Catalogo de Salas",
        "largura_blocos": 1,
        "altura_blocos": 1,
        "tamanho_bloco_sala_tiles": bloco,
        "largura_bloco_sala_tiles": bloco_w,
        "altura_bloco_sala_tiles": bloco_h,
        "porta_largura_tiles": _int_seguro(regras.get("porta_largura_tiles", 4), 4),
        "parede_largura_tiles": _int_seguro(regras.get("parede_largura_tiles", 2), 2),
        "tile_vazio_dungeon": _int_seguro(regras.get("tile_vazio_dungeon", 9), 9),
        "tile_chao_dungeon": _int_seguro(regras.get("tile_chao_dungeon", 8), 8),
        "tile_agua_funda": _int_seguro(regras.get("tile_agua_funda", 0), 0),
        "tile_agua_rasa": _int_seguro(regras.get("tile_agua_rasa", 1), 1),
        "tile_buraco": _int_seguro(regras.get("tile_buraco", 10), 10),
        "tile_quebradinho": _int_seguro(regras.get("tile_quebradinho", regras.get("tile_chao_dungeon", 8)), 8),
        "salas": [sala],
        "entradas": entradas,
        "grid_tiles": grid,
        "armadilhas": [{"sala_id": sala.get("id"), **trap} for trap in list(cfg.get("armadilhas") or []) if isinstance(trap, dict)],
    }


def _linhas_dungeons_csv(raiz: Path) -> list[dict[str, str]]:
    try:
        from Servidor.Gerais.LoaderTabelas import carregar_csv_dict

        linhas = carregar_csv_dict("Pokemon Global Server - Dungeons.csv")
        if isinstance(linhas, list) and linhas:
            return [dict(l) for l in linhas if isinstance(l, dict)]
    except Exception:
        pass

    caminho = raiz / "Dados" / "Tabelas" / "Pokemon Global Server - Dungeons.csv"
    if not caminho.exists():
        return []
    with caminho.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _entradas_da_linha(row: dict[str, Any]) -> list[dict[str, Any]]:
    qtd = max(1, _int_seguro(row.get("Entradas", 1), 1))
    return [
        {"porta_idx": i, "pedra_id": 0, "ativa": True, "porta_ativa": True, "estrutura_quebrada": True}
        for i in range(1, qtd + 1)
    ]


def gerar_imagens_catalogo(GD, ilustrador: IlustradorSalas, pasta_saida: Path, forcar: bool, fator_modelo: float, portas_modelo: list[str]) -> tuple[int, int]:
    catalogo = GD.carregar_catalogo_dungeons()
    modelos = [dict(s) for s in list(catalogo.get("salas") or []) if isinstance(s, dict)]
    geradas = 0
    puladas = 0
    for idx, modelo in enumerate(modelos, start=1):
        layout = _montar_layout_modelo(GD, catalogo, modelo, fator_modelo, portas_modelo)
        sala = layout["salas"][0]
        modelo_id = str(modelo.get("modelo_id") or sala.get("modelo_id") or sala.get("id") or idx)
        nome = str(modelo.get("nome") or sala.get("nome") or modelo_id)
        destino = pasta_saida / f"{_int_seguro(modelo.get('id', idx), idx):03d}_{_slug(modelo_id)}__{_slug(nome)}.png"
        status = ilustrador.salvar_sala(sala, layout, destino, forcar=forcar)
        geradas += 1 if status == "gerada" else 0
        puladas += 1 if status == "pulada" else 0
    return geradas, puladas


def gerar_imagens_dungeons(GD, ilustrador: IlustradorSalas, raiz: Path, pasta_saida: Path, forcar: bool, codigos: set[str] | None = None) -> tuple[int, int]:
    linhas = _linhas_dungeons_csv(raiz)
    geradas = 0
    puladas = 0
    for row in linhas:
        code = str(row.get("Code") or "").strip()
        if not code:
            continue
        if codigos and code.casefold() not in codigos:
            continue
        layout = GD.gerar_dungeon_layout(code, _entradas_da_linha(row))
        nome_dungeon = str(layout.get("dungeon_nome") or row.get("Nome") or code)
        for sala in list(layout.get("salas") or []):
            if not isinstance(sala, dict):
                continue
            sala_num = _int_seguro(sala.get("id_numerico", 0), 0)
            sala_id = str(sala.get("id") or f"sala_{sala_num}")
            modelo = str(sala.get("modelo_id") or sala.get("tipo") or "sala")
            destino = pasta_saida / f"dungeon_{_slug(code)}_{_slug(nome_dungeon)}__{sala_num:03d}_{_slug(modelo)}_{_slug(sala_id)}.png"
            status = ilustrador.salvar_sala(sala, layout, destino, forcar=forcar)
            geradas += 1 if status == "gerada" else 0
            puladas += 1 if status == "pulada" else 0
    return geradas, puladas


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera imagens fiéis das salas de dungeon em Recursos/Visual/Salas.")
    parser.add_argument("--modo", choices=["catalogo", "dungeons", "ambos"], default="catalogo", help="catalogo gera 1 imagem por modelo de sala; dungeons gera as salas materializadas das dungeons do CSV.")
    parser.add_argument("--saida", default="Recursos/Visual/Salas", help="Pasta de saída relativa à raiz do projeto.")
    parser.add_argument("--tile-px", type=int, default=24, help="Tamanho de cada tile em pixels na imagem final.")
    parser.add_argument("--tick", type=int, default=0, help="Tick usado para posicionar bolas de barra_fogo no preview estático.")
    parser.add_argument("--fator-modelo", type=float, default=0.70, help="Fator 0..1 usado para ilustrar variações de dificuldade dos modelos do catálogo.")
    parser.add_argument("--portas-modelo", default="N,S,L,O", help="Portas abertas exibidas nas imagens de modelos do catálogo. Use 'nenhuma' para sala fechada.")
    parser.add_argument("--codigo", action="append", default=[], help="No modo dungeons, limita a um Code específico. Pode repetir.")
    parser.add_argument("--forcar", action="store_true", help="Sobrescreve imagens já existentes.")
    parser.add_argument("--sem-claridade", action="store_true", help="Não aplica escurecimento por claridade da sala.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = criar_parser().parse_args(argv)
    raiz = _descobrir_raiz_projeto()
    _configurar_imports(raiz)
    pygame = _preparar_pygame()

    try:
        GD = _carregar_gerador_dungeons()
    except Exception as exc:
        print("[IlustradorSalas] Falha ao importar o gerador oficial de dungeons.")
        print(f"[IlustradorSalas] Raiz detectada: {raiz}")
        print(f"[IlustradorSalas] Erro: {exc}")
        return 1

    pasta_saida = Path(args.saida)
    if not pasta_saida.is_absolute():
        pasta_saida = raiz / pasta_saida
    pasta_saida.mkdir(parents=True, exist_ok=True)

    ilustrador = IlustradorSalas(
        pygame,
        raiz=raiz,
        tile_px=int(args.tile_px),
        tick_preview=int(args.tick),
        aplicar_claridade=not bool(args.sem_claridade),
    )

    total_geradas = 0
    total_puladas = 0
    portas_modelo = _parse_direcoes(args.portas_modelo)

    if args.modo in {"catalogo", "ambos"}:
        geradas, puladas = gerar_imagens_catalogo(
            GD,
            ilustrador,
            pasta_saida,
            forcar=bool(args.forcar),
            fator_modelo=_clamp(float(args.fator_modelo), 0.0, 1.0),
            portas_modelo=portas_modelo,
        )
        total_geradas += geradas
        total_puladas += puladas
        print(f"[IlustradorSalas] Catalogo: {geradas} geradas, {puladas} puladas.")

    if args.modo in {"dungeons", "ambos"}:
        codigos = {str(c).strip().casefold() for c in list(args.codigo or []) if str(c).strip()}
        geradas, puladas = gerar_imagens_dungeons(
            GD,
            ilustrador,
            raiz,
            pasta_saida,
            forcar=bool(args.forcar),
            codigos=codigos or None,
        )
        total_geradas += geradas
        total_puladas += puladas
        print(f"[IlustradorSalas] Dungeons: {geradas} geradas, {puladas} puladas.")

    print(f"[IlustradorSalas] Saida: {pasta_saida}")
    print(f"[IlustradorSalas] Total: {total_geradas} geradas, {total_puladas} puladas.")
    try:
        pygame.quit()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
