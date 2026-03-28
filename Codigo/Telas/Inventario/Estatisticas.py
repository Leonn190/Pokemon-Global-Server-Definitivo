from __future__ import annotations

from pathlib import Path

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Modulos.DesenhaAtor import DesenhaAtor
from Codigo.Prefabs.Barra import BarraEditavel
from Codigo.Prefabs.Texto import Texto


class InventarioPerfil:
    """Painel de perfil do jogador dentro do unificador do inventário."""

    def __init__(self, ator=None):
        self.Ator = ator

        self._layout_chave = None
        self._slider_skin: BarraEditavel | None = None
        self._skins: list[tuple[str, pygame.Surface]] = []
        self._skin_index = 0
        self._desenhador: DesenhaAtor | None = None

        self._txt_titulo = Texto("Perfil do Jogador", style={"size": 34, "align": "topleft", "outline_thickness": 1, "shadow": False})
        self._txt_hint = Texto("Use o slider para trocar a skin liberada.", style={"size": 20, "align": "topleft", "outline_thickness": 1, "shadow": False, "color": (190, 210, 245)})
        self._txt_skin = Texto("", style={"size": 24, "align": "topleft", "outline_thickness": 1, "shadow": False, "color": (220, 238, 255)})

        self._labels: list[Texto] = []
        self._values: list[Texto] = []
        for _ in range(9):
            self._labels.append(Texto("", style={"size": 24, "align": "topleft", "outline_thickness": 1, "shadow": False, "color": (183, 202, 236)}))
            self._values.append(Texto("", style={"size": 31, "align": "topleft", "outline_thickness": 1, "shadow": False, "color": (243, 248, 255)}))

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

        self._slider_skin = BarraEditavel(
            pygame.Rect(rect.x + 28, rect.bottom - 54, rect.width - 56, 22),
            "Skin",
            self._skin_index + 1,
            1,
            max(1, len(self._skins)),
            casas_decimais=0,
        )
        self._slider_skin.cor_fundo = (26, 34, 58)
        self._slider_skin.cor_preenchimento = (114, 188, 255)
        self._slider_skin.cor_borda = (200, 228, 255)
        self._slider_skin.cor_manopla = (245, 250, 255)

        self._desenhador = DesenhaAtor(self._skins[self._skin_index][1], escala=2.0)

    def _maior_poder(self, pokemons: list[dict]) -> int:
        """Formato oficial de pokemon materializado: chave `total`."""
        maior = 0.0
        for pokemon in pokemons:
            if not isinstance(pokemon, dict):
                continue
            total = float(pokemon.get("total", 0.0) or 0.0)
            if total > maior:
                maior = total
        return int(round(maior))

    def _coletar_dados(self) -> list[tuple[str, str]]:
        ator = self.Ator
        perfil = getattr(ator, "Perfil", None)
        inventario = getattr(ator, "Inventario", None)

        nome = str(getattr(ator, "Nome", "") or "Treinador")
        vitorias_pvp = int(getattr(perfil, "BatalhasPVPVencidas", 0) or 0)
        vitorias_bot = int(getattr(perfil, "BatalhasBotVencidas", 0) or 0)
        vitorias_totais = vitorias_pvp + vitorias_bot

        pokemons = [p for p in list(getattr(inventario, "Pokemons", []) or []) if isinstance(p, dict)]
        numero_pokemons = len(pokemons)

        baus_abertos = int(getattr(perfil, "BausAbertos", 0) or 0)
        tempo = self._formatar_tempo(getattr(perfil, "TempoJogoSegundos", 0.0) or 0.0)
        metros = int(round(float(getattr(perfil, "MetrosAndados", 0.0) or 0.0)))

        return [
            ("Nome", nome),
            ("Vitórias totais", str(vitorias_totais)),
            ("Vitórias vs BOT", str(vitorias_bot)),
            ("Vitórias vs Players", str(vitorias_pvp)),
            ("Número de Pokémons", str(numero_pokemons)),
            ("Baús abertos", str(baus_abertos)),
            ("Maior poder Pokémon", str(self._maior_poder(pokemons))),
            ("Tempo de jogo", tempo),
            ("Metros andados", f"{metros} m"),
        ]

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

    def renderizar(self, tela, rect, inventario=None, eventos=None, dt=0.0):
        if self.Ator is None:
            aviso = Texto("Perfil indisponível", pos=(rect.x + 18, rect.y + 22), style={"size": 24, "align": "topleft"})
            aviso.draw(tela)
            return

        eventos = eventos or []
        self._reconstruir_layout(rect)

        painel = pygame.Rect(rect.x + 10, rect.y + 10, rect.width - 20, rect.height - 20)
        pygame.draw.rect(tela, (9, 13, 26), painel, border_radius=18)
        pygame.draw.rect(tela, (52, 76, 128), painel, 2, border_radius=18)

        self._txt_titulo.set_pos((painel.x + 18, painel.y + 14))
        self._txt_titulo.draw(tela)

        area_conteudo = pygame.Rect(painel.x + 16, painel.y + 64, painel.width - 32, painel.height - 124)
        area_stats = pygame.Rect(area_conteudo.x, area_conteudo.y, int(area_conteudo.width * 0.63), area_conteudo.height)
        area_skin = pygame.Rect(area_stats.right + 14, area_conteudo.y, area_conteudo.right - (area_stats.right + 14), area_conteudo.height)

        pygame.draw.rect(tela, (15, 22, 42), area_skin, border_radius=14)
        pygame.draw.rect(tela, (78, 106, 160), area_skin, 1, border_radius=14)

        blocos = self._coletar_dados()
        cols, rows = 3, 3
        gap_x, gap_y = 16, 12
        bloco_w = max(150, (area_stats.width - gap_x * (cols - 1)) // cols)
        bloco_h = max(84, (area_stats.height - gap_y * (rows - 1)) // rows)

        for i, (rotulo, valor) in enumerate(blocos):
            c = i % cols
            l = i // cols
            card = pygame.Rect(area_stats.x + c * (bloco_w + gap_x), area_stats.y + l * (bloco_h + gap_y), bloco_w, bloco_h)
            pygame.draw.rect(tela, (18, 27, 48), card, border_radius=12)
            pygame.draw.rect(tela, (60, 87, 140), card, 1, border_radius=12)

            self._labels[i].set_text(rotulo)
            self._labels[i].set_pos((card.x + 12, card.y + 10))
            self._labels[i].draw(tela)

            self._values[i].set_text(valor)
            self._values[i].set_pos((card.x + 12, card.y + 40))
            self._values[i].draw(tela)

        skin_nome = self._skins[self._skin_index][0].replace(".png", "") if self._skins else "S1"
        self._txt_skin.set_text(f"Skin atual: {skin_nome}")
        self._txt_skin.set_pos((area_skin.x + 14, area_skin.y + 12))
        self._txt_skin.draw(tela)

        quadro_ator = pygame.Rect(area_skin.x + 20, area_skin.y + 52, area_skin.width - 40, area_skin.height - 72)
        pygame.draw.rect(tela, (22, 33, 57), quadro_ator, border_radius=14)
        pygame.draw.rect(tela, (90, 126, 188), quadro_ator, 2, border_radius=14)
        self._desenhador.desenhar(tela, quadro_ator.center, pygame.mouse.get_pos())

        alterou = self._slider_skin.render(tela, eventos, dt)
        if alterou:
            self._aplicar_troca_skin()

        self._txt_hint.set_pos((painel.x + 22, painel.bottom - 94))
        self._txt_hint.draw(tela)
