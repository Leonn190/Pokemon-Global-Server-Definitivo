from __future__ import annotations

import pygame


class Portal:
    RAIO_INTERACAO_TILES = 1.25

    @staticmethod
    def distancia_quadrada(pos_a, pos_b):
        return (float(pos_a[0]) - float(pos_b[0])) ** 2 + (float(pos_a[1]) - float(pos_b[1])) ** 2

    @classmethod
    def esta_perto(cls, pos_player, pos_portal, raio=None):
        r = cls.RAIO_INTERACAO_TILES if raio is None else float(raio)
        return cls.distancia_quadrada(pos_player, pos_portal) <= float(r) ** 2

    @staticmethod
    def payload_dungeon_entrada(estrutura, pos_player):
        estado = estrutura.get("estado") if isinstance(estrutura.get("estado"), dict) else {}
        return {"acao": "entrar", "estrutura_id": int(estrutura.get("id", 0) or 0), "dungeon_code": str(estado.get("dungeon_code") or ""), "porta_idx": int(estado.get("porta_idx", 1) or 1), "pos_player": [float(pos_player[0]), float(pos_player[1])]}

    @staticmethod
    def payload_dungeon_saida(pos_player):
        return {"acao": "sair", "pos_player": [float(pos_player[0]), float(pos_player[1])]}

    @staticmethod
    def renderizar(tela, camera, posicao, modo="dungeon", **kwargs):
        x, y = camera.mundo_para_tela_px((float(posicao[0]), float(posicao[1])))
        if modo == "estadio":
            tile = float(getattr(camera, "TilePx", 50) or 50)
            px_porta = int(kwargs.get("px_porta", x))
            py_porta = int(kwargs.get("py_porta", y))
            px = lambda v: max(1, int(v * tile))
            porta_w = max(px(1.7), 34)
            porta_h = max(px(2.4), 52)
            porta_externa = pygame.Rect(0, 0, porta_w, porta_h)
            porta_externa.midbottom = (px_porta, py_porta)
            pygame.draw.rect(tela, (44, 50, 64), porta_externa, border_radius=max(8, px(0.16)))
            arco = pygame.Rect(porta_externa.left - px(0.15), porta_externa.top - px(0.75), porta_externa.width + px(0.3), max(px(1.0), int(porta_externa.height * 0.62)))
            pygame.draw.ellipse(tela, (68, 79, 100), arco)
            pygame.draw.ellipse(tela, (44, 50, 64), arco, max(2, px(0.07)))
            porta_interna = porta_externa.inflate(-px(0.42), -px(0.42))
            pygame.draw.rect(tela, (115, 185, 255), porta_interna, border_radius=max(6, px(0.12)))
            brilho = porta_interna.inflate(-px(0.45), -px(0.55))
            if brilho.width > 4 and brilho.height > 4:
                pygame.draw.rect(tela, (190, 230, 255), brilho, border_radius=max(4, px(0.08)))
            faixa_topo = pygame.Rect(porta_externa.left - px(0.25), porta_externa.top - px(0.22), porta_externa.width + px(0.5), max(6, px(0.24)))
            pygame.draw.rect(tela, (88, 100, 124), faixa_topo, border_radius=max(4, px(0.08)))
            luz_r = max(3, px(0.10))
            pygame.draw.circle(tela, (255, 214, 95), (porta_externa.left + px(0.22), porta_externa.top + px(0.34)), luz_r)
            pygame.draw.circle(tela, (255, 214, 95), (porta_externa.right - px(0.22), porta_externa.top + px(0.34)), luz_r)
            return
        raio = max(7, int(getattr(camera, "TilePx", 50) * 0.52))
        pygame.draw.circle(tela, (8, 8, 8), (int(x), int(y)), raio)
        pygame.draw.circle(tela, (70, 70, 70), (int(x), int(y)), raio, 2)


distancia_quadrada = Portal.distancia_quadrada
esta_perto = Portal.esta_perto
payload_dungeon_entrada = Portal.payload_dungeon_entrada
payload_dungeon_saida = Portal.payload_dungeon_saida
renderizar = Portal.renderizar
