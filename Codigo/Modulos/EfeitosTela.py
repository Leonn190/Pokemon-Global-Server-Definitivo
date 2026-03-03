# Codigo/Modulos/EfeitosTela.py
import pygame
import math


GerouSurface = False
surface = None


def aplicar_claridade(tela, claridade):
    global GerouSurface, surface

    if (not GerouSurface) or surface is None or surface.get_size() != tela.get_size():
        surface = pygame.Surface(tela.get_size())
        surface = surface.convert_alpha()
        GerouSurface = True

    claridade = int(max(0, min(100, claridade)))

    if claridade == 75:
        return

    if claridade < 75:
        intensidade = int((75 - claridade) / 50 * 50)
        surface.fill((0, 0, 0, intensidade))
    else:
        intensidade = int((claridade - 75) / 25 * 70)
        surface.fill((255, 255, 255, intensidade))

    tela.blit(surface, (0, 0))


def _clamp(v, a, b):
    return a if v < a else b if v > b else v


def _atualizar(JOGO, dt, dur, direcao):
    # garante atributo
    if not hasattr(JOGO, "Escuro"):
        JOGO.Escuro = 0.0
    passo = 100.0 * (dt / max(dur, 0.001)) * direcao
    JOGO.Escuro = _clamp(JOGO.Escuro + passo, 0.0, 100.0)


def Escurecer(JOGO, dt, dur=0.25):
    """0 -> 100 (overlay preto)"""
    _atualizar(JOGO, dt, dur, +1)

    alpha = int(255 * (JOGO.Escuro / 100.0))
    w, h = JOGO.TELA.get_size()
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((0, 0, 0, alpha))
    JOGO.TELA.blit(s, (0, 0))


def Clarear(JOGO, dt, dur=0.25):
    """100 -> 0 (overlay preto indo embora)"""
    _atualizar(JOGO, dt, dur, -1)

    alpha = int(255 * (JOGO.Escuro / 100.0))
    w, h = JOGO.TELA.get_size()
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((0, 0, 0, alpha))
    JOGO.TELA.blit(s, (0, 0))


def FecharIris(JOGO, dt, dur=0.35):
    """0 -> 100 (íris fechando)"""
    _atualizar(JOGO, dt, dur, +1)

    w, h = JOGO.TELA.get_size()
    cx, cy = w // 2, h // 2
    raio_max = int(math.hypot(w, h) / 2)

    # Escuro=0 => aberto; Escuro=100 => fechado
    raio = int(raio_max * (1.0 - (JOGO.Escuro / 100.0)))

    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    mask.fill((0, 0, 0, 255))
    pygame.draw.circle(mask, (0, 0, 0, 0), (cx, cy), max(0, raio))
    JOGO.TELA.blit(mask, (0, 0))


def AbrirIris(JOGO, dt, dur=0.35):
    """100 -> 0 (íris abrindo)"""
    _atualizar(JOGO, dt, dur, -1)

    w, h = JOGO.TELA.get_size()
    cx, cy = w // 2, h // 2
    raio_max = int(math.hypot(w, h) / 2)

    raio = int(raio_max * (1.0 - (JOGO.Escuro / 100.0)))

    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    mask.fill((0, 0, 0, 255))
    pygame.draw.circle(mask, (0, 0, 0, 0), (cx, cy), max(0, raio))
    JOGO.TELA.blit(mask, (0, 0))
    