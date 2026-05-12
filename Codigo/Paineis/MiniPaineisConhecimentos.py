from __future__ import annotations

from pathlib import Path
import unicodedata

import pygame

from Codigo.Paineis.FichaAtaque import FichaAtaque
from Codigo.Paineis.FichaItem import FichaItem
from Codigo.Prefabs.Barra import Barra
from Codigo.Prefabs.Texto import Texto, TextoAtaque

try:
    from Codigo.ModulosGerais.Auxiliares import construir_icone_tipo_com_fundo_branco
except Exception:
    construir_icone_tipo_com_fundo_branco = None

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


def _texto_valor(dados: dict | None, *chaves, default="-"):
    if not isinstance(dados, dict):
        return default
    alvo = {_norm(ch) for ch in chaves if str(ch or "").strip()}
    for chave, valor in dados.items():
        if _norm(chave) in alvo and valor not in (None, ""):
            return valor
    return default


def _fmt(valor):
    texto = str(valor if valor is not None else "-").strip()
    if not texto:
        return "-"
    try:
        numero = float(texto.replace(",", "."))
        if numero.is_integer():
            return str(int(numero))
        return f"{numero:.2f}".rstrip("0").rstrip(".")
    except Exception:
        return texto


class _RecursosVisuais:
    _cache_superficies: dict[tuple[str, tuple[int, int], str], pygame.Surface | None] = {}
    _cache_listagem: dict[str, dict[str, Path]] = {}
    _cache_primeiro_frame: dict[tuple[str, int], pygame.Surface | None] = {}

    @classmethod
    def roots(cls) -> list[Path]:
        atual = Path(__file__).resolve()
        candidatos = [Path(".").resolve(), atual.parent]
        candidatos.extend(atual.parents[:7])
        vistos: list[Path] = []
        for caminho in candidatos:
            if caminho not in vistos:
                vistos.append(caminho)
        return vistos

    @classmethod
    def pastas_existentes(cls, subcaminho: Path) -> list[Path]:
        pastas = []
        for raiz in cls.roots():
            pasta = raiz / subcaminho
            if pasta.exists() and pasta.is_dir():
                pastas.append(pasta)
        return pastas

    @classmethod
    def _listar_arquivos(cls, pasta: Path) -> dict[str, Path]:
        chave = str(pasta.resolve())
        if chave in cls._cache_listagem:
            return cls._cache_listagem[chave]
        mapa: dict[str, Path] = {}
        try:
            for arquivo in pasta.iterdir():
                if arquivo.is_file():
                    mapa.setdefault(_norm(arquivo.stem), arquivo)
        except OSError:
            pass
        cls._cache_listagem[chave] = mapa
        return mapa

    @classmethod
    def achar_arquivo(cls, subcaminho: Path, *nomes) -> Path | None:
        candidatos = [_norm(nome) for nome in nomes if str(nome or "").strip()]
        if not candidatos:
            return None
        for pasta in cls.pastas_existentes(subcaminho):
            mapa = cls._listar_arquivos(pasta)
            for nome in candidatos:
                if nome in mapa:
                    return mapa[nome]
            for nome in candidatos:
                for chave, arquivo in mapa.items():
                    if chave == nome or chave.startswith(nome) or nome in chave:
                        return arquivo
        return None

    @classmethod
    def carregar_surface(cls, arquivo: Path | None, tamanho: tuple[int, int], modo="contain") -> pygame.Surface | None:
        if arquivo is None:
            return None
        chave = (str(arquivo), tuple(map(int, tamanho)), str(modo))
        if chave in cls._cache_superficies:
            return cls._cache_superficies[chave]
        try:
            img = pygame.image.load(str(arquivo)).convert_alpha()
        except Exception:
            cls._cache_superficies[chave] = None
            return None
        tw, th = max(1, int(tamanho[0])), max(1, int(tamanho[1]))
        if modo == "fill":
            surf = pygame.transform.smoothscale(img, (tw, th))
        else:
            iw, ih = img.get_size()
            escala = min(tw / max(1, iw), th / max(1, ih))
            nw, nh = max(1, int(iw * escala)), max(1, int(ih * escala))
            surf = pygame.transform.smoothscale(img, (nw, nh))
        cls._cache_superficies[chave] = surf
        return surf

    @classmethod
    def primeiro_frame_pokemon(cls, nome: str, limite_px: int) -> pygame.Surface | None:
        chave = (_norm(nome), int(limite_px))
        if chave in cls._cache_primeiro_frame:
            return cls._cache_primeiro_frame[chave]
        pastas = cls.pastas_existentes(Path("Recursos") / "Visual" / "Pokemons" / "Animação")
        alvo = _norm(nome)
        for base in pastas:
            candidatos = [base / alvo, base / str(nome or "").strip().lower(), base / str(nome or "").strip()]
            try:
                for pasta in base.iterdir():
                    if pasta.is_dir() and (_norm(pasta.name) == alvo or alvo in _norm(pasta.name)):
                        candidatos.append(pasta)
            except OSError:
                pass
            for pasta in candidatos:
                if not pasta.exists() or not pasta.is_dir():
                    continue
                arquivos = sorted(pasta.glob("*.png"))
                if not arquivos:
                    continue
                surf = cls.carregar_surface(arquivos[0], (limite_px, limite_px), "contain")
                cls._cache_primeiro_frame[chave] = surf
                return surf
        cls._cache_primeiro_frame[chave] = None
        return None

    @classmethod
    def icone_atributo(cls, atributo: str, lado: int) -> pygame.Surface | None:
        nome = "escala" if _norm(atributo) in {"tamanho", "escala"} else str(atributo or "")
        arq = cls.achar_arquivo(Path("Recursos") / "Visual" / "Icones" / "Atributos", nome)
        return cls.carregar_surface(arq, (lado, lado), "contain")

    @classmethod
    def icone_ataque(cls, nome: str, tipo: str, lado: int) -> pygame.Surface | None:
        arq_global = FichaAtaque._icone_ataque_path(nome)
        surf = cls.carregar_surface(arq_global, (lado, lado), "contain")
        if surf is not None:
            return surf
        sub = Path("Recursos") / "Visual" / "Icones" / "Ataques"
        for pasta_base in cls.pastas_existentes(sub):
            pastas_tipo = []
            try:
                for pasta in pasta_base.iterdir():
                    if pasta.is_dir() and (_norm(tipo) == _norm(pasta.name) or _norm(tipo) in _norm(pasta.name)):
                        pastas_tipo.append(pasta)
            except OSError:
                pass
            for pasta in pastas_tipo:
                arq = cls.achar_arquivo(sub / pasta.name, nome)
                surf = cls.carregar_surface(arq, (lado, lado), "contain")
                if surf is not None:
                    return surf
        arq = cls.achar_arquivo(sub, nome)
        return cls.carregar_surface(arq, (lado, lado), "contain")

    @classmethod
    def icone_efeito(cls, nome: str, lado: int) -> pygame.Surface | None:
        arq = cls.achar_arquivo(Path("Recursos") / "Visual" / "Icones" / "Efeitos", nome)
        return cls.carregar_surface(arq, (lado, lado), "contain")


class _MiniBase:
    ALTURA = 82

    def __init__(self):
        self.txt_titulo = Texto("", style={**_BASE_TEXTO, "size": 20, "color": (248, 251, 255)})
        self.txt_sub = Texto("", style={**_BASE_TEXTO, "size": 15, "color": (185, 205, 236)})
        self.txt_mini = Texto("", style={**_BASE_TEXTO, "size": 13, "color": (230, 239, 255), "align": "center"})
        self.txt_direita = Texto("", style={**_BASE_TEXTO, "size": 15, "color": (210, 225, 250), "align": "topright"})
        self.txt_desc = TextoAtaque(rect=(0, 0, 10, 10), texto="", linhas=2, caracteres_por_linha=70, style={**_BASE_TEXTO, "size": 14, "color": (190, 204, 230)})

    @staticmethod
    def _fundo(tela: pygame.Surface, rect: pygame.Rect, borda=(78, 112, 178), fundo=(13, 20, 36)):
        pygame.draw.rect(tela, fundo, rect, border_radius=15)
        pygame.draw.rect(tela, borda, rect, 1, border_radius=15)

    def _draw_texto(self, txt: Texto, tela, texto, pos):
        txt.set_text(str(texto))
        txt.set_pos(pos)
        txt.draw(tela)

    def _draw_icone_fallback(self, tela, rect: pygame.Rect, texto: str, cor=(70, 110, 190)):
        pygame.draw.rect(tela, (21, 31, 55), rect, border_radius=12)
        pygame.draw.rect(tela, cor, rect, 2, border_radius=12)
        self._draw_texto(self.txt_mini, tela, texto[:3].upper(), rect.center)


class MiniPainelPokemon(_MiniBase):
    ALTURA = 114
    STATUS = ("Vida", "Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Ene", "Int", "CrD", "CrC")

    def __init__(self):
        super().__init__()
        self.txt_status = Texto("", style={**_BASE_TEXTO, "size": 12, "color": (242, 247, 255), "align": "midleft"})
        self.txt_grupo = Texto("", style={**_BASE_TEXTO, "size": 14, "color": (225, 235, 255)})

    @staticmethod
    def tipos(pokemon: dict) -> list[str]:
        tipos = []
        for chave in ("Tipo1", "Tipo2", "Tipo3"):
            tipo = str(_texto_valor(pokemon, chave, default="")).strip()
            if tipo and _norm(tipo) not in {_norm(t) for t in tipos}:
                tipos.append(tipo)
        return tipos

    def _desenhar_atributo(self, tela, x, y, largura, atributo, valor):
        pill = pygame.Rect(x, y, largura, 22)
        pygame.draw.rect(tela, (18, 28, 50), pill, border_radius=9)
        pygame.draw.rect(tela, (54, 83, 138), pill, 1, border_radius=9)
        icone = _RecursosVisuais.icone_atributo(atributo, 16)
        if icone is not None:
            tela.blit(icone, icone.get_rect(midleft=(pill.x + 5, pill.centery)))
            tx = pill.x + 24
        else:
            tx = pill.x + 7
        self.txt_status.set_text(str(_fmt(valor)))
        self.txt_status.set_pos((tx, pill.centery))
        self.txt_status.draw(tela)

    def renderizar(self, tela: pygame.Surface, rect, pokemon: dict, eventos=None, dt=0.0):
        rect = pygame.Rect(rect)
        self._fundo(tela, rect, borda=(80, 122, 200), fundo=(12, 19, 36))
        nome = str(_texto_valor(pokemon, "Nome", "Pokemon", "Pokémon", default="Pokémon"))
        code = str(_texto_valor(pokemon, "Code", "ID", "Id", default="-"))

        img_box = pygame.Rect(rect.x + 10, rect.y + 10, 78, rect.height - 20)
        pygame.draw.rect(tela, (18, 28, 50), img_box, border_radius=14)
        pygame.draw.rect(tela, (90, 132, 208), img_box, 2, border_radius=14)
        frame = _RecursosVisuais.primeiro_frame_pokemon(nome, min(img_box.width - 6, img_box.height - 6))
        if frame is not None:
            tela.blit(frame, frame.get_rect(center=img_box.center))
        else:
            pygame.draw.circle(tela, (92, 144, 232), img_box.center, 18)
            pygame.draw.circle(tela, (210, 228, 255), img_box.center, 18, 2)

        x0 = img_box.right + 12
        self._draw_texto(self.txt_titulo, tela, nome, (x0, rect.y + 8))
        self._draw_texto(self.txt_direita, tela, f"#{code}", (rect.right - 12, rect.y + 10))

        tipos = self.tipos(pokemon)
        tx = rect.right - 14 - (len(tipos) * 26 + max(0, len(tipos) - 1) * 5)
        for tipo in tipos:
            area = pygame.Rect(tx, rect.y + 40, 26, 26)
            icone = construir_icone_tipo_com_fundo_branco(tipo, 26) if construir_icone_tipo_com_fundo_branco else None
            if icone is not None:
                tela.blit(icone, area.topleft)
            else:
                pygame.draw.circle(tela, (238, 243, 255), area.center, 13)
                self._draw_texto(self.txt_mini, tela, tipo[:2].upper(), area.center)
            tx += 31

        grupo = _texto_valor(pokemon, "Grupo", default="-")
        altura = _texto_valor(pokemon, "Altura", default="-")
        peso = _texto_valor(pokemon, "Peso", default="-")
        tamanho = _texto_valor(pokemon, "Tamanho", "Escala", default="-")
        self._draw_texto(self.txt_grupo, tela, f"Grupo: {grupo}", (x0, rect.y + 35))

        area_stats = pygame.Rect(x0, rect.y + 58, rect.right - x0 - 14, 48)
        largura = max(54, min(70, (area_stats.width - 7 * 5) // 8))
        itens = list(self.STATUS) + ["Peso", "Altura", "Tamanho"]
        valores = {s: _texto_valor(pokemon, s, default="0") for s in self.STATUS}
        valores.update({"Peso": peso, "Altura": altura, "Tamanho": tamanho})
        for i, atributo in enumerate(itens[:16]):
            col = i % 8
            lin = i // 8
            self._desenhar_atributo(tela, area_stats.x + col * (largura + 5), area_stats.y + lin * 24, largura, atributo, valores.get(atributo, "-"))


class MiniPainelAtaque(_MiniBase):
    ALTURA = 94

    def renderizar(self, tela: pygame.Surface, rect, ataque: dict, eventos=None, dt=0.0):
        rect = pygame.Rect(rect)
        tipo = str(_texto_valor(ataque, "Tipo", default="normal"))
        nome = str(_texto_valor(ataque, "Ataque", "Nome", default="Ataque"))
        code = str(_texto_valor(ataque, "Code", "ID", default="-"))
        custo = _texto_valor(ataque, "Custo", "Custo Nivel 1", "Custo Nível 1", default="-")
        descricao = str(FichaAtaque._descricao_ataque(ataque) if hasattr(FichaAtaque, "_descricao_ataque") else _texto_valor(ataque, "Descrição", "Descricao", default="Sem descrição."))
        self._fundo(tela, rect, borda=(86, 126, 195), fundo=(13, 20, 36))

        ico_box = pygame.Rect(rect.x + 10, rect.y + 12, 66, 66)
        icone = _RecursosVisuais.icone_ataque(nome, tipo, 54)
        if icone is not None:
            pygame.draw.rect(tela, (22, 32, 56), ico_box, border_radius=13)
            pygame.draw.rect(tela, (168, 198, 255), ico_box, 2, border_radius=13)
            tela.blit(icone, icone.get_rect(center=ico_box.center))
        else:
            self._draw_icone_fallback(tela, ico_box, nome, (90, 132, 208))

        x0 = ico_box.right + 12
        self._draw_texto(self.txt_titulo, tela, nome, (x0, rect.y + 9))
        self._draw_texto(self.txt_direita, tela, f"#{code}", (rect.right - 12, rect.y + 10))
        pill = pygame.Rect(x0, rect.y + 36, 86, 24)
        pygame.draw.rect(tela, (32, 40, 64), pill, border_radius=10)
        pygame.draw.rect(tela, (232, 240, 255), pill, 1, border_radius=10)
        self._draw_texto(self.txt_mini, tela, f"Custo {custo}", pill.center)
        tipo_ico = construir_icone_tipo_com_fundo_branco(tipo, 28) if construir_icone_tipo_com_fundo_branco else None
        if tipo_ico is not None:
            tela.blit(tipo_ico, (pill.right + 10, rect.y + 34))
        self.txt_desc.configurar_rect(pygame.Rect(x0 + 110, rect.y + 34, rect.right - x0 - 190, 48))
        self.txt_desc.set_texto(descricao)
        self.txt_desc.draw(tela)


class MiniPainelEfeito(_MiniBase):
    ALTURA = 84

    def renderizar(self, tela: pygame.Surface, rect, efeito: dict, eventos=None, dt=0.0):
        rect = pygame.Rect(rect)
        nome = str(_texto_valor(efeito, "Efeito", "Nome", default="Efeito"))
        code = str(_texto_valor(efeito, "Code", "ID", default="-"))
        passos = _texto_valor(efeito, "Passos Base", "Passos", default="-")
        descricao = str(_texto_valor(efeito, "Descrição", "Descricao", default="Sem descrição cadastrada."))
        self._fundo(tela, rect, borda=(86, 126, 195), fundo=(13, 20, 36))

        ico_box = pygame.Rect(rect.x + 10, rect.y + 10, 58, 58)
        icone = _RecursosVisuais.icone_efeito(nome, 48)
        if icone is not None:
            pygame.draw.rect(tela, (22, 32, 56), ico_box, border_radius=13)
            pygame.draw.rect(tela, (168, 198, 255), ico_box, 2, border_radius=13)
            tela.blit(icone, icone.get_rect(center=ico_box.center))
        else:
            self._draw_icone_fallback(tela, ico_box, nome, (120, 95, 200))

        x0 = ico_box.right + 12
        self._draw_texto(self.txt_titulo, tela, nome, (x0, rect.y + 8))
        self._draw_texto(self.txt_direita, tela, f"#{code}", (rect.right - 12, rect.y + 10))
        self._draw_texto(self.txt_sub, tela, f"Passos base: {passos}", (x0, rect.y + 36))
        self.txt_desc.configurar_rect(pygame.Rect(x0 + 160, rect.y + 34, rect.right - x0 - 250, 42))
        self.txt_desc.set_texto(descricao)
        self.txt_desc.draw(tela)


class MiniPainelItem(_MiniBase):
    ALTURA = 74

    def __init__(self):
        super().__init__()
        self._ficha = FichaItem()

    def renderizar(self, tela: pygame.Surface, rect, item: dict, eventos=None, dt=0.0):
        rect = pygame.Rect(rect)
        self._fundo(tela, rect, borda=(78, 112, 178), fundo=(13, 20, 36))
        self._ficha.renderizar(tela, rect, item)


class MiniPainelMusica(_MiniBase):
    ALTURA = 72

    def __init__(self):
        super().__init__()
        self._barras: dict[str, Barra] = {}

    @staticmethod
    def chave(musica: dict) -> str:
        return str(musica.get("Chave") or musica.get("Nome") or musica.get("id") or "")

    @staticmethod
    def duracao(musica: dict) -> float:
        try:
            return max(1.0, float(musica.get("fimloop") or musica.get("FimLoop") or 1.0))
        except Exception:
            return 1.0

    @staticmethod
    def areas(rect: pygame.Rect) -> tuple[pygame.Rect, pygame.Rect]:
        rect = pygame.Rect(rect)
        play = pygame.Rect(rect.x + 14, rect.y + (rect.height - 38) // 2, 38, 38)
        barra = pygame.Rect(rect.x + 260, rect.y + (rect.height - 16) // 2, max(80, rect.width - 410), 16)
        return play, barra

    @staticmethod
    def _tempo(segundos: float) -> str:
        s = max(0, int(segundos))
        return f"{s // 60}:{s % 60:02d}"

    def renderizar(self, tela: pygame.Surface, rect, musica: dict, eventos=None, dt=0.0):
        rect = pygame.Rect(rect)
        chave = self.chave(musica)
        nome = str(musica.get("Nome") or musica.get("nome") or chave or "Música")
        mid = str(musica.get("id") or chave or "-")
        duracao = self.duracao(musica)
        tocando = False
        posicao = 0.0
        if Sonoridades is not None and hasattr(Sonoridades, "musica_conhecimento_estado"):
            estado = Sonoridades.musica_conhecimento_estado()
            tocando = estado.get("nome") == chave and bool(estado.get("tocando"))
            if estado.get("nome") == chave:
                posicao = float(estado.get("posicao") or 0.0)

        self._fundo(tela, rect, borda=(78, 112, 178), fundo=(13, 20, 36))
        play, barra_rect = self.areas(rect)
        pygame.draw.rect(tela, (28, 44, 76) if not tocando else (84, 44, 72), play, border_radius=12)
        pygame.draw.rect(tela, (210, 228, 255), play, 2, border_radius=12)
        if tocando:
            pygame.draw.rect(tela, (245, 248, 255), pygame.Rect(play.centerx - 8, play.y + 10, 5, play.height - 20), border_radius=2)
            pygame.draw.rect(tela, (245, 248, 255), pygame.Rect(play.centerx + 3, play.y + 10, 5, play.height - 20), border_radius=2)
        else:
            pontos = [(play.centerx - 5, play.y + 10), (play.centerx - 5, play.bottom - 10), (play.centerx + 11, play.centery)]
            pygame.draw.polygon(tela, (245, 248, 255), pontos)

        x0 = play.right + 14
        self._draw_texto(self.txt_titulo, tela, nome, (x0, rect.y + 11))
        self._draw_texto(self.txt_sub, tela, f"ID: {mid}", (x0, rect.y + 39))
        self._draw_texto(self.txt_direita, tela, f"#{mid}", (rect.right - 12, rect.y + 10))

        barra = self._barras.get(chave)
        if barra is None:
            barra = Barra(barra_rect, texto="", valor=0, minimo=0, maximo=duracao, mostrar_rotulo=False, suavizacao=20.0)
            self._barras[chave] = barra
        barra.configurar(rect=barra_rect, minimo=0, maximo=duracao, cor_fundo=(20, 27, 46), cor_preenchimento=(100, 154, 245), cor_borda=(170, 205, 255), border_radius=8)
        barra.set_valor(max(0.0, min(posicao, duracao)), animar=False)
        barra.render(tela, [], dt)
        pct = 0.0 if duracao <= 0 else max(0.0, min(1.0, posicao / duracao))
        knob_x = barra_rect.x + int(barra_rect.width * pct)
        pygame.draw.circle(tela, (245, 248, 255), (knob_x, barra_rect.centery), 8)
        pygame.draw.circle(tela, (20, 26, 42), (knob_x, barra_rect.centery), 8, 2)
        self._draw_texto(self.txt_sub, tela, f"{self._tempo(posicao)} / {self._tempo(duracao)}", (barra_rect.right + 14, rect.y + 36))
