"""Módulo de colisão/interação genérico para entidades e estruturas."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple


Vector2 = Tuple[float, float]
RectData = Tuple[float, float, float, float]


@dataclass
class Colisor:
    """Componente de colisão/interação com raios separados.

    - raio_colisao: contato físico.
    - raio_interacao: detecção/ação em área.
    """

    x: float
    y: float
    raio_colisao: float
    raio_interacao: Optional[float] = None
    ativo: bool = True
    tipo_colisao: str = "circulo"
    semi_eixo_x: Optional[float] = None
    semi_eixo_y: Optional[float] = None
    campo_semi_eixo_x: Optional[float] = None
    campo_semi_eixo_y: Optional[float] = None

    def __post_init__(self) -> None:
        if self.raio_interacao is None:
            self.raio_interacao = self.raio_colisao
        self.raio_colisao = max(0.0, float(self.raio_colisao))
        self.raio_interacao = max(float(self.raio_colisao), float(self.raio_interacao))
        self.tipo_colisao = str(self.tipo_colisao or "circulo").strip().lower()
        if self.tipo_colisao not in {"circulo", "elipse"}:
            self.tipo_colisao = "circulo"
        if self.semi_eixo_x is None:
            self.semi_eixo_x = float(self.raio_colisao)
        if self.semi_eixo_y is None:
            self.semi_eixo_y = float(self.raio_colisao)
        self.semi_eixo_x = max(0.001, float(self.semi_eixo_x))
        self.semi_eixo_y = max(0.001, float(self.semi_eixo_y))
        if self.campo_semi_eixo_x is None:
            self.campo_semi_eixo_x = float(self.semi_eixo_x)
        if self.campo_semi_eixo_y is None:
            self.campo_semi_eixo_y = float(self.semi_eixo_y)
        self.campo_semi_eixo_x = max(float(self.semi_eixo_x), float(self.campo_semi_eixo_x))
        self.campo_semi_eixo_y = max(float(self.semi_eixo_y), float(self.campo_semi_eixo_y))

    @property
    def centro(self) -> Vector2:
        return (self.x, self.y)

    def mover_para(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)

    def deslocar(self, dx: float, dy: float) -> None:
        self.x += float(dx)
        self.y += float(dy)

    def distancia_para(self, outro: "Colisor") -> float:
        return math.hypot(self.x - outro.x, self.y - outro.y)

    def testa_com(self, outro: "Colisor") -> dict:
        """Retorna um dicionário com estado de colisão/interação."""
        if not self.ativo or not outro.ativo:
            return {
                "colidiu": False,
                "interagiu": False,
                "distancia": float("inf"),
                "profundidade_colisao": 0.0,
                "profundidade_interacao": 0.0,
                "direcao": (0.0, 0.0),
            }

        dx = outro.x - self.x
        dy = outro.y - self.y
        dist = math.hypot(dx, dy)
        direcao = (1.0, 0.0) if dist == 0 else (dx / dist, dy / dist)

        limite_colisao = self.raio_colisao + outro.raio_colisao
        limite_interacao = self.raio_interacao + outro.raio_interacao

        profundidade_colisao = max(0.0, limite_colisao - dist)
        profundidade_interacao = max(0.0, limite_interacao - dist)

        return {
            "colidiu": profundidade_colisao > 0,
            "interagiu": profundidade_interacao > 0,
            "distancia": dist,
            "profundidade_colisao": profundidade_colisao,
            "profundidade_interacao": profundidade_interacao,
            "direcao": direcao,
        }

    def resolver_empurrao(
        self,
        alvo: "Colisor",
        fator: float = 1.0,
        empurrar_ambos: bool = False,
    ) -> Vector2:
        """Resolve sobreposição física entre `self` e `alvo`."""
        info = self.testa_com(alvo)
        if not info["colidiu"]:
            return (0.0, 0.0)

        dx, dy = info["direcao"]
        correcao = info["profundidade_colisao"] * max(0.0, fator)

        if empurrar_ambos:
            meio = correcao * 0.5
            self.deslocar(-dx * meio, -dy * meio)
            alvo.deslocar(dx * meio, dy * meio)
            return (dx * meio, dy * meio)

        alvo.deslocar(dx * correcao, dy * correcao)
        return (dx * correcao, dy * correcao)

    def dentro_da_area(self, ponto: Vector2, usar_interacao: bool = True) -> bool:
        px, py = ponto
        if self.tipo_colisao == "elipse":
            ex = float(self.campo_semi_eixo_x if usar_interacao else self.semi_eixo_x)
            ey = float(self.campo_semi_eixo_y if usar_interacao else self.semi_eixo_y)
            return Colisor.ponto_em_elipse((float(px), float(py)), self.centro, ex, ey)
        raio = self.raio_interacao if usar_interacao else self.raio_colisao
        return math.hypot(px - self.x, py - self.y) <= raio

    @staticmethod
    def ponto_em_elipse(ponto: Vector2, centro: Vector2, semi_eixo_x: float, semi_eixo_y: float, margem: float = 0.0) -> bool:
        ex = max(0.001, float(semi_eixo_x) + max(0.0, float(margem)))
        ey = max(0.001, float(semi_eixo_y) + max(0.0, float(margem)))
        dx = float(ponto[0]) - float(centro[0])
        dy = float(ponto[1]) - float(centro[1])
        return ((dx * dx) / (ex * ex) + (dy * dy) / (ey * ey)) <= 1.0

    @staticmethod
    def circle_rect_collide(center: Vector2, raio: float, rect: RectData) -> bool:
        """Teste círculo-retângulo sem dependência de pygame."""
        cx, cy = center
        rx, ry, rw, rh = rect

        closest_x = min(max(cx, rx), rx + rw)
        closest_y = min(max(cy, ry), ry + rh)

        dx = cx - closest_x
        dy = cy - closest_y
        return (dx * dx + dy * dy) <= (raio * raio)

    @staticmethod
    def intersecao_segmento_circulo(
        origem: Vector2,
        destino: Vector2,
        centro: Vector2,
        raio: float,
    ) -> Optional[float]:
        """Retorna ``t`` (0..1) da primeira interseção do segmento com o círculo."""
        ox, oy = origem
        dx = destino[0] - ox
        dy = destino[1] - oy
        fx = ox - centro[0]
        fy = oy - centro[1]

        a = dx * dx + dy * dy
        if a <= 1e-10:
            return None

        b = 2.0 * (fx * dx + fy * dy)
        c = (fx * fx + fy * fy) - (raio * raio)
        delta = b * b - 4.0 * a * c
        if delta < 0.0:
            return None

        raiz = math.sqrt(delta)
        inv = 1.0 / (2.0 * a)
        t1 = (-b - raiz) * inv
        t2 = (-b + raiz) * inv
        candidatos = [t for t in (t1, t2) if 0.0 <= t <= 1.0]
        if not candidatos:
            return None
        return min(candidatos)

    @staticmethod
    def resolver_movimento_com_colisores(
        posicao_antes: Vector2,
        posicao_depois: Vector2,
        raio_entidade: float,
        colisores: list[tuple[int, float, float, float, str, float, float, dict | None]],
        dt: float,
    ) -> Vector2:
        """Resolve bloqueio por colisão e repulsão por campo para uma entidade móvel."""
        raio_entidade = max(0.0, float(raio_entidade))
        if raio_entidade <= 0.0:
            return (float(posicao_depois[0]), float(posicao_depois[1]))

        melhor_t = None
        for _, sx, sy, raio_obj, _, _, _, colisor_cfg in colisores:
            cfg = colisor_cfg if isinstance(colisor_cfg, dict) else {}
            tipo_cfg = str(cfg.get("tipo", "circulo")).strip().lower()
            if tipo_cfg == "elipse":
                ex = float(cfg.get("semi_eixo_x", raio_obj) or raio_obj)
                ey = float(cfg.get("semi_eixo_y", raio_obj) or raio_obj)
                t = Colisor.intersecao_segmento_circulo(
                    ((float(posicao_antes[0]) - float(sx)) / max(0.001, ex + raio_entidade), (float(posicao_antes[1]) - float(sy)) / max(0.001, ey + raio_entidade)),
                    ((float(posicao_depois[0]) - float(sx)) / max(0.001, ex + raio_entidade), (float(posicao_depois[1]) - float(sy)) / max(0.001, ey + raio_entidade)),
                    (0.0, 0.0),
                    1.0,
                )
            else:
                t = Colisor.intersecao_segmento_circulo(
                    posicao_antes,
                    posicao_depois,
                    (sx, sy),
                    raio_entidade + raio_obj,
                )
            if t is None:
                continue
            if melhor_t is None or t < melhor_t:
                melhor_t = t

        px, py = float(posicao_depois[0]), float(posicao_depois[1])
        if melhor_t is not None:
            dx = posicao_depois[0] - posicao_antes[0]
            dy = posicao_depois[1] - posicao_antes[1]
            t_seguro = max(0.0, melhor_t - 0.02)
            px = posicao_antes[0] + dx * t_seguro
            py = posicao_antes[1] + dy * t_seguro

        for _ in range(3):
            ajustou = False
            for _, sx, sy, raio_obj, _, _, _, colisor_cfg in colisores:
                cfg = colisor_cfg if isinstance(colisor_cfg, dict) else {}
                tipo_cfg = str(cfg.get("tipo", "circulo")).strip().lower()
                if tipo_cfg == "elipse":
                    ex = float(cfg.get("semi_eixo_x", raio_obj) or raio_obj)
                    ey = float(cfg.get("semi_eixo_y", raio_obj) or raio_obj)
                    if not Colisor.ponto_em_elipse((px, py), (sx, sy), ex, ey, margem=raio_entidade):
                        continue
                    vx = px - sx
                    vy = py - sy
                    dist = math.hypot(vx, vy)
                    if dist <= 1e-8:
                        vx, vy, dist = 1.0, 0.0, 1.0
                    nx = vx / dist
                    ny = vy / dist
                    px += nx * 0.08
                    py += ny * 0.08
                    ajustou = True
                else:
                    vx = px - sx
                    vy = py - sy
                    dist = math.hypot(vx, vy)
                    limite = raio_entidade + raio_obj
                    if dist >= limite or limite <= 0.0:
                        continue
                    if dist <= 1e-8:
                        vx, vy, dist = 1.0, 0.0, 1.0

                    nx = vx / dist
                    ny = vy / dist
                    sobreposicao = limite - dist
                    px += nx * (sobreposicao + 1e-4)
                    py += ny * (sobreposicao + 1e-4)
                    ajustou = True
            if not ajustou:
                break

        dt = max(0.0, float(dt))
        if dt > 0.0:
            for _, sx, sy, raio_obj, tipo_obj, campo, intensidade, colisor_cfg in colisores:
                if not tipo_obj.startswith("estrutura"):
                    continue
                cfg = colisor_cfg if isinstance(colisor_cfg, dict) else {}
                if str(cfg.get("tipo", "circulo")).strip().lower() == "elipse":
                    mvx, mvy = Colisor.aplicar_repulsao_eliptica(
                        posicao_entidade=(px, py),
                        movimento_entidade=(0.0, 0.0),
                        centro_estrutura=(sx, sy),
                        semi_eixo_x=float(cfg.get("campo_semi_eixo_x", cfg.get("semi_eixo_x", raio_obj)) or raio_obj),
                        semi_eixo_y=float(cfg.get("campo_semi_eixo_y", cfg.get("semi_eixo_y", raio_obj)) or raio_obj),
                        intensidade=intensidade,
                        delta_time=dt,
                        raio_entidade=raio_entidade,
                    )
                    px += mvx
                    py += mvy
                    continue
                mvx, mvy = Colisor.aplicar_repulsao_circular(
                    posicao_entidade=(px, py),
                    movimento_entidade=(0.0, 0.0),
                    centro_estrutura=(sx, sy),
                    raio_estrutura=raio_obj,
                    campo=campo,
                    intensidade=intensidade,
                    delta_time=dt,
                    raio_entidade=raio_entidade,
                )
                px += mvx
                py += mvy

        return (px, py)

    @staticmethod
    def aplicar_repulsao_circular(
        posicao_entidade: Vector2,
        movimento_entidade: Vector2,
        centro_estrutura: Vector2,
        raio_estrutura: float,
        campo: float,
        intensidade: float,
        delta_time: float,
        raio_entidade: float = 0.0,
    ) -> Vector2:
        """Aplica repulsão circular em movimento da entidade (unidades de mundo/frame)."""
        campo = max(0.0, float(campo))
        intensidade = max(0.0, float(intensidade))
        if campo <= 0.0 and intensidade <= 0.0:
            return (float(movimento_entidade[0]), float(movimento_entidade[1]))

        px, py = float(posicao_entidade[0]), float(posicao_entidade[1])
        mvx, mvy = float(movimento_entidade[0]), float(movimento_entidade[1])
        cx, cy = float(centro_estrutura[0]), float(centro_estrutura[1])
        limite = max(0.0, float(raio_estrutura)) + campo + max(0.0, float(raio_entidade))
        if limite <= 0.0:
            return (mvx, mvy)

        vx = px - cx
        vy = py - cy
        dist = math.hypot(vx, vy)
        if dist == 0.0:
            vx, vy, dist = 1.0, 0.0, 1.0
        if dist > limite:
            return (mvx, mvy)

        dirx = vx / dist
        diry = vy / dist
        t = max(0.0, min(1.0, 1.0 - (dist / max(limite, 1e-6))))

        towardx, towardy = -dirx, -diry
        comp_toward = mvx * towardx + mvy * towardy
        if comp_toward > 0.0:
            atenuacao = 0.7 * t
            mvx -= towardx * (comp_toward * atenuacao)
            mvy -= towardy * (comp_toward * atenuacao)

        push = intensidade * t * max(0.0, float(delta_time))
        mvx += dirx * push
        mvy += diry * push
        return (mvx, mvy)

    @staticmethod
    def aplicar_repulsao_eliptica(
        posicao_entidade: Vector2,
        movimento_entidade: Vector2,
        centro_estrutura: Vector2,
        semi_eixo_x: float,
        semi_eixo_y: float,
        intensidade: float,
        delta_time: float,
        raio_entidade: float = 0.0,
    ) -> Vector2:
        intensidade = max(0.0, float(intensidade))
        if intensidade <= 0.0:
            return (float(movimento_entidade[0]), float(movimento_entidade[1]))
        ex = max(0.001, float(semi_eixo_x) + max(0.0, float(raio_entidade)))
        ey = max(0.001, float(semi_eixo_y) + max(0.0, float(raio_entidade)))
        px, py = float(posicao_entidade[0]), float(posicao_entidade[1])
        cx, cy = float(centro_estrutura[0]), float(centro_estrutura[1])
        if not Colisor.ponto_em_elipse((px, py), (cx, cy), ex, ey):
            return (float(movimento_entidade[0]), float(movimento_entidade[1]))
        vx = px - cx
        vy = py - cy
        dist = math.hypot(vx, vy)
        if dist <= 1e-8:
            vx, vy, dist = 1.0, 0.0, 1.0
        nx = vx / dist
        ny = vy / dist
        push = intensidade * max(0.0, float(delta_time))
        return (float(movimento_entidade[0]) + nx * push, float(movimento_entidade[1]) + ny * push)
