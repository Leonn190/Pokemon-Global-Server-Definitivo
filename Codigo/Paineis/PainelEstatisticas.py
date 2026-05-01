from __future__ import annotations

from pathlib import Path

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Geradores.PokemonInventario import PokemonInventario
from Codigo.ModulosGerais.DesenhaAtor import DesenhaAtor
from Codigo.Paineis.PainelArvoreHabilidades import PainelArvoreHabilidades
from Codigo.Paineis.PainelConhecimento import PainelConhecimento
from Codigo.Paineis.PainelProgresso import PainelProgresso
from Codigo.Prefabs.Barra import Barra, BarraEditavel
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto


class PainelEstatisticas:
    def __init__(self, ator=None):
        self.Ator = ator
        self._layout_chave = None
        self._skins: list[tuple[str, pygame.Surface]] = []
        self._skin_index = 0
        self._slider_skin: BarraEditavel | None = None
        self._barra_xp: Barra | None = None
        self._desenhador: DesenhaAtor | None = None
        self._painel_skill = PainelArvoreHabilidades(ator)
        self._arvore_aberta = False
        self._botao_skill: Botao | None = None
        self._botao_conhecimento: Botao | None = None
        self._botao_progresso: Botao | None = None
        self._painel_conhecimento = PainelConhecimento(ator)
        self._painel_progresso = PainelProgresso(ator)
        self._overlay_extra = ""

        self._area_stats = pygame.Rect(0, 0, 0, 0)
        self._area_direita = pygame.Rect(0, 0, 0, 0)
        self._area_ator = pygame.Rect(0, 0, 0, 0)

        base = {"outline": True, "outline_thickness": 1, "outline_color": (0, 0, 0), "shadow": False}
        self.txt_nome_bloco = Texto("", style={**base, "size": 32, "color": (245, 248, 255)})
        self.txt_nivel = Texto("", style={**base, "size": 26, "color": (245, 248, 255)})
        self.txt_xp = Texto("", style={**base, "size": 18, "color": (186, 205, 238)})
        self.txt_skin_liberadas = Texto("", style={**base, "size": 18, "color": (193, 212, 244)})
        self.txt_skin_atual = Texto("", style={**base, "size": 17, "color": (221, 234, 255), "align": "topright"})
        self.txt_dinheiro = Texto("", style={**base, "size": 24, "color": (255, 223, 121), "align": "topright"})
        self._icone_dinheiro = self._carregar_icone_dinheiro()
        self._labels = [Texto("", style={**base, "size": 18, "color": (164, 184, 221)}) for _ in range(16)]
        self._values = [Texto("", style={**base, "size": 26, "color": (247, 250, 255)}) for _ in range(16)]

    @staticmethod
    def _carregar_icone_dinheiro() -> pygame.Surface | None:
        caminho = Path("Recursos") / "Visual" / "Icones" / "Diversos" / "Moeda.png"
        if not caminho.exists():
            return None
        try:
            return pygame.transform.smoothscale(pygame.image.load(str(caminho)).convert_alpha(), (24, 24))
        except pygame.error:
            return None

    @staticmethod
    def _formatar_tempo(segundos: float) -> str:
        total = max(0, int(segundos or 0.0))
        horas = total // 3600
        minutos = (total % 3600) // 60
        segs = total % 60
        return f"{horas:02d}:{minutos:02d}:{segs:02d}"

    @staticmethod
    def _normalizar_nome_skin(nome_skin: str) -> str:
        base = str(nome_skin or "1").strip() or "1"
        if base.lower().startswith("s") and base[1:].isdigit():
            base = base[1:]
        return base if base.lower().endswith(".png") else f"{base}.png"

    @staticmethod
    def _ordem_skin(nome_skin: str) -> tuple[int, int | str]:
        base = str(nome_skin or "").strip().lower()
        if base.endswith(".png"):
            base = base[:-4]
        if base.isdigit():
            return (0, int(base))
        return (1, base)

    def _coletar_skins_liberadas(self) -> list[tuple[str, pygame.Surface]]:
        ator = self.Ator
        perfil = getattr(ator, "Perfil", None)
        liberadas = [self._normalizar_nome_skin(s) for s in list(getattr(perfil, "SkinsLiberadas", []) or [])]
        atual = self._normalizar_nome_skin(getattr(ator, "NomeSkin", "S1"))
        if not liberadas:
            liberadas = [atual]
        elif atual not in liberadas:
            liberadas.append(atual)
        liberadas = sorted(dict.fromkeys(liberadas), key=self._ordem_skin)

        skins: list[tuple[str, pygame.Surface]] = []
        for nome in liberadas:
            caminho = Path("Recursos") / "Visual" / "Skins" / nome
            if caminho.exists():
                try:
                    skins.append((nome, pygame.image.load(str(caminho)).convert_alpha()))
                    continue
                except pygame.error:
                    pass
            skins.append((nome, Ator.carregar_skin(nome)))
        return skins

    def _reconstruir_layout(self, rect: pygame.Rect):
        chave = (rect.x, rect.y, rect.width, rect.height)
        if self._layout_chave == chave and self._slider_skin is not None and self._desenhador is not None:
            return

        self._layout_chave = chave
        self._skins = self._coletar_skins_liberadas()
        self._skin_index = 0

        nome_skin_atual = self._normalizar_nome_skin(getattr(self.Ator, "NomeSkin", "1"))
        for i, (nome, _) in enumerate(self._skins):
            if nome == nome_skin_atual:
                self._skin_index = i
                break

        margem = 18
        topo = rect.y + 16
        largura_stats = int(rect.width * 0.63)
        altura_painel = max(0, rect.height - 32)
        self._area_stats = pygame.Rect(rect.x + margem, topo, largura_stats, altura_painel)
        self._area_direita = pygame.Rect(self._area_stats.right + 24, topo, rect.right - self._area_stats.right - margem - 24, altura_painel)

        y_botao_skill = self._area_direita.y + 108
        h_botao_skill = 48
        gap_botao_ator = 14
        y_ator = y_botao_skill + h_botao_skill + gap_botao_ator
        self._area_ator = pygame.Rect(self._area_direita.x + 18, y_ator, self._area_direita.width - 36, self._area_direita.height - (y_ator - self._area_direita.y) - 64)

        barra_rect = pygame.Rect(self._area_direita.x + 18, self._area_direita.y + 44, self._area_direita.width - 36, 22)
        self._barra_xp = Barra(barra_rect, texto="", valor=0, minimo=0, maximo=100, mostrar_rotulo=False, suavizacao=10.0)
        self._barra_xp.cor_fundo = (22, 29, 46)
        self._barra_xp.cor_preenchimento = (126, 86, 224)
        self._barra_xp.cor_borda = (216, 202, 255)

        self._slider_skin = BarraEditavel(
            pygame.Rect(self._area_ator.x + 8, self._area_direita.bottom - 30, self._area_ator.width - 16, 18),
            "",
            self._skin_index + 1,
            1,
            max(1, len(self._skins)),
            casas_decimais=0,
        )
        self._slider_skin.cor_fundo = (26, 34, 58)
        self._slider_skin.cor_preenchimento = (114, 188, 255)
        self._slider_skin.cor_borda = (200, 228, 255)
        self._slider_skin.cor_manopla = (245, 250, 255)

        self._desenhador = DesenhaAtor(self._skins[self._skin_index][1], escala=1.28)

        def _abrir(_jogo, _botao):
            self._arvore_aberta = True
            self._overlay_extra = ""

        def _abrir_conhecimento(_jogo, _botao):
            self._arvore_aberta = False
            self._overlay_extra = "conhecimento"

        def _abrir_progresso(_jogo, _botao):
            self._arvore_aberta = False
            self._overlay_extra = "progresso"

        self._botao_skill = Botao(
            pygame.Rect(self._area_direita.x + 18, y_botao_skill, self._area_direita.width - 36, h_botao_skill),
            "Abrir árvore de habilidades",
            execute=_abrir,
            style={
                "radius": 16,
                "bg": (44, 84, 154),
                "bg_hover": (58, 103, 182),
                "bg_pressed": (34, 67, 122),
                "border": (188, 224, 255),
                "border_hover": (235, 246, 255),
                "text_style": {"size": 21, "outline_thickness": 1, "shadow": False},
            },
        )


        coluna3_x = self._area_stats.x + 18 + 2 * (((self._area_stats.width - 72) // 3) + 18)
        col_w = ((self._area_stats.width - 72) // 3)
        self._botao_conhecimento = Botao(
            pygame.Rect(coluna3_x, self._area_stats.bottom - 122, col_w, 42),
            "Conhecimento", execute=_abrir_conhecimento,
            style={"radius": 12, "bg": (52, 100, 160), "bg_hover": (67, 122, 191), "bg_pressed": (45, 86, 140), "border": (188, 224, 255), "text_style": {"size": 18, "outline_thickness": 1, "shadow": False}},
        )
        self._botao_progresso = Botao(
            pygame.Rect(coluna3_x, self._area_stats.bottom - 72, col_w, 42),
            "Progresso", execute=_abrir_progresso,
            style={"radius": 12, "bg": (70, 112, 76), "bg_hover": (86, 136, 92), "bg_pressed": (58, 96, 64), "border": (210, 236, 214), "text_style": {"size": 18, "outline_thickness": 1, "shadow": False}},
        )
    def on_open(self):
        pass

    def on_close(self):
        self._arvore_aberta = False
        self._overlay_extra = ""

    def esta_com_overlay_aberto(self) -> bool:
        return bool(self._arvore_aberta or self._overlay_extra)

    def _maior_poder(self, pokemons: list[dict]) -> int:
        maior = 0.0
        for pokemon in pokemons:
            if not isinstance(pokemon, dict):
                continue
            total = float(PokemonInventario.poder_total(pokemon))
            if total > maior:
                maior = total
        return int(round(maior))

    def _maior_poder_time(self) -> int:
        inventario = getattr(self.Ator, "Inventario", None)
        times = list(getattr(inventario, "TimesPokemons", []) or []) if inventario is not None else []
        melhor = 0
        for time in times:
            if isinstance(time, dict):
                slots = list(time.get("Slots") or time.get("slots") or [])
            elif isinstance(time, list):
                slots = list(time)
            else:
                continue
            total = 0.0
            for pokemon in slots:
                if isinstance(pokemon, dict):
                    total += float(PokemonInventario.poder_total(pokemon))
            melhor = max(melhor, int(round(total)))
        return melhor

    def _quantidade_total_itens(self, itens):
        total = 0
        for item in itens:
            if isinstance(item, dict):
                total += max(1, int(item.get("quantidade", 1)))
            elif item is not None:
                total += 1
        return total

    def _coletar_dados(self):
        ator = self.Ator
        perfil = getattr(ator, "Perfil", None)
        inventario = getattr(ator, "Inventario", None)

        nome = str(getattr(ator, "Nome", "") or "Treinador")
        vitorias_pvp = int(getattr(perfil, "BatalhasPVPVencidas", 0) or 0)
        vitorias_bot = int(getattr(perfil, "BatalhasBotVencidas", 0) or 0)
        vitorias_totais = vitorias_pvp + vitorias_bot
        batalhas_totais = int(getattr(perfil, "BatalhasTotais", vitorias_totais) or vitorias_totais)
        derrotas_totais = max(0, batalhas_totais - vitorias_totais)
        tempo = self._formatar_tempo(getattr(perfil, "TempoJogoSegundos", 0.0) or 0.0)
        baus = int(getattr(perfil, "BausAbertos", 0) or 0)
        maestria = int(getattr(perfil, "Maestria", 0) or 0)

        pokemons = [p for p in list(getattr(inventario, "Pokemons", []) or []) if isinstance(p, dict)]
        itens = list(getattr(inventario, "Itens", []) or [])
        total_itens = self._quantidade_total_itens(itens)
        capacidade_itens = max(1, int(getattr(perfil, "NivelMochila", 1) or 1) * 100)
        limite_pokemons = int(getattr(perfil, "LimitePokemons", 64) or 64)

        esquerda = [
            ("Batalhas totais", str(batalhas_totais)),
            ("Derrotas totais", str(derrotas_totais)),
            ("Vitórias totais", str(vitorias_totais)),
            ("Vitórias vs jogadores", str(vitorias_pvp)),
            ("Vitórias vs BOT", str(vitorias_bot)),
            ("Fugas totais", str(int(getattr(perfil, "Fugas", 0) or 0))),
        ]
        meio = [
            ("Baús abertos", str(baus)),
            ("Itens no inventário", f"{total_itens} / {capacidade_itens}"),
            ("Pokémons guardados", f"{len(pokemons)} / {limite_pokemons}"),
            ("Maior poder Pokémon", str(self._maior_poder(pokemons))),
            ("Maior poder Time", str(self._maior_poder_time())),
            ("Maestria", str(maestria)),
        ]
        direita = [
            ("Insígnias", f"{len(getattr(perfil, 'Insignias', []) or [])} / 25"),
            ("Dungeons terminadas", f"{int(getattr(perfil, 'DungeonsTerminadas', 0) or 0)} / 60"),
            ("Elo", str(int(getattr(perfil, 'Elo', 0) or 0))),
            ("Tempo de jogo", tempo),
        ]
        return nome, esquerda, meio, direita

    def _aplicar_troca_skin(self):
        if self._slider_skin is None or self._desenhador is None or not self._skins:
            return
        novo_indice = max(0, min(len(self._skins) - 1, int(round(self._slider_skin.valor)) - 1))
        if novo_indice == self._skin_index:
            self._slider_skin.set_valor(self._skin_index + 1)
            return
        self._skin_index = novo_indice
        nome_skin, surface_skin = self._skins[self._skin_index]
        self._desenhador.set_skin(surface_skin)
        self.Ator.NomeSkin = nome_skin
        self.Ator.set_skin(surface_skin)
        self._slider_skin.set_valor(self._skin_index + 1)

    def _desenhar_stats(self, tela, eventos, dt):
        pygame.draw.rect(tela, (10, 16, 30), self._area_stats, border_radius=18)
        pygame.draw.rect(tela, (67, 92, 148), self._area_stats, 1, border_radius=18)

        nome, esquerda, meio, direita = self._coletar_dados()
        self.txt_nome_bloco.set_text(nome)
        self.txt_nome_bloco.set_pos((self._area_stats.x + 18, self._area_stats.y + 18))
        self.txt_nome_bloco.draw(tela)

        col_w = (self._area_stats.width - 72) // 3
        row_gap = 68
        base_y = self._area_stats.y + 74
        idx = 0
        for c, bloco in enumerate((esquerda, meio, direita)):
            x = self._area_stats.x + 18 + c * (col_w + 18)
            for i, (rotulo, valor) in enumerate(bloco):
                y = base_y + i * row_gap
                self._labels[idx].set_text(rotulo)
                self._labels[idx].set_pos((x, y))
                self._labels[idx].draw(tela)
                self._values[idx].set_text(valor)
                self._values[idx].set_pos((x, y + 24))
                self._values[idx].draw(tela)
                idx += 1
        if self._botao_conhecimento is not None:
            self._botao_conhecimento.render(tela, eventos, dt, None)
        if self._botao_progresso is not None:
            self._botao_progresso.render(tela, eventos, dt, None)

    def _desenhar_direita(self, tela, eventos, dt):
        pygame.draw.rect(tela, (10, 16, 30), self._area_direita, border_radius=18)
        pygame.draw.rect(tela, (67, 92, 148), self._area_direita, 1, border_radius=18)

        perfil = getattr(self.Ator, "Perfil", None)
        nivel = int(getattr(perfil, "Nivel", 0) or 0)
        xp = max(0, int(getattr(perfil, "XP", 0) or 0))
        xp_alvo = max(0, int(getattr(perfil, "XPAlvo", 0) or 0))
        pontos = self._painel_skill._pontos_disponiveis()

        self.txt_nivel.set_text(f"Nível {nivel}")
        self.txt_nivel.set_pos((self._area_direita.x + 18, self._area_direita.y + 14))
        self.txt_nivel.draw(tela)
        dinheiro = int(getattr(perfil, "Dinheiro", 0) or 0)
        x_direita = self._area_stats.right - 18
        self.txt_dinheiro.set_text(str(dinheiro))
        self.txt_dinheiro.set_pos((x_direita, self._area_stats.y + 16))
        self.txt_dinheiro.draw(tela)
        if self._icone_dinheiro is not None:
            rect_icone = self._icone_dinheiro.get_rect()
            rect_icone.midright = (x_direita - 56, self._area_stats.y + 30)
            tela.blit(self._icone_dinheiro, rect_icone)

        max_barra = xp_alvo if xp_alvo > 0 else 1
        valor_barra = min(xp, max_barra)
        self._barra_xp.minimo = 0.0
        self._barra_xp.maximo = float(max_barra)
        self._barra_xp.set_valor(valor_barra)
        self._barra_xp.render(tela, [], dt)

        self.txt_xp.set_text(f"XP: {xp} / {xp_alvo if xp_alvo > 0 else 'MAX'}")
        self.txt_xp.set_pos((self._area_direita.x + 18, self._area_direita.y + 72))
        self.txt_xp.draw(tela)

        self._botao_skill.set_pulsando(pontos > 0, cor=(195, 132, 255), cor_borda=(232, 210, 255), velocidade=1.7, intensidade=0.48)
        self._botao_skill.render(tela, eventos, dt, None)

        pygame.draw.rect(tela, (16, 24, 42), self._area_ator, border_radius=18)
        pygame.draw.rect(tela, (83, 114, 177), self._area_ator, 2, border_radius=18)
        centro = (self._area_ator.centerx, self._area_ator.centery - 8)
        self._desenhador.desenhar(tela, centro, pygame.mouse.get_pos())

        nome_skin = self._skins[self._skin_index][0].replace(".png", "") if self._skins else "1"
        self.txt_skin_atual.set_text(nome_skin)
        self.txt_skin_atual.set_pos((self._area_ator.right - 12, self._area_ator.y + 10))
        self.txt_skin_atual.draw(tela)

        self.txt_skin_liberadas.set_text(f"{len(self._skins)} skins liberadas")
        self.txt_skin_liberadas.set_pos((self._area_ator.x + 4, self._area_ator.bottom + 8))
        self.txt_skin_liberadas.draw(tela)

        alterou = self._slider_skin.render(tela, eventos, dt)
        if alterou:
            self._aplicar_troca_skin()

    def renderizar(self, tela, rect, inventario=None, eventos=None, dt=0.0):
        if self.Ator is None:
            Texto("Perfil indisponível", pos=(rect.x + 18, rect.y + 22), style={"size": 24, "align": "topleft"}).draw(tela)
            return

        eventos = eventos or []
        self._reconstruir_layout(pygame.Rect(rect))
        self._painel_skill.Ator = self.Ator

        fundo = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        fundo.fill((8, 12, 24, 228))
        tela.blit(fundo, rect.topleft)

        if self._arvore_aberta:
            if self._painel_skill.renderizar(tela, pygame.Rect(rect), eventos=eventos, dt=dt):
                self._arvore_aberta = False
            return

        if self._overlay_extra == "conhecimento":
            self._painel_conhecimento.Ator = self.Ator
            if self._painel_conhecimento.renderizar(tela, pygame.Rect(rect), eventos=eventos, dt=dt):
                self._overlay_extra = ""
            return
        if self._overlay_extra == "progresso":
            self._painel_progresso.Ator = self.Ator
            if self._painel_progresso.renderizar(tela, pygame.Rect(rect), eventos=eventos, dt=dt):
                self._overlay_extra = ""
            return

        self._desenhar_stats(tela, eventos, dt)
        self._desenhar_direita(tela, eventos, dt)
