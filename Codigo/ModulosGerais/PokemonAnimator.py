from __future__ import annotations

import math
from typing import Dict, List, Tuple

import pygame

Vector2 = Tuple[float, float]


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, float(valor)))


def _ease_out_back(t: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * ((t - 1.0) ** 3) + c1 * ((t - 1.0) ** 2)


class PokemonAnimator:
    def __init__(self, pokemon) -> None:
        self.Pokemon = pokemon
        self._ultimo_tick = pygame.time.get_ticks()
        self._flashes: List[Dict[str, object]] = []
        self._cartuchos: List[Dict[str, object]] = []
        self._setas: List[Dict[str, object]] = []
        self._movimento: Dict[str, object] | None = None

    def atualizar(self) -> None:
        agora = pygame.time.get_ticks()
        dt = max(0.0, min(0.05, (agora - self._ultimo_tick) / 1000.0))
        self._ultimo_tick = agora

        self._atualizar_flashes(dt)
        self._atualizar_cartuchos(dt)
        self._atualizar_setas(dt)
        self._atualizar_movimento(dt)

    def renderizar(self, tela: pygame.Surface, camera) -> None:
        self._desenhar_flash(tela, camera)
        self._desenhar_setas(tela, camera)
        self._desenhar_cartuchos(tela, camera)

    def tomar_dano(self, valor: float = 0.0, critico: bool = False) -> None:
        self._adicionar_flash((255, 72, 72), 0.24)
        if valor:
            self.cartucho(valor, tipo='dano', critico=critico)

    def tomar_cura(self, valor: float = 0.0) -> None:
        self._adicionar_flash((72, 235, 120), 0.24)
        if valor:
            self.cartucho(valor, tipo='cura', critico=False)

    def cartucho(self, valor: float, tipo: str = 'dano', critico: bool = False) -> None:
        valor_num = float(valor)
        cor = (230, 74, 74) if tipo == 'dano' else (72, 214, 110)
        prefixo = '-' if tipo == 'dano' else '+'
        magnitude = abs(valor_num)
        self._cartuchos.append(
            {
                'valor': magnitude,
                'texto': f"{prefixo}{int(round(magnitude))}",
                'tipo': tipo,
                'critico': bool(critico),
                'cor': cor,
                'tempo': 0.0,
                'duracao': 0.72 if critico else 0.62,
                'offset_x_tiles': 0.0,
            }
        )

    def buffar(self, intensidade: int = 1) -> None:
        self._gerar_setas(subindo=True, intensidade=intensidade)

    def nerfar(self, intensidade: int = 1) -> None:
        self._gerar_setas(subindo=False, intensidade=intensidade)

    def mover(self, destino: Vector2, velocidade_tiles_por_seg: float) -> None:
        inicio = (float(self.Pokemon.Posicao[0]), float(self.Pokemon.Posicao[1]))
        destino = (float(destino[0]), float(destino[1]))
        velocidade = max(0.01, float(velocidade_tiles_por_seg))
        self._movimento = {
            'inicio': inicio,
            'destino': destino,
            'velocidade': velocidade,
        }

    def esta_movendo(self) -> bool:
        return self._movimento is not None

    def _adicionar_flash(self, cor: Tuple[int, int, int], duracao: float) -> None:
        self._flashes.append({'cor': tuple(cor), 'tempo': 0.0, 'duracao': float(duracao)})

    def _atualizar_flashes(self, dt: float) -> None:
        novos = []
        for efeito in self._flashes:
            efeito['tempo'] = float(efeito['tempo']) + dt
            if float(efeito['tempo']) < float(efeito['duracao']):
                novos.append(efeito)
        self._flashes = novos

    def _atualizar_cartuchos(self, dt: float) -> None:
        novos = []
        for cartucho in self._cartuchos:
            cartucho['tempo'] = float(cartucho['tempo']) + dt
            if float(cartucho['tempo']) < float(cartucho['duracao']):
                novos.append(cartucho)
        self._cartuchos = novos

    def _atualizar_setas(self, dt: float) -> None:
        novos = []
        for seta in self._setas:
            seta['tempo'] = float(seta['tempo']) + dt
            if float(seta['tempo']) < float(seta['duracao']):
                novos.append(seta)
        self._setas = novos

    def _atualizar_movimento(self, dt: float) -> None:
        if self._movimento is None:
            return

        atual_x, atual_y = float(self.Pokemon.Posicao[0]), float(self.Pokemon.Posicao[1])
        destino_x, destino_y = self._movimento['destino']
        delta_x = destino_x - atual_x
        delta_y = destino_y - atual_y
        distancia = math.hypot(delta_x, delta_y)
        if distancia <= 0.0001:
            self.Pokemon.Posicao = (destino_x, destino_y)
            self._movimento = None
            return

        passo = float(self._movimento['velocidade']) * dt
        if passo >= distancia:
            self.Pokemon.Posicao = (destino_x, destino_y)
            self._movimento = None
            return

        nx = delta_x / distancia
        ny = delta_y / distancia
        self.Pokemon.Posicao = (atual_x + nx * passo, atual_y + ny * passo)

    def _gerar_setas(self, *, subindo: bool, intensidade: int = 1) -> None:
        total = max(1, min(6, int(intensidade) + 2))
        offsets = []
        if total == 1:
            offsets = [0.0]
        else:
            largura = 0.78
            offsets = [
                (-largura * 0.5) + (largura * (indice / (total - 1)))
                for indice in range(total)
            ]
        for indice, offset in enumerate(offsets):
            self._setas.append(
                {
                    'subindo': bool(subindo),
                    'tempo': -(indice * 0.045),
                    'duracao': 0.52,
                    'offset_x_tiles': offset,
                }
            )

    def _desenhar_flash(self, tela: pygame.Surface, camera) -> None:
        if not self._flashes:
            return
        centro = self.Pokemon.centro_tela(camera)
        raio = self.Pokemon.raio_px(camera)
        tamanho = max(8, raio * 4)
        camada = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
        centro_local = (tamanho // 2, tamanho // 2)

        for efeito in self._flashes:
            t = _clamp(float(efeito['tempo']) / float(efeito['duracao']), 0.0, 1.0)
            envelope = math.sin(t * math.pi)
            alpha = int(140 * envelope)
            if alpha <= 0:
                continue
            cor = efeito['cor']
            pygame.draw.circle(camada, (cor[0], cor[1], cor[2], alpha), centro_local, raio)
            pygame.draw.circle(camada, (255, 255, 255, int(alpha * 0.45)), centro_local, max(2, int(raio * 0.92)), max(2, int(raio * 0.12)))

        tela.blit(camada, camada.get_rect(center=centro))

    def _desenhar_cartuchos(self, tela: pygame.Surface, camera) -> None:
        if not self._cartuchos:
            return
        tile_px = max(16, int(getattr(camera, 'TilePx', 40) or 40))
        centro_x, centro_y = self.Pokemon.centro_tela(camera)
        raio = self.Pokemon.raio_px(camera)

        for cartucho in self._cartuchos:
            t = _clamp(float(cartucho['tempo']) / float(cartucho['duracao']), 0.0, 1.0)
            alpha = int(255 * (1.0 - t))
            if alpha <= 0:
                continue

            valor = float(cartucho['valor'])
            fator_valor = min(1.0, valor / 250.0)
            escala_base = 0.58 + (0.42 * _ease_out_back(t))
            escala = escala_base * (1.0 + fator_valor * 0.38)
            tamanho_fonte = max(16, int(tile_px * (0.42 + fator_valor * 0.24) * escala))
            fonte = pygame.font.SysFont("arial", tamanho_fonte, bold=True)
            texto = fonte.render(str(cartucho['texto']), True, (255, 255, 255))
            largura = texto.get_width() + max(18, int(tile_px * 0.36))
            altura = texto.get_height() + max(10, int(tile_px * 0.18))

            y = centro_y - raio - int(tile_px * (0.28 + t * 0.95))
            x = centro_x + int(float(cartucho['offset_x_tiles']) * tile_px)
            rect = pygame.Rect(0, 0, largura, altura)
            rect.center = (x, y)

            camada = pygame.Surface((largura + 18, altura + 18), pygame.SRCALPHA)
            rect_local = pygame.Rect(9, 9, largura, altura)
            cor = cartucho['cor']
            pygame.draw.rect(camada, (0, 0, 0, int(alpha * 0.78)), rect_local.inflate(4, 4), border_radius=max(8, altura // 2))
            pygame.draw.rect(camada, (cor[0], cor[1], cor[2], alpha), rect_local, border_radius=max(8, altura // 2))
            pygame.draw.rect(camada, (255, 255, 255, int(alpha * 0.85)), rect_local, 2, border_radius=max(8, altura // 2))

            if bool(cartucho['critico']):
                self._desenhar_espinhos(camada, rect_local, alpha)

            texto_sombra = fonte.render(str(cartucho['texto']), True, (0, 0, 0))
            texto_sombra.set_alpha(int(alpha * 0.6))
            texto_alpha = texto.copy()
            texto_alpha.set_alpha(alpha)
            camada.blit(texto_sombra, texto_sombra.get_rect(center=(rect_local.centerx + 1, rect_local.centery + 1)))
            camada.blit(texto_alpha, texto_alpha.get_rect(center=rect_local.center))

            tela.blit(camada, camada.get_rect(center=rect.center))

    def _desenhar_espinhos(self, camada: pygame.Surface, rect: pygame.Rect, alpha: int) -> None:
        centro = pygame.Vector2(rect.center)
        raio_x = rect.width * 0.62
        raio_y = rect.height * 0.9
        pontos = []
        total = 16
        for indice in range(total):
            ang = (math.tau * indice) / total
            externo = (indice % 2) == 0
            fator_x = 1.26 if externo else 1.04
            fator_y = 1.36 if externo else 1.08
            pontos.append(
                (
                    centro.x + math.cos(ang) * raio_x * fator_x,
                    centro.y + math.sin(ang) * raio_y * fator_y,
                )
            )
        pygame.draw.polygon(camada, (255, 230, 120, int(alpha * 0.5)), pontos)

    def _desenhar_setas(self, tela: pygame.Surface, camera) -> None:
        if not self._setas:
            return
        tile_px = max(16, int(getattr(camera, 'TilePx', 40) or 40))
        centro_x, centro_y = self.Pokemon.centro_tela(camera)
        raio = self.Pokemon.raio_px(camera)

        for seta in self._setas:
            if float(seta['tempo']) < 0.0:
                continue
            t = _clamp(float(seta['tempo']) / float(seta['duracao']), 0.0, 1.0)
            alpha = int(210 * (1.0 - t))
            if alpha <= 0:
                continue

            deslocamento = (t * tile_px * 0.95)
            direcao = -1 if bool(seta['subindo']) else 1
            x = centro_x + int(float(seta['offset_x_tiles']) * tile_px)
            y = centro_y + int(direcao * (-raio * 0.15 + deslocamento))

            self._desenhar_seta_unica(
                tela,
                (x, y),
                altura=max(18, int(tile_px * 0.55)),
                largura=max(12, int(tile_px * 0.28)),
                alpha=alpha,
                subindo=bool(seta['subindo']),
            )

    @staticmethod
    def _desenhar_seta_unica(
        tela: pygame.Surface,
        centro: Tuple[int, int],
        *,
        altura: int,
        largura: int,
        alpha: int,
        subindo: bool,
    ) -> None:
        camada = pygame.Surface((largura * 3, altura * 3), pygame.SRCALPHA)
        cx, cy = camada.get_width() // 2, camada.get_height() // 2
        corpo_altura = max(6, int(altura * 0.44))
        corpo_largura = max(4, int(largura * 0.36))
        cabeca_altura = max(8, int(altura * 0.42))
        cor = (100, 215, 255, alpha) if subindo else (255, 175, 90, alpha)

        if subindo:
            rect_corpo = pygame.Rect(cx - corpo_largura // 2, cy - corpo_altura // 2 + 3, corpo_largura, corpo_altura)
            ponta = [(cx, cy - corpo_altura // 2 - cabeca_altura), (cx - largura // 2, cy - corpo_altura // 2), (cx + largura // 2, cy - corpo_altura // 2)]
        else:
            rect_corpo = pygame.Rect(cx - corpo_largura // 2, cy - corpo_altura // 2 - 3, corpo_largura, corpo_altura)
            ponta = [(cx, cy + corpo_altura // 2 + cabeca_altura), (cx - largura // 2, cy + corpo_altura // 2), (cx + largura // 2, cy + corpo_altura // 2)]

        pygame.draw.rect(camada, cor, rect_corpo, border_radius=max(2, corpo_largura // 2))
        pygame.draw.polygon(camada, cor, ponta)
        pygame.draw.rect(camada, (255, 255, 255, int(alpha * 0.55)), rect_corpo, 1, border_radius=max(2, corpo_largura // 2))
        pygame.draw.lines(camada, (255, 255, 255, int(alpha * 0.55)), True, ponta, 1)
        tela.blit(camada, camada.get_rect(center=centro))
