import pygame
from pathlib import Path

CAMINHO_FONTE_PADRAO = Path("Recursos/Visual/Fontes/FontePadrão.ttf")


class Texto:
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
        setattr(rect, self.style["align"], self.pos)
        return rect

    def medir_largura(self, texto: str) -> int:
        return int(self._font.size(str(texto or ""))[0])

    def draw(self, tela: pygame.Surface):
        surf = self._render()
        rect = surf.get_rect()
        setattr(rect, self.style["align"], self.pos)
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
