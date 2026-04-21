from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

EPSILON = 1e-8


@dataclass(frozen=True, slots=True)
class Vetor2:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class ArenaRetangular:
    x_min: float
    y_min: float
    x_max: float
    y_max: float


def como_vetor2(valor, padrao: tuple[float, float] = (0.0, 0.0)) -> Vetor2:
    if isinstance(valor, Vetor2):
        return valor
    if isinstance(valor, dict):
        x = valor.get("x", padrao[0])
        y = valor.get("y", padrao[1])
        return Vetor2(float(x), float(y))
    if isinstance(valor, Iterable) and not isinstance(valor, (str, bytes)):
        itens = list(valor)
        if len(itens) >= 2:
            return Vetor2(float(itens[0]), float(itens[1]))
    return Vetor2(float(padrao[0]), float(padrao[1]))


def somar(a, b) -> Vetor2:
    va = como_vetor2(a)
    vb = como_vetor2(b)
    return Vetor2(va.x + vb.x, va.y + vb.y)


def subtrair(a, b) -> Vetor2:
    va = como_vetor2(a)
    vb = como_vetor2(b)
    return Vetor2(va.x - vb.x, va.y - vb.y)


def multiplicar(v, escalar: float) -> Vetor2:
    vv = como_vetor2(v)
    return Vetor2(vv.x * float(escalar), vv.y * float(escalar))


def dividir(v, escalar: float) -> Vetor2:
    vv = como_vetor2(v)
    esc = float(escalar)
    if abs(esc) < EPSILON:
        return Vetor2(0.0, 0.0)
    return Vetor2(vv.x / esc, vv.y / esc)


def comprimento(v) -> float:
    vv = como_vetor2(v)
    return math.hypot(vv.x, vv.y)


def comprimento_quadrado(v) -> float:
    vv = como_vetor2(v)
    return vv.x * vv.x + vv.y * vv.y


def normalizar(v) -> Vetor2:
    vv = como_vetor2(v)
    comp = comprimento(vv)
    if comp < EPSILON:
        return Vetor2(0.0, 0.0)
    return Vetor2(vv.x / comp, vv.y / comp)


def dot(a, b) -> float:
    va = como_vetor2(a)
    vb = como_vetor2(b)
    return va.x * vb.x + va.y * vb.y


def distancia(a, b) -> float:
    return comprimento(subtrair(a, b))


def perpendicular(v) -> Vetor2:
    vv = como_vetor2(v)
    return Vetor2(-vv.y, vv.x)


def clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def lerp(a, b, t: float) -> Vetor2:
    va = como_vetor2(a)
    vb = como_vetor2(b)
    fator = clamp(float(t), 0.0, 1.0)
    return Vetor2(va.x + (vb.x - va.x) * fator, va.y + (vb.y - va.y) * fator)


def ponto_em_circulo(ponto, centro, raio: float) -> bool:
    return distancia(ponto, centro) <= float(raio)


def circulos_colidem(centro_a, raio_a: float, centro_b, raio_b: float) -> bool:
    return distancia(centro_a, centro_b) <= float(raio_a) + float(raio_b)


def distancia_ponto_segmento(ponto, a, b) -> float:
    pp = como_vetor2(ponto)
    aa = como_vetor2(a)
    bb = como_vetor2(b)
    ab = subtrair(bb, aa)
    ab2 = comprimento_quadrado(ab)
    if ab2 < EPSILON:
        return distancia(pp, aa)
    t = dot(subtrair(pp, aa), ab) / ab2
    t = clamp(t, 0.0, 1.0)
    proj = lerp(aa, bb, t)
    return distancia(pp, proj)


def ponto_em_capsula(ponto, a, b, raio: float) -> bool:
    return distancia_ponto_segmento(ponto, a, b) <= float(raio)


def segmento_intersecta_circulo(a, b, centro, raio: float) -> bool:
    return distancia_ponto_segmento(centro, a, b) <= float(raio)


def varredura_circulo_vs_circulo(inicio, fim, raio_movel: float, centro_alvo, raio_alvo: float) -> tuple[bool, float, Vetor2]:
    i = como_vetor2(inicio)
    f = como_vetor2(fim)
    c = como_vetor2(centro_alvo)
    r = float(raio_movel) + float(raio_alvo)
    d = subtrair(f, i)
    a = dot(d, d)
    if a < EPSILON:
        if circulos_colidem(i, raio_movel, c, raio_alvo):
            n = normal_colisao_circulo(i, c)
            return True, 0.0, n
        return False, 1.0, Vetor2(0.0, 0.0)

    f_rel = subtrair(i, c)
    b = 2.0 * dot(f_rel, d)
    cterm = dot(f_rel, f_rel) - r * r
    delta = b * b - 4.0 * a * cterm
    if delta < 0.0:
        return False, 1.0, Vetor2(0.0, 0.0)

    raiz = math.sqrt(delta)
    t1 = (-b - raiz) / (2.0 * a)
    t2 = (-b + raiz) / (2.0 * a)
    candidatos = [t for t in (t1, t2) if 0.0 <= t <= 1.0]
    if not candidatos:
        return False, 1.0, Vetor2(0.0, 0.0)
    t_hit = min(candidatos)
    ponto = lerp(i, f, t_hit)
    normal = normal_colisao_circulo(ponto, c)
    return True, t_hit, normal


def ponto_em_cone(ponto, origem, direcao, alcance: float, angulo_graus: float) -> bool:
    p = como_vetor2(ponto)
    o = como_vetor2(origem)
    d = normalizar(direcao)
    if comprimento_quadrado(d) < EPSILON:
        return False
    v = subtrair(p, o)
    dist = comprimento(v)
    if dist > float(alcance):
        return False
    if dist < EPSILON:
        return True
    vn = dividir(v, dist)
    meia_abertura = math.radians(float(angulo_graus) * 0.5)
    limite = math.cos(meia_abertura)
    return dot(vn, d) >= limite


def ponto_em_trapezio(ponto, origem, direcao, alcance: float, largura_base: float, largura_topo: float) -> bool:
    p = como_vetor2(ponto)
    o = como_vetor2(origem)
    frente = normalizar(direcao)
    if comprimento_quadrado(frente) < EPSILON:
        return False
    lateral = perpendicular(frente)
    rel = subtrair(p, o)
    progresso = dot(rel, frente)
    if progresso < 0.0 or progresso > float(alcance):
        return False
    t = progresso / max(float(alcance), EPSILON)
    largura = float(largura_base) + (float(largura_topo) - float(largura_base)) * t
    offset = abs(dot(rel, lateral))
    return offset <= largura * 0.5


def refletir_vetor(direcao, normal) -> Vetor2:
    d = como_vetor2(direcao)
    n = normalizar(normal)
    return subtrair(d, multiplicar(n, 2.0 * dot(d, n)))


def normal_colisao_circulo(centro_a, centro_b) -> Vetor2:
    delta = subtrair(centro_b, centro_a)
    n = normalizar(delta)
    if comprimento_quadrado(n) < EPSILON:
        return Vetor2(1.0, 0.0)
    return n


def colisao_circulo_arena(posicao, raio: float, arena: ArenaRetangular | dict | None) -> tuple[bool, Vetor2 | None, str | None]:
    if arena is None:
        return False, None, None
    a = arena if isinstance(arena, ArenaRetangular) else ArenaRetangular(**arena)
    p = como_vetor2(posicao)
    r = float(raio)
    if p.x - r < a.x_min:
        return True, Vetor2(1.0, 0.0), "esquerda"
    if p.x + r > a.x_max:
        return True, Vetor2(-1.0, 0.0), "direita"
    if p.y - r < a.y_min:
        return True, Vetor2(0.0, 1.0), "topo"
    if p.y + r > a.y_max:
        return True, Vetor2(0.0, -1.0), "baixo"
    return False, None, None


def resolver_impulso_colisao(vel_a, massa_a: float, vel_b, massa_b: float, normal, restituicao: float = 0.35) -> tuple[Vetor2, Vetor2]:
    va = como_vetor2(vel_a)
    vb = como_vetor2(vel_b)
    n = normalizar(normal)
    if comprimento_quadrado(n) < EPSILON:
        return va, vb
    ma = max(float(massa_a), EPSILON)
    mb = max(float(massa_b), EPSILON)
    vel_rel = dot(subtrair(va, vb), n)
    if vel_rel <= 0.0:
        return va, vb

    e = clamp(float(restituicao), 0.0, 1.0)
    j = (1.0 + e) * vel_rel
    j /= (1.0 / ma) + (1.0 / mb)

    novo_a = somar(va, multiplicar(n, j / ma))
    novo_b = subtrair(vb, multiplicar(n, j / mb))
    return novo_a, novo_b


def estimar_impulso_colisao(vel_relativa, massa_a: float, massa_b: float, normal) -> float:
    n = normalizar(normal)
    if comprimento_quadrado(n) < EPSILON:
        return 0.0
    vr = como_vetor2(vel_relativa)
    fechamento = max(0.0, dot(vr, n))
    ma = max(float(massa_a), EPSILON)
    mb = max(float(massa_b), EPSILON)
    massa_reduzida = (ma * mb) / (ma + mb)
    return massa_reduzida * fechamento
