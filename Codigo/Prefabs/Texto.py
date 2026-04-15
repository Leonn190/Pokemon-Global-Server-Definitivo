import pygame
import re
from pathlib import Path

CAMINHO_FONTE_PADRAO = Path("Recursos/Visual/Fontes/FontePadrão.ttf")


class Texto:
    ALIGN_ALIASES = {
        "left": "midleft",
        "right": "midright",
        "top": "midtop",
        "bottom": "midbottom",
    }

    DEFAULT_STYLE = {
        "size": 24,
        "color": (255, 255, 255),
        "align": "topleft",

        "outline": True,
        "outline_color": (0, 0, 0),
        "outline_thickness": 2,

        "highlight": False,
        "highlight_color": (255, 235, 80, 200),
        "highlight_padding": (8, 4),
        "highlight_radius": 10,

        "shadow": False,
        "shadow_color": (0, 0, 0, 160),
        "shadow_offset": (2, 2),
    }

    def __init__(self, text: str, pos=(0, 0), style=None):
        self.text = text
        self.pos = pos
        self.style = dict(self.DEFAULT_STYLE)
        if style:
            self.style.update(style)

        self._font = None

        # cache “estrutural” (tudo exceto cor do texto)
        self._structure_key = None
        self._structure_surf = None
        self._structure_origin = (0, 0)  # onde blitar o texto dentro do surf estrutural

        # cache de render do texto por cor (evita renderizar infinitamente)
        self._text_color_cache = {}  # (text, color, size) -> Surface
        self._max_color_cache = 32   # limite simples pra não crescer infinito

        # cache final (último frame)
        self._final_key = None
        self._final_surf = None

        self._load_font()
        self._invalidate_all()

    def _load_font(self):
        self._font = pygame.font.Font(str(CAMINHO_FONTE_PADRAO), int(self.style["size"]))

    def _invalidate_all(self):
        self._structure_key = None
        self._structure_surf = None
        self._final_key = None
        self._final_surf = None

    def _invalidate_final(self):
        self._final_key = None
        self._final_surf = None

    # --- API ---
    def set_style(self, **kwargs):
        size_before = int(self.style["size"])
        self.style.update(kwargs)
        size_after = int(self.style["size"])

        if size_after != size_before:
            self._load_font()
            # fonte mudou -> limpa tudo + cache de cores (pq muda o tamanho real)
            self._text_color_cache.clear()
            self._invalidate_all()
            return

        # se mudou algo “estrutural”, recria estrutura
        # se mudou só "color", não precisa refazer outline/shadow/highlight, só o final
        structural_keys = {
            "align",
            "outline", "outline_color", "outline_thickness",
            "highlight", "highlight_color", "highlight_padding", "highlight_radius",
            "shadow", "shadow_color", "shadow_offset",
        }

        if any(k in structural_keys for k in kwargs.keys()):
            self._structure_key = None
            self._structure_surf = None
            self._invalidate_final()
        else:
            # provavelmente só cor (ou algo irrelevante) -> só invalida o final
            self._invalidate_final()

    def set_text(self, text: str):
        if text != self.text:
            self.text = text
            self._invalidate_final()
            # texto mudou -> estrutura também muda (tamanho)
            self._structure_key = None
            self._structure_surf = None

    def set_pos(self, pos):
        self.pos = pos

    # --------- helpers de cache ----------
    def _render_text_color(self, text: str, color):
        # cache de superfície renderizada (por cor)
        key = (text, color, int(self.style["size"]))
        surf = self._text_color_cache.get(key)
        if surf is not None:
            return surf

        surf = self._font.render(text, True, color).convert_alpha()

        # cache simples com limite
        if len(self._text_color_cache) >= self._max_color_cache:
            # remove um item qualquer (FIFO/aleatório simples)
            self._text_color_cache.pop(next(iter(self._text_color_cache)))
        self._text_color_cache[key] = surf
        return surf

    def _ensure_structure(self):
        st = self.style

        # a estrutura depende de tudo exceto da cor do texto (pq a cor muda sempre no hover)
        structure_key = (
            self.text,
            int(st["size"]),
            bool(st["outline"]),
            int(st["outline_thickness"]),
            tuple(st["outline_color"]),
            bool(st["highlight"]),
            tuple(st["highlight_color"]),
            tuple(st["highlight_padding"]),
            int(st["highlight_radius"]),
            bool(st["shadow"]),
            tuple(st["shadow_color"]),
            tuple(st["shadow_offset"]),
        )

        if self._structure_key == structure_key and self._structure_surf is not None:
            return

        # mede com uma cor qualquer (branco) só pra pegar w/h
        base_measure = self._font.render(self.text, True, (255, 255, 255)).convert_alpha()
        w, h = base_measure.get_size()

        pad_outline = int(st["outline_thickness"]) if st["outline"] else 0
        hp_x, hp_y = st["highlight_padding"]
        pad_high_x = hp_x if st["highlight"] else 0
        pad_high_y = hp_y if st["highlight"] else 0

        shadow = st["shadow"]
        sh_x, sh_y = st["shadow_offset"] if shadow else (0, 0)

        pad_total_x = pad_outline + pad_high_x + abs(sh_x)
        pad_total_y = pad_outline + pad_high_y + abs(sh_y)

        surf = pygame.Surface((w + pad_total_x * 2, h + pad_total_y * 2), pygame.SRCALPHA)

        # highlight antes
        if st["highlight"]:
            rect = pygame.Rect(
                pad_total_x - pad_high_x,
                pad_total_y - pad_high_y,
                w + pad_high_x * 2,
                h + pad_high_y * 2,
            )
            pygame.draw.rect(
                surf,
                st["highlight_color"],
                rect,
                border_radius=int(st["highlight_radius"]),
            )

        # sombra (renderiza uma vez na cor de shadow)
        if shadow:
            shadow_surf = self._render_text_color(self.text, st["shadow_color"])
            surf.blit(shadow_surf, (pad_total_x + sh_x, pad_total_y + sh_y))

        # outline (renderiza uma vez a “fonte” do contorno)
        if st["outline"] and pad_outline > 0:
            border_surf = self._render_text_color(self.text, st["outline_color"])
            # otimização: só desenha o “anel” (não o quadrado inteiro)
            t = pad_outline
            for dx in range(-t, t + 1):
                for dy in range(-t, t + 1):
                    if dx == 0 and dy == 0:
                        continue
                    # pular interior (deixa só a borda externa), reduz blits
                    if abs(dx) != t and abs(dy) != t:
                        continue
                    surf.blit(border_surf, (pad_total_x + dx, pad_total_y + dy))

        # onde o texto principal vai ser blitado depois
        self._structure_origin = (pad_total_x, pad_total_y)
        self._structure_surf = surf
        self._structure_key = structure_key

        # estrutura mudou, final inválido
        self._final_key = None
        self._final_surf = None

    def _render(self):
        self._ensure_structure()

        st = self.style
        color = st["color"]

        final_key = (self._structure_key, tuple(color))
        if self._final_key == final_key and self._final_surf is not None:
            return self._final_surf

        # monta final = estrutura + texto na cor atual
        surf = self._structure_surf.copy()
        base = self._render_text_color(self.text, color)
        ox, oy = self._structure_origin
        surf.blit(base, (ox, oy))

        self._final_surf = surf
        self._final_key = final_key
        return surf

    def get_rect(self):
        surf = self._render()
        rect = surf.get_rect()
        align = self.ALIGN_ALIASES.get(str(self.style["align"]).strip().lower(), self.style["align"])
        setattr(rect, align, self.pos)
        return rect

    def medir_largura(self, texto: str) -> int:
        return int(self._font.size(str(texto or ""))[0])

    def draw(self, tela: pygame.Surface):
        surf = self._render()
        rect = surf.get_rect()
        align = self.ALIGN_ALIASES.get(str(self.style["align"]).strip().lower(), self.style["align"])
        setattr(rect, align, self.pos)
        tela.blit(surf, rect)


class SetorTexto:
    _ALINHAMENTOS = {
        "left": "topleft",
        "esquerda": "topleft",
        "right": "topright",
        "direita": "topright",
        "center": "midtop",
        "centro": "midtop",
        "justify": "topleft",
        "justificado": "topleft",
    }

    def __init__(self, rect=(0, 0, 10, 10), texto: str = "", linhas: int = 3, caracteres_por_linha: int = 36, style=None):
        self.Rect = pygame.Rect(rect)
        self.TextoBruto = str(texto or "")
        self.LinhasMax = max(1, int(linhas))
        self.CaracteresPorLinha = max(1, int(caracteres_por_linha))
        self._style = dict(Texto.DEFAULT_STYLE)
        self._style.update({"align": "topleft"})
        if style:
            self._style.update(style)
        self._estilo_setor = str(self._style.pop("setor_align", "left")).strip().lower()
        self._texto = Texto("", style=self._style)

    def configurar_rect(self, rect):
        self.Rect = pygame.Rect(rect)

    def set_texto(self, texto: str):
        self.TextoBruto = str(texto or "")

    def set_limites(self, linhas: int | None = None, caracteres_por_linha: int | None = None):
        if linhas is not None:
            self.LinhasMax = max(1, int(linhas))
        if caracteres_por_linha is not None:
            self.CaracteresPorLinha = max(1, int(caracteres_por_linha))

    def set_style(self, **kwargs):
        if "setor_align" in kwargs:
            self._estilo_setor = str(kwargs.pop("setor_align")).strip().lower()
        if kwargs:
            self._texto.set_style(**kwargs)

    def _alinhar_linha(self, linha: str, y: int):
        alinhamento = self._ALINHAMENTOS.get(self._estilo_setor, "topleft")
        if alinhamento == "topright":
            self._texto.set_pos((self.Rect.right, y))
        elif alinhamento == "midtop":
            self._texto.set_pos((self.Rect.centerx, y))
        else:
            self._texto.set_pos((self.Rect.x, y))
        self._texto.set_style(align=alinhamento)
        self._texto.set_text(linha)

    def _quebrar_linhas(self) -> list[str]:
        palavras = self.TextoBruto.split()
        if not palavras:
            return []

        linhas: list[str] = []
        atual = ""
        for palavra in palavras:
            tentativa = palavra if not atual else f"{atual} {palavra}"
            largura_ok = self._texto.medir_largura(tentativa) <= self.Rect.width
            chars_ok = len(tentativa) <= self.CaracteresPorLinha
            if (largura_ok and chars_ok) or not atual:
                atual = tentativa
            else:
                linhas.append(atual)
                atual = palavra
            if len(linhas) >= self.LinhasMax:
                break
        if len(linhas) < self.LinhasMax and atual:
            linhas.append(atual)

        if len(linhas) > self.LinhasMax:
            linhas = linhas[: self.LinhasMax]
        if len(linhas) == self.LinhasMax and " ".join(palavras) != " ".join(linhas):
            ultima = linhas[-1].rstrip(". ")
            while ultima and self._texto.medir_largura(f"{ultima}...") > self.Rect.width:
                ultima = ultima[:-1]
            linhas[-1] = f"{ultima}..." if ultima else "..."
        return linhas

    def draw(self, tela: pygame.Surface):
        linhas = self._quebrar_linhas()
        if not linhas:
            return
        altura_linha = max(10, int(self._style.get("size", 14) * 1.08))
        y = self.Rect.y
        for i, linha in enumerate(linhas):
            self._alinhar_linha(linha, y + i * altura_linha)
            self._texto.draw(tela)


class TextoAtaque(SetorTexto):
    _REGEX_ESCALA_PAREN = re.compile(r"\(\s*(?P<conteudo>(?P<pct>\d+(?:[.,]\d+)?)%\s+d[aeo]\s+(?P<attr>[A-Za-zÀ-ÿ]{2,4}))\s*\)", re.IGNORECASE)
    _CORES_ATRIBUTO = {
        "vida": (108, 201, 123),
        "atk": (235, 109, 94),
        "def": (227, 192, 92),
        "spa": (166, 104, 255),
        "spd": (121, 214, 255),
        "vel": (255, 174, 82),
        "mag": (255, 138, 206),
        "per": (155, 155, 155),
        "ene": (56, 104, 212),
        "int": (86, 229, 240),
        "crc": (235, 109, 94),
        "crd": (235, 109, 94),
    }
    _NOME_ATRIBUTO = {
        "vida": "Vida", "atk": "Atk", "def": "Def", "spa": "SpA", "spd": "SpD",
        "vel": "Vel", "mag": "Mag", "per": "Per", "ene": "Ene", "int": "Int",
        "crc": "CrC", "crd": "CrD",
    }
    _cache_icones: dict[str, pygame.Surface] = {}

    def __init__(self, rect=(0, 0, 10, 10), texto: str = "", linhas: int = 4, caracteres_por_linha: int = 40, style=None):
        super().__init__(rect=rect, texto=texto, linhas=linhas, caracteres_por_linha=caracteres_por_linha, style=style)
        self._atributos: dict[str, float] = {}
        self._areas_tooltip: list[tuple[pygame.Rect, str]] = []

    @staticmethod
    def _normalizar_attr(nome: str) -> str:
        base = (nome or "").strip().lower()
        return "".join(c for c in base if c.isalnum())

    def set_atributos(self, atributos: dict | None):
        self._atributos = {}
        if not isinstance(atributos, dict):
            return
        for chave, valor in atributos.items():
            n = self._normalizar_attr(str(chave))
            if not n:
                continue
            try:
                self._atributos[n] = float(valor)
            except (TypeError, ValueError):
                continue

    @classmethod
    def _carregar_icone_attr(cls, atributo: str, tamanho: int) -> pygame.Surface | None:
        nome = cls._NOME_ATRIBUTO.get(atributo, atributo)
        chave = f"{nome}:{tamanho}"
        if chave in cls._cache_icones:
            return cls._cache_icones[chave]
        caminho = Path("Recursos") / "Visual" / "Icones" / "Atributos" / f"{nome}.png"
        if not caminho.exists():
            return None
        try:
            imagem = pygame.image.load(str(caminho)).convert_alpha()
            img = pygame.transform.smoothscale(imagem, (tamanho, tamanho))
            cls._cache_icones[chave] = img
            return img
        except Exception:
            return None

    def _valor_atributo(self, atributo: str) -> float:
        return float(self._atributos.get(atributo, 0.0))

    def _segmentos_linha(self, linha: str):
        segmentos = []
        inicio = 0
        for match in self._REGEX_ESCALA_PAREN.finditer(linha):
            if match.start() > inicio:
                segmentos.append({"tipo": "texto", "texto": linha[inicio:match.start()]})
            pct_txt = match.group("pct").replace(",", ".")
            atributo_n = self._normalizar_attr(match.group("attr"))
            if atributo_n in self._NOME_ATRIBUTO:
                try:
                    pct = float(pct_txt)
                except ValueError:
                    pct = 0.0
                base = self._valor_atributo(atributo_n)
                calculado = int(round(base * (pct / 100.0)))
                segmentos.append(
                    {
                        "tipo": "calc",
                        "texto": str(calculado),
                        "atributo": atributo_n,
                        "tooltip": f"{int(round(pct))}% de {self._NOME_ATRIBUTO[atributo_n]}: {int(round(base))} × {pct / 100.0:.2f} = {calculado}",
                    }
                )
            else:
                segmentos.append({"tipo": "texto", "texto": match.group(0)})
            inicio = match.end()
        if inicio < len(linha):
            segmentos.append({"tipo": "texto", "texto": linha[inicio:]})
        return segmentos

    def _quebrar_linhas(self) -> list[str]:
        palavras = self.TextoBruto.split()
        if not palavras:
            return []

        linhas: list[str] = []
        atual = ""
        for palavra in palavras:
            tentativa = palavra if not atual else f"{atual} {palavra}"
            extras = len(self._REGEX_ESCALA_PAREN.findall(tentativa)) * 2
            largura_ok = self._texto.medir_largura(tentativa + (" " * extras)) <= self.Rect.width
            chars_ok = (len(tentativa) + extras) <= self.CaracteresPorLinha
            if (largura_ok and chars_ok) or not atual:
                atual = tentativa
            else:
                linhas.append(atual)
                atual = palavra
            if len(linhas) >= self.LinhasMax:
                break
        if len(linhas) < self.LinhasMax and atual:
            linhas.append(atual)

        if len(linhas) > self.LinhasMax:
            linhas = linhas[: self.LinhasMax]
        if len(linhas) == self.LinhasMax and " ".join(palavras) != " ".join(linhas):
            ultima = linhas[-1].rstrip(". ")
            while ultima:
                extras = len(self._REGEX_ESCALA_PAREN.findall(ultima)) * 2
                if self._texto.medir_largura(f"{ultima}..." + (" " * extras)) <= self.Rect.width:
                    break
                ultima = ultima[:-1]
            linhas[-1] = f"{ultima}..." if ultima else "..."
        return linhas

    def draw(self, tela: pygame.Surface):
        from Codigo.Prefabs.Tooltip import Tooltip

        self._areas_tooltip = []
        linhas = self._quebrar_linhas()
        if not linhas:
            return
        altura_linha = max(10, int(self._style.get("size", 14) * 1.1))
        y = self.Rect.y
        base_style = dict(self._style)
        base_style["align"] = "topleft"
        icon_lado = max(12, int(base_style.get("size", 14) * 0.88))
        mouse_pos = pygame.mouse.get_pos()
        for i, linha in enumerate(linhas):
            x = self.Rect.x
            for seg in self._segmentos_linha(linha):
                if seg["tipo"] == "texto":
                    txt = Texto(seg["texto"], pos=(x, y + i * altura_linha), style=base_style)
                    txt.draw(tela)
                    x += txt.get_rect().width
                    continue

                cor_attr = self._CORES_ATRIBUTO.get(seg["atributo"], base_style.get("color", (220, 230, 245)))
                style_num = dict(base_style)
                style_num["color"] = cor_attr
                num = Texto(seg["texto"], pos=(x, y + i * altura_linha), style=style_num)
                num.draw(tela)
                rect_num = num.get_rect()
                rect_num.topleft = (x, y + i * altura_linha)
                x += rect_num.width

                icone = self._carregar_icone_attr(seg["atributo"], icon_lado)
                rect_total = pygame.Rect(rect_num)
                if icone is not None:
                    rect_i = icone.get_rect(midleft=(x + 4, rect_num.centery))
                    tela.blit(icone, rect_i)
                    rect_total.union_ip(rect_i)
                    x = rect_i.right + 2

                self._areas_tooltip.append((rect_total, seg["tooltip"]))

        for area, texto in self._areas_tooltip:
            if area.collidepoint(mouse_pos):
                tip = Tooltip(texto=texto, area_ativacao=area, largura_max=220, padding=8, raio=9, style={"size": 13})
                tip.definir_posicao_fixa((area.centerx - 96, area.y - 46))
                tip.render(tela, mouse_pos=mouse_pos, forcar=True)


class TextoRegistroLog(TextoAtaque):
    def __init__(self, rect=(0, 0, 10, 10), texto: str = "", linhas: int = 8, caracteres_por_linha: int = 60, style=None):
        super().__init__(rect=rect, texto=texto, linhas=linhas, caracteres_por_linha=caracteres_por_linha, style=style)
        self._segmentos_registro: list[dict[str, object]] = []
        self._linhas_cache: list[list[dict[str, object]]] = []
        self._cache_layout_key = None

    def set_texto(self, texto: str):
        super().set_texto(texto)
        self._segmentos_registro = []
        self._cache_layout_key = None

    def set_segmentos(self, segmentos: list[dict[str, object]] | None):
        self._segmentos_registro = [dict(item) for item in list(segmentos or []) if isinstance(item, dict)]
        if self._segmentos_registro:
            self.TextoBruto = "".join(str(item.get("texto") or "") for item in self._segmentos_registro)
        self._cache_layout_key = None

    def obter_areas_tooltip(self) -> list[dict[str, object]]:
        return [dict(item) for item in list(self._areas_tooltip or []) if isinstance(item, dict)]

    def altura_linha(self) -> int:
        return max(10, int(self._style.get("size", 14) * 1.14))

    def medir_altura(self) -> int:
        linhas = self._linhas_quebradas()
        if not linhas:
            return 0
        return len(linhas) * self.altura_linha()

    def _segmentos_fonte(self) -> list[dict[str, object]]:
        if self._segmentos_registro:
            return [dict(item) for item in self._segmentos_registro]
        return [{"texto": self.TextoBruto}]

    def _tokenizar_segmento(self, segmento: dict[str, object]) -> list[dict[str, object]]:
        texto = str(segmento.get("texto") or "")
        if not texto:
            return []
        base = {k: v for k, v in dict(segmento).items() if k != "texto"}
        tokens: list[dict[str, object]] = []
        for bloco in re.split(r"(\n)", texto):
            if bloco == "":
                continue
            if bloco == "\n":
                tokens.append({"tipo": "quebra"})
                continue
            for parte in re.split(r"(\s+)", bloco):
                if parte == "":
                    continue
                tokens.append({"tipo": "texto", "texto": parte, **base})
        return tokens

    def _tokens(self) -> list[dict[str, object]]:
        tokens: list[dict[str, object]] = []
        for segmento in self._segmentos_fonte():
            tokens.extend(self._tokenizar_segmento(segmento))
        return tokens

    def _medir_token(self, token: dict[str, object]) -> int:
        return int(self._texto.medir_largura(str(token.get("texto") or "")))

    @staticmethod
    def _linha_vazia(tokens: list[dict[str, object]]) -> bool:
        return not any(str(token.get("texto") or "").strip() for token in tokens if token.get("tipo") == "texto")

    @staticmethod
    def _remover_espacos_fim(tokens: list[dict[str, object]]) -> list[dict[str, object]]:
        saida = list(tokens)
        while saida and str(saida[-1].get("texto") or "").isspace():
            saida.pop()
        return saida

    def _adicionar_ellipsis(self, linha: list[dict[str, object]]) -> list[dict[str, object]]:
        ellipsis = {"tipo": "texto", "texto": "..."}
        linha = self._remover_espacos_fim(linha)
        while linha:
            largura = sum(self._medir_token(token) for token in linha) + self._texto.medir_largura("...")
            if largura <= self.Rect.width:
                break
            linha.pop()
            linha = self._remover_espacos_fim(linha)
        linha.append(ellipsis)
        return linha

    def _linhas_quebradas(self) -> list[list[dict[str, object]]]:
        chave = (
            self.Rect.width,
            self.Rect.height,
            self.LinhasMax,
            self.CaracteresPorLinha,
            self.TextoBruto,
            tuple(
                (
                    str(item.get("texto") or ""),
                    str(item.get("atributo") or ""),
                    str(item.get("tooltip") or ""),
                    str(item.get("titulo_tooltip") or ""),
                    str(item.get("descricao_tooltip") or ""),
                )
                for item in self._segmentos_registro
            ),
        )
        if self._cache_layout_key == chave:
            return self._linhas_cache

        linhas: list[list[dict[str, object]]] = []
        linha_atual: list[dict[str, object]] = []
        largura_atual = 0
        chars_atual = 0
        houve_corte = False

        for token in self._tokens():
            if token.get("tipo") == "quebra":
                if linha_atual or not linhas:
                    linhas.append(self._remover_espacos_fim(linha_atual))
                linha_atual = []
                largura_atual = 0
                chars_atual = 0
                if len(linhas) >= self.LinhasMax:
                    houve_corte = True
                    break
                continue

            texto_token = str(token.get("texto") or "")
            if not texto_token:
                continue

            if texto_token.isspace() and not linha_atual:
                continue

            largura = self._medir_token(token)
            novo_chars = chars_atual + len(texto_token)
            excedeu_largura = bool(linha_atual) and (largura_atual + largura > self.Rect.width)
            excedeu_chars = bool(linha_atual) and (novo_chars > self.CaracteresPorLinha)

            if excedeu_largura or excedeu_chars:
                linhas.append(self._remover_espacos_fim(linha_atual))
                linha_atual = []
                largura_atual = 0
                chars_atual = 0
                if len(linhas) >= self.LinhasMax:
                    houve_corte = True
                    break
                if texto_token.isspace():
                    continue

            linha_atual.append(dict(token))
            largura_atual += largura
            chars_atual += len(texto_token)

        if not houve_corte and (linha_atual or not linhas):
            linhas.append(self._remover_espacos_fim(linha_atual))

        linhas = [linha for linha in linhas if linha and not self._linha_vazia(linha)]
        if houve_corte and linhas:
            linhas[-1] = self._adicionar_ellipsis(linhas[-1])
        if len(linhas) > self.LinhasMax:
            linhas = linhas[: self.LinhasMax]
            linhas[-1] = self._adicionar_ellipsis(linhas[-1])

        self._linhas_cache = linhas
        self._cache_layout_key = chave
        return linhas

    def draw(self, tela: pygame.Surface):
        self._areas_tooltip = []
        linhas = self._linhas_quebradas()
        if not linhas:
            return

        base_style = dict(self._style)
        base_style["align"] = "topleft"
        altura_linha = self.altura_linha()

        for indice_linha, linha in enumerate(linhas):
            x = self.Rect.x
            y = self.Rect.y + indice_linha * altura_linha
            for token in linha:
                texto_token = str(token.get("texto") or "")
                if not texto_token:
                    continue
                atributo = self._normalizar_attr(str(token.get("atributo") or ""))
                style_token = dict(base_style)
                if atributo:
                    style_token["color"] = self._CORES_ATRIBUTO.get(atributo, style_token.get("color", (220, 230, 245)))
                txt = Texto(texto_token, pos=(x, y), style=style_token)
                txt.draw(tela)
                rect_token = txt.get_rect()
                rect_token.topleft = (x, y)
                tooltip = token.get("tooltip")
                titulo_tooltip = str(token.get("titulo_tooltip") or "").strip()
                descricao_tooltip = str(token.get("descricao_tooltip") or "").strip()
                if (tooltip or titulo_tooltip or descricao_tooltip) and not texto_token.isspace():
                    self._areas_tooltip.append(
                        {
                            "rect": pygame.Rect(rect_token),
                            "tooltip": str(tooltip or ""),
                            "titulo": titulo_tooltip,
                            "descricao": descricao_tooltip,
                        }
                    )
                x += rect_token.width


class TextoAnimado:
    def __init__(self, texto: str = "", cps: float = 46.0):
        self.TextoCompleto = str(texto or "")
        self.Cps = max(1.0, float(cps))
        self._tempo = 0.0
        self._chars_visiveis = 0
        self._concluido = False

    def set_texto(self, texto: str) -> None:
        self.TextoCompleto = str(texto or "")
        self._tempo = 0.0
        self._chars_visiveis = 0
        self._concluido = False

    def atualizar(self, dt: float) -> None:
        if self._concluido:
            return
        self._tempo += max(0.0, float(dt))
        alvo = int(self._tempo * self.Cps)
        self._chars_visiveis = max(self._chars_visiveis, alvo)
        if self._chars_visiveis >= len(self.TextoCompleto):
            self._chars_visiveis = len(self.TextoCompleto)
            self._concluido = True

    def pular_animacao(self) -> None:
        self._chars_visiveis = len(self.TextoCompleto)
        self._concluido = True

    @property
    def concluido(self) -> bool:
        return bool(self._concluido)

    @property
    def texto_visivel(self) -> str:
        return self.TextoCompleto[: max(0, int(self._chars_visiveis))]
