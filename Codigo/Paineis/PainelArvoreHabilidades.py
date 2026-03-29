from __future__ import annotations

from dataclasses import dataclass

import pygame

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
    efeitos: tuple[tuple[str, float], ...]
    descricao: str


@dataclass(frozen=True)
class NodoDecorativo:
    id: str
    pos_norm: tuple[float, float]
    pais: tuple[str, ...]
    rotulo: str = "?"


class PainelArvoreHabilidades:
    """
    Árvore desenhada a partir da geometria normalizada da imagem de referência.

    Não existe mais mapeamento indireto por índice de imagem. Cada nó já nasce
    com sua posição normalizada e com suas conexões próprias.
    """

    LAYOUT_W = 1018.0
    LAYOUT_H = 593.0
    LAYOUT_ASPECT = LAYOUT_W / LAYOUT_H

    ROOT_POS = (0.4853, 0.8735)

    # Coordenadas extraídas da imagem-base e normalizadas para 0..1.
    POS = {
        # movimento
        "mv_v1": (0.3684, 0.8280),
        "mv_p1": (0.2790, 0.7875),
        "mv_n1": (0.3409, 0.6965),
        "mv_p2": (0.2279, 0.6847),
        "mv_r1": (0.2092, 0.7673),
        "mv_n2": (0.2859, 0.6239),
        "mv_c1": (0.3517, 0.5953),
        "mv_v2": (0.2171, 0.5531),
        "mv_b1": (0.1631, 0.6509),
        "mv_r2": (0.1365, 0.7572),
        "mv_a1": (0.2976, 0.5008),
        "mv_c2": (0.3605, 0.4806),
        "mv_p3": (0.1493, 0.4722),
        "mv_n3": (0.2308, 0.4334),
        "mv_b2": (0.1031, 0.5531),
        "mv_a2": (0.3153, 0.3879),
        "mv_r3": (0.1071, 0.3626),
        "mv_c3": (0.2505, 0.3120),
        "mv_aq": (0.1572, 0.2395),
        "mv_v3": (0.1994, 0.1046),

        # centro em construção
        "ct_low": (0.4823, 0.6965),
        "ct_l1": (0.4440, 0.5481),
        "ct_r1": (0.5265, 0.5481),
        "ct_l2a": (0.4028, 0.3929),
        "ct_l2b": (0.4587, 0.3761),
        "ct_top_l": (0.4293, 0.2445),
        "ct_top": (0.4853, 0.0995),
        "ct_top_r": (0.5354, 0.2395),
        "ct_r2a": (0.5059, 0.3727),
        "ct_r2b": (0.5589, 0.3761),

        # inventário
        "in_m1": (0.5982, 0.8179),
        "in_s1": (0.6238, 0.6897),
        "in_pk1": (0.6876, 0.7808),
        "in_t1": (0.7387, 0.6745),
        "in_m2": (0.6139, 0.5885),
        "in_pk2": (0.7574, 0.7605),
        "in_s2": (0.6798, 0.6138),
        "in_t2": (0.8026, 0.6425),
        "in_m3": (0.6051, 0.4722),
        "in_pk3": (0.8301, 0.7504),
        "in_s3": (0.6680, 0.4924),
        "in_t3": (0.8625, 0.5447),
        "in_m4": (0.6503, 0.3794),
        "in_pk4": (0.8163, 0.4637),
        "in_s4": (0.7495, 0.5447),
        "in_t4": (0.8585, 0.3524),
        "in_m5": (0.7161, 0.3052),
        "in_pk5": (0.8084, 0.2293),
        "in_m6": (0.7672, 0.0944),
        "in_pk6": (0.7348, 0.4266),
    }

    def __init__(self, ator=None):
        self.Ator = ator
        self._layout_chave = None
        self._rect = pygame.Rect(0, 0, 0, 0)
        self._graph_rect = pygame.Rect(0, 0, 0, 0)
        self._tooltip_pos = (20, 20)
        self._botao_fechar: Botao | None = None
        self._botoes_nodos: dict[str, Botao] = {}
        self._solicitou_fechar = False

        base = {"outline": True, "outline_thickness": 1, "outline_color": (0, 0, 0), "shadow": False}
        self.txt_titulo = Texto("Árvore de habilidades", style={**base, "size": 32, "color": (246, 249, 255)})
        self.txt_info = Texto("", style={**base, "size": 18, "color": (186, 203, 236)})
        self.txt_centro = Texto("Em construção", style={**base, "size": 22, "color": (255, 212, 117), "align": "center"})

        self._nodos = self._montar_nodos_skills()
        self._decorativos = self._montar_nodos_decorativos()
        self._todos_pontos = self._montar_pontos_unificados()
        self._nodos_por_id = {nodo.id: nodo for nodo in self._nodos}

    def _montar_nodos_skills(self):
        P = self.POS
        return [
            # --- movimento ---
            NodoSkill("velocista_1", "Velocista I", "V1", P["mv_v1"], ("root",), (("VelocidadeBaseTiles", 0.5),), "Velocidade base +0.5."),
            NodoSkill("pulmao_1", "Pulmão I", "P1", P["mv_p1"], ("velocista_1",), (("StaminaMax", 20.0),), "Stamina máxima +20."),
            NodoSkill("nadador_1", "Nadador I", "N1", P["mv_n1"], ("velocista_1",), (("CustoStaminaAguaFunda", -3.0),), "Água funda custa 3 a menos."),
            NodoSkill("pulmao_2", "Pulmão II", "P2", P["mv_p2"], ("pulmao_1",), (("StaminaMax", 20.0),), "Stamina máxima +20."),
            NodoSkill("respirador_1", "Respirador I", "R1", P["mv_r1"], ("pulmao_1",), (("RegeneracaoStaminaParado", 3.0), ("RegeneracaoStaminaAndando", 2.0)), "Regeneração de stamina +3 parado e +2 andando."),
            NodoSkill("nadador_2", "Nadador II", "N2", P["mv_n2"], ("nadador_1",), (("CustoStaminaAguaFunda", -3.0),), "Água funda custa 3 a menos."),
            NodoSkill("corredor_1", "Corredor I", "C1", P["mv_c1"], ("nadador_1",), (("BonusVelocidadeCorridaMin", 0.05), ("BonusVelocidadeCorridaMax", 0.10)), "Bônus de corrida: mínimo +0.05 e máximo +0.10."),
            NodoSkill("velocista_2", "Velocista II", "V2", P["mv_v2"], ("pulmao_2", "nadador_2"), (("VelocidadeBaseTiles", 0.5),), "Velocidade base +0.5."),
            NodoSkill("boxeador_1", "Boxeador I", "B1", P["mv_b1"], ("pulmao_2", "respirador_1"), (("TapaPorSegundo", 0.75),), "Tapas por segundo +0.75."),
            NodoSkill("respirador_2", "Respirador II", "R2", P["mv_r2"], ("respirador_1",), (("RegeneracaoStaminaParado", 3.0), ("RegeneracaoStaminaAndando", 2.0)), "Regeneração de stamina +3 parado e +2 andando."),
            NodoSkill("acelerador_1", "Acelerador I", "A1", P["mv_a1"], ("nadador_2", "corredor_1"), (("TempoAceleracaoCorrida", 0.25), ("TempoDesaceleracaoCorrida", 0.75)), "Aceleração +0.25 e desaceleração +0.75."),
            NodoSkill("corredor_2", "Corredor II", "C2", P["mv_c2"], ("corredor_1",), (("BonusVelocidadeCorridaMin", 0.05), ("BonusVelocidadeCorridaMax", 0.10)), "Bônus de corrida: mínimo +0.05 e máximo +0.10."),
            NodoSkill("pulmao_3", "Pulmão III", "P3", P["mv_p3"], ("velocista_2",), (("StaminaMax", 10.0),), "Stamina máxima +10."),
            NodoSkill("nadador_3", "Nadador III", "N3", P["mv_n3"], ("velocista_2",), (("CustoStaminaAguaFunda", -2.0),), "Água funda custa 2 a menos."),
            NodoSkill("boxeador_2", "Boxeador II", "B2", P["mv_b2"], ("boxeador_1", "respirador_2"), (("TapaPorSegundo", 0.75),), "Tapas por segundo +0.75."),
            NodoSkill("acelerador_2", "Acelerador II", "A2", P["mv_a2"], ("acelerador_1", "corredor_2"), (("TempoAceleracaoCorrida", 0.25), ("TempoDesaceleracaoCorrida", 0.75)), "Aceleração +0.25 e desaceleração +0.75."),
            NodoSkill("respirador_3", "Respirador III", "R3", P["mv_r3"], ("pulmao_3", "boxeador_2"), (("RegeneracaoStaminaParado", 2.0), ("RegeneracaoStaminaAndando", 1.0)), "Regeneração de stamina +2 parado e +1 andando."),
            NodoSkill("corredor_3", "Corredor III", "C3", P["mv_c3"], ("nadador_3", "acelerador_2"), (("BonusVelocidadeCorridaMin", 0.025), ("BonusVelocidadeCorridaMax", 0.05)), "Bônus de corrida: mínimo +0.025 e máximo +0.05."),
            NodoSkill("aquatico_1", "Aquático I", "AQ", P["mv_aq"], ("respirador_3", "corredor_3"), (("CustoStaminaAguaRasa", -3.0),), "Água rasa custa 3 a menos."),
            NodoSkill("velocista_3", "Velocista III", "V3", P["mv_v3"], ("aquatico_1",), (("VelocidadeBaseTiles", 0.5),), "Velocidade base +0.5."),

            # --- inventário ---
            NodoSkill("mochila_1", "Mochila I", "M1", P["in_m1"], ("root",), (("NivelMochila", 1.0),), "Nível da mochila +1."),
            NodoSkill("slots_1", "Slots I", "S1", P["in_s1"], ("mochila_1",), (("LimiteSlotsInventario", 8.0),), "Slots do inventário +8."),
            NodoSkill("pokemons_1", "Pokémons I", "PK1", P["in_pk1"], ("mochila_1",), (("LimitePokemons", 32.0),), "Limite de pokémons +32."),
            NodoSkill("times_1", "Times I", "T1", P["in_t1"], ("pokemons_1",), (("LimiteTimesPokemon", 3.0),), "Times disponíveis +3."),
            NodoSkill("mochila_2", "Mochila II", "M2", P["in_m2"], ("slots_1",), (("NivelMochila", 2.0),), "Nível da mochila +2."),
            NodoSkill("pokemons_2", "Pokémons II", "PK2", P["in_pk2"], ("pokemons_1",), (("LimitePokemons", 32.0),), "Limite de pokémons +32."),
            NodoSkill("slots_2", "Slots II", "S2", P["in_s2"], ("slots_1",), (("LimiteSlotsInventario", 16.0),), "Slots do inventário +16."),
            NodoSkill("times_2", "Times II", "T2", P["in_t2"], ("times_1", "pokemons_2"), (("LimiteTimesPokemon", 3.0),), "Times disponíveis +3."),
            NodoSkill("mochila_3", "Mochila III", "M3", P["in_m3"], ("mochila_2",), (("NivelMochila", 1.0),), "Nível da mochila +1."),
            NodoSkill("pokemons_3", "Pokémons III", "PK3", P["in_pk3"], ("pokemons_2",), (("LimitePokemons", 32.0),), "Limite de pokémons +32."),
            NodoSkill("slots_3", "Slots III", "S3", P["in_s3"], ("mochila_2", "slots_2"), (("LimiteSlotsInventario", 8.0),), "Slots do inventário +8."),
            NodoSkill("times_3", "Times III", "T3", P["in_t3"], ("times_2", "pokemons_3"), (("LimiteTimesPokemon", 4.0),), "Times disponíveis +4."),
            NodoSkill("mochila_4", "Mochila IV", "M4", P["in_m4"], ("mochila_3", "slots_3"), (("NivelMochila", 2.0),), "Nível da mochila +2."),
            NodoSkill("pokemons_4", "Pokémons IV", "PK4", P["in_pk4"], ("times_2",), (("LimitePokemons", 40.0),), "Limite de pokémons +40."),
            NodoSkill("slots_4", "Slots IV", "S4", P["in_s4"], ("slots_2", "times_1"), (("LimiteSlotsInventario", 16.0),), "Slots do inventário +16."),
            NodoSkill("times_4", "Times IV", "T4", P["in_t4"], ("times_3", "pokemons_4"), (("LimiteTimesPokemon", 4.0),), "Times disponíveis +4."),
            NodoSkill("mochila_5", "Mochila V", "M5", P["in_m5"], ("mochila_4",), (("NivelMochila", 1.0),), "Nível da mochila +1."),
            NodoSkill("pokemons_5", "Pokémons V", "PK5", P["in_pk5"], ("mochila_5", "times_4"), (("LimitePokemons", 40.0),), "Limite de pokémons +40."),
            NodoSkill("mochila_6", "Mochila VI", "M6", P["in_m6"], ("pokemons_5",), (("NivelMochila", 2.0),), "Nível da mochila +2."),
            NodoSkill("pokemons_6", "Pokémons VI", "PK6", P["in_pk6"], ("mochila_5", "slots_4"), (("LimitePokemons", 80.0),), "Limite de pokémons +80."),
        ]

    def _montar_nodos_decorativos(self):
        P = self.POS
        return [
            NodoDecorativo("centro_0", P["ct_low"], ("root",)),
            NodoDecorativo("centro_1", P["ct_l1"], ("centro_0",)),
            NodoDecorativo("centro_2", P["ct_r1"], ("centro_0",)),
            NodoDecorativo("centro_3", P["ct_l2a"], ("centro_1",)),
            NodoDecorativo("centro_4", P["ct_l2b"], ("centro_1",)),
            NodoDecorativo("centro_5", P["ct_top_l"], ("centro_3", "centro_4")),
            NodoDecorativo("centro_6", P["ct_top"], ("centro_5", "centro_7")),
            NodoDecorativo("centro_7", P["ct_top_r"], ("centro_2",)),
            NodoDecorativo("centro_8", P["ct_r2a"], ("centro_2",)),
            NodoDecorativo("centro_9", P["ct_r2b"], ("centro_7", "centro_2")),
        ]

    def _montar_pontos_unificados(self):
        pontos = {"root": self.ROOT_POS}
        for nodo in self._nodos:
            pontos[nodo.id] = nodo.pos_norm
        for nodo in self._decorativos:
            pontos[nodo.id] = nodo.pos_norm
        return pontos

    def _perfil(self):
        return getattr(self.Ator, "Perfil", None)

    def _garantir_estado_perfil(self):
        perfil = self._perfil()
        if perfil is None:
            return None

        padroes = {
            "TapaPorSegundo": 2.0,
            "LimitePokemons": 64,
            "LimiteTimesPokemon": 6,
            "HabilidadesAprendidas": [],
        }
        for chave, valor in padroes.items():
            if not hasattr(perfil, chave):
                setattr(perfil, chave, [] if isinstance(valor, list) else valor)
        if not isinstance(perfil.HabilidadesAprendidas, list):
            perfil.HabilidadesAprendidas = list(perfil.HabilidadesAprendidas or [])
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
        return max(0, self._nivel() - len(self._lista_aprendidas()))

    def _status_nodo(self, nodo: NodoSkill):
        aprendidas = self._aprendidas_set()
        if nodo.id in aprendidas:
            return "aprendida"
        if nodo.pais and not any(pai == "root" or pai in aprendidas for pai in nodo.pais):
            return "trancada"
        if self._pontos_disponiveis() <= 0:
            return "sem_ponto"
        return "disponivel"

    def _nodo_por_id(self, nid: str) -> NodoSkill:
        return self._nodos_por_id[nid]

    def _aplicar_delta(self, campo: str, delta: float):
        perfil = self._garantir_estado_perfil()
        if perfil is None:
            return

        valor_atual = float(getattr(perfil, campo, 0.0) or 0.0)
        novo_valor = valor_atual + float(delta)

        if campo in {"NivelMochila", "LimiteSlotsInventario", "LimitePokemons", "LimiteTimesPokemon"}:
            novo_valor = max(1.0, novo_valor)
        elif campo in {"VelocidadeBaseTiles", "StaminaMax", "TapaPorSegundo", "TempoAceleracaoCorrida", "TempoDesaceleracaoCorrida"}:
            novo_valor = max(0.1, novo_valor)
        else:
            novo_valor = max(0.0, novo_valor)

        if campo in {"NivelMochila", "LimiteSlotsInventario", "LimitePokemons", "LimiteTimesPokemon"}:
            setattr(perfil, campo, int(round(novo_valor)))
        else:
            setattr(perfil, campo, float(novo_valor))

        if campo == "StaminaMax":
            perfil.Stamina = min(float(getattr(perfil, "Stamina", 0.0)) + float(delta), float(perfil.StaminaMax))

        inventario = getattr(self.Ator, "Inventario", None)
        if inventario is not None:
            if campo in {"NivelMochila", "LimiteSlotsInventario"}:
                capacidade = max(1, int(getattr(perfil, "NivelMochila", 1))) * 100
                slots = max(1, int(getattr(perfil, "LimiteSlotsInventario", 32)))
                if hasattr(inventario, "definir_limite_itens"):
                    inventario.definir_limite_itens(capacidade)
                else:
                    inventario.LimiteItens = capacidade
                if hasattr(inventario, "definir_limite_slots"):
                    inventario.definir_limite_slots(slots)
                else:
                    inventario.LimiteSlots = slots
                    if hasattr(inventario, "Itens") and isinstance(inventario.Itens, list) and len(inventario.Itens) < slots:
                        inventario.Itens.extend([None] * (slots - len(inventario.Itens)))
            if campo == "LimitePokemons":
                inventario.LimitePokemons = int(getattr(perfil, "LimitePokemons", 64))
            if campo == "LimiteTimesPokemon":
                inventario.LimiteTimesPokemon = int(getattr(perfil, "LimiteTimesPokemon", 6))
                if hasattr(inventario, "TimesPokemons") and isinstance(inventario.TimesPokemons, list):
                    while len(inventario.TimesPokemons) < inventario.LimiteTimesPokemon:
                        inventario.TimesPokemons.append({"Nome": f"Time {len(inventario.TimesPokemons) + 1}", "Slots": [None] * 6})

        controle = getattr(self.Ator, "Controle", None)
        if controle is not None and campo == "VelocidadeBaseTiles":
            controle.VelocidadeTiles = float(getattr(perfil, "VelocidadeBaseTiles", controle.VelocidadeTiles))

    def aprender(self, nid: str):
        nodo = self._nodo_por_id(nid)
        if self._status_nodo(nodo) != "disponivel":
            return False

        for campo, delta in nodo.efeitos:
            self._aplicar_delta(campo, delta)

        aprendidas = self._lista_aprendidas()
        if nid not in aprendidas:
            aprendidas.append(nid)
            perfil = self._perfil()
            if perfil is not None:
                setattr(perfil, "_habilidades_aprendidas_dirty", True)
        return True

    def _estilo_nodo(self, status: str):
        estilo = {
            "radius": 999,
            "border_width": 3,
            "hover_scale": 1.05,
            "press_scale": 0.95,
            "text_style": {
                "size": 17,
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
            estilo.update({
                "bg": (41, 142, 99),
                "bg_hover": (54, 162, 114),
                "bg_pressed": (32, 107, 76),
                "border": (197, 255, 226),
                "border_hover": (239, 255, 246),
            })
        elif status == "disponivel":
            estilo.update({
                "bg": (163, 120, 34),
                "bg_hover": (196, 145, 44),
                "bg_pressed": (131, 96, 27),
                "border": (255, 232, 186),
                "border_hover": (255, 248, 224),
            })
        else:
            estilo.update({
                "bg": (56, 64, 84),
                "bg_hover": (56, 64, 84),
                "bg_pressed": (56, 64, 84),
                "border": (103, 116, 146),
                "border_hover": (103, 116, 146),
                "bg_disabled": (46, 53, 70),
                "border_disabled": (96, 106, 134),
                "text_disabled": (184, 192, 214),
            })
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
        gx = self._graph_rect.x + int(pos_norm[0] * self._graph_rect.width)
        gy = self._graph_rect.y + int(pos_norm[1] * self._graph_rect.height)
        return gx, gy

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
        self._tooltip_pos = (self._rect.right - 380, self._rect.bottom - 122)

        def _fechar(_jogo, _botao):
            self._solicitou_fechar = True

        self._botao_fechar = Botao(
            pygame.Rect(self._rect.right - 68, self._rect.y + 16, 52, 52),
            "X",
            execute=_fechar,
            style={
                "radius": 18,
                "bg": (113, 32, 45),
                "bg_hover": (145, 40, 59),
                "bg_pressed": (86, 23, 34),
                "border": (255, 195, 203),
                "border_hover": (255, 236, 240),
                "text_style": {"size": 26, "outline_thickness": 1, "shadow": False},
            },
        )
        self._botao_fechar.set_tooltip(Tooltip(titulo="Fechar", descricao="Fechar a árvore de habilidades.", pos_fixa=self._tooltip_pos, largura_max=240))

        lado = max(36, int(self._graph_rect.width * 0.028) + 2)
        self._botoes_nodos = {}
        for nodo in self._nodos:
            cx, cy = self._ponto_tela(nodo.id)
            rect_botao = pygame.Rect(0, 0, lado, lado)
            rect_botao.center = (cx, cy)

            def _acao(_jogo, _botao, nid=nodo.id):
                self.aprender(nid)

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

        info = f"Nível {self._nivel()}  •  Aprendidas {len(self._lista_aprendidas())}  •  Pontos {self._pontos_disponiveis()}"
        self.txt_info.set_text(info)
        self.txt_info.set_pos((self._rect.x + 20, self._rect.y + 56))
        self.txt_info.draw(tela)

    def _desenhar_raiz(self, tela):
        raiz = self._ponto_tela("root")
        raio = max(15, int(self._graph_rect.width * 0.018))
        pygame.draw.circle(tela, (49, 101, 176), raiz, raio)
        pygame.draw.circle(tela, (205, 227, 255), raiz, max(2, raio // 6))

    def _cor_aresta(self, origem_id: str, destino_id: str):
        aprendidas = self._aprendidas_set()
        decorativos = {n.id for n in self._decorativos}

        if origem_id == "root" or destino_id == "root" or origem_id in decorativos or destino_id in decorativos:
            return (86, 107, 152)

        if origem_id in aprendidas and destino_id in aprendidas:
            return (214, 229, 255)
        return (86, 107, 152)

    def _desenhar_conexoes(self, tela):
        # decorativos e skills usam a mesma regra: desenha linha para cada pai.
        for nodo in [*self._decorativos, *self._nodos]:
            origem = self._ponto_tela(nodo.id)
            for pai in nodo.pais:
                destino = self._ponto_tela(pai)
                pygame.draw.line(tela, self._cor_aresta(nodo.id, pai), destino, origem, 5)

    def _desenhar_decorativos(self, tela):
        raio = max(14, int(self._graph_rect.width * 0.016))
        estilo_txt = {
            "size": 22,
            "align": "center",
            "outline": True,
            "outline_thickness": 1,
            "outline_color": (0, 0, 0),
            "shadow": False,
        }
        for nodo in self._decorativos:
            ponto = self._ponto_tela(nodo.id)
            pygame.draw.circle(tela, (48, 54, 74), ponto, raio)
            pygame.draw.circle(tela, (136, 145, 178), ponto, 2)
            Texto(nodo.rotulo, pos=ponto, style=estilo_txt).draw(tela)

        self.txt_centro.set_pos((self._graph_rect.centerx, self._graph_rect.centery + int(self._graph_rect.height * 0.22)))
        self.txt_centro.draw(tela)

    def _desenhar_nodos(self, tela, eventos, dt):
        Botao.iniciar_camada_tooltips()
        for nodo in self._nodos:
            status = self._status_nodo(nodo)
            botao = self._botoes_nodos[nodo.id]
            botao.set_style(**self._estilo_nodo(status))
            botao.set_habilitado(status in {"aprendida", "disponivel"})
            botao.set_execute(None if status == "aprendida" else (lambda _jogo, _botao, nid=nodo.id: self.aprender(nid)))
            if botao.tooltip is not None:
                botao.tooltip.definir_posicao_fixa(self._tooltip_pos)
                botao.tooltip.definir_conteudo(titulo=nodo.nome, descricao=nodo.descricao)
            botao.render(tela, eventos, dt, None)
        self._botao_fechar.render(tela, eventos, dt, None)
        Botao.finalizar_camada_tooltips(tela)

    def renderizar(self, tela, rect, eventos=None, dt=0.0):
        eventos = eventos or []
        self._solicitou_fechar = False
        self._reconstruir_layout(pygame.Rect(rect))
        self._desenhar_fundo(tela)
        self._desenhar_textos(tela)
        self._desenhar_conexoes(tela)
        self._desenhar_raiz(tela)
        self._desenhar_decorativos(tela)
        self._desenhar_nodos(tela, eventos, dt)
        return self._solicitou_fechar
