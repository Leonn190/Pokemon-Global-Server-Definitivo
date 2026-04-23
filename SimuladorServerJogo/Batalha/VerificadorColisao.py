from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

Vec2 = Tuple[float, float]
EPSILON = 1e-6


@dataclass
class ImpactoColisao:
    t: float
    ponto: Vec2
    normal: Vec2
    tipo: str
    alvo_id: str = ""
    alvo_tipo: str = ""


def distancia(a: Vec2, b: Vec2) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def normalizar(v: Vec2) -> Vec2:
    mag = math.hypot(float(v[0]), float(v[1]))
    if mag <= EPSILON:
        return (1.0, 0.0)
    return (float(v[0]) / mag, float(v[1]) / mag)


def refletir_vetor(direcao: Vec2, normal: Vec2) -> Vec2:
    d = normalizar(direcao)
    n = normalizar(normal)
    dot = (d[0] * n[0]) + (d[1] * n[1])
    return normalizar((d[0] - (2.0 * dot * n[0]), d[1] - (2.0 * dot * n[1])))


def colide_circulo_circulo(pos_a: Vec2, raio_a: float, pos_b: Vec2, raio_b: float) -> bool:
    return distancia(pos_a, pos_b) <= (float(raio_a) + float(raio_b))


def intersecao_segmento_circulo(inicio: Vec2, fim: Vec2, centro: Vec2, raio: float) -> ImpactoColisao | None:
    dx = float(fim[0] - inicio[0])
    dy = float(fim[1] - inicio[1])
    fx = float(inicio[0] - centro[0])
    fy = float(inicio[1] - centro[1])

    a = (dx * dx) + (dy * dy)
    if a <= EPSILON:
        if distancia(inicio, centro) <= float(raio):
            return ImpactoColisao(0.0, inicio, normalizar((inicio[0] - centro[0], inicio[1] - centro[1])), "pokemon")
        return None

    b = 2.0 * ((fx * dx) + (fy * dy))
    c = (fx * fx) + (fy * fy) - (float(raio) * float(raio))
    disc = (b * b) - (4.0 * a * c)
    if disc < 0.0:
        return None

    raiz = math.sqrt(max(0.0, disc))
    ts = [(-b - raiz) / (2.0 * a), (-b + raiz) / (2.0 * a)]
    for t in sorted(ts):
        if t < -EPSILON or t > 1.0 + EPSILON:
            continue
        t_clamped = max(0.0, min(1.0, t))
        ponto = (inicio[0] + (dx * t_clamped), inicio[1] + (dy * t_clamped))
        return ImpactoColisao(t_clamped, ponto, normalizar((ponto[0] - centro[0], ponto[1] - centro[1])), "pokemon")
    return None


def normal_parede(impacto: Vec2, limites: Tuple[float, float, float, float], raio: float) -> Vec2:
    x0, y0, x1, y1 = [float(v) for v in limites]
    x, y = float(impacto[0]), float(impacto[1])
    rx = float(raio)
    nx = 0.0
    ny = 0.0
    if x <= x0 + rx + EPSILON:
        nx += 1.0
    if x >= x1 - rx - EPSILON:
        nx -= 1.0
    if y <= y0 + rx + EPSILON:
        ny += 1.0
    if y >= y1 - rx - EPSILON:
        ny -= 1.0
    if abs(nx) <= EPSILON and abs(ny) <= EPSILON:
        return (0.0, 0.0)
    return normalizar((nx, ny))


def intersecao_segmento_parede(inicio: Vec2, fim: Vec2, raio: float, limites: Tuple[float, float, float, float]) -> ImpactoColisao | None:
    x0, y0, x1, y1 = [float(v) for v in limites]
    min_x = x0 + float(raio)
    min_y = y0 + float(raio)
    max_x = x1 - float(raio)
    max_y = y1 - float(raio)

    sx, sy = float(inicio[0]), float(inicio[1])
    ex, ey = float(fim[0]), float(fim[1])
    dx = ex - sx
    dy = ey - sy
    candidatos: List[ImpactoColisao] = []

    if abs(dx) > EPSILON:
        for parede_x in (min_x, max_x):
            t = (parede_x - sx) / dx
            if -EPSILON <= t <= 1.0 + EPSILON:
                y = sy + (dy * t)
                if min_y - EPSILON <= y <= max_y + EPSILON:
                    ponto = (parede_x, y)
                    candidatos.append(ImpactoColisao(max(0.0, min(1.0, t)), ponto, (1.0 if parede_x == min_x else -1.0, 0.0), "parede"))

    if abs(dy) > EPSILON:
        for parede_y in (min_y, max_y):
            t = (parede_y - sy) / dy
            if -EPSILON <= t <= 1.0 + EPSILON:
                x = sx + (dx * t)
                if min_x - EPSILON <= x <= max_x + EPSILON:
                    ponto = (x, parede_y)
                    candidatos.append(ImpactoColisao(max(0.0, min(1.0, t)), ponto, (0.0, 1.0 if parede_y == min_y else -1.0), "parede"))

    if not candidatos:
        return None
    candidatos.sort(key=lambda c: c.t)
    primeiro = candidatos[0]
    normais = [primeiro.normal]
    for evento in candidatos[1:]:
        if abs(evento.t - primeiro.t) <= 1e-5:
            normais.append(evento.normal)
    nx = sum(n[0] for n in normais)
    ny = sum(n[1] for n in normais)
    return ImpactoColisao(primeiro.t, primeiro.ponto, normalizar((nx, ny)), "parede")


def primeiro_impacto_segmento(
    inicio: Vec2,
    fim: Vec2,
    raio_projetil: float,
    limites: Tuple[float, float, float, float],
    pokemons: Iterable[Dict[str, object]],
    objetos: Iterable[Dict[str, object]] | None = None,
    ignorar_ids: Iterable[str] | None = None,
) -> ImpactoColisao | None:
    ignorados = {str(i) for i in list(ignorar_ids or [])}
    candidatos: List[ImpactoColisao] = []

    parede = intersecao_segmento_parede(inicio, fim, raio_projetil, limites)
    if parede is not None:
        candidatos.append(parede)

    for pokemon in list(pokemons or []):
        pid = str(pokemon.get("id") or "")
        if pid in ignorados:
            continue
        pos = pokemon.get("pos") or pokemon.get("posicao") or (0.0, 0.0)
        raio_alvo = float(pokemon.get("raio_tiles") or 0.0) + float(raio_projetil)
        impacto = intersecao_segmento_circulo(inicio, fim, (float(pos[0]), float(pos[1])), raio_alvo)
        if impacto is None:
            continue
        impacto.tipo = "pokemon"
        impacto.alvo_id = pid
        impacto.alvo_tipo = "pokemon"
        candidatos.append(impacto)

    for objeto in list(objetos or []):
        oid = str(objeto.get("id") or "")
        pos = objeto.get("pos") or objeto.get("posicao") or (0.0, 0.0)
        raio_obj = float(objeto.get("raio_tiles") or objeto.get("raio") or 0.0) + float(raio_projetil)
        impacto = intersecao_segmento_circulo(inicio, fim, (float(pos[0]), float(pos[1])), raio_obj)
        if impacto is None:
            continue
        impacto.tipo = "objeto"
        impacto.alvo_id = oid
        impacto.alvo_tipo = "objeto"
        candidatos.append(impacto)

    if not candidatos:
        return None
    candidatos.sort(key=lambda c: c.t)
    return candidatos[0]
