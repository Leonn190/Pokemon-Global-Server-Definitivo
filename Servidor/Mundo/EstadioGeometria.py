CASCO_ESCALA_X = 0.90
CASCO_ESCALA_Y = 0.60
CASCO_DESLOCAMENTO_Y = -0.02


def deslocamento_casco_colisao(raio_y: float) -> tuple[float, float]:
    ry = max(2.0, float(raio_y))
    return (0.0, (2.0 * ry) * CASCO_DESLOCAMENTO_Y)


def offset_porta_externa(raio_y: float) -> tuple[float, float]:
    ry = max(2.0, float(raio_y))
    _, off_casco_y = deslocamento_casco_colisao(ry)
    return (0.0, off_casco_y + (ry * CASCO_ESCALA_Y))


def raios_casco_colisao(raio_x: float, raio_y: float) -> tuple[float, float]:
    rx = max(2.0, float(raio_x) * CASCO_ESCALA_X)
    ry = max(2.0, float(raio_y) * CASCO_ESCALA_Y)
    return (rx, ry)


def contexto_batalha_estadio(estado_estadio: dict | None = None) -> dict:
    estado = estado_estadio if isinstance(estado_estadio, dict) else {}
    largura = 80
    altura = 40
    arena_largura = 40
    arena_altura = 20
    centro = [largura * 0.5, altura * 0.5]
    return {
        "origem": [0.0, 0.0],
        "centro": centro,
        "largura": largura,
        "altura": altura,
        "arena_largura": arena_largura,
        "arena_altura": arena_altura,
        "tiles": [],
        "estruturas": [],
        "contexto_estadio": True,
        "tipo_estadio": str(estado.get("tipo_estadio") or "normal"),
    }
