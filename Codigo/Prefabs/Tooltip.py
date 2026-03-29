from __future__ import annotations

from pathlib import Path

import pygame

from Codigo.Prefabs.Texto import CAMINHO_FONTE_PADRAO, Texto


class Tooltip:
    """Tooltip elegante com título opcional e descrição curta."""

    def __init__(
        self,
        texto: str = "",
        area_ativacao=None,
        pos_fixa=None,
        largura_max: int = 320,
        padding: int = 12,
        raio: int = 14,
        style=None,
        titulo: str | None = None,
        descricao: str | None = None,
    ):
        self.AreaAtivacao = pygame.Rect(area_ativacao) if area_ativacao is not None else None
        self.PosFixa = tuple(pos_fixa) if pos_fixa is not None else None
        self.LarguraMax = max(160, int(largura_max))
        self.Padding = max(6, int(padding))
        self.Raio = max(0, int(raio))

        self.StyleTitulo = {
            "size": 20,
            "color": (247, 250, 255),
            "outline": True,
            "outline_color": (0, 0, 0),
            "outline_thickness": 1,
            "shadow": False,
            "align": "topleft",
        }
        self.StyleDescricao = {
            "size": 16,
            "color": (205, 217, 238),
            "outline": True,
            "outline_color": (0, 0, 0),
            "outline_thickness": 1,
            "shadow": False,
            "align": "topleft",
        }
        if style:
            self.StyleDescricao.update(style)

        self.CorFundo = (6, 10, 18, 244)
        self.CorBorda = (114, 152, 220)
        self.CorSombra = (0, 0, 0, 120)
        self.OffsetMouse = (18, 18)

        self.Titulo = ""
        self.Descricao = ""
        self._quebra_chave = None
        self._linhas_descricao: list[str] = []
        self._texto_titulo = Texto("", style=self.StyleTitulo)
        self._textos_descricao: list[Texto] = []

        if titulo is not None or descricao is not None:
            self.definir_conteudo(titulo=titulo or "", descricao=descricao or texto or "")
        else:
            self.definir_texto(texto)

    def definir_texto(self, texto: str):
        texto = str(texto or "").strip()
        if "\n" in texto:
            linhas = [linha.strip() for linha in texto.split("\n") if linha.strip()]
            if len(linhas) >= 2:
                self.definir_conteudo(titulo=linhas[0], descricao="\n".join(linhas[1:]))
                return
        self.definir_conteudo(titulo="", descricao=texto)

    def definir_conteudo(self, titulo: str = "", descricao: str = ""):
        titulo = str(titulo or "").strip()
        descricao = str(descricao or "").strip()
        if titulo == self.Titulo and descricao == self.Descricao:
            return
        self.Titulo = titulo
        self.Descricao = descricao
        self._quebra_chave = None

    def definir_area(self, area):
        self.AreaAtivacao = pygame.Rect(area) if area is not None else None

    def definir_posicao_fixa(self, pos):
        self.PosFixa = tuple(pos) if pos is not None else None

    def _fonte_medicao(self, tamanho):
        caminho = Path(CAMINHO_FONTE_PADRAO)
        return pygame.font.Font(str(caminho), int(tamanho))

    def _quebrar_linhas(self):
        chave = (self.Titulo, self.Descricao, self.LarguraMax, self.Padding, self.StyleTitulo.get("size", 20), self.StyleDescricao.get("size", 16))
        if self._quebra_chave == chave:
            return

        limite = max(100, self.LarguraMax - self.Padding * 2)
        fonte_desc = self._fonte_medicao(self.StyleDescricao.get("size", 16))
        linhas: list[str] = []

        for bloco in self.Descricao.split("\n"):
            bloco = bloco.strip()
            if not bloco:
                continue
            palavras = bloco.split()
            atual = palavras[0]
            for palavra in palavras[1:]:
                tentativa = f"{atual} {palavra}"
                if fonte_desc.size(tentativa)[0] <= limite:
                    atual = tentativa
                else:
                    linhas.append(atual)
                    atual = palavra
            linhas.append(atual)

        self._linhas_descricao = linhas
        self._texto_titulo = Texto(self.Titulo, style=self.StyleTitulo)
        self._textos_descricao = [Texto(linha, style=self.StyleDescricao) for linha in self._linhas_descricao]
        self._quebra_chave = chave

    def ativo(self, mouse_pos=None) -> bool:
        if self.AreaAtivacao is None:
            return False
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()
        return self.AreaAtivacao.collidepoint(mouse_pos)

    def _medidas_caixa(self):
        self._quebrar_linhas()
        largura = 0
        altura = self.Padding * 2
        espacamento_desc = 5

        if self.Titulo:
            rect_titulo = self._texto_titulo.get_rect()
            largura = max(largura, rect_titulo.width)
            altura += rect_titulo.height
            if self._textos_descricao:
                altura += 6

        for texto in self._textos_descricao:
            rect = texto.get_rect()
            largura = max(largura, rect.width)
            altura += rect.height
        altura += max(0, len(self._textos_descricao) - 1) * espacamento_desc
        largura += self.Padding * 2
        return largura, altura, espacamento_desc

    def _posicao_caixa(self, tela, largura, altura, mouse_pos=None):
        area = tela.get_rect()
        if self.PosFixa is not None:
            x, y = self.PosFixa
        else:
            if mouse_pos is None:
                mouse_pos = pygame.mouse.get_pos()
            x = int(mouse_pos[0] + self.OffsetMouse[0])
            y = int(mouse_pos[1] + self.OffsetMouse[1])

        x = max(area.left + 8, min(int(x), area.right - largura - 8))
        y = max(area.top + 8, min(int(y), area.bottom - altura - 8))
        return x, y

    def render(self, tela, mouse_pos=None, forcar=False):
        if not forcar and not self.ativo(mouse_pos):
            return False

        largura, altura, espacamento = self._medidas_caixa()
        x, y = self._posicao_caixa(tela, largura, altura, mouse_pos=mouse_pos)

        sombra = pygame.Rect(x + 4, y + 5, largura, altura)
        caixa = pygame.Rect(x, y, largura, altura)

        pygame.draw.rect(tela, self.CorSombra, sombra, border_radius=self.Raio)
        pygame.draw.rect(tela, self.CorFundo, caixa, border_radius=self.Raio)
        pygame.draw.rect(tela, self.CorBorda, caixa, 2, border_radius=self.Raio)

        cy = caixa.y + self.Padding
        if self.Titulo:
            self._texto_titulo.set_pos((caixa.x + self.Padding, cy))
            self._texto_titulo.draw(tela)
            cy += self._texto_titulo.get_rect().height + (6 if self._textos_descricao else 0)

        for texto in self._textos_descricao:
            texto.set_pos((caixa.x + self.Padding, cy))
            texto.draw(tela)
            cy += texto.get_rect().height + espacamento
        return True
