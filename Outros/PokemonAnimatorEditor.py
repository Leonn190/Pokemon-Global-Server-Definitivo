from __future__ import annotations

import sys
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Codigo.Geradores.PokemonBatalha import PokemonBatalha
from Codigo.ModulosGerais.PokemonAnimator import EFEITOS_ATAQUE_FPS


class CameraEditor:
    def __init__(self, tile_px: int = 96, origem_tela=(640, 360)) -> None:
        self.TilePx = int(tile_px)
        self._origem_tela = (int(origem_tela[0]), int(origem_tela[1]))

    def mundo_para_tela_px(self, posicao):
        x = self._origem_tela[0] + int(float(posicao[0]) * self.TilePx)
        y = self._origem_tela[1] + int(float(posicao[1]) * self.TilePx)
        return x, y


class Botao:
    def __init__(self, rect: pygame.Rect, texto: str, acao) -> None:
        self.rect = pygame.Rect(rect)
        self.texto = str(texto)
        self.acao = acao

    def clicar(self, pos) -> bool:
        if self.rect.collidepoint(pos):
            self.acao()
            return True
        return False

    def desenhar(self, tela: pygame.Surface, fonte: pygame.font.Font, hover: bool) -> None:
        cor = (62, 72, 96) if not hover else (82, 96, 128)
        pygame.draw.rect(tela, cor, self.rect, border_radius=10)
        pygame.draw.rect(tela, (210, 220, 238), self.rect, 2, border_radius=10)
        texto = fonte.render(self.texto, True, (245, 248, 255))
        tela.blit(texto, texto.get_rect(center=self.rect.center))


def criar_pokemon_teste() -> PokemonBatalha:
    dados = {
        'nome': 'Pikachu',
        'especie': 'pikachu',
        'nivel': 32,
        'tipos': ['eletrico'],
        'Vida': 120,
        'VidaMax': 120,
        'vida_atual': 95,
        'Ene': 50,
        'EnergiaMaxima': 90,
        'Escala': 0,
        'Atk': 55,
        'Def': 40,
        'Mag': 50,
        'Vel': 90,
        'SpA': 50,
        'SpD': 50,
        'Per': 60,
        'Int': 45,
        'CrC': 10,
        'CrD': 1.5,
        'ataques': [{'Ataque': 'Choque do Trovão', 'Tipo': 'eletrico'}],
        'build': [],
    }
    regras = {
        'combate_pokemon_tamanho_diametro_base_tiles': 1.5,
        'combate_pokemon_tamanho_incremento_por_escala': 0.0,
        'pokemon_tamanho_diametro_base_tiles': 1.5,
        'pokemon_tamanho_incremento_por_escala': 0.0,
    }
    return PokemonBatalha(dados=dados, posicao=(0.0, 0.0), lado='jogador', regras=regras)


def desenhar_grade(tela: pygame.Surface, camera: CameraEditor) -> None:
    largura, altura = tela.get_size()
    tile = camera.TilePx
    ox, oy = camera._origem_tela

    for x in range(ox % tile, largura, tile):
        pygame.draw.line(tela, (38, 42, 56), (x, 0), (x, altura), 1)
    for y in range(oy % tile, altura, tile):
        pygame.draw.line(tela, (38, 42, 56), (0, y), (largura, y), 1)

    pygame.draw.line(tela, (62, 82, 118), (0, oy), (largura, oy), 2)
    pygame.draw.line(tela, (62, 82, 118), (ox, 0), (ox, altura), 2)


def criar_botoes(pokemon: PokemonBatalha, estado_editor: dict) -> list[Botao]:
    animador = pokemon.Animador

    def tocar_efeito_selecionado() -> None:
        nome = estado_editor['efeitos'][estado_editor['indice_efeito']]
        animador.SofrerAtaqueEfeito(nome)

    def alterar_efeito(delta: int) -> None:
        total = len(estado_editor['efeitos'])
        estado_editor['indice_efeito'] = (estado_editor['indice_efeito'] + delta) % total

    return [
        Botao(pygame.Rect(24, 24, 170, 42), 'Tomar Dano', lambda: animador.tomar_dano(36)),
        Botao(pygame.Rect(204, 24, 170, 42), 'Tomar Cura', lambda: animador.tomar_cura(28)),
        Botao(pygame.Rect(384, 24, 190, 42), 'Dano Crítico', lambda: animador.tomar_dano(92, critico=True)),
        Botao(pygame.Rect(584, 24, 170, 42), 'Cartucho Dano', lambda: animador.cartucho(54, tipo='dano')),
        Botao(pygame.Rect(764, 24, 170, 42), 'Cartucho Cura', lambda: animador.cartucho(48, tipo='cura')),
        Botao(pygame.Rect(944, 24, 180, 42), 'Cartucho Crítico', lambda: animador.cartucho(128, tipo='dano', critico=True)),
        Botao(pygame.Rect(24, 78, 170, 42), 'Buffar', lambda: animador.buffar()),
        Botao(pygame.Rect(204, 78, 170, 42), 'Nerfar', lambda: animador.nerfar()),
        Botao(pygame.Rect(384, 78, 170, 42), 'Mover Direita', lambda: animador.mover((2.0, 0.0), 4.0)),
        Botao(pygame.Rect(564, 78, 170, 42), 'Mover Esquerda', lambda: animador.mover((-2.0, 0.0), 4.0)),
        Botao(pygame.Rect(744, 78, 170, 42), 'Mover Cima', lambda: animador.mover((0.0, -1.5), 3.2)),
        Botao(pygame.Rect(924, 78, 170, 42), 'Mover Baixo', lambda: animador.mover((0.0, 1.5), 3.2)),
        Botao(pygame.Rect(1104, 78, 120, 42), 'Centro', lambda: animador.mover((0.0, 0.0), 4.2)),
        Botao(pygame.Rect(24, 132, 48, 42), '<', lambda: alterar_efeito(-1)),
        Botao(pygame.Rect(82, 132, 270, 42), 'Tocar SofrerAtaqueEfeito', tocar_efeito_selecionado),
        Botao(pygame.Rect(362, 132, 48, 42), '>', lambda: alterar_efeito(1)),
    ]


def main() -> None:
    pygame.init()
    tela = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption('PokemonAnimatorEditor')
    relogio = pygame.time.Clock()

    fonte = pygame.font.SysFont('arial', 18)
    fonte_info = pygame.font.SysFont('arial', 20, bold=True)

    camera = CameraEditor(tile_px=96, origem_tela=(640, 420))
    pokemon = criar_pokemon_teste()
    if pokemon.Animador is None:
        raise RuntimeError('PokemonAnimator não foi carregado no PokemonBatalha.')

    estado_editor = {
        'efeitos': sorted(EFEITOS_ATAQUE_FPS.keys()),
        'indice_efeito': 0,
    }
    botoes = criar_botoes(pokemon, estado_editor)
    rodando = True

    while rodando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    rodando = False
                elif evento.key == pygame.K_1:
                    pokemon.Animador.tomar_dano(36)
                elif evento.key == pygame.K_2:
                    pokemon.Animador.tomar_cura(28)
                elif evento.key == pygame.K_3:
                    pokemon.Animador.tomar_dano(92, critico=True)
                elif evento.key == pygame.K_4:
                    pokemon.Animador.buffar()
                elif evento.key == pygame.K_5:
                    pokemon.Animador.nerfar()
                elif evento.key == pygame.K_6:
                    nome = estado_editor['efeitos'][estado_editor['indice_efeito']]
                    pokemon.Animador.SofrerAtaqueEfeito(nome)
                elif evento.key == pygame.K_LEFT:
                    estado_editor['indice_efeito'] = (estado_editor['indice_efeito'] - 1) % len(estado_editor['efeitos'])
                elif evento.key == pygame.K_RIGHT:
                    estado_editor['indice_efeito'] = (estado_editor['indice_efeito'] + 1) % len(estado_editor['efeitos'])
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                for botao in botoes:
                    if botao.clicar(evento.pos):
                        break

        tela.fill((18, 20, 28))
        desenhar_grade(tela, camera)

        painel = pygame.Rect(16, 16, 1248, 172)
        pygame.draw.rect(tela, (24, 28, 38), painel, border_radius=14)
        pygame.draw.rect(tela, (64, 78, 106), painel, 2, border_radius=14)

        mouse = pygame.mouse.get_pos()
        for botao in botoes:
            botao.desenhar(tela, fonte, botao.rect.collidepoint(mouse))

        pokemon.renderizar(tela, camera, selecionado=True)

        efeito_atual = estado_editor['efeitos'][estado_editor['indice_efeito']]
        fps_atual = EFEITOS_ATAQUE_FPS.get(efeito_atual, 0.0)

        info_1 = fonte_info.render('Editor de animações do PokemonBatalha', True, (240, 244, 252))
        info_2 = fonte.render('Teclas rápidas: 1 dano | 2 cura | 3 crítico | 4 buff | 5 nerf | 6 efeito | ← → troca efeito | ESC sair', True, (198, 206, 222))
        info_3 = fonte.render(f'Posição em tiles: ({pokemon.Posicao[0]:.2f}, {pokemon.Posicao[1]:.2f})  |  Diâmetro: {pokemon.DiametroTiles:.2f} tiles', True, (198, 206, 222))
        info_4 = fonte.render(f'Efeito atual: {efeito_atual}  |  FPS: {fps_atual:.2f}', True, (214, 220, 235))
        tela.blit(info_1, (24, 196))
        tela.blit(info_2, (24, 224))
        tela.blit(info_3, (24, 248))
        tela.blit(info_4, (24, 272))

        pygame.display.flip()
        relogio.tick(60)

    pygame.quit()


if __name__ == '__main__':
    main()
