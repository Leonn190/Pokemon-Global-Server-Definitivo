from __future__ import annotations

import json
import math
import random
import csv
from pathlib import Path
from typing import Callable

import pygame

from Codigo.Prefabs.TextoCinematico import TextoCinematico


_RAIZ_PROJETO = Path(__file__).resolve().parents[3]
_CAMINHO_FONTE_PADRAO = _RAIZ_PROJETO / "Recursos" / "Visual" / "Fontes" / "FontePadrão.ttf"
_CAMINHO_FONTE_CINEMATICA = _RAIZ_PROJETO / "Recursos" / "Visual" / "Fontes" / "FonteCinematica.ttf"
_CAMINHOS_JSON = (
    _RAIZ_PROJETO / "Dados" / "Catalogo" / "Creditos.json",
    Path("Dados") / "Catalogo" / "Creditos.json",
    Path(__file__).with_name("Creditos.json"),
    Path("Creditos.json"),
)
_AUTOR_PADRAO = "Leon Cunha Alvaro Lopez Soto"


_DADOS_FALLBACK = {
    "config": {
        "duracao_total": 110.0,
        "inicio_scroll": 12.0,
        "inicio_final": 94.5,
        "musica": "Creditos",
        "permitir_pular": False,
        "logo": "Recursos/Visual/Icones/GlobalServer Logo.png",
        "logo_alternativas": [
            "Recursos/Visual/Icones/GlobalServer Logo.png",
            "Recursos/Visual/Icones/GlobalServer/Logo.png",
            "Recursos/Visual/Icones/GlobalServer/Icone.png",
        ],
    },
    "cinematico_inicio": {
        "titulo": "Pokemon Global Server",
        "subtitulo": "Obrigado por jogar",
    },
    "creditos": [
        {
            "topico": "Direção e Criação",
            "entradas": [
                {"cargo": "Direção Geral", "nomes": [_AUTOR_PADRAO]},
                {"cargo": "Game Design", "nomes": [_AUTOR_PADRAO]},
                {"cargo": "Balanceamento Geral", "nomes": [_AUTOR_PADRAO]},
                {"cargo": "Coordenador", "nomes": [_AUTOR_PADRAO]},
                {"cargo": "Líder de FrontEnd", "nomes": [_AUTOR_PADRAO]},
                {"cargo": "Líder de BackEnd", "nomes": [_AUTOR_PADRAO]},
            ],
        }
    ],
    "cinematico_final": {
        "texto": [
            "Pokémon Global Server é um fangame independente, sem fins comerciais, criado inicialmente como portfólio, estudo e aprendizado.",
            "Este projeto não é afiliado, associado, aprovado ou patrocinado pela Nintendo, The Pokémon Company ou Game Freak.",
            "Todos os recursos de terceiros pertencem aos seus respectivos autores e proprietários.",
        ],
        "agradecimento": "Obrigado novamente por jogar Pokémon Global Server.",
    },
}


class TelaCreditos:
    """Overlay de créditos com fade, logo, rolagem e encerramento automático.

    Uso esperado nas cenas:
        self._tela_creditos = TelaCreditos()
        self._tela_creditos.abrir(JOGO.TELA.get_size(), ao_finalizar=lambda: setattr(JOGO, "CenaAlvo", "Menu"))
        self._tela_creditos.atualizar(EVENTOS, dt, JOGO)
        self._tela_creditos.desenhar(surface, EVENTOS, dt, JOGO)
    """

    def __init__(self, caminho_json: str | Path | None = None):
        self._ativa = False
        self._finalizada = False
        self._tempo = 0.0
        self._ao_finalizar: Callable[[], None] | None = None
        self._dados = self._carregar_dados(caminho_json)
        self._config = self._dados.get("config") if isinstance(self._dados.get("config"), dict) else {}

        self._titulo = TextoCinematico("Pokemon Global Server", tamanho=92)
        self._obrigado = TextoCinematico("Obrigado por jogar", tamanho=56)

        self._fonte_cache: dict[tuple[str, int], pygame.font.Font] = {}
        self._texto_cache: dict[tuple[str, int, tuple[int, int, int], int], pygame.Surface] = {}
        self._logo_original: pygame.Surface | None = None
        self._logo_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._estrelas: list[tuple[float, float, float, int]] = []
        self._ultimo_tamanho: tuple[int, int] | None = None
        self._linhas_creditos: list[dict] = []
        self._altura_creditos = 1
        self._alpha_fundo = 0.0
        self._callback_executado = False

    @property
    def ativa(self) -> bool:
        return bool(self._ativa)

    @property
    def finalizada(self) -> bool:
        return bool(self._finalizada)

    def abrir(self, tamanho_tela: tuple[int, int], ao_finalizar: Callable[[], None] | None = None) -> None:
        self._ativa = True
        self._finalizada = False
        self._tempo = 0.0
        self._alpha_fundo = 0.0
        self._ao_finalizar = ao_finalizar
        self._callback_executado = False
        self._ultimo_tamanho = None
        self._linhas_creditos = []
        self._altura_creditos = 1
        self._logo_cache.clear()
        self._garantir_layout(tamanho_tela)
        self._iniciar_musica_creditos()

    def fechar(self) -> None:
        self._ativa = False

    def atualizar(self, eventos, dt: float, jogo) -> None:
        if not self._ativa:
            return

        dt = max(0.0, min(0.10, float(dt or 0.0)))
        self._tempo += dt
        self._alpha_fundo = min(255.0, self._alpha_fundo + (170.0 * dt))

        if bool(self._config.get("permitir_pular", False)) and self._tempo >= 4.0:
            for evento in list(eventos or []):
                if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    self._tempo = max(self._tempo, self._duracao_total())
                    break

        if self._tempo >= self._duracao_total():
            self._finalizar()

    def desenhar(self, surface: pygame.Surface, eventos=None, dt: float = 0.0, jogo=None) -> None:
        if not self._ativa:
            return

        tamanho = surface.get_size()
        self._garantir_layout(tamanho)
        self._desenhar_fundo(surface)
        self._desenhar_estrelas(surface)

        if self._tempo < self._inicio_scroll():
            self._desenhar_intro(surface)
            return

        if self._tempo < self._inicio_final():
            self._desenhar_creditos_rolando(surface)
            return

        self._desenhar_final(surface)

    def coletar_efeito_shader(self):
        if not self._ativa:
            return {}
        for texto in (self._titulo, self._obrigado):
            efeito = texto.efeito_shader(modo=0.15)
            if efeito:
                efeito["tipo"] = "hud"
                return efeito
        return {}

    # ------------------------------------------------------------------
    # Dados e configuração
    # ------------------------------------------------------------------
    def _carregar_dados(self, caminho_json: str | Path | None) -> dict:
        candidatos: list[Path] = []
        if caminho_json is not None:
            candidatos.append(Path(caminho_json))
        candidatos.extend(_CAMINHOS_JSON)
        for caminho in candidatos:
            try:
                if caminho.exists():
                    with caminho.open("r", encoding="utf-8") as arquivo:
                        dados = json.load(arquivo)
                    return dados if isinstance(dados, dict) else dict(_DADOS_FALLBACK)
            except Exception as exc:
                print(f"[TelaCreditos] falha ao carregar {caminho}: {exc}")
        return dict(_DADOS_FALLBACK)

    def _duracao_total(self) -> float:
        return max(45.0, float(self._config.get("duracao_total", 110.0) or 110.0))

    def _inicio_scroll(self) -> float:
        return max(6.0, min(self._duracao_total() - 20.0, float(self._config.get("inicio_scroll", 12.0) or 12.0)))

    def _inicio_final(self) -> float:
        return max(self._inicio_scroll() + 25.0, min(self._duracao_total() - 8.0, float(self._config.get("inicio_final", 94.5) or 94.5)))

    def _duracao_scroll(self) -> float:
        return max(1.0, self._inicio_final() - self._inicio_scroll())

    def _iniciar_musica_creditos(self) -> None:
        nome = str(self._config.get("musica") or "").strip()
        if not nome:
            return
        try:
            from Codigo.ModulosGerais import Sonoridades

            if nome in getattr(Sonoridades, "Musicas", {}):
                Sonoridades.TransicaoMusica(nome)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Layout e recursos
    # ------------------------------------------------------------------
    def _garantir_layout(self, tamanho_tela: tuple[int, int]) -> None:
        tamanho_tela = (int(tamanho_tela[0]), int(tamanho_tela[1]))
        if self._ultimo_tamanho == tamanho_tela and self._linhas_creditos:
            return
        self._ultimo_tamanho = tamanho_tela
        largura, altura = tamanho_tela
        self._titulo = TextoCinematico(
            self._inicio_dados().get("titulo", "Pokemon Global Server"),
            tamanho=max(52, min(118, int(largura / 16))),
        )
        self._obrigado = TextoCinematico(
            self._inicio_dados().get("subtitulo", "Obrigado por jogar"),
            tamanho=max(32, min(68, int(largura / 27))),
        )
        self._carregar_logo()
        self._criar_estrelas(largura, altura)
        self._montar_linhas_creditos(largura, altura)

    def _inicio_dados(self) -> dict:
        dados = self._dados.get("cinematico_inicio") if isinstance(self._dados.get("cinematico_inicio"), dict) else {}
        return dados

    def _carregar_logo(self) -> None:
        if self._logo_original is not None:
            return
        caminhos = []
        if self._config.get("logo"):
            caminhos.append(str(self._config.get("logo")))
        caminhos.extend(list(self._config.get("logo_alternativas") or []))
        for bruto in caminhos:
            caminho = Path(str(bruto))
            if not caminho.is_absolute():
                caminho = _RAIZ_PROJETO / caminho
            if not caminho.exists():
                continue
            try:
                self._logo_original = pygame.image.load(str(caminho)).convert_alpha()
                return
            except Exception as exc:
                print(f"[TelaCreditos] falha ao carregar logo {caminho}: {exc}")
        self._logo_original = None

    def _criar_estrelas(self, largura: int, altura: int) -> None:
        rng = random.Random(190)
        quantidade = max(70, min(180, int((largura * altura) / 15000)))
        self._estrelas = [
            (rng.uniform(0, largura), rng.uniform(0, altura), rng.uniform(4.0, 20.0), rng.randint(55, 155))
            for _ in range(quantidade)
        ]

    def _fonte(self, tamanho: int, cinematica: bool = False) -> pygame.font.Font:
        familia = "cine" if cinematica else "padrao"
        chave = (familia, int(tamanho))
        fonte = self._fonte_cache.get(chave)
        if fonte is not None:
            return fonte
        caminho = _CAMINHO_FONTE_CINEMATICA if cinematica else _CAMINHO_FONTE_PADRAO
        if caminho.exists():
            fonte = pygame.font.Font(str(caminho), int(tamanho))
        else:
            fonte = pygame.font.SysFont("arial", int(tamanho), bold=cinematica)
        self._fonte_cache[chave] = fonte
        return fonte

    def _texto_surf(self, texto: str, tamanho: int, cor: tuple[int, int, int], outline: int = 2, cinematica: bool = False) -> pygame.Surface:
        texto = str(texto or "")
        chave = (texto, int(tamanho), tuple(cor), int(outline), int(bool(cinematica)))
        surf = self._texto_cache.get(chave)
        if surf is not None:
            return surf
        fonte = self._fonte(tamanho, cinematica=cinematica)
        base = fonte.render(texto, True, cor).convert_alpha()
        if outline <= 0:
            self._texto_cache[chave] = base
            return base
        borda = fonte.render(texto, True, (0, 0, 0)).convert_alpha()
        w, h = base.get_size()
        surf = pygame.Surface((w + outline * 4, h + outline * 4), pygame.SRCALPHA)
        centro = outline * 2
        for dx in range(-outline, outline + 1):
            for dy in range(-outline, outline + 1):
                if dx == 0 and dy == 0:
                    continue
                if (dx * dx + dy * dy) <= (outline * outline + 1):
                    surf.blit(borda, (centro + dx, centro + dy))
        sombra = fonte.render(texto, True, (0, 0, 0)).convert_alpha()
        sombra.set_alpha(120)
        surf.blit(sombra, (centro + 3, centro + 3))
        surf.blit(base, (centro, centro))
        if len(self._texto_cache) > 900:
            self._texto_cache.clear()
        self._texto_cache[chave] = surf
        return surf

    def _desenhar_texto(self, surface: pygame.Surface, texto: str, pos: tuple[float, float], tamanho: int, cor=(245, 246, 255), alpha: float = 255.0, align: str = "center", outline: int = 2, cinematica: bool = False) -> pygame.Rect:
        surf = self._texto_surf(texto, tamanho, tuple(cor), outline=outline, cinematica=cinematica).copy()
        surf.set_alpha(max(0, min(255, int(alpha))))
        rect = surf.get_rect()
        if align == "left":
            rect.midleft = (int(pos[0]), int(pos[1]))
        elif align == "right":
            rect.midright = (int(pos[0]), int(pos[1]))
        elif align == "topcenter":
            rect.midtop = (int(pos[0]), int(pos[1]))
        else:
            rect.center = (int(pos[0]), int(pos[1]))
        surface.blit(surf, rect.topleft)
        return rect

    def _quebrar(self, texto: str, largura_px: int, tamanho: int) -> list[str]:
        fonte = self._fonte(tamanho)
        palavras = str(texto or "").split()
        if not palavras:
            return []
        linhas: list[str] = []
        atual = ""
        for palavra in palavras:
            tentativa = palavra if not atual else f"{atual} {palavra}"
            if fonte.size(tentativa)[0] <= largura_px or not atual:
                atual = tentativa
            else:
                linhas.append(atual)
                atual = palavra
        if atual:
            linhas.append(atual)
        return linhas

    def _montar_linhas_creditos(self, largura_tela: int, altura_tela: int) -> None:
        self._linhas_creditos = []
        largura_texto = int(largura_tela * 0.78)

        def add(tipo: str, texto: str = "", **kwargs) -> None:
            item = {"tipo": tipo, "texto": texto, **kwargs}
            self._linhas_creditos.append(item)

        add("intro_titulo")
        add("spacer", altura=int(altura_tela * 0.24))
        add("intro_logo")
        add("spacer", altura=int(altura_tela * 0.26))
        add("intro_obrigado")
        add("spacer", altura=int(altura_tela * 0.32))
        for secao in list(self._dados.get("creditos") or []):
            if not isinstance(secao, dict):
                continue
            add("topico", str(secao.get("topico") or "Créditos"))
            add("spacer", altura=20)

            if str(secao.get("auto") or "").strip().lower() == "numeros_projeto":
                for linha in self._linhas_numeros_projeto():
                    add("texto", linha)

            for linha in list(secao.get("texto") or []):
                for quebrada in self._quebrar(str(linha), largura_texto, 27):
                    add("texto", quebrada)

            for entrada in list(secao.get("entradas") or []):
                if not isinstance(entrada, dict):
                    continue
                nomes = ", ".join(str(n) for n in list(entrada.get("nomes") or []) if str(n).strip())
                add("par", cargo=str(entrada.get("cargo") or ""), nomes=nomes)

            for nome in list(secao.get("nomes") or []):
                add("nome", str(nome))

            rodape = str(secao.get("rodape") or "").strip()
            if rodape:
                add("spacer", altura=10)
                for quebrada in self._quebrar(rodape, largura_texto, 22):
                    add("rodape", quebrada)
            add("spacer", altura=72)

        add("spacer", altura=160)
        y = 0
        for item in self._linhas_creditos:
            item["y"] = y
            y += self._altura_linha(item)
        self._altura_creditos = max(1, y)

    def _altura_linha(self, item: dict) -> int:
        tipo = str(item.get("tipo") or "")
        if tipo == "spacer":
            return int(item.get("altura", 24) or 24)
        if tipo.startswith("intro_"):
            return 1
        if tipo == "topico":
            return 64
        if tipo == "par":
            return 42
        if tipo == "nome":
            return 38
        if tipo == "rodape":
            return 30
        return 34

    def _linhas_numeros_projeto(self) -> list[str]:
        relatorio = self._ultimo_relatorio()
        resumo = relatorio.get("resumo") if isinstance(relatorio.get("resumo"), dict) else {}
        python = relatorio.get("python") if isinstance(relatorio.get("python"), dict) else {}
        return [
            f"{self._fmt_int(self._contar_csv('Pokemon Global Server - Pokemons.csv'))} Pokemon registrados",
            f"{self._fmt_int(self._contar_csv('Pokemon Global Server - Ataques.csv'))} ataques registrados",
            f"{self._fmt_int(self._contar_csv('Pokemon Global Server - Efeitos.csv'))} efeitos registrados",
            f"{self._fmt_int(self._contar_csv('Pokemon Global Server - Itens.csv'))} itens registrados",
            f"{self._fmt_int(self._contar_csv('Pokemon Global Server - Equipaveis.csv'))} equipaveis registrados",
            f"{self._fmt_int(self._contar_csv('Pokemon Global Server - NPC Combatente.csv') + self._contar_csv('Pokemon Global Server - NPC Vendedor.csv'))} NPCs cadastrados",
            f"{self._fmt_int(self._contar_json_catalogo('Musicas'))} trilhas sonoras",
            f"{self._fmt_int(len(list((_RAIZ_PROJETO / 'Dados' / 'PropriedadesAtaques').glob('Propriedades*.json'))))} tipos de Pokemon",
            f"{self._fmt_int(resumo.get('linhas_totais_geral'))} linhas totais gerais",
            f"{self._fmt_int(python.get('linhas_totais'))} linhas de Python",
            f"{self._fmt_int(python.get('py_arquivos'))} arquivos Python",
            f"{self._fmt_int(python.get('funcoes_encontradas'))} funcoes registradas",
            f"{self._fmt_int(python.get('metodos_encontrados'))} metodos registrados",
            f"{self._fmt_int(resumo.get('commits'))} commits do projeto",
            f"{self._fmt_int(resumo.get('horas_estimadas'))} horas estimadas",
        ]

    def _contar_csv(self, nome: str) -> int:
        caminho = _RAIZ_PROJETO / "Dados" / "Tabelas" / nome
        try:
            with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
                return sum(1 for _ in csv.DictReader(arquivo))
        except Exception:
            return 0

    def _contar_json_catalogo(self, nome: str) -> int:
        caminho = _RAIZ_PROJETO / "Dados" / "Catalogo" / f"{nome}.json"
        try:
            with caminho.open("r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
            return len(dados) if isinstance(dados, dict) else 0
        except Exception:
            return 0

    def _ultimo_relatorio(self) -> dict:
        pasta = _RAIZ_PROJETO / "Outros" / "Relatorios" / "Relatorios"
        try:
            arquivos = sorted(pasta.glob("*.json"), key=lambda p: p.name)
            if not arquivos:
                return {}
            with arquivos[-1].open("r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
            return dados if isinstance(dados, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _fmt_int(valor) -> str:
        try:
            numero = int(round(float(valor)))
        except (TypeError, ValueError):
            numero = 0
        return f"{numero:,}".replace(",", ".")

    # ------------------------------------------------------------------
    # Desenho
    # ------------------------------------------------------------------
    def _desenhar_fundo(self, surface: pygame.Surface) -> None:
        ov = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, int(self._alpha_fundo)))
        surface.blit(ov, (0, 0))

    def _desenhar_estrelas(self, surface: pygame.Surface) -> None:
        if self._alpha_fundo < 180:
            return
        w, h = surface.get_size()
        alpha_base = min(1.0, max(0.0, (self._alpha_fundo - 180.0) / 75.0))
        camada = pygame.Surface((w, h), pygame.SRCALPHA)
        for x, y, velocidade, alpha in self._estrelas:
            yy = (y + self._tempo * velocidade) % h
            a = int(alpha * alpha_base * (0.72 + 0.28 * math.sin(self._tempo * 1.3 + x)))
            camada.fill((255, 255, 255, max(0, min(170, a))), (int(x), int(yy), 2, 2))
        surface.blit(camada, (0, 0))

    @staticmethod
    def _fade_janela(tempo: float, inicio: float, fade_in: float, fim: float, fade_out: float) -> float:
        if tempo < inicio or tempo > fim:
            return 0.0
        entrada = 1.0 if fade_in <= 0 else min(1.0, max(0.0, (tempo - inicio) / fade_in))
        saida = 1.0 if fade_out <= 0 else min(1.0, max(0.0, (fim - tempo) / fade_out))
        return max(0.0, min(1.0, min(entrada, saida)))

    def _desenhar_intro(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        a_titulo = min(1.0, max(0.0, (self._tempo - 0.9) / 1.4)) * 255.0
        a_logo = min(1.0, max(0.0, (self._tempo - 3.0) / 1.25)) * 255.0
        a_obrigado = min(1.0, max(0.0, (self._tempo - 5.9) / 1.2)) * 255.0

        self._titulo.set_alpha(a_titulo)
        self._titulo.desenhar(surface, (w // 2, int(h * 0.24)))

        logo = self._logo_escalada(w, h)
        if logo is not None and a_logo > 0:
            img = logo.copy()
            img.set_alpha(int(a_logo))
            rect = img.get_rect(center=(w // 2, int(h * 0.48)))
            surface.blit(img, rect.topleft)

        self._obrigado.set_alpha(a_obrigado)
        self._obrigado.desenhar(surface, (w // 2, int(h * 0.74)))

    def _logo_escalada(self, largura: int, altura: int) -> pygame.Surface | None:
        if self._logo_original is None:
            return None
        max_w = max(292, int(largura * 0.55))
        max_h = max(164, int(altura * 0.40))
        escala = min(max_w / max(1, self._logo_original.get_width()), max_h / max(1, self._logo_original.get_height()), 1.82)
        alvo = (max(1, int(self._logo_original.get_width() * escala)), max(1, int(self._logo_original.get_height() * escala)))
        if alvo not in self._logo_cache:
            self._logo_cache[alvo] = pygame.transform.smoothscale(self._logo_original, alvo)
        return self._logo_cache[alvo]

    def _desenhar_creditos_rolando(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        progresso = max(0.0, min(1.0, (self._tempo - self._inicio_scroll()) / self._duracao_scroll()))
        y_base = int(h * 0.24) - progresso * (self._altura_creditos + int(h * 0.30))
        fade_global = min(1.0, max(0.0, (self._inicio_final() - self._tempo) / 1.2))
        for item in self._linhas_creditos:
            y = y_base + float(item.get("y", 0))
            if y < -100 or y > h + 100:
                continue
            alpha_borda = min(1.0, max(0.0, (y + 80) / 120.0), max(0.0, (h + 60 - y) / 120.0))
            alpha = 255.0 * alpha_borda * fade_global
            self._desenhar_linha_credito(surface, item, y, alpha)

    def _desenhar_linha_credito(self, surface: pygame.Surface, item: dict, y: float, alpha: float) -> None:
        if alpha <= 1:
            return
        w, _h = surface.get_size()
        tipo = str(item.get("tipo") or "")
        if tipo == "intro_titulo":
            self._titulo.set_alpha(alpha)
            self._titulo.desenhar(surface, (w // 2, int(y)))
            return
        if tipo == "intro_logo":
            logo = self._logo_escalada(*surface.get_size())
            if logo is not None:
                img = logo.copy()
                img.set_alpha(int(alpha))
                rect = img.get_rect(center=(w // 2, int(y)))
                surface.blit(img, rect.topleft)
            return
        if tipo == "intro_obrigado":
            self._obrigado.set_alpha(alpha)
            self._obrigado.desenhar(surface, (w // 2, int(y)))
            return
        if tipo == "topico":
            cor_topico = (190, 210, 116)
            self._desenhar_texto(surface, str(item.get("texto") or ""), (w / 2, y), 44, cor=cor_topico, alpha=alpha, outline=3, cinematica=True)
            pygame.draw.line(surface, (*cor_topico, int(alpha)), (int(w * 0.36), int(y + 38)), (int(w * 0.64), int(y + 38)), 2)
            return
        if tipo == "par":
            cargo = str(item.get("cargo") or "")
            nomes = str(item.get("nomes") or "")
            if w >= 980:
                self._desenhar_texto(surface, cargo, (w / 2 - 34, y), 24, cor=(210, 222, 238), alpha=alpha, align="right", outline=2)
                self._desenhar_texto(surface, nomes, (w / 2 + 34, y), 24, cor=(255, 236, 170), alpha=alpha, align="left", outline=2)
            else:
                self._desenhar_texto(surface, f"{cargo} — {nomes}", (w / 2, y), 21, cor=(238, 238, 240), alpha=alpha, outline=2)
            return
        if tipo == "nome":
            self._desenhar_texto(surface, str(item.get("texto") or ""), (w / 2, y), 28, cor=(242, 245, 255), alpha=alpha, outline=2)
            return
        if tipo == "rodape":
            self._desenhar_texto(surface, str(item.get("texto") or ""), (w / 2, y), 22, cor=(178, 190, 210), alpha=alpha, outline=1)
            return
        if tipo == "texto":
            self._desenhar_texto(surface, str(item.get("texto") or ""), (w / 2, y), 27, cor=(216, 226, 244), alpha=alpha, outline=2)

    def _desenhar_final(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        final = self._dados.get("cinematico_final") if isinstance(self._dados.get("cinematico_final"), dict) else {}
        textos = [str(t) for t in list(final.get("texto") or []) if str(t).strip()]
        agradecimento = str(final.get("agradecimento") or "Obrigado novamente por jogar Pokémon Global Server.")
        t = max(0.0, self._tempo - self._inicio_final())
        dur = max(1.0, self._duracao_total() - self._inicio_final())

        if t < dur * 0.66:
            alpha = self._fade_janela(t, 0.3, 1.8, dur * 0.66, 1.6) * 255.0
            tamanho = max(21, min(30, int(w / 62)))
            largura_texto = int(w * 0.72)
            linhas: list[str] = []
            for paragrafo in textos:
                linhas.extend(self._quebrar(paragrafo, largura_texto, tamanho))
                linhas.append("")
            if linhas and linhas[-1] == "":
                linhas.pop()
            altura_linha = int(tamanho * 1.45)
            y0 = int(h * 0.50) - (len(linhas) * altura_linha) // 2
            for i, linha in enumerate(linhas):
                if not linha:
                    continue
                self._desenhar_texto(surface, linha, (w / 2, y0 + i * altura_linha), tamanho, cor=(230, 235, 248), alpha=alpha, outline=2)
            return

        alpha = self._fade_janela(t, dur * 0.62, 1.8, dur - 0.2, 1.4) * 255.0
        self._desenhar_texto(surface, agradecimento, (w / 2, h * 0.38), max(30, min(56, int(w / 34))), cor=(255, 236, 170), alpha=alpha, outline=3, cinematica=True)
        logo = self._logo_escalada(w, h)
        if logo is not None and alpha > 0:
            img = logo.copy()
            img.set_alpha(int(alpha * 0.90))
            rect = img.get_rect(center=(w // 2, int(h * 0.62)))
            surface.blit(img, rect.topleft)

    def _finalizar(self) -> None:
        if self._callback_executado:
            return
        self._callback_executado = True
        self._ativa = False
        self._finalizada = True
        if callable(self._ao_finalizar):
            self._ao_finalizar()
