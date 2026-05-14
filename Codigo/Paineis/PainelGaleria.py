from __future__ import annotations

from pathlib import Path
import unicodedata

import pygame

from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Painel import PainelRolavel
from Codigo.Prefabs.Texto import Texto


_BASE_TEXTO = {
    "outline": True,
    "outline_thickness": 1,
    "outline_color": (0, 0, 0),
    "shadow": False,
}


def _norm_id(valor) -> str:
    texto = str(valor or "").strip()
    if "." in Path(texto).name:
        texto = Path(texto).stem
    bruto = unicodedata.normalize("NFKD", texto.casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _ids_unicos(valores) -> list[str]:
    saida: list[str] = []
    vistos: set[str] = set()
    for valor in list(valores or []):
        texto = str(valor or "").strip()
        chave = _norm_id(texto)
        if not texto or not chave or chave in vistos:
            continue
        vistos.add(chave)
        saida.append(texto)
    return saida


class _ListaGaleriaRolavel(PainelRolavel):
    def __init__(self, owner: "PainelGaleria", rect, **kwargs):
        kwargs["area_real"] = pygame.Rect(0, 0, pygame.Rect(rect).width, pygame.Rect(rect).height)
        super().__init__(rect, **kwargs)
        self.owner = owner

    def definir_area_real(self, largura, altura):
        nova_largura = max(self.rect.width, int(largura))
        nova_altura = max(self.rect.height, int(altura))
        if self.AreaReal.width != nova_largura or self.AreaReal.height != nova_altura:
            self.AreaReal.width = nova_largura
            self.AreaReal.height = nova_altura
            self._viewport_suja = True
        self._clamp_scroll()

    def _garantir_surfaces(self):
        if (
            self._surface_viewport is None
            or self._surface_viewport.get_width() != self.rect.width
            or self._surface_viewport.get_height() != self.rect.height
        ):
            self._recriar_surface_viewport()
            self._viewport_suja = True

    def render(self, tela, eventos, dt, jogo=None):
        if not self.Visivel:
            return
        self._garantir_surfaces()
        scroll_antes = (self.ScrollX, self.ScrollY)
        self._processar_scroll(eventos)
        if scroll_antes != (self.ScrollX, self.ScrollY):
            self._viewport_suja = True
        self._surface_viewport.fill((0, 0, 0, 0))
        self.owner._desenhar_conteudo_rolavel(self._surface_viewport, self)
        self._aplicar_mascara_raio(self._surface_viewport)
        tela.blit(self._surface_viewport, self.rect.topleft)
        if self.Borda > 0:
            pygame.draw.rect(tela, self.CorBorda, self.rect, self.Borda, border_radius=self.Raio)
        self._desenhar_scrollbar(tela, dt)


class PainelGaleria:
    PASTAS_INSIGNIAS = ("Insigneas", "Insígnias", "Insignias", "insigneas", "insignias")
    PASTAS_MEDALHOES = ("Medalhoes", "Medalhões", "medalhoes")
    EXTENSOES = (".png", ".webp", ".jpg", ".jpeg")

    def __init__(self, ator=None):
        self.Ator = ator
        self._layout_chave = None
        self._rect = pygame.Rect(0, 0, 0, 0)
        self._area_lista = pygame.Rect(0, 0, 0, 0)
        self._rolavel: _ListaGaleriaRolavel | None = None
        self._botao_fechar: Botao | None = None
        self._solicitou_fechar = False
        self._textos: dict[str, Texto] = {}
        self._cache_imgs: dict[Path, pygame.Surface | None] = {}
        self._cache_arquivos: dict[str, dict[str, Path]] = {}
        self._hover: dict[str, float] = {}
        self._ultima_assinatura = None
        self._tela_atual = None
        self._eventos_frame = []
        self._dt_frame = 0.0

    def _perfil(self):
        return getattr(self.Ator, "Perfil", None) if self.Ator is not None else None

    @staticmethod
    def _roots() -> list[Path]:
        atual = Path(__file__).resolve()
        candidatos = [Path(".").resolve(), atual.parent]
        candidatos.extend(atual.parents[:7])
        vistos: list[Path] = []
        for caminho in candidatos:
            if caminho not in vistos:
                vistos.append(caminho)
        return vistos

    @classmethod
    def _pasta_icones(cls, nomes: tuple[str, ...]) -> Path | None:
        for raiz in cls._roots():
            base = raiz / "Recursos" / "Visual" / "Icones"
            for nome in nomes:
                caminho = base / nome
                if caminho.exists() and caminho.is_dir():
                    return caminho
        return None

    def _indice_arquivos(self, tipo: str) -> dict[str, Path]:
        if tipo in self._cache_arquivos:
            return self._cache_arquivos[tipo]
        nomes = self.PASTAS_INSIGNIAS if tipo == "insignia" else self.PASTAS_MEDALHOES
        pasta = self._pasta_icones(nomes)
        indice: dict[str, Path] = {}
        if pasta is not None:
            for arquivo in pasta.iterdir():
                if arquivo.is_file() and arquivo.suffix.lower() in self.EXTENSOES:
                    indice.setdefault(_norm_id(arquivo.stem), arquivo)
        self._cache_arquivos[tipo] = indice
        return indice

    @staticmethod
    def _candidatos_id(item_id: str) -> list[str]:
        base = _norm_id(item_id)
        candidatos = [base]
        for prefixo in ("estadio", "insignia", "medalhao"):
            if base.startswith(prefixo):
                candidatos.append(base[len(prefixo):])
        return [c for c in dict.fromkeys(candidatos) if c]

    def _arquivo_item(self, tipo: str, item_id: str) -> Path | None:
        indice = self._indice_arquivos(tipo)
        candidatos = self._candidatos_id(item_id)
        for cand in candidatos:
            if cand in indice:
                return indice[cand]
        for cand in candidatos:
            for chave, caminho in indice.items():
                if chave.endswith(cand) or cand.endswith(chave):
                    return caminho
        return None

    def _imagem_item(self, tipo: str, item_id: str) -> pygame.Surface | None:
        caminho = self._arquivo_item(tipo, item_id)
        if caminho is None:
            return None
        if caminho in self._cache_imgs:
            return self._cache_imgs[caminho]
        try:
            img = pygame.image.load(str(caminho)).convert_alpha()
        except pygame.error:
            img = None
        self._cache_imgs[caminho] = img
        return img

    def _itens(self) -> list[tuple[str, str]]:
        perfil = self._perfil()
        insignias = _ids_unicos(getattr(perfil, "Insignias", []) if perfil is not None else [])
        medalhoes = _ids_unicos(getattr(perfil, "Medalhoes", []) if perfil is not None else [])
        return [("insignia", item) for item in insignias] + [("medalhao", item) for item in medalhoes]

    @staticmethod
    def _style_texto(size=18, color=(238, 242, 255), align=None):
        style = dict(_BASE_TEXTO)
        style.update({"size": size, "color": color})
        if align:
            style["align"] = align
        return style

    def _texto(self, chave: str, conteudo: str, pos, style: dict, tela=None):
        txt = self._textos.get(chave)
        if txt is None:
            txt = Texto(conteudo, style=style)
            self._textos[chave] = txt
        txt.set_text(conteudo)
        txt.set_pos(pos)
        txt.draw(tela or self._tela_atual)

    def _reconstruir_layout(self, rect: pygame.Rect):
        chave = (rect.x, rect.y, rect.width, rect.height)
        if chave == self._layout_chave and self._botao_fechar is not None and self._rolavel is not None:
            return
        self._layout_chave = chave
        self._rect = pygame.Rect(rect)
        self._area_lista = pygame.Rect(rect.x + 28, rect.y + 108, rect.width - 56, rect.height - 130)

        def _fechar(_jogo, _botao):
            self._solicitou_fechar = True

        self._botao_fechar = Botao(
            pygame.Rect(rect.right - 68, rect.y + 16, 52, 52),
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
        self._rolavel = _ListaGaleriaRolavel(
            self,
            self._area_lista,
            area_real=pygame.Rect(0, 0, self._area_lista.width, self._area_lista.height),
            velocidade_scroll=54,
            cor_fundo=(9, 14, 26, 220),
            cor_borda=(82, 120, 195),
            borda=2,
            raio=18,
        )

    def _desenhar_fundo(self, tela):
        tela.fill((8, 12, 22), self._rect)
        camada = pygame.Surface(self._rect.size, pygame.SRCALPHA)
        pygame.draw.rect(camada, (12, 18, 32, 248), camada.get_rect(), border_radius=22)
        pygame.draw.ellipse(camada, (58, 82, 150, 30), (-120, -190, self._rect.width + 240, 300))
        pygame.draw.ellipse(camada, (22, 36, 82, 30), (self._rect.width - 360, 36, 420, 260))
        tela.blit(camada, self._rect.topleft)

    def _desenhar_topo(self, tela, total: int):
        self._texto("titulo", "Galeria", (self._rect.x + 26, self._rect.y + 20), self._style_texto(34, (247, 250, 255)))
        self._texto("contador", f"{total} conquistas obtidas", (self._rect.x + 28, self._rect.y + 62), self._style_texto(17, (185, 205, 238)))
        self._botao_fechar.render(tela, self._eventos_frame, self._dt_frame, None)

    @staticmethod
    def _misturar(c1, c2, t: float):
        t = max(0.0, min(1.0, float(t)))
        return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

    def _sigla(self, item_id: str) -> str:
        base = _norm_id(item_id).upper()
        return (base[:3] or "?")

    def _desenhar_placeholder(self, tela, rect: pygame.Rect, item_id: str):
        pygame.draw.rect(tela, (24, 34, 58), rect, border_radius=18)
        pygame.draw.rect(tela, (106, 138, 196), rect, 2, border_radius=18)
        self._texto(f"ph_{item_id}", self._sigla(item_id), rect.center, self._style_texto(24, (208, 226, 255), "center"), tela)

    def _desenhar_item(self, tela, rect: pygame.Rect, tipo: str, item_id: str, hover_t: float):
        card = pygame.Rect(rect)
        card.inflate_ip(int(card.width * 0.05 * hover_t), int(card.height * 0.05 * hover_t))
        card.center = rect.center
        cor = self._misturar((16, 25, 45), (30, 48, 84), hover_t)
        borda = self._misturar((84, 118, 184), (178, 212, 255), hover_t)
        pygame.draw.rect(tela, cor, card, border_radius=18)
        pygame.draw.rect(tela, borda, card, 2, border_radius=18)

        img = self._imagem_item(tipo, item_id)
        area_img = card.inflate(-18, -18)
        if img is None:
            self._desenhar_placeholder(tela, area_img, item_id)
            return
        iw, ih = img.get_size()
        escala = min(area_img.width / max(1, iw), area_img.height / max(1, ih))
        escala *= 1.0 + 0.04 * hover_t
        destino = (max(1, int(iw * escala)), max(1, int(ih * escala)))
        try:
            desenhada = pygame.transform.smoothscale(img, destino)
        except pygame.error:
            self._desenhar_placeholder(tela, area_img, item_id)
            return
        tela.blit(desenhada, desenhada.get_rect(center=card.center))

    def _desenhar_vazio(self, tela_painel: pygame.Surface, largura: int):
        cy = max(100, self._area_lista.height // 2 - 20)
        self._texto("vazio1", "Nenhuma insígnia ou medalhão obtido ainda.", (largura // 2, cy), self._style_texto(24, (235, 242, 255), "center"), tela_painel)
        self._texto("vazio2", "Derrote líderes de estádio e bosses de dungeon para preencher a galeria.", (largura // 2, cy + 36), self._style_texto(17, (170, 190, 225), "center"), tela_painel)

    def _metricas_grade(self, largura: int):
        colunas = 6
        margem = 18
        gap = 14
        card = max(54, (largura - margem * 2 - gap * (colunas - 1)) // colunas)
        card = min(124, card)
        row_h = card + 18
        return colunas, margem, gap, card, row_h

    def _desenhar_conteudo_rolavel(self, tela_painel: pygame.Surface, rolavel: _ListaGaleriaRolavel):
        pygame.draw.rect(tela_painel, (9, 14, 26, 220), tela_painel.get_rect(), border_radius=18)
        itens = self._itens()
        largura = rolavel.AreaReal.width
        if not itens:
            self._desenhar_vazio(tela_painel, largura)
            return

        colunas, margem, gap, card, row_h = self._metricas_grade(largura)
        visivel = rolavel.obter_area_visivel_no_conteudo()
        inicio_linha = max(0, int((visivel.y - margem) // row_h) - 1)
        fim_linha = int((visivel.bottom - margem) // row_h) + 2
        inicio = max(0, inicio_linha * colunas)
        fim = min(len(itens), fim_linha * colunas)

        mouse_global = pygame.mouse.get_pos()
        mouse_conteudo = None
        if rolavel.rect.collidepoint(mouse_global):
            mouse_conteudo = (mouse_global[0] - rolavel.rect.x + rolavel.ScrollX, mouse_global[1] - rolavel.rect.y + rolavel.ScrollY)

        dt = max(0.0, min(0.05, float(self._dt_frame or 0.0)))
        for indice in range(inicio, fim):
            tipo, item_id = itens[indice]
            linha = indice // colunas
            coluna = indice % colunas
            x = margem + coluna * (card + gap)
            y = margem + linha * row_h
            rect_item = pygame.Rect(x, y, card, card)
            hover = mouse_conteudo is not None and rect_item.collidepoint(mouse_conteudo)
            chave = f"{tipo}:{_norm_id(item_id)}"
            alvo = 1.0 if hover else 0.0
            atual = float(self._hover.get(chave, 0.0))
            atual += (alvo - atual) * min(1.0, 12.0 * dt)
            self._hover[chave] = max(0.0, min(1.0, atual))
            self._desenhar_item(tela_painel, rect_item.move(-rolavel.ScrollX, -rolavel.ScrollY), tipo, item_id, self._hover[chave])

    def renderizar(self, tela, rect, eventos=None, dt=0.0) -> bool:
        eventos = eventos or []
        self._solicitou_fechar = False
        self._tela_atual = tela
        self._eventos_frame = eventos
        self._dt_frame = dt
        self._reconstruir_layout(pygame.Rect(rect))

        itens = self._itens()
        assinatura = tuple((tipo, item_id) for tipo, item_id in itens)
        if assinatura != self._ultima_assinatura:
            self._ultima_assinatura = assinatura
            if self._rolavel is not None:
                self._rolavel.ScrollY = 0
                self._rolavel.marcar_sujo()

        colunas, margem, _gap, _card, row_h = self._metricas_grade(self._area_lista.width)
        linhas = (len(itens) + colunas - 1) // colunas if itens else 0
        altura_total = margem * 2 + linhas * row_h
        self._rolavel.definir_area_real(self._area_lista.width, max(self._area_lista.height, altura_total))

        self._desenhar_fundo(tela)
        self._desenhar_topo(tela, len(itens))
        self._rolavel.render(tela, eventos, dt, None)
        return self._solicitou_fechar
