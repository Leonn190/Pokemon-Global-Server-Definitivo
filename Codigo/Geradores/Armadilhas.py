from __future__ import annotations

from pathlib import Path
import math

import pygame


class ArmadilhaVisual:
    def __init__(self, trap_id: str, tipo: str, posicao) -> None:
        self.id = str(trap_id or "")
        self.tipo = str(tipo or "")
        self.posicao = [float(posicao[0]), float(posicao[1])]
        self.alvo = [float(posicao[0]), float(posicao[1])]
        self.bolas: dict[str, list[float]] = {}
        self.projeteis: dict[str, list[float]] = {}

    def definir_alvo(self, posicao) -> None:
        self.alvo = [float(posicao[0]), float(posicao[1])]

    def atualizar(self, dt: float) -> None:
        k = min(1.0, max(0.0, float(dt)) * 18.0)
        self.posicao[0] += (self.alvo[0] - self.posicao[0]) * k
        self.posicao[1] += (self.alvo[1] - self.posicao[1]) * k

    @staticmethod
    def _suavizar_pontos(cache: dict[str, list[float]], pontos: list, dt: float, prefixo: str) -> list[list[float]]:
        vivos = set()
        k = min(1.0, max(0.0, float(dt)) * 20.0)
        out = []
        for idx, ponto in enumerate(pontos):
            if not isinstance(ponto, (list, tuple)) or len(ponto) != 2:
                continue
            pid = f"{prefixo}_{idx}"
            vivos.add(pid)
            alvo = [float(ponto[0]), float(ponto[1])]
            atual = cache.setdefault(pid, list(alvo))
            atual[0] += (alvo[0] - atual[0]) * k
            atual[1] += (alvo[1] - atual[1]) * k
            out.append([float(atual[0]), float(atual[1])])
        for pid in list(cache.keys()):
            if pid not in vivos:
                cache.pop(pid, None)
        return out


class ArmadilhasDungeon:
    def __init__(self) -> None:
        self._visuais: dict[str, ArmadilhaVisual] = {}
        self._sprites: dict[str, pygame.Surface | None] = {}
        self._bolas_suavizadas: dict[str, list[list[float]]] = {}
        self._projeteis_suavizados: dict[str, list[list[float]]] = {}

    def _sprite(self, nome: str):
        chave = str(nome or "")
        if chave in self._sprites:
            return self._sprites[chave]
        caminho = Path("Recursos") / "Visual" / "Mundo" / "Outros" / chave
        try:
            surf = pygame.image.load(str(caminho)).convert_alpha()
        except Exception:
            surf = None
        self._sprites[chave] = surf
        return surf

    @staticmethod
    def _mundo_para_tela(camera, pos):
        return camera.mundo_para_tela_px((float(pos[0]), float(pos[1])))

    @staticmethod
    def _config(trap: dict) -> dict:
        return trap.get("config") if isinstance(trap.get("config"), dict) else {}

    def _iter_traps(self, layout: dict):
        for sala in layout.get("salas", []) if isinstance(layout, dict) else []:
            if not isinstance(sala, dict):
                continue
            cfg = sala.get("config") if isinstance(sala.get("config"), dict) else {}
            for trap in list(cfg.get("armadilhas") or []):
                if isinstance(trap, dict):
                    yield trap

    def atualizar(self, layout: dict, dt: float) -> None:
        if not isinstance(layout, dict):
            self._visuais.clear()
            return
        estado_armadilhas = layout.get("estado_armadilhas") if isinstance(layout.get("estado_armadilhas"), dict) else {}
        traps_estado = estado_armadilhas.get("traps") if isinstance(estado_armadilhas.get("traps"), dict) else {}
        vistos = set()
        for trap in self._iter_traps(layout):
            tid = str(trap.get("id") or "")
            if not tid:
                continue
            vistos.add(tid)
            tipo = str(trap.get("tipo") or "")
            estado = traps_estado.get(tid) if isinstance(traps_estado.get(tid), dict) else {}
            pos_base = estado.get("posicao") if isinstance(estado.get("posicao"), (list, tuple)) else trap.get("posicao", [0.0, 0.0])
            visual = self._visuais.get(tid)
            if visual is None:
                visual = ArmadilhaVisual(tid, tipo, pos_base)
                self._visuais[tid] = visual
            visual.tipo = tipo
            visual.definir_alvo(pos_base)
            visual.atualizar(dt)
            if tipo == "barra_fogo":
                self._bolas_suavizadas[tid] = visual._suavizar_pontos(visual.bolas, list(estado.get("bolas_posicoes") or []), dt, "bola")
            elif tipo == "torreta":
                pontos = [
                    proj.get("posicao")
                    for proj in list(estado.get("projeteis") or [])
                    if isinstance(proj, dict) and isinstance(proj.get("posicao"), (list, tuple))
                ]
                self._projeteis_suavizados[tid] = visual._suavizar_pontos(visual.projeteis, pontos, dt, "tiro")
        for tid in list(self._visuais.keys()):
            if tid not in vistos:
                self._visuais.pop(tid, None)
                self._bolas_suavizadas.pop(tid, None)
                self._projeteis_suavizados.pop(tid, None)

    def renderizar(self, tela, camera, layout: dict) -> None:
        if not isinstance(layout, dict):
            return
        estado_armadilhas = layout.get("estado_armadilhas") if isinstance(layout.get("estado_armadilhas"), dict) else {}
        traps_estado = estado_armadilhas.get("traps") if isinstance(estado_armadilhas.get("traps"), dict) else {}
        for trap in self._iter_traps(layout):
            tid = str(trap.get("id") or "")
            tipo = str(trap.get("tipo") or "")
            estado = traps_estado.get(tid) if isinstance(traps_estado.get(tid), dict) else {}
            visual = self._visuais.get(tid)
            pos = visual.posicao if visual is not None else trap.get("posicao", [0.0, 0.0])
            if tipo == "espeto":
                self._desenhar_espeto(tela, camera, pos, movel=False, escala=float(self._config(trap).get("escala", 1.0) or 1.0))
            elif tipo == "espeto_movel":
                self._desenhar_espeto(tela, camera, pos, movel=True, escala=float(self._config(trap).get("escala", 1.0) or 1.0))
            elif tipo == "quebradinho":
                self._desenhar_quebradinho(tela, camera, trap.get("posicao", [0, 0]), fase=str(estado.get("fase") or "inteiro"))
            elif tipo == "barra_fogo":
                self._desenhar_barra_fogo(tela, camera, trap, pos, self._bolas_suavizadas.get(tid, list(estado.get("bolas_posicoes") or [])))
            elif tipo == "torreta":
                self._desenhar_torreta(tela, camera, pos, self._projeteis_suavizados.get(tid, []))

    def _desenhar_espeto(self, tela, camera, pos, movel=False, escala=1.0):
        sprite = self._sprite("Espetos Movel.png" if movel else "Espetos.png")
        cx, cy = self._mundo_para_tela(camera, pos)
        tile = float(getattr(camera, "TilePx", 50) or 50)
        lado = max(12, int(tile * float(escala)))
        if sprite is not None:
            img = pygame.transform.smoothscale(sprite, (lado, lado))
            tela.blit(img, img.get_rect(center=(int(cx), int(cy))))
            return
        cor = (150, 150, 162) if not movel else (190, 180, 210)
        pts = [(int(cx), int(cy - lado * 0.45)), (int(cx - lado * 0.36), int(cy + lado * 0.32)), (int(cx + lado * 0.36), int(cy + lado * 0.32))]
        pygame.draw.polygon(tela, cor, pts)
        pygame.draw.polygon(tela, (44, 44, 52), pts, 2)

    def _desenhar_quebradinho(self, tela, camera, pos, fase="inteiro"):
        cx, cy = self._mundo_para_tela(camera, pos)
        tile = int(getattr(camera, "TilePx", 50) or 50)
        rect = pygame.Rect(0, 0, max(6, int(tile * 0.86)), max(6, int(tile * 0.86)))
        rect.center = (int(cx), int(cy))
        cor = (64, 64, 70) if fase != "buraco" else (0, 0, 0)
        pygame.draw.rect(tela, cor, rect, border_radius=max(1, tile // 18))
        if fase != "buraco":
            pygame.draw.line(tela, (20, 20, 24), rect.midtop, rect.center, 2)
            pygame.draw.line(tela, (20, 20, 24), rect.center, rect.bottomright, 2)
            pygame.draw.line(tela, (20, 20, 24), rect.center, rect.midleft, 2)

    def _desenhar_barra_fogo(self, tela, camera, trap, pos, bolas):
        cx, cy = self._mundo_para_tela(camera, pos)
        tile = float(getattr(camera, "TilePx", 50) or 50)
        rect = pygame.Rect(0, 0, int(tile), int(tile))
        rect.center = (int(cx), int(cy))
        pygame.draw.rect(tela, (48, 42, 42), rect)
        pygame.draw.rect(tela, (190, 190, 170), rect, max(2, int(tile * 0.05)))
        pygame.draw.circle(tela, (95, 82, 72), rect.center, max(4, int(tile * 0.20)))
        raio_bola = max(6, int(tile * float(self._config(trap).get("raio_bola", 0.34) or 0.34)))
        for bola in list(bolas or []):
            bx, by = self._mundo_para_tela(camera, bola)
            pygame.draw.circle(tela, (255, 92, 24), (int(bx), int(by)), raio_bola)
            pygame.draw.circle(tela, (255, 220, 74), (int(bx), int(by)), max(3, int(raio_bola * 0.55)))
            pygame.draw.circle(tela, (255, 245, 174), (int(bx - raio_bola * 0.18), int(by - raio_bola * 0.18)), max(2, int(raio_bola * 0.22)))

    def _desenhar_torreta(self, tela, camera, pos, projeteis):
        cx, cy = self._mundo_para_tela(camera, pos)
        tile = float(getattr(camera, "TilePx", 50) or 50)
        rect = pygame.Rect(0, 0, int(tile), int(tile))
        rect.center = (int(cx), int(cy))
        pygame.draw.rect(tela, (52, 58, 66), rect)
        pygame.draw.rect(tela, (180, 190, 205), rect, max(2, int(tile * 0.05)))
        pygame.draw.circle(tela, (25, 28, 34), rect.center, max(5, int(tile * 0.22)))
        for p in list(projeteis or []):
            px, py = self._mundo_para_tela(camera, p)
            r = max(5, int(tile * 0.18))
            pygame.draw.circle(tela, (255, 114, 46), (int(px), int(py)), r)
            pygame.draw.circle(tela, (255, 230, 120), (int(px), int(py)), max(2, r // 2))
