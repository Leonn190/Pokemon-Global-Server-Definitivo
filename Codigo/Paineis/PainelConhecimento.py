from __future__ import annotations

import csv
import json
from pathlib import Path
import unicodedata

import pygame

from Codigo.Paineis.MiniPaineisConhecimentos import (
    MiniPainelAtaque,
    MiniPainelEfeito,
    MiniPainelItem,
    MiniPainelMusica,
    MiniPainelPokemon,
)
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Painel import PainelRolavel
from Codigo.Prefabs.Texto import Texto

try:
    from Codigo.ModulosGerais.LoaderTabelas import carregar_csv_dict
except Exception:
    carregar_csv_dict = None

try:
    import Codigo.ModulosGerais.Sonoridades as Sonoridades
except Exception:
    Sonoridades = None


_BASE_TEXTO = {
    "outline": True,
    "outline_thickness": 1,
    "outline_color": (0, 0, 0),
    "shadow": False,
}


def _norm(texto) -> str:
    base = "".join(
        c for c in unicodedata.normalize("NFKD", str(texto or "").strip().lower())
        if not unicodedata.combining(c)
    )
    for ch in ("_", "-", ".", "'", "(", ")", "[", "]", "{", "}", ":", ";", ",", "/", "\\"):
        base = base.replace(ch, " ")
    return " ".join(base.split())


def _valor(dados: dict | None, *chaves, default=""):
    if not isinstance(dados, dict):
        return default
    alvos = {_norm(ch) for ch in chaves if str(ch or "").strip()}
    for chave, valor in dados.items():
        if _norm(chave) in alvos and valor not in (None, ""):
            return valor
    return default


class _ListaConhecimentoRolavel(PainelRolavel):
    def __init__(self, owner: "PainelConhecimento", rect, **kwargs):
        # Inicializa com area_real pequena para evitar a criação inicial de uma
        # surface gigante. A altura real é guardada só como número para o scroll.
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
        if self._viewport_suja:
            self._surface_viewport.fill((0, 0, 0, 0))
            self.owner._desenhar_conteudo_rolavel(self._surface_viewport, self)
            self._aplicar_mascara_raio(self._surface_viewport)
            self._viewport_suja = False
        tela.blit(self._surface_viewport, self.rect.topleft)
        if self.Borda > 0:
            pygame.draw.rect(tela, self.CorBorda, self.rect, self.Borda, border_radius=self.Raio)
        self._desenhar_scrollbar(tela, dt)


class PainelConhecimento:
    ABAS = (
        ("pokemons", "Pokémons"),
        ("ataques", "Ataques"),
        ("efeitos", "Efeitos"),
        ("itens", "Itens"),
        ("musicas", "Músicas"),
    )

    ARQUIVOS_CSV = {
        "pokemons": "Pokemon Global Server - Pokemons.csv",
        "ataques": "Pokemon Global Server - Ataques.csv",
        "efeitos": "Pokemon Global Server - Efeitos.csv",
        "itens": "Pokemon Global Server - Itens.csv",
    }

    REGISTROS_PERFIL = {
        "pokemons": ("ConhecimentoPokemons", "PokemonsRegistrados", "PokémonsRegistrados", "RegistroPokemons", "Pokedex", "PokemonsConhecidos"),
        "ataques": ("ConhecimentoAtaques", "AtaquesRegistrados", "RegistroAtaques", "AtaquesConhecidos"),
        "efeitos": ("ConhecimentoEfeitos", "EfeitosRegistrados", "RegistroEfeitos", "EfeitosConhecidos"),
        "itens": ("ConhecimentoItens", "ItensRegistrados", "RegistroItens", "ItensConhecidos"),
        "musicas": ("ConhecimentoMusicas", "MusicasRegistradas", "MúsicasRegistradas", "RegistroMusicas", "MusicasConhecidas"),
    }

    ALTURAS = {
        "pokemons": MiniPainelPokemon.ALTURA,
        "ataques": MiniPainelAtaque.ALTURA,
        "efeitos": MiniPainelEfeito.ALTURA,
        "itens": MiniPainelItem.ALTURA,
        "musicas": MiniPainelMusica.ALTURA,
    }

    def __init__(self, ator=None):
        self.Ator = ator
        self._layout_chave = None
        self._rect = pygame.Rect(0, 0, 0, 0)
        self._area_tabs = pygame.Rect(0, 0, 0, 0)
        self._area_lista = pygame.Rect(0, 0, 0, 0)
        self._rolavel: _ListaConhecimentoRolavel | None = None
        self._botao_fechar: Botao | None = None
        self._botoes_abas: dict[str, Botao] = {}
        self._status_estilo_abas: dict[str, bool] = {}
        self._aba = "pokemons"
        self._aba_anterior = self._aba
        self._solicitou_fechar = False
        self._catalogos: dict[str, list[dict]] = {}
        self._lista_cache: dict[str, list[dict]] = {}
        self._cache_chave: dict[str, tuple] = {}
        self._textos: dict[str, Texto] = {}
        self._minis = {
            "pokemons": MiniPainelPokemon(),
            "ataques": MiniPainelAtaque(),
            "efeitos": MiniPainelEfeito(),
            "itens": MiniPainelItem(),
            "musicas": MiniPainelMusica(),
        }
        self._arrastando_musica: str | None = None
        self._ultima_lista_assinatura = None

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------
    def _perfil(self):
        return getattr(self.Ator, "Perfil", None) if self.Ator is not None else None

    def _inventario(self):
        return getattr(self.Ator, "Inventario", None) if self.Ator is not None else None

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
    def _arquivo_dados(cls, sub: Path) -> Path | None:
        for raiz in cls._roots():
            caminho = raiz / sub
            if caminho.exists():
                return caminho
        return None

    @classmethod
    def _carregar_csv(cls, nome: str) -> list[dict]:
        if carregar_csv_dict is not None:
            try:
                return [dict(linha) for linha in carregar_csv_dict(nome)]
            except Exception:
                pass
        caminho = cls._arquivo_dados(Path("Dados") / "Tabelas" / nome)
        if caminho is None:
            return []
        try:
            with caminho.open("r", encoding="utf-8-sig", newline="") as arq:
                return [dict(linha) for linha in csv.DictReader(arq)]
        except Exception:
            return []

    @classmethod
    def _carregar_musicas_catalogo(cls) -> list[dict]:
        if Sonoridades is not None and isinstance(getattr(Sonoridades, "Musicas", None), dict):
            saida = []
            for chave, dados in Sonoridades.Musicas.items():
                if isinstance(dados, dict):
                    item = dict(dados)
                    item.setdefault("Chave", chave)
                    item.setdefault("Nome", chave)
                    item.setdefault("id", str(item.get("id") or chave))
                    saida.append(item)
            return saida
        caminho = cls._arquivo_dados(Path("Dados") / "Catalogo" / "Musicas.json")
        if caminho is None:
            return []
        try:
            with caminho.open("r", encoding="utf-8") as arq:
                dados = json.load(arq)
        except Exception:
            return []
        saida = []
        if isinstance(dados, dict):
            for chave, valor in dados.items():
                if isinstance(valor, dict):
                    item = dict(valor)
                    item.setdefault("Chave", chave)
                    item.setdefault("Nome", chave)
                    item.setdefault("id", str(item.get("id") or chave))
                    saida.append(item)
        return saida

    def _catalogo(self, aba: str) -> list[dict]:
        if aba in self._catalogos:
            return self._catalogos[aba]
        if aba == "musicas":
            dados = self._carregar_musicas_catalogo()
        else:
            dados = self._carregar_csv(self.ARQUIVOS_CSV.get(aba, ""))
        self._catalogos[aba] = dados
        return dados

    @staticmethod
    def _tokens_de_item_registro(item) -> set[str]:
        tokens = set()
        if isinstance(item, dict):
            for chave in ("Code", "code", "ID", "Id", "id", "Nome", "nome", "Pokemon", "Pokémon", "Ataque", "Efeito", "Chave"):
                valor = item.get(chave)
                if valor not in (None, ""):
                    tokens.add(_norm(valor))
                    tokens.add(str(valor).strip())
        else:
            if item not in (None, ""):
                tokens.add(_norm(item))
                tokens.add(str(item).strip())
        return {t for t in tokens if t}

    def _registro_bruto(self, aba: str):
        perfil = self._perfil()
        if perfil is not None:
            conhecimento = getattr(perfil, "Conhecimento", None)
            if isinstance(conhecimento, dict):
                chave_real = {
                    "pokemons": "Pokemons",
                    "ataques": "Ataques",
                    "efeitos": "Efeitos",
                    "itens": "Itens",
                    "musicas": "Musicas",
                }.get(aba)
                valor = conhecimento.get(chave_real)
                if valor not in (None, ""):
                    return valor
        if perfil is not None:
            for nome in self.REGISTROS_PERFIL.get(aba, ()):  # tenta todos os contratos prováveis
                if hasattr(perfil, nome):
                    valor = getattr(perfil, nome)
                    if valor not in (None, ""):
                        return valor

        # Fallbacks úteis enquanto o contrato real do conhecimento ainda não existir.
        inv = self._inventario()
        if aba == "pokemons" and inv is not None:
            pokemons = getattr(inv, "Pokemons", None)
            if pokemons:
                return list(pokemons)
        if aba == "itens" and inv is not None:
            itens = getattr(inv, "Itens", None)
            if itens:
                return list(itens)
        return []

    def _tokens_registrados(self, aba: str) -> tuple[set[str], int | None, tuple]:
        bruto = self._registro_bruto(aba)
        tokens: set[str] = set()
        limite_int = None
        assinatura = (id(bruto),)

        if isinstance(bruto, dict):
            assinatura = ("dict", tuple(sorted((str(k), str(v)) for k, v in bruto.items())))
            for chave, valor in bruto.items():
                if isinstance(valor, bool) and not valor:
                    continue
                tokens.update(self._tokens_de_item_registro(chave))
                tokens.update(self._tokens_de_item_registro(valor))
        elif isinstance(bruto, (list, tuple, set)):
            assinatura = ("seq", tuple(sorted(str(item) for item in bruto)))
            for item in bruto:
                tokens.update(self._tokens_de_item_registro(item))
        elif isinstance(bruto, (int, float)):
            limite_int = max(0, int(bruto))
            assinatura = ("int", limite_int)
        else:
            tokens.update(self._tokens_de_item_registro(bruto))
            assinatura = (str(bruto),)

        return tokens, limite_int, assinatura

    def _tokens_linha(self, aba: str, linha: dict) -> set[str]:
        tokens = set()
        if aba == "pokemons":
            chaves = ("Code", "Nome")
        elif aba == "ataques":
            chaves = ("Code", "Ataque", "Nome")
        elif aba == "efeitos":
            chaves = ("Code", "Efeito", "Nome")
        elif aba == "itens":
            chaves = ("Code", "Nome")
        else:
            chaves = ("id", "Chave", "Nome")
        for chave in chaves:
            valor = _valor(linha, chave, default="")
            if valor not in (None, ""):
                tokens.add(_norm(valor))
                tokens.add(str(valor).strip())
        return {t for t in tokens if t}

    def _lista_atual(self) -> list[dict]:
        aba = self._aba
        catalogo = self._catalogo(aba)
        tokens, limite_int, assinatura = self._tokens_registrados(aba)
        chave = (id(self.Ator), aba, len(catalogo), assinatura)
        if self._cache_chave.get(aba) == chave and aba in self._lista_cache:
            return self._lista_cache[aba]

        if limite_int is not None:
            lista = list(catalogo[:limite_int])
        elif not tokens:
            lista = []
        else:
            lista = [linha for linha in catalogo if self._tokens_linha(aba, linha) & tokens]

        self._lista_cache[aba] = lista
        self._cache_chave[aba] = chave
        return lista

    # ------------------------------------------------------------------
    # Layout / estilos
    # ------------------------------------------------------------------
    def _texto(self, chave: str, conteudo: str, pos, style: dict):
        txt = self._textos.get(chave)
        if txt is None:
            txt = Texto(conteudo, style=style)
            self._textos[chave] = txt
        txt.set_text(conteudo)
        txt.set_pos(pos)
        txt.draw(self._tela_atual)

    @staticmethod
    def _style_texto(size=18, color=(238, 242, 255), align=None):
        style = dict(_BASE_TEXTO)
        style.update({"size": size, "color": color})
        if align:
            style["align"] = align
        return style

    @staticmethod
    def _misturar(c1, c2, t: float):
        t = max(0.0, min(1.0, float(t)))
        return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

    def _style_botao_aba(self, selecionado: bool):
        return {
            "radius": 14,
            "border_width": 2,
            "hover_scale": 1.01,
            "press_scale": 0.985,
            "bg": (42, 86, 54) if selecionado else (48, 74, 145),
            "bg_hover": (56, 112, 72) if selecionado else (68, 96, 176),
            "bg_pressed": (30, 67, 42) if selecionado else (38, 60, 120),
            "border": (190, 255, 203) if selecionado else (126, 156, 230),
            "border_hover": (230, 255, 235),
            "text_style": {
                "size": 20,
                "color": (255, 255, 255),
                "hover_color": (255, 255, 255),
                "align": "center",
                "outline": True,
                "outline_color": (0, 0, 0),
                "outline_thickness": 1,
                "shadow": False,
            },
        }

    def _reconstruir_layout(self, rect: pygame.Rect):
        chave = (rect.x, rect.y, rect.width, rect.height)
        if chave == self._layout_chave and self._botao_fechar is not None and self._rolavel is not None:
            return

        self._layout_chave = chave
        self._rect = pygame.Rect(rect)
        self._area_tabs = pygame.Rect(rect.x + 300, rect.y + 16, rect.width - 390, 48)
        self._area_lista = pygame.Rect(rect.x + 28, rect.y + 132, rect.width - 56, rect.height - 154)

        def _fechar(_jogo, _botao):
            self._parar_musica_conhecimento()
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

        gap = 10
        qtd = len(self.ABAS)
        largura = (self._area_tabs.width - gap * (qtd - 1)) // qtd
        self._botoes_abas = {}
        self._status_estilo_abas = {}
        for i, (aba, rotulo) in enumerate(self.ABAS):
            x = self._area_tabs.x + i * (largura + gap)
            w = largura if i < qtd - 1 else self._area_tabs.right - x

            def _selecionar(_jogo, _botao, aba_id=aba):
                if aba_id != self._aba:
                    if self._aba == "musicas":
                        self._parar_musica_conhecimento()
                    self._aba = aba_id
                    if self._rolavel is not None:
                        self._rolavel.ScrollY = 0
                        self._rolavel.marcar_sujo()

            self._botoes_abas[aba] = Botao(
                pygame.Rect(x, self._area_tabs.y, w, self._area_tabs.height),
                rotulo,
                execute=_selecionar,
                style=self._style_botao_aba(aba == self._aba),
            )

        self._rolavel = _ListaConhecimentoRolavel(
            self,
            self._area_lista,
            area_real=pygame.Rect(0, 0, self._area_lista.width, self._area_lista.height),
            velocidade_scroll=54,
            cor_fundo=(9, 14, 26, 220),
            cor_borda=(82, 120, 195),
            borda=2,
            raio=18,
        )

    # ------------------------------------------------------------------
    # Interação de músicas
    # ------------------------------------------------------------------
    def _parar_musica_conhecimento(self):
        self._arrastando_musica = None
        if Sonoridades is not None and hasattr(Sonoridades, "parar_musica_conhecimento"):
            Sonoridades.parar_musica_conhecimento(restaurar=True)

    def _musica_por_indice(self, indice: int) -> dict | None:
        lista = self._lista_atual()
        if 0 <= indice < len(lista):
            return lista[indice]
        return None

    def _rect_item_content(self, indice: int, largura: int) -> pygame.Rect:
        altura = self.ALTURAS.get(self._aba, 80)
        gap = 10
        return pygame.Rect(8, 8 + indice * (altura + gap), max(1, largura - 16), altura)

    def _posicao_barra_musica(self, musica: dict, barra_rect: pygame.Rect, mouse_x: int) -> float:
        duracao = MiniPainelMusica.duracao(musica)
        pct = (mouse_x - barra_rect.x) / float(max(1, barra_rect.width))
        pct = max(0.0, min(1.0, pct))
        return duracao * pct

    def _tocar_ou_seek_musica(self, musica: dict, posicao: float | None = None):
        if Sonoridades is None:
            return
        chave = MiniPainelMusica.chave(musica)
        if not chave:
            return
        posicao = 0.0 if posicao is None else float(posicao)
        estado = Sonoridades.musica_conhecimento_estado() if hasattr(Sonoridades, "musica_conhecimento_estado") else {}
        if estado.get("nome") == chave and hasattr(Sonoridades, "alterar_posicao_musica_conhecimento"):
            Sonoridades.alterar_posicao_musica_conhecimento(chave, posicao)
        elif hasattr(Sonoridades, "tocar_musica_conhecimento"):
            Sonoridades.tocar_musica_conhecimento(chave, posicao=posicao)

    def _processar_interacao_musicas(self, eventos):
        if self._aba != "musicas" or self._rolavel is None:
            return
        largura = self._rolavel.AreaReal.width
        altura = self.ALTURAS["musicas"]
        gap = 10
        for evento in eventos:
            if evento.type == pygame.MOUSEBUTTONDOWN and getattr(evento, "button", 0) == 1:
                if not self._rolavel.rect.collidepoint(evento.pos):
                    continue
                cx = evento.pos[0] - self._rolavel.rect.x + self._rolavel.ScrollX
                cy = evento.pos[1] - self._rolavel.rect.y + self._rolavel.ScrollY
                indice = max(0, int((cy - 8) // (altura + gap)))
                item_rect = self._rect_item_content(indice, largura)
                musica = self._musica_por_indice(indice)
                if musica is None or not item_rect.collidepoint((cx, cy)):
                    continue
                play, barra = MiniPainelMusica.areas(item_rect)
                chave = MiniPainelMusica.chave(musica)
                if play.collidepoint((cx, cy)):
                    estado = Sonoridades.musica_conhecimento_estado() if Sonoridades is not None and hasattr(Sonoridades, "musica_conhecimento_estado") else {}
                    if estado.get("nome") == chave and estado.get("tocando"):
                        self._parar_musica_conhecimento()
                    else:
                        self._tocar_ou_seek_musica(musica, 0.0)
                    self._rolavel.marcar_sujo()
                    continue
                if barra.collidepoint((cx, cy)):
                    pos = self._posicao_barra_musica(musica, barra, cx)
                    self._arrastando_musica = chave
                    self._tocar_ou_seek_musica(musica, pos)
                    self._rolavel.marcar_sujo()

            elif evento.type == pygame.MOUSEMOTION and self._arrastando_musica:
                cx = evento.pos[0] - self._rolavel.rect.x + self._rolavel.ScrollX
                cy = evento.pos[1] - self._rolavel.rect.y + self._rolavel.ScrollY
                indice = max(0, int((cy - 8) // (altura + gap)))
                musica = self._musica_por_indice(indice)
                if musica is None or MiniPainelMusica.chave(musica) != self._arrastando_musica:
                    continue
                item_rect = self._rect_item_content(indice, largura)
                _play, barra = MiniPainelMusica.areas(item_rect)
                pos = self._posicao_barra_musica(musica, barra, cx)
                self._tocar_ou_seek_musica(musica, pos)
                self._rolavel.marcar_sujo()

            elif evento.type == pygame.MOUSEBUTTONUP and getattr(evento, "button", 0) == 1:
                self._arrastando_musica = None

    # ------------------------------------------------------------------
    # Desenho
    # ------------------------------------------------------------------
    def _desenhar_fundo(self, tela):
        tela.fill((8, 12, 22), self._rect)
        camada = pygame.Surface(self._rect.size, pygame.SRCALPHA)
        pygame.draw.rect(camada, (12, 18, 32, 248), camada.get_rect(), border_radius=22)
        pygame.draw.ellipse(camada, (58, 82, 150, 28), (-120, -190, self._rect.width + 240, 300))
        pygame.draw.ellipse(camada, (22, 36, 82, 30), (self._rect.width - 360, 36, 420, 260))
        tela.blit(camada, self._rect.topleft)

    def _desenhar_topo(self, tela, lista):
        self._texto("titulo", "Conhecimento", (self._rect.x + 26, self._rect.y + 20), self._style_texto(34, (247, 250, 255)))
        self._texto(
            "contador",
            f"{len(lista)} registros encontrados",
            (self._rect.x + 28, self._rect.y + 62),
            self._style_texto(17, (185, 205, 238)),
        )
        for aba, _rotulo in self.ABAS:
            botao = self._botoes_abas[aba]
            selecionado = aba == self._aba
            if self._status_estilo_abas.get(aba) != selecionado:
                botao.set_style(**self._style_botao_aba(selecionado))
                self._status_estilo_abas[aba] = selecionado
            botao.render(tela, self._eventos_frame, self._dt_frame, None)
        self._botao_fechar.render(tela, self._eventos_frame, self._dt_frame, None)

    def _desenhar_conteudo_rolavel(self, tela_painel: pygame.Surface, rolavel: _ListaConhecimentoRolavel):
        pygame.draw.rect(tela_painel, (9, 14, 26, 220), tela_painel.get_rect(), border_radius=18)
        lista = self._lista_atual()
        largura = rolavel.AreaReal.width
        altura_item = self.ALTURAS.get(self._aba, 80)
        gap = 10
        total = len(lista)
        visivel = rolavel.obter_area_visivel_no_conteudo()
        y_base = 8

        if total <= 0:
            msg = "Nenhum registro encontrado nessa categoria."
            sub = "Quando o perfil tiver IDs de conhecimento, eles aparecem aqui."
            self._texto_local(tela_painel, "vazio1", msg, (largura // 2, 80), self._style_texto(24, (235, 242, 255), "center"))
            self._texto_local(tela_painel, "vazio2", sub, (largura // 2, 116), self._style_texto(17, (170, 190, 225), "center"))
            return

        inicio = max(0, int((visivel.y - y_base) // (altura_item + gap)) - 2)
        fim = min(total, int((visivel.bottom - y_base) // (altura_item + gap)) + 3)
        mini = self._minis[self._aba]
        for indice in range(inicio, fim):
            item = lista[indice]
            rect_item = self._rect_item_content(indice, largura)
            mini.renderizar(tela_painel, rect_item.move(-rolavel.ScrollX, -rolavel.ScrollY), item, eventos=self._eventos_frame, dt=self._dt_frame)

    def _texto_local(self, tela_local, chave: str, conteudo: str, pos, style: dict):
        txt = self._textos.get(chave)
        if txt is None:
            txt = Texto(conteudo, style=style)
            self._textos[chave] = txt
        txt.set_text(conteudo)
        txt.set_pos(pos)
        txt.draw(tela_local)

    def renderizar(self, tela, rect, eventos=None, dt=0.0):
        eventos = eventos or []
        self._solicitou_fechar = False
        self._tela_atual = tela
        self._eventos_frame = eventos
        self._dt_frame = dt

        self._reconstruir_layout(pygame.Rect(rect))
        if self._aba_anterior != self._aba:
            self._aba_anterior = self._aba
            if self._rolavel is not None:
                self._rolavel.marcar_sujo()

        lista = self._lista_atual()
        assinatura_lista = (self._aba, len(lista), id(lista))
        if assinatura_lista != self._ultima_lista_assinatura:
            self._ultima_lista_assinatura = assinatura_lista
            if self._rolavel is not None:
                self._rolavel.marcar_sujo()
        altura_item = self.ALTURAS.get(self._aba, 80)
        gap = 10
        altura_total = 16 + len(lista) * (altura_item + gap)
        self._rolavel.definir_area_real(self._area_lista.width, max(self._area_lista.height, altura_total))

        # Música atualiza o cursor da barra a cada frame.
        if self._aba == "musicas":
            self._processar_interacao_musicas(eventos)
            self._rolavel.marcar_sujo()

        self._desenhar_fundo(tela)
        self._desenhar_topo(tela, lista)
        self._rolavel.render(tela, eventos, dt, None)
        return self._solicitou_fechar
