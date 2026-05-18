from __future__ import annotations

import pygame

from Codigo.Prefabs.Barra import BarraEditavel
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Painel import PainelRolavel
from Codigo.Prefabs.Texto import Texto
from Codigo.Telas.Subtelas.Subtela import Subtela


_COR_FUNDO_MODAL = (11, 16, 30)
_COR_PAINEL = (18, 25, 44, 238)
_COR_PAINEL_BORDA = (255, 220, 120)
_COR_CARD = (26, 36, 62, 232)
_COR_CARD_BORDA = (76, 96, 140)
_COR_CARD_BORDA_HOVER = (255, 220, 120)
_COR_TEXTO_APAGADO = (177, 190, 218)


ESTILO_BOTAO_MUNDO = {
    "radius": 16,
    "border_width": 2,
    "border": (18, 24, 44),
    "border_hover": (255, 220, 120),
    "bg": (40, 56, 98),
    "bg_hover": (58, 79, 136),
    "bg_pressed": (34, 47, 82),
    "hover_scale": 1.03,
    "hover_speed": 10.0,
    "press_scale": 0.97,
    "text_style": {
        "size": 28,
        "color": (245, 246, 255),
        "hover_color": (255, 235, 130),
        "hover_speed": 18.0,
        "align": "center",
        "outline": True,
        "outline_color": (0, 0, 0),
        "outline_thickness": 1,
        "shadow": True,
        "shadow_color": (0, 0, 0, 160),
        "shadow_offset": (2, 2),
    },
}


TAMANHOS_MUNDO = [
    {"id": "pequeno", "rotulo": "Pequeno", "width": 7000, "height": 7000},
    {"id": "regular", "rotulo": "Regular", "width": 10000, "height": 10000},
    {"id": "grande", "rotulo": "Grande", "width": 12000, "height": 12000},
]

BIOMAS_CONTROLE = [
    ("FIELD", "Campo"),
    ("FOREST", "Floresta"),
    ("DESERT", "Deserto"),
    ("SNOW", "Neve"),
    ("MAGIC", "Magico"),
    ("VOLCANIC", "Vulcanico"),
    ("SWAMP", "Pantano"),
]

RECURSOS_CONTROLE = [
    ("arvores", "Arvores", "TREE, TREE_TROMBOSA, PALM e PINE."),
    ("pedras_minerios", "Pedras e minerios", "ROCK, COAL, IRON, COPPER e gemas comuns."),
    ("plantas_decorativas", "Plantas decorativas", "BUSH, FLOWER e PLANT."),
    ("recursos_raros", "Recursos raros", "Ouro, diamante, rubi, esmeralda, safira, topazio e similares."),
]

VALORES_PADRAO = {
    "tamanho_mundo": 1,
    "agua": 50,
    "rios_quantidade": 50,
    "rios_comprimento": 50,
    "rios_largura": 50,
    "lagos": 50,
    "bioma_FIELD": 50,
    "bioma_FOREST": 50,
    "bioma_DESERT": 50,
    "bioma_SNOW": 50,
    "bioma_MAGIC": 50,
    "bioma_VOLCANIC": 50,
    "bioma_SWAMP": 50,
    "recursos_arvores": 50,
    "recursos_pedras_minerios": 50,
    "recursos_plantas_decorativas": 50,
    "recursos_recursos_raros": 50,
    "vilas": 50,
}


class _BarraEditavelLocal(BarraEditavel):
    def render_local(self, tela, eventos, dt=0.0, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        alterou = False

        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and self.rect.collidepoint(mouse_pos):
                self.arrastando = True
                self._estava_arrastando = True
                valor_antes = self.valor
                self._valor_por_mouse(evento.pos[0])
                alterou = alterou or (self.valor != valor_antes)

            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                if self._estava_arrastando:
                    valor_antes = self.valor
                    self._encaixar_no_ponto_mais_proximo()
                    alterou = alterou or (self.valor != valor_antes)
                self.arrastando = False
                self._estava_arrastando = False

            if evento.type == pygame.MOUSEMOTION and self.arrastando:
                valor_antes = self.valor
                self._valor_por_mouse(evento.pos[0])
                alterou = alterou or (self.valor != valor_antes)

        self.atualizar(dt)
        self._desenhar_barra(tela)

        percentual = _clamp((self.valor - self.minimo) / float(max(self.maximo - self.minimo, 1)), 0.0, 1.0)
        x_manopla = self.rect.x + int(self.rect.width * percentual)
        x_manopla = _clamp(x_manopla, self.rect.x, self.rect.right)
        pygame.draw.circle(tela, self.cor_manopla, (int(x_manopla), self.rect.centery), self.rect.height // 2 + 4)
        pygame.draw.circle(tela, (30, 30, 45), (int(x_manopla), self.rect.centery), self.rect.height // 2 + 4, 2)
        return alterou


def _clamp(valor, minimo, maximo):
    return minimo if valor < minimo else maximo if valor > maximo else valor


def _texto_estilo(size=24, align="topleft", color=(245, 246, 255), outline=True):
    return {
        "size": int(size),
        "align": align,
        "color": color,
        "outline": bool(outline),
        "outline_color": (0, 0, 0),
        "outline_thickness": 1,
        "shadow": True,
        "shadow_color": (0, 0, 0, 150),
        "shadow_offset": (1, 1),
    }


def _traduzir_eventos_mouse(eventos, origem_x, origem_y, scroll_x, scroll_y):
    traduzidos = []
    tipos_mouse = {pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION}

    for evento in eventos:
        if evento.type not in tipos_mouse:
            continue

        dados = {}
        for nome in ("button", "buttons", "rel", "touch", "window"):
            if hasattr(evento, nome):
                dados[nome] = getattr(evento, nome)

        pos = getattr(evento, "pos", None)
        if pos is not None:
            dados["pos"] = (int(pos[0] - origem_x + scroll_x), int(pos[1] - origem_y + scroll_y))
        else:
            mx, my = pygame.mouse.get_pos()
            dados["pos"] = (int(mx - origem_x + scroll_x), int(my - origem_y + scroll_y))

        traduzidos.append(pygame.event.Event(evento.type, dados))

    return traduzidos


class _ControleSliderMundo:
    ALTURA = 116

    def __init__(
        self,
        chave,
        titulo,
        valor=50,
        minimo=0,
        maximo=100,
        casas_decimais=0,
        descricao="",
        opcoes=None,
    ):
        self.chave = chave
        self.titulo = titulo
        self.descricao = descricao
        self.opcoes = list(opcoes or [])
        self.rect = pygame.Rect(0, 0, 100, self.ALTURA)
        self.barra = _BarraEditavelLocal(
            pygame.Rect(0, 0, 100, 24),
            "",
            valor,
            minimo,
            maximo,
            casas_decimais=casas_decimais,
        )
        self.barra.cor_fundo = (18, 24, 42)
        self.barra.cor_preenchimento = (79, 160, 255)
        self.barra.cor_borda = (195, 215, 255)
        self.barra.cor_manopla = (255, 244, 190)

        self._txt_titulo = Texto(titulo, style=_texto_estilo(25, "topleft"))
        self._txt_valor = Texto("", style=_texto_estilo(23, "topright", color=(255, 235, 130)))
        self._txt_desc = Texto(descricao, style=_texto_estilo(19, "topleft", color=_COR_TEXTO_APAGADO, outline=True))

    def configurar_rect(self, rect):
        self.rect = pygame.Rect(rect)
        margem_x = 22
        self.barra.rect = pygame.Rect(
            self.rect.x + margem_x,
            self.rect.y + 68,
            max(80, self.rect.width - margem_x * 2),
            24,
        )
        self.barra.base_rect = pygame.Rect(self.barra.rect)

    def valor(self):
        if self.opcoes:
            return int(round(self.barra.valor))
        return int(round(self.barra.valor))

    def set_valor(self, valor):
        self.barra.set_valor(valor, animar=False)
        if self.opcoes:
            self.barra.set_valor(int(round(self.barra.valor)), animar=False)

    def _formatar_valor(self):
        if self.opcoes:
            indice = int(_clamp(round(self.barra.valor), 0, len(self.opcoes) - 1))
            opcao = self.opcoes[indice]
            return str(opcao.get("rotulo", opcao.get("id", indice)))
        return f"{int(round(self.barra.valor))}%"

    def render(self, tela, eventos, dt, mouse_local):
        hover = self.rect.collidepoint(mouse_local)
        borda = _COR_CARD_BORDA_HOVER if hover else _COR_CARD_BORDA
        pygame.draw.rect(tela, _COR_CARD, self.rect, border_radius=16)
        pygame.draw.rect(tela, borda, self.rect, width=2, border_radius=16)

        self._txt_titulo.set_pos((self.rect.x + 20, self.rect.y + 18))
        self._txt_titulo.draw(tela)

        self._txt_valor.set_text(self._formatar_valor())
        self._txt_valor.set_pos((self.rect.right - 20, self.rect.y + 18))
        self._txt_valor.draw(tela)

        if self.descricao:
            self._txt_desc.set_pos((self.rect.x + 20, self.rect.y + 43))
            self._txt_desc.draw(tela)

        alterou = self.barra.render_local(tela, eventos, dt, mouse_pos=mouse_local)
        if self.opcoes and alterou:
            self.barra.set_valor(int(round(self.barra.valor)), animar=False)
        return alterou


class _PainelConfiguracaoMundo(PainelRolavel):
    def __init__(self, rect, controles):
        self.controles = list(controles)
        self.padding = 24
        self.espaco = 14
        super().__init__(
            rect,
            area_real=(0, 0, rect[2], 100),
            velocidade_scroll=42,
            cor_fundo=_COR_PAINEL,
            cor_borda=(74, 92, 130),
            borda=2,
            raio=18,
        )
        self.recalcular_layout()

    def recalcular_layout(self):
        largura = max(320, self.rect.width)
        y = self.padding
        for controle in self.controles:
            controle.configurar_rect(pygame.Rect(self.padding, y, largura - self.padding * 2, controle.ALTURA))
            y += controle.ALTURA + self.espaco
        altura = y + self.padding
        self.definir_area_real(largura, altura)

    def configurar_rect(self, rect):
        self.rect = pygame.Rect(rect)
        self._recriar_surface_viewport()
        self.recalcular_layout()
        self._clamp_scroll()

    def render(self, tela, eventos, dt, jogo=None):
        if not self.Visivel:
            return False

        self._garantir_surfaces()
        self._processar_scroll(eventos)
        self._garantir_surfaces()

        mouse_global = pygame.mouse.get_pos()
        mouse_local = (
            int(mouse_global[0] - self.rect.x + self.ScrollX),
            int(mouse_global[1] - self.rect.y + self.ScrollY),
        )
        eventos_local = _traduzir_eventos_mouse(eventos, self.rect.x, self.rect.y, self.ScrollX, self.ScrollY)

        self._surface_conteudo.fill((0, 0, 0, 0))
        pygame.draw.rect(self._surface_conteudo, self.CorFundo, self.AreaReal, border_radius=self.Raio)

        alterou = False
        for controle in self.controles:
            alterou = controle.render(self._surface_conteudo, eventos_local, dt, mouse_local) or alterou

        self._surface_viewport.fill((0, 0, 0, 0))
        self._surface_viewport.blit(self._surface_conteudo, (-self.ScrollX, -self.ScrollY))
        self._aplicar_mascara_raio(self._surface_viewport)
        tela.blit(self._surface_viewport, self.rect.topleft)

        if self.Borda > 0:
            pygame.draw.rect(tela, self.CorBorda, self.rect, self.Borda, border_radius=self.Raio)
        self._desenhar_scrollbar(tela, dt)
        return alterou


class SubtelaMundo(Subtela):
    """Subtela de configuração avançada de criação de mundo por servidor.

    A classe só cuida da interface. A integração com as regras reais do servidor
    deve ser feita por callback externo via salvar_callback.
    """

    bloquear_input_fundo = True
    usar_overlay_gerenciador = True
    alpha_overlay = 190
    camada_render = "hud"

    def __init__(self, tela_size, valores_iniciais=None, salvar_callback=None, fechar_callback=None):
        super().__init__()
        self.salvar_callback = salvar_callback
        self.fechar_callback = fechar_callback
        self._cache_size = (0, 0)
        self._valores = self._normalizar_valores(valores_iniciais)

        self.caixa = pygame.Rect(0, 0, 100, 100)
        self.titulo = Texto("Configuracao de Mundo", style=_texto_estilo(42, "center"))
        self.subtitulo = Texto(
            "Ajustes avancados usados na proxima criacao do mundo deste servidor.",
            style=_texto_estilo(22, "center", color=_COR_TEXTO_APAGADO),
        )
        self._controles = self._criar_controles()
        self.painel = _PainelConfiguracaoMundo(pygame.Rect(0, 0, 400, 400), self._controles)
        self.botao_fechar = None
        self.botao_resetar = None
        self.botao_salvar = None

        self._rebuild_cache(tela_size)

    def _normalizar_valores(self, valores):
        saida = dict(VALORES_PADRAO)
        if not isinstance(valores, dict):
            return saida

        for chave in list(saida.keys()):
            if chave in valores:
                saida[chave] = valores[chave]

        tamanho = valores.get("tamanho_mundo")
        if isinstance(tamanho, dict):
            tamanho = tamanho.get("id") or tamanho.get("opcao") or tamanho.get("valor")
        if isinstance(tamanho, str):
            ids = [t["id"] for t in TAMANHOS_MUNDO]
            if tamanho in ids:
                saida["tamanho_mundo"] = ids.index(tamanho)
        elif isinstance(tamanho, (int, float)):
            saida["tamanho_mundo"] = int(_clamp(round(tamanho), 0, len(TAMANHOS_MUNDO) - 1))

        agua = valores.get("agua")
        if isinstance(agua, (int, float)):
            saida["agua"] = int(_clamp(round(agua), 0, 100))

        rios = valores.get("rios")
        if isinstance(rios, dict):
            for origem, destino in (
                ("quantidade", "rios_quantidade"),
                ("comprimento", "rios_comprimento"),
                ("largura", "rios_largura"),
            ):
                if isinstance(rios.get(origem), (int, float)):
                    saida[destino] = int(_clamp(round(rios[origem]), 0, 100))

        biomas = valores.get("biomas")
        if isinstance(biomas, dict):
            for biome_id, _rotulo in BIOMAS_CONTROLE:
                valor = biomas.get(biome_id)
                if isinstance(valor, (int, float)):
                    saida[f"bioma_{biome_id}"] = int(_clamp(round(valor), 0, 100))

        recursos = valores.get("recursos")
        if isinstance(recursos, dict):
            for recurso_id, _rotulo, _desc in RECURSOS_CONTROLE:
                valor = recursos.get(recurso_id)
                if isinstance(valor, (int, float)):
                    saida[f"recursos_{recurso_id}"] = int(_clamp(round(valor), 0, 100))

        for chave in saida:
            if chave == "tamanho_mundo":
                saida[chave] = int(_clamp(round(float(saida[chave])), 0, len(TAMANHOS_MUNDO) - 1))
            else:
                saida[chave] = int(_clamp(round(float(saida[chave])), 0, 100))
        return saida

    def _criar_controles(self):
        controles = [
            _ControleSliderMundo(
                "tamanho_mundo",
                "Tamanho do mundo",
                self._valores["tamanho_mundo"],
                0,
                2,
                0,
                "Pequeno 7000x7000, Regular 10000x10000 ou Grande 12000x12000.",
                opcoes=TAMANHOS_MUNDO,
            ),
            _ControleSliderMundo("agua", "Quantidade de agua", self._valores["agua"], descricao="Afeta nivel do mar, bordas de oceano e agua rasa/profunda."),
            _ControleSliderMundo("rios_quantidade", "Quantidade de rios", self._valores["rios_quantidade"], descricao="Controla quantas fontes de rios o mundo tenta gerar."),
            _ControleSliderMundo("rios_comprimento", "Comprimento dos rios", self._valores["rios_comprimento"], descricao="Controla se os rios tendem a terminar cedo ou atravessar mais terreno."),
            _ControleSliderMundo("rios_largura", "Largura dos rios", self._valores["rios_largura"], descricao="Controla a faixa de largura minima e maxima dos rios."),
            _ControleSliderMundo("lagos", "Quantidade de lagos", self._valores["lagos"], descricao="Traduz para limiar de lago, umidade minima e altitude perto do mar."),
        ]

        for biome_id, rotulo in BIOMAS_CONTROLE:
            controles.append(
                _ControleSliderMundo(
                    f"bioma_{biome_id}",
                    f"Frequencia do bioma: {rotulo}",
                    self._valores[f"bioma_{biome_id}"],
                    descricao="Ajusta o peso relativo do bioma sem expor temperatura/umidade tecnica.",
                )
            )

        for recurso_id, rotulo, descricao in RECURSOS_CONTROLE:
            controles.append(
                _ControleSliderMundo(
                    f"recursos_{recurso_id}",
                    rotulo,
                    self._valores[f"recursos_{recurso_id}"],
                    descricao=descricao,
                )
            )

        controles.append(
            _ControleSliderMundo(
                "vilas",
                "Quantidade de vilas",
                self._valores["vilas"],
                descricao="Controla a faixa de min/max de vilas por mundo, mantendo regras de distancia.",
            )
        )
        return controles

    def _rebuild_cache(self, tela_size):
        self._cache_size = tuple(tela_size)
        largura, altura = tela_size

        self.caixa = pygame.Rect(0, 0, min(1180, int(largura * 0.88)), min(840, int(altura * 0.86)))
        self.caixa.center = (largura // 2, altura // 2)

        self.titulo.set_pos((self.caixa.centerx, self.caixa.top + 42))
        self.subtitulo.set_pos((self.caixa.centerx, self.caixa.top + 80))

        x_painel = self.caixa.left + 34
        y_painel = self.caixa.top + 112
        w_painel = self.caixa.width - 68
        h_painel = self.caixa.height - 222
        self.painel.configurar_rect(pygame.Rect(x_painel, y_painel, w_painel, h_painel))

        estilo_x = dict(ESTILO_BOTAO_MUNDO)
        estilo_x["text_style"] = dict(ESTILO_BOTAO_MUNDO["text_style"])
        estilo_x["text_style"]["size"] = 24

        self.botao_fechar = Botao(
            pygame.Rect(self.caixa.right - 64, self.caixa.top + 22, 42, 42),
            "X",
            execute=self._fechar,
            style=estilo_x,
        )

        estilo_acao = dict(ESTILO_BOTAO_MUNDO)
        estilo_acao["text_style"] = dict(ESTILO_BOTAO_MUNDO["text_style"])
        estilo_acao["text_style"]["size"] = 30

        largura_botao = 260
        altura_botao = 70
        y_botoes = self.caixa.bottom - 88
        self.botao_resetar = Botao(
            pygame.Rect(self.caixa.centerx - largura_botao - 18, y_botoes, largura_botao, altura_botao),
            "Resetar",
            execute=self._resetar,
            style=estilo_acao,
        )
        self.botao_salvar = Botao(
            pygame.Rect(self.caixa.centerx + 18, y_botoes, largura_botao, altura_botao),
            "Salvar",
            execute=self._salvar,
            style=estilo_acao,
        )

    def _fechar(self, jogo, botao):
        if callable(self.fechar_callback):
            self.fechar_callback()
        self.encerrada = True

    def _resetar(self, jogo, botao):
        self._valores = dict(VALORES_PADRAO)
        for controle in self._controles:
            controle.set_valor(self._valores.get(controle.chave, 50))

    def _salvar(self, jogo, botao):
        payload = self.obter_configuracao()
        retorno = None
        if callable(self.salvar_callback):
            retorno = self.salvar_callback(payload)
        if retorno is False:
            return
        self.encerrada = True

    def obter_configuracao(self):
        valores = {controle.chave: controle.valor() for controle in self._controles}
        indice_tamanho = int(_clamp(valores["tamanho_mundo"], 0, len(TAMANHOS_MUNDO) - 1))
        tamanho = dict(TAMANHOS_MUNDO[indice_tamanho])

        biomas = {}
        for biome_id, _rotulo in BIOMAS_CONTROLE:
            biomas[biome_id] = int(valores[f"bioma_{biome_id}"])

        recursos = {}
        for recurso_id, _rotulo, _desc in RECURSOS_CONTROLE:
            recursos[recurso_id] = int(valores[f"recursos_{recurso_id}"])

        return {
            "versao": 1,
            "tamanho_mundo": tamanho,
            "agua": int(valores["agua"]),
            "rios": {
                "quantidade": int(valores["rios_quantidade"]),
                "comprimento": int(valores["rios_comprimento"]),
                "largura": int(valores["rios_largura"]),
            },
            "lagos": int(valores["lagos"]),
            "biomas": biomas,
            "recursos": recursos,
            "vilas": int(valores["vilas"]),
            "sliders": valores,
        }

    def render(self, tela, eventos, dt, JOGO=None):
        size = tela.get_size()
        if size != self._cache_size:
            self._rebuild_cache(size)

        pygame.draw.rect(tela, _COR_FUNDO_MODAL, self.caixa, border_radius=22)
        pygame.draw.rect(tela, _COR_PAINEL_BORDA, self.caixa, width=2, border_radius=22)

        self.titulo.draw(tela)
        self.subtitulo.draw(tela)
        self.painel.render(tela, eventos, dt, jogo=JOGO)

        self.botao_fechar.render(tela, eventos, dt, JOGO=JOGO)
        self.botao_resetar.render(tela, eventos, dt, JOGO=JOGO)
        self.botao_salvar.render(tela, eventos, dt, JOGO=JOGO)
