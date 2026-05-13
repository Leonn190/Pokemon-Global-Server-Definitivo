from __future__ import annotations

from dataclasses import dataclass

import pygame

from Codigo.ModulosGerais.ServicoSkills import (
    aprender_skill,
    listar_skills,
    pontos_disponiveis,
    pontos_gastos,
    status_skill,
)
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto
from Codigo.Prefabs.Tooltip import Tooltip


@dataclass(frozen=True)
class NodoSkill:
    id: str
    nome: str
    sigla: str
    pos_norm: tuple[float, float]
    pais: tuple[str, ...]
    descricao: str


class PainelArvoreHabilidades:
    LAYOUT_W = 1018.0
    LAYOUT_H = 593.0
    LAYOUT_ASPECT = LAYOUT_W / LAYOUT_H
    ROOT_POS = (0.4853, 0.8735)

    def __init__(self, ator=None):
        self.Ator = ator
        self._layout_chave = None
        self._rect = pygame.Rect(0, 0, 0, 0)
        self._graph_rect = pygame.Rect(0, 0, 0, 0)
        self._tooltip_pos = (20, 20)
        self._botao_fechar: Botao | None = None
        self._botoes_nodos: dict[str, Botao] = {}
        self._status_cache_nodos: dict[str, str] = {}
        self._exec_por_nodo: dict[str, callable] = {}
        self._solicitou_fechar = False
        self._surface_estatica: pygame.Surface | None = None
        self._surface_estatica_chave = None

        base = {"outline": True, "outline_thickness": 1, "outline_color": (0, 0, 0), "shadow": False}
        self.txt_titulo = Texto("Árvore de habilidades", style={**base, "size": 32, "color": (246, 249, 255)})
        self.txt_info = Texto("", style={**base, "size": 18, "color": (186, 203, 236)})

        self._nodos = self._montar_nodos_skills()
        self._todos_pontos = self._montar_pontos_unificados()
        self._nodos_por_id = {nodo.id: nodo for nodo in self._nodos}
        self._aprendidas_frame = set()

    @staticmethod
    def _linha(ids, xs, ys):
        return {sid: (x, y) for sid, x, y in zip(ids, xs, ys)}

    def _posicoes_skills(self) -> dict[str, tuple[float, float]]:
        pos = {}
        L = self._linha
        pos.update(L([f"velocista_{i}" for i in range(1, 6)], [0.37, 0.34, 0.30, 0.25, 0.20], [0.79, 0.66, 0.53, 0.40, 0.27]))
        pos.update(L([f"corredor_{i}" for i in range(1, 5)], [0.32, 0.30, 0.28, 0.26], [0.70, 0.58, 0.46, 0.34]))
        pos.update(L([f"acelerador_{i}" for i in range(1, 4)], [0.28, 0.25, 0.22], [0.60, 0.48, 0.36]))
        pos.update(L([f"pulmao_{i}" for i in range(1, 6)], [0.23, 0.20, 0.17, 0.14, 0.11], [0.78, 0.66, 0.54, 0.42, 0.30]))
        pos.update(L([f"respirador_{i}" for i in range(1, 5)], [0.16, 0.13, 0.10, 0.08], [0.72, 0.60, 0.48, 0.36]))
        pos.update(L([f"nadador_{i}" for i in range(1, 5)], [0.29, 0.25, 0.21, 0.17], [0.76, 0.64, 0.52, 0.40]))
        pos.update(L([f"aquatico_{i}" for i in range(1, 3)], [0.15, 0.18], [0.24, 0.13]))
        pos.update(L([f"boxeador_{i}" for i in range(1, 3)], [0.11, 0.08], [0.64, 0.52]))
        pos.update(L([f"alcance_mao_{i}" for i in range(1, 4)], [0.10, 0.075, 0.055], [0.43, 0.31, 0.19]))

        pos.update(L([f"maestria_captura_{i}" for i in range(1, 11)], [0.485] * 10, [0.80, 0.72, 0.64, 0.56, 0.48, 0.40, 0.32, 0.24, 0.16, 0.08]))
        pos.update(L([f"coracoes_{i}" for i in range(1, 5)], [0.42, 0.39, 0.36, 0.33], [0.66, 0.54, 0.42, 0.30]))
        pos.update({"visao_expandida_1": (0.53, 0.73), "treinador_experiente_1": (0.44, 0.73), "frutificador_1": (0.36, 0.68), "teleportador_1": (0.485, 0.015), "desbravador_1": (0.36, 0.18)})
        pos.update(L([f"sniper_{i}" for i in range(1, 4)], [0.39, 0.36, 0.33], [0.58, 0.46, 0.34]))
        pos.update(L([f"renda_passiva_{i}" for i in range(1, 4)], [0.54, 0.56, 0.58], [0.58, 0.46, 0.34]))
        pos.update(L([f"aprendizado_xp_{i}" for i in range(1, 4)], [0.61, 0.63, 0.65], [0.58, 0.46, 0.34]))
        pos.update(L([f"rastreador_{i}" for i in range(1, 3)], [0.56, 0.59], [0.66, 0.54]))
        pos.update({"explorador_1": (0.62, 0.42)})
        pos.update(L([f"negociador_{i}" for i in range(1, 4)], [0.66, 0.68, 0.70], [0.50, 0.38, 0.26]))
        pos.update(L([f"pulso_firme_{i}" for i in range(1, 3)], [0.31, 0.28], [0.43, 0.31]))

        pos.update(L([f"mochila_{i}" for i in range(1, 7)], [0.60, 0.63, 0.66, 0.69, 0.72, 0.75], [0.79, 0.67, 0.55, 0.43, 0.31, 0.19]))
        pos.update(L([f"slots_{i}" for i in range(1, 6)], [0.66, 0.69, 0.72, 0.75, 0.78], [0.72, 0.60, 0.48, 0.36, 0.24]))
        pos.update(L([f"pokemons_{i}" for i in range(1, 7)], [0.70, 0.75, 0.80, 0.84, 0.87, 0.90], [0.79, 0.69, 0.59, 0.49, 0.38, 0.27]))
        pos.update(L([f"times_{i}" for i in range(1, 6)], [0.78, 0.82, 0.86, 0.89, 0.92], [0.72, 0.61, 0.50, 0.39, 0.28]))
        pos.update(L([f"conhecimento_{i}" for i in range(1, 9)], [0.64, 0.67, 0.70, 0.73, 0.76, 0.79, 0.82, 0.85], [0.62, 0.53, 0.44, 0.35, 0.26, 0.17, 0.095, 0.035]))
        pos.update(L([f"acumulador_{i}" for i in range(1, 3)], [0.89, 0.92], [0.16, 0.08]))
        return pos

    def _montar_nodos_skills(self):
        pos = self._posicoes_skills()
        nodos = []
        for skill in listar_skills():
            if skill.id not in pos:
                continue
            nodos.append(NodoSkill(skill.id, skill.nome, skill.sigla, pos[skill.id], skill.pais, skill.descricao))
        return nodos

    def _montar_pontos_unificados(self):
        pontos = {"root": self.ROOT_POS}
        for nodo in self._nodos:
            pontos[nodo.id] = nodo.pos_norm
        return pontos

    def _perfil(self):
        return getattr(self.Ator, "Perfil", None)

    def _garantir_estado_perfil(self):
        perfil = self._perfil()
        if perfil is None:
            return None
        if not hasattr(perfil, "HabilidadesAprendidas") or not isinstance(perfil.HabilidadesAprendidas, list):
            perfil.HabilidadesAprendidas = list(getattr(perfil, "HabilidadesAprendidas", []) or [])
        return perfil

    def _lista_aprendidas(self):
        perfil = self._garantir_estado_perfil()
        return [] if perfil is None else perfil.HabilidadesAprendidas

    def _aprendidas_set(self):
        return set(str(v) for v in self._lista_aprendidas())

    def _nivel(self):
        perfil = self._garantir_estado_perfil()
        return 0 if perfil is None else max(0, int(getattr(perfil, "Nivel", 0) or 0))

    def _pontos_disponiveis(self):
        return pontos_disponiveis(self._garantir_estado_perfil())

    def _status_nodo(self, nodo: NodoSkill):
        return status_skill(self._garantir_estado_perfil(), nodo.id)

    def aprender(self, nid: str):
        self._garantir_estado_perfil()
        return aprender_skill(self._perfil(), nid, ator=self.Ator)

    def _estilo_nodo(self, status: str):
        estilo = {
            "radius": 999,
            "border_width": 3,
            "hover_scale": 1.05,
            "press_scale": 0.95,
            "text_style": {
                "size": 14,
                "color": (255, 255, 255),
                "hover_color": (255, 255, 255),
                "align": "center",
                "outline": True,
                "outline_color": (0, 0, 0),
                "outline_thickness": 1,
                "shadow": False,
            },
        }
        if status == "aprendida":
            estilo.update({"bg": (41, 142, 99), "bg_hover": (54, 162, 114), "bg_pressed": (32, 107, 76), "border": (197, 255, 226), "border_hover": (239, 255, 246)})
        elif status == "disponivel":
            estilo.update({"bg": (163, 120, 34), "bg_hover": (196, 145, 44), "bg_pressed": (131, 96, 27), "border": (255, 232, 186), "border_hover": (255, 248, 224)})
        else:
            estilo.update({"bg": (56, 64, 84), "bg_hover": (56, 64, 84), "bg_pressed": (56, 64, 84), "border": (103, 116, 146), "border_hover": (103, 116, 146), "bg_disabled": (46, 53, 70), "border_disabled": (96, 106, 134), "text_disabled": (184, 192, 214)})
        return estilo

    def _tooltip_nodo(self, nodo: NodoSkill):
        return Tooltip(titulo=nodo.nome, descricao=nodo.descricao, pos_fixa=self._tooltip_pos, largura_max=360)

    def _fit_graph_rect(self, area: pygame.Rect):
        w = area.width
        h = int(w / self.LAYOUT_ASPECT)
        if h > area.height:
            h = area.height
            w = int(h * self.LAYOUT_ASPECT)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = area.center
        return rect

    def _pos_para_tela(self, pos_norm: tuple[float, float]):
        return (
            self._graph_rect.x + int(pos_norm[0] * self._graph_rect.width),
            self._graph_rect.y + int(pos_norm[1] * self._graph_rect.height),
        )

    def _ponto_tela(self, ponto_id: str):
        return self._pos_para_tela(self._todos_pontos[ponto_id])

    def _reconstruir_layout(self, rect: pygame.Rect):
        topo_h = 84
        area_graph = pygame.Rect(rect.x + 18, rect.y + topo_h, rect.width - 36, rect.height - topo_h - 18)
        graph_rect = self._fit_graph_rect(area_graph)
        chave = (rect.x, rect.y, rect.width, rect.height, graph_rect.x, graph_rect.y, graph_rect.width, graph_rect.height)
        if chave == self._layout_chave and self._botao_fechar is not None:
            return

        self._layout_chave = chave
        self._rect = pygame.Rect(rect)
        self._graph_rect = graph_rect
        self._tooltip_pos = (self._rect.right - 365, self._rect.bottom - 122)
        self._status_cache_nodos = {}
        self._surface_estatica = None
        self._surface_estatica_chave = None

        def _fechar(_jogo, _botao):
            self._solicitou_fechar = True

        self._botao_fechar = Botao(
            pygame.Rect(self._rect.right - 68, self._rect.y + 16, 52, 52),
            "X",
            execute=_fechar,
            style={"radius": 18, "bg": (113, 32, 45), "bg_hover": (145, 40, 59), "bg_pressed": (86, 23, 34), "border": (255, 195, 203), "border_hover": (255, 236, 240), "text_style": {"size": 26, "outline_thickness": 1, "shadow": False}},
        )
        lado = max(26, int(self._graph_rect.width * 0.023) + 2)
        self._botoes_nodos = {}
        self._exec_por_nodo = {}
        for nodo in self._nodos:
            cx, cy = self._ponto_tela(nodo.id)
            rect_botao = pygame.Rect(0, 0, lado, lado)
            rect_botao.center = (cx, cy)

            def _acao(_jogo, _botao, nid=nodo.id):
                self.aprender(nid)

            self._exec_por_nodo[nodo.id] = _acao
            botao = Botao(rect_botao, nodo.sigla, execute=_acao)
            botao.set_tooltip(self._tooltip_nodo(nodo))
            self._botoes_nodos[nodo.id] = botao

    def _desenhar_fundo(self, tela):
        tela.fill((8, 12, 22), self._rect)
        grad = pygame.Surface(self._rect.size, pygame.SRCALPHA)
        pygame.draw.rect(grad, (12, 18, 32, 248), grad.get_rect(), border_radius=22)
        tela.blit(grad, self._rect.topleft)

    def _desenhar_textos(self, tela):
        self.txt_titulo.set_pos((self._rect.x + 18, self._rect.y + 20))
        self.txt_titulo.draw(tela)
        gastos = pontos_gastos(self._garantir_estado_perfil())
        info = f"Nível {self._nivel()}  •  Aprendidas {len(self._lista_aprendidas())}  •  Pontos {self._pontos_disponiveis()}  •  Gastos {gastos}/100"
        self.txt_info.set_text(info)
        self.txt_info.set_pos((self._rect.x + 20, self._rect.y + 56))
        self.txt_info.draw(tela)

    def _desenhar_raiz(self, tela):
        raiz = self._ponto_tela("root")
        raio = max(15, int(self._graph_rect.width * 0.018))
        pygame.draw.circle(tela, (49, 101, 176), raiz, raio)
        pygame.draw.circle(tela, (205, 227, 255), raiz, max(2, raio // 6))

    def _cor_aresta(self, origem_id: str, destino_id: str):
        aprendidas = self._aprendidas_frame
        if origem_id in aprendidas and destino_id in aprendidas:
            return (214, 229, 255)
        return (86, 107, 152)

    def _desenhar_conexoes(self, tela, estatico: bool = False):
        for nodo in self._nodos:
            origem = self._ponto_tela(nodo.id)
            for pai in nodo.pais:
                destino = self._ponto_tela(pai)
                cor = (86, 107, 152) if estatico or pai == "root" else self._cor_aresta(nodo.id, pai)
                pygame.draw.line(tela, cor, destino, origem, 4)

    def _garantir_camada_estatica(self):
        chave = (self._rect.width, self._rect.height, self._graph_rect.x, self._graph_rect.y, self._graph_rect.width, self._graph_rect.height)
        if self._surface_estatica is not None and self._surface_estatica_chave == chave:
            return
        self._surface_estatica_chave = chave
        self._surface_estatica = pygame.Surface((self._rect.width, self._rect.height), pygame.SRCALPHA)
        rect_original = pygame.Rect(self._rect)
        graph_original = pygame.Rect(self._graph_rect)
        self._rect = pygame.Rect(0, 0, rect_original.width, rect_original.height)
        self._graph_rect = graph_original.move(-rect_original.x, -rect_original.y)
        self._desenhar_fundo(self._surface_estatica)
        self._desenhar_conexoes(self._surface_estatica, estatico=True)
        self._desenhar_raiz(self._surface_estatica)
        self._rect = rect_original
        self._graph_rect = graph_original

    def _desenhar_nodos(self, tela, eventos, dt):
        Botao.iniciar_camada_tooltips()
        for nodo in self._nodos:
            status = self._status_nodo(nodo)
            botao = self._botoes_nodos[nodo.id]
            if self._status_cache_nodos.get(nodo.id) != status:
                botao.set_style(**self._estilo_nodo(status))
                botao.set_habilitado(status in {"aprendida", "disponivel"})
                botao.set_execute(None if status == "aprendida" else self._exec_por_nodo.get(nodo.id))
                self._status_cache_nodos[nodo.id] = status
            if botao.tooltip is not None:
                botao.tooltip.definir_posicao_fixa(self._tooltip_pos)
            botao.render(tela, eventos, dt, None)
        self._botao_fechar.render(tela, eventos, dt, None)
        Botao.finalizar_camada_tooltips(tela)

    def renderizar(self, tela, rect, eventos=None, dt=0.0):
        eventos = eventos or []
        self._solicitou_fechar = False
        self._aprendidas_frame = self._aprendidas_set()
        self._reconstruir_layout(pygame.Rect(rect))
        self._garantir_camada_estatica()
        tela.blit(self._surface_estatica, self._rect.topleft)
        self._desenhar_textos(tela)
        self._desenhar_conexoes(tela)
        self._desenhar_nodos(tela, eventos, dt)
        return self._solicitou_fechar
