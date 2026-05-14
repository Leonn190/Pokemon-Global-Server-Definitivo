from __future__ import annotations

import pygame

from Codigo.ModulosGerais.LoaderTabelas import carregar_csv_dict

from Codigo.ModulosMundo.Geradores.ItemInventario import ItemInventario
from Codigo.ModulosMundo.Geradores.Doce import Doce
from Codigo.ModulosMundo.Geradores.PokemonInventario import PokemonInventario
from Codigo.Paineis.Container import Container
from Codigo.Prefabs.Botao import BotaoSelecao
from Codigo.Prefabs.Texto import Texto


class PainelAuxiliarPoke:
    ABAS = ("times", "pokemons", "equipaveis", "pocoes")

    def __init__(self, rect: pygame.Rect):
        self.Rect = pygame.Rect(rect)
        self.RectAbas = pygame.Rect(rect.x, rect.y, rect.width, 32)
        self._aba_ativa = "times"
        self._botoes: dict[str, BotaoSelecao] = {}
        self._container: Container | None = None
        self._itens_filtro: list = []
        self._indices_inventario: list[int | None] = []
        self._assinatura_sincronizada = None
        self._fonte = Texto("", style={"size": 14, "outline": True, "outline_thickness": 1, "outline_color": (8, 12, 20)})
        self._configurar_layout()
        self._mapa_estilos = self._carregar_mapa_estilos()
        self._pokemon_analisado = None

    @staticmethod
    def _carregar_mapa_estilos():
        base = {}
        try:
            for linha in carregar_csv_dict('Pokemon Global Server - Itens.csv'):
                    estilo = str(linha.get('Estilo') or '').strip().lower()
                    nome = str(linha.get('Nome') or '').strip().lower()
                    code = str(linha.get('Code') or '').strip()
                    if nome:
                        base[('nome', nome)] = estilo
                    if code:
                        base[('code', code)] = estilo
        except OSError:
            pass
        return base

    @property
    def aba_ativa(self) -> str:
        return self._aba_ativa

    def configurar_rects(self, rect_abas: pygame.Rect, rect_conteudo: pygame.Rect):
        self.RectAbas = pygame.Rect(rect_abas)
        self.Rect = pygame.Rect(rect_conteudo)
        self._configurar_layout()

    def _configurar_layout(self):
        antigos = self._botoes
        self._botoes = {}
        gap = 8
        margem = 12
        largura = max(68, int((self.Rect.width - margem * 2 - gap * 3) / 4))
        y = self.RectAbas.y + max(0, (self.RectAbas.height - 30) // 2)
        x = self.RectAbas.x + margem
        for nome in self.ABAS:
            rect = pygame.Rect(x, y, largura, 30)
            botao = antigos.get(nome)
            if botao is None:
                botao = BotaoSelecao(
                    rect,
                    self._titulo_aba(nome),
                    execute=lambda _jogo, _botao, aba=nome: self._selecionar_aba(aba),
                    style={
                        "radius": 10,
                        "border_width": 2,
                        "bg": (31, 44, 72),
                        "bg_hover": (46, 66, 108),
                        "bg_pressed": (24, 35, 58),
                        "border": (76, 102, 148),
                        "border_hover": (185, 210, 255),
                        "hover_scale": 1.0,
                        "press_scale": 0.98,
                        "text_style": {"size": 15, "outline_thickness": 1, "shadow": False},
                    },
                    selecionado=(nome == self._aba_ativa),
                )
            else:
                botao.base_rect = pygame.Rect(rect)
                botao.rect = pygame.Rect(rect)
            botao.set_selecionado(nome == self._aba_ativa)
            self._botoes[nome] = botao
            x += largura + gap

    def _selecionar_aba(self, aba: str):
        if aba not in self.ABAS:
            return
        self._aba_ativa = aba
        self._assinatura_sincronizada = None
        for nome, botao in self._botoes.items():
            botao.set_selecionado(nome == aba)

    def _titulo_aba(self, aba: str) -> str:
        return {
            "times": "Times",
            "pocoes": "Poções",
            "pokemons": "Pokémons",
            "equipaveis": "Equipáveis",
        }.get(aba, aba.title())

    def _filtrar_itens(self, itens, estilo: str):
        alvo = str(estilo or "").strip().lower()
        saida = []
        indices = []
        for idx, item in enumerate(itens or []):
            if not isinstance(item, dict):
                continue
            nome = str(item.get('Nome') or item.get('nome') or '').strip().lower()
            code = str(item.get('Code') or item.get('code') or '').strip()
            est = self._mapa_estilos.get(('code', code)) or self._mapa_estilos.get(('nome', nome)) or str(item.get("Estilo") or item.get("estilo") or "").strip().lower()
            if (alvo == "pocoes" and est == "poção") or (alvo == "equipaveis" and est == "equipavel"):
                saida.append(item)
                indices.append(idx)
        return saida, indices

    def definir_pokemon_analisado(self, pokemon):
        self._pokemon_analisado = pokemon if isinstance(pokemon, dict) else None
        self._assinatura_sincronizada = None

    def sincronizar(self, inventario, area_conteudo: pygame.Rect, area_abas: pygame.Rect | None = None):
        if area_abas is not None:
            self.configurar_rects(area_abas, area_conteudo)
        else:
            self.Rect = pygame.Rect(area_conteudo)
        area_sig = (self.Rect.x, self.Rect.y, self.Rect.width, self.Rect.height, self.RectAbas.x, self.RectAbas.y, self.RectAbas.width, self.RectAbas.height)
        inventario_itens = getattr(inventario, "Itens", []) or []
        inventario_pokemons = getattr(inventario, "Pokemons", []) or []
        assinatura_itens = tuple(
            (
                str(item.get('Code') or item.get('Nome') or ''),
                int(item.get('quantidade', 1) or 1),
            )
            for item in inventario_itens if isinstance(item, dict)
        )
        assinatura = (self._aba_ativa, area_sig, id(inventario_itens), len(inventario_itens), assinatura_itens, id(inventario_pokemons), len(inventario_pokemons))
        if assinatura == self._assinatura_sincronizada:
            return
        self._assinatura_sincronizada = assinatura

        if self._aba_ativa == "pokemons":
            self._itens_filtro = [p for p in list(getattr(inventario, "Pokemons", []) or []) if p is not None]
            self._indices_inventario = []
            renderizador = PokemonInventario
            colunas = 5
            gap = 10
            slot_px = 54
        elif self._aba_ativa in ("pocoes", "equipaveis"):
            self._itens_filtro, self._indices_inventario = self._filtrar_itens(getattr(inventario, "Itens", []), self._aba_ativa)
            if self._aba_ativa == "pocoes":
                estado = self._pokemon_analisado.get("estado") if isinstance(getattr(self, "_pokemon_analisado", None), dict) and isinstance(self._pokemon_analisado.get("estado"), dict) else self._pokemon_analisado
                grupo = str((estado or {}).get("grupo") or "").strip()
                doces = getattr(inventario, "Doces", {})
                qtd_doces = int((doces or {}).get(grupo, 0) or 0)
                if grupo and qtd_doces > 0:
                    self._itens_filtro = [{"Nome": f"Doce {grupo}", "Estilo": "doce", "Grupo": grupo, "quantidade": qtd_doces}] + self._itens_filtro
                    self._indices_inventario = [None] + self._indices_inventario
            renderizador = ItemInventario
            colunas = 5
            gap = 10
            slot_px = 54
            if self._aba_ativa == "pocoes":
                renderizador = Doce
        else:
            self._itens_filtro = []
            self._indices_inventario = []
            self._container = None
            return

        slots_total = max(1, len(self._itens_filtro))
        area_grid = pygame.Rect(self.Rect)
        linhas_visiveis = max(1, min(8, (slots_total + colunas - 1) // colunas))

        if self._container is None:
            self._container = Container(
                area_grid,
                self._itens_filtro,
                slots_total=slots_total,
                colunas=colunas,
                linhas_visiveis=linhas_visiveis,
                slot_px=slot_px,
                gap=gap,
                cor_fundo=(18, 26, 44, 242),
                cor_borda=(66, 88, 136),
                borda=2,
                raio=16,
                stackable=False,
                renderizador_item=renderizador,
            )
        else:
            self._container.Itens = self._itens_filtro
            self._container.SlotsTotal = slots_total
            self._container.Colunas = colunas
            self._container.LinhasVisiveis = linhas_visiveis
            self._container.SlotPx = slot_px
            self._container.Gap = gap
            self._container.RenderizadorItem = renderizador
            self._container.configurar_rect(area_grid)

    def marcar_sujo(self):
        self._assinatura_sincronizada = None

    def processar_eventos(self, eventos):
        if self._aba_ativa != "times" and self._container is not None:
            self._container._processar_scroll(eventos)
        return False

    def alvo_no_mouse(self, pos):
        if self._container is None:
            return None
        idx = self._container.indice_no_mouse(pos)
        if idx is None:
            return None
        item = self._container.item_por_slot_visual(idx)
        if item is None:
            return None
        return ("aux", self._aba_ativa, idx)

    def item_por_visual(self, indice_visual):
        if indice_visual is None:
            return None
        idx = int(indice_visual)
        if not (0 <= idx < len(self._itens_filtro)):
            return None
        return self._itens_filtro[idx]

    def slot_inventario_por_visual(self, indice_visual):
        if indice_visual is None or not (0 <= int(indice_visual) < len(self._indices_inventario)):
            return None
        return self._indices_inventario[int(indice_visual)]

    def desenhar(self, tela: pygame.Surface, eventos=None, dt: float = 0.0):
        eventos = eventos or []
        for botao in self._botoes.values():
            botao.render(tela, eventos, dt, JOGO=None)

        if self._aba_ativa == "times":
            return
        if self._container is not None:
            self._container.desenhar(tela)
