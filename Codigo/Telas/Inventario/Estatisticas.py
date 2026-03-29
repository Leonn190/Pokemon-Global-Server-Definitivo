from __future__ import annotations

from pathlib import Path

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Modulos.DesenhaAtor import DesenhaAtor
from Codigo.Paineis.PainelArvoreHabilidades import PainelArvoreHabilidades
from Codigo.Prefabs.Barra import Barra, BarraEditavel
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto


class InventarioPerfil:
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
        self._botoes_rotas: list[tuple[Texto, Botao]] = []

        self._area_stats = pygame.Rect(0, 0, 0, 0)
        self._area_direita = pygame.Rect(0, 0, 0, 0)
        self._area_ator = pygame.Rect(0, 0, 0, 0)
        self._area_rotas = pygame.Rect(0, 0, 0, 0)

        base = {"outline": True, "outline_thickness": 1, "outline_color": (0, 0, 0), "shadow": False}
        self.txt_nome_bloco = Texto("", style={**base, "size": 32, "color": (245, 248, 255)})
        self.txt_nivel = Texto("", style={**base, "size": 26, "color": (245, 248, 255)})
        self.txt_xp = Texto("", style={**base, "size": 18, "color": (186, 205, 238)})
        self.txt_skin_liberadas = Texto("", style={**base, "size": 18, "color": (193, 212, 244)})
        self.txt_skin_atual = Texto("", style={**base, "size": 17, "color": (221, 234, 255), "align": "topright"})

        self._labels = [Texto("", style={**base, "size": 18, "color": (164, 184, 221)}) for _ in range(12)]
        self._values = [Texto("", style={**base, "size": 26, "color": (247, 250, 255)}) for _ in range(12)]

    @staticmethod
    def _formatar_tempo(segundos: float) -> str:
        total = max(0, int(segundos or 0.0))
        horas = total // 3600
        minutos = (total % 3600) // 60
        segs = total % 60
        return f"{horas:02d}:{minutos:02d}:{segs:02d}"

    @staticmethod
    def _normalizar_nome_skin(nome_skin: str) -> str:
        base = str(nome_skin or "S1").strip() or "S1"
        return base if base.lower().endswith(".png") else f"{base}.png"

    def _coletar_skins_liberadas(self) -> list[tuple[str, pygame.Surface]]:
        ator = self.Ator
        perfil = getattr(ator, "Perfil", None)
        liberadas = [self._normalizar_nome_skin(s) for s in list(getattr(perfil, "SkinsLiberadas", []) or [])]
        atual = self._normalizar_nome_skin(getattr(ator, "NomeSkin", "S1"))
        if not liberadas:
            liberadas = [atual]
        elif atual not in liberadas:
            liberadas.insert(0, atual)

        skins: list[tuple[str, pygame.Surface]] = []
        for nome in dict.fromkeys(liberadas):
            caminho = Path("Recursos") / "Visual" / "Skins" / "Liberadas" / nome
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

        nome_skin_atual = self._normalizar_nome_skin(getattr(self.Ator, "NomeSkin", "S1"))
        for i, (nome, _) in enumerate(self._skins):
            if nome == nome_skin_atual:
                self._skin_index = i
                break

        margem = 18
        topo = rect.y + 16
        largura_stats = int(rect.width * 0.63)
        self._area_stats = pygame.Rect(rect.x + margem, topo, largura_stats, rect.height - 128)
        self._area_direita = pygame.Rect(self._area_stats.right + 24, topo, rect.right - self._area_stats.right - margem - 24, rect.height - 128)
        self._area_rotas = pygame.Rect(rect.x + 16, rect.bottom - 96, rect.width - 32, 82)

        self._area_ator = pygame.Rect(self._area_direita.x + 18, self._area_direita.y + 144, self._area_direita.width - 36, self._area_direita.height - 252)

        barra_rect = pygame.Rect(self._area_direita.x + 18, self._area_direita.y + 44, self._area_direita.width - 36, 22)
        self._barra_xp = Barra(barra_rect, texto="", valor=0, minimo=0, maximo=100, mostrar_rotulo=False, suavizacao=10.0)
        self._barra_xp.cor_fundo = (22, 29, 46)
        self._barra_xp.cor_preenchimento = (126, 86, 224)
        self._barra_xp.cor_borda = (216, 202, 255)

        self._slider_skin = BarraEditavel(
            pygame.Rect(self._area_ator.x + 8, self._area_ator.bottom + 32, self._area_ator.width - 16, 18),
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

        self._botao_skill = Botao(
            pygame.Rect(self._area_direita.x + 18, self._area_direita.y + 94, self._area_direita.width - 36, 48),
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

        rotas = [
            ("Intelectual", (76, 108, 178), (108, 143, 216)),
            ("Magnata", (155, 118, 33), (193, 149, 46)),
            ("Herói", (45, 130, 88), (61, 160, 109)),
            ("Campeão", (136, 52, 118), (168, 68, 146)),
            ("Imperador", (142, 62, 42), (180, 79, 56)),
        ]
        self._botoes_rotas = []
        gap = 12
        largura_botao = (self._area_rotas.width - gap * 4) // 5
        for i, (nome, cor, cor_hover) in enumerate(rotas):
            bx = self._area_rotas.x + i * (largura_botao + gap)
            label = Texto("caminho do", style={**{"outline": True, "outline_thickness": 1, "outline_color": (0, 0, 0), "shadow": False}, "size": 14, "color": (154, 170, 204)})
            botao = Botao(
                pygame.Rect(bx, self._area_rotas.y + 18, largura_botao, 60),
                nome,
                execute=None,
                style={
                    "radius": 18,
                    "bg": cor,
                    "bg_hover": cor_hover,
                    "bg_pressed": cor,
                    "border": (227, 235, 255),
                    "border_hover": (255, 245, 214),
                    "text_style": {"size": 21, "outline_thickness": 1, "shadow": False},
                },
            )
            self._botoes_rotas.append((label, botao))

    def _maior_poder(self, pokemons: list[dict]) -> int:
        maior = 0.0
        for pokemon in pokemons:
            if not isinstance(pokemon, dict):
                continue
            total = float(pokemon.get("total", 0.0) or 0.0)
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
                    total += float(pokemon.get("total", 0.0) or 0.0)
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
            ("Tempo de jogo", tempo),
        ]
        direita = [
            ("Baús abertos", str(baus)),
            ("Itens no inventário", f"{total_itens} / {capacidade_itens}"),
            ("Pokémons guardados", f"{len(pokemons)} / {limite_pokemons}"),
            ("Maior poder Pokémon", str(self._maior_poder(pokemons))),
            ("Maior poder Time", str(self._maior_poder_time())),
            ("Maestria", str(maestria)),
        ]
        return nome, esquerda, direita

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

    def _desenhar_stats(self, tela):
        pygame.draw.rect(tela, (10, 16, 30), self._area_stats, border_radius=18)
        pygame.draw.rect(tela, (67, 92, 148), self._area_stats, 1, border_radius=18)

        nome, esquerda, direita = self._coletar_dados()
        self.txt_nome_bloco.set_text(nome)
        self.txt_nome_bloco.set_pos((self._area_stats.x + 18, self._area_stats.y + 18))
        self.txt_nome_bloco.draw(tela)

        col_w = (self._area_stats.width - 54) // 2
        row_gap = 74
        base_y = self._area_stats.y + 74
        idx = 0
        for c, bloco in enumerate((esquerda, direita)):
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

        nome_skin = self._skins[self._skin_index][0].replace(".png", "") if self._skins else "S1"
        self.txt_skin_atual.set_text(nome_skin)
        self.txt_skin_atual.set_pos((self._area_ator.right - 12, self._area_ator.y + 10))
        self.txt_skin_atual.draw(tela)

        self.txt_skin_liberadas.set_text(f"{len(self._skins)} skins liberadas")
        self.txt_skin_liberadas.set_pos((self._area_ator.x + 4, self._area_ator.bottom + 8))
        self.txt_skin_liberadas.draw(tela)

        alterou = self._slider_skin.render(tela, eventos, dt)
        if alterou:
            self._aplicar_troca_skin()

    def _desenhar_rotas(self, tela, eventos, dt):
        for label, botao in self._botoes_rotas:
            label.set_pos((botao.base_rect.x + 18, botao.base_rect.y + 2))
            label.draw(tela)
            botao.render(tela, eventos, dt, None)

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

        self._desenhar_stats(tela)
        self._desenhar_direita(tela, eventos, dt)
        self._desenhar_rotas(tela, eventos, dt)
