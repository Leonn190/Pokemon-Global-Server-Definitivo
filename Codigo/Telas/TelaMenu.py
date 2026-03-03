import pygame
from pathlib import Path

from Codigo.Prefabs.Botao import Botao


def inicializar_tela_menu(JOGO):
    largura_tela, altura_tela = JOGO.TELA.get_size()

    caminho_fundo = Path("Recursos/Visual/Fundos/FundoMenu.jpg")
    fundo = pygame.image.load(str(caminho_fundo)).convert()
    fundo_largura, fundo_altura = fundo.get_size()

    caminho_logo = Path("Recursos/Visual/Icones/GlobalServer/Logo.png")
    logo_surface = pygame.image.load(str(caminho_logo)).convert_alpha()

    largura_logo = min(int(largura_tela * 0.36), logo_surface.get_width())
    altura_logo = int(logo_surface.get_height() * (largura_logo / logo_surface.get_width()))
    logo_surface = pygame.transform.smoothscale(logo_surface, (largura_logo, altura_logo))
    logo_pos = (largura_tela // 2 - largura_logo // 2, int(altura_tela * 0.3) - altura_logo // 2)

    pasta_textura = Path("Recursos/Visual/Texturas/TexturaCosmica")
    frames_textura = sorted(pasta_textura.glob("gif_frame*.png"), key=lambda p: int(p.stem.replace("gif_frame", "")))
    frames_hover = [
        pygame.image.load(str(frame)).convert_alpha()
        for i, frame in enumerate(frames_textura)
        if i % 6 == 0
    ]
    textura_base = frames_hover[0] if frames_hover else None

    estilo_botao = {
        "radius": 22,
        "border_width": 2,
        "border": (22, 26, 40),
        "border_hover": (252, 234, 125),
        "bg": (18, 20, 30),
        "bg_hover": (38, 44, 66),
        "bg_pressed": (16, 19, 28),
        "bg_image": textura_base,
        "bg_frames_hover": frames_hover,
        "bg_frames_fps": 15,
        "hover_scale": 1.08,
        "hover_speed": 14.0,
        "press_scale": 0.97,
        "text_style": {
            "size": 40,
            "color": (245, 246, 255),
            "hover_color": (255, 232, 80),
            "hover_speed": 28.0,
            "outline": True,
            "outline_color": (0, 0, 0),
            "outline_thickness": 2,
            "shadow": True,
            "shadow_color": (0, 0, 0, 170),
            "shadow_offset": (2, 2),
        },
    }

    largura_botao = 480
    altura_botao = 120
    espacamento = 28
    inicio_y = int(altura_tela * 0.58)
    x = (largura_tela - largura_botao) // 2

    botoes = [
        Botao(pygame.Rect(x, inicio_y + (altura_botao + espacamento) * 0, largura_botao, altura_botao), "Jogar", style=estilo_botao),
        Botao(pygame.Rect(x, inicio_y + (altura_botao + espacamento) * 1, largura_botao, altura_botao), "Configurações", style=estilo_botao),
        Botao(pygame.Rect(x, inicio_y + (altura_botao + espacamento) * 2, largura_botao, altura_botao), "Sair", style=estilo_botao),
    ]

    return {
        "fundo": fundo,
        "fundo_largura": fundo_largura,
        "fundo_altura": fundo_altura,
        "fundo_offset_x": 0.0,
        "fundo_direcao": 1,
        "fundo_velocidade": 26.0,
        "logo": logo_surface,
        "logo_pos": logo_pos,
        "botoes": botoes,
    }


def _desenhar_fundo(JOGO, estado, dt):
    largura_tela, altura_tela = JOGO.TELA.get_size()

    max_offset = max(estado["fundo_largura"], largura_tela)
    estado["fundo_offset_x"] += estado["fundo_velocidade"] * dt * estado["fundo_direcao"]
    if estado["fundo_offset_x"] >= max_offset:
        estado["fundo_offset_x"] = max_offset
        estado["fundo_direcao"] = -1
    elif estado["fundo_offset_x"] <= 0:
        estado["fundo_offset_x"] = 0
        estado["fundo_direcao"] = 1

    x_base = int(estado["fundo_offset_x"])

    for x in (-x_base, estado["fundo_largura"] - x_base):
        for y in range(0, altura_tela, estado["fundo_altura"]):
            JOGO.TELA.blit(estado["fundo"], (x, y))

    if estado["fundo_altura"] != altura_tela:
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 70))
        JOGO.TELA.blit(overlay, (0, 0))


def desenhar_tela_menu(JOGO, estado, EVENTOS, dt):
    _desenhar_fundo(JOGO, estado, dt)
    JOGO.TELA.blit(estado["logo"], estado["logo_pos"])

    for botao in estado["botoes"]:
        botao.render(JOGO.TELA, EVENTOS, dt, JOGO=JOGO)
