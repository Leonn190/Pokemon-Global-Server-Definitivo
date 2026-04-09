from __future__ import annotations

import math
from pathlib import Path
from typing import Optional, Tuple

import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Geradores.PokemonInventario import PokemonInventario
from Codigo.Paineis.FichaPokemon import FichaPokemon
from Codigo.Prefabs.Barra import Barra
from Codigo.Prefabs.Botao import BotaoAlavanca, BotaoSelecao
from Codigo.Prefabs.Texto import Texto


class FichaPokemonBatalha:
    def __init__(self) -> None:
        self.rect = pygame.Rect(0, 0, 0, 0)
        self._cache_tela: Optional[Tuple[int, int]] = None
        self._toggle_extra = BotaoAlavanca(pygame.Rect(0, 0, 28, 20), "+", estado_inicial=False)
        self._barra_vida: Optional[Barra] = None
        self._barra_energia: Optional[Barra] = None
        self._icones_stats = self._mapa_icone_stats()
        self._cache_ataque_icones: dict[tuple[str, str, int], pygame.Surface | None] = {}
        self._botoes_ataque: dict[str, BotaoSelecao] = {}
        self._opcoes_acao: list[dict] = []
        self._acao_selecionada: str = "mover"
        self._previsao_custo: float = 0.0
        self._previsao_pode: bool = True

    def _mapa_icone_stats(self):
        pasta = Path("Recursos") / "Visual" / "Icones" / "Atributos"
        return {arq.stem.lower(): str(arq) for arq in pasta.glob("*.png")}

    def _icone_stat(self, chave: str, lado: int) -> Optional[pygame.Surface]:
        caminho = self._icones_stats.get(str(chave).lower())
        if not caminho:
            return None
        try:
            return pygame.transform.smoothscale(pygame.image.load(caminho).convert_alpha(), (lado, lado))
        except Exception:
            return None

    def _icone_ataque(self, ataque: dict, lado: int) -> Optional[pygame.Surface]:
        nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()
        tipo = str(ataque.get("Tipo") or ataque.get("tipo") or "Normal").strip() or "Normal"
        chave = (nome.lower(), tipo.lower(), int(lado))
        if chave in self._cache_ataque_icones:
            return self._cache_ataque_icones[chave]
        caminho = FichaPokemon._icone_ataque_path(nome, tipo)
        surf = None
        if caminho is not None:
            try:
                img = pygame.image.load(str(caminho)).convert_alpha()
                surf = pygame.transform.smoothscale(img, (lado, lado))
            except Exception:
                surf = None
        self._cache_ataque_icones[chave] = surf
        return surf

    def _garantir_layout(self, tela: pygame.Surface):
        tamanho = tuple(tela.get_size())
        if self._cache_tela == tamanho and self.rect.width > 0:
            return
        self._cache_tela = tamanho
        w, h = tamanho
        largura = min(1060, int(w * 0.88))
        altura = max(170, int(h * 0.27))
        self.rect = pygame.Rect((w - largura) // 2, h - altura - 18, largura, altura)

    def _desenhar_bloco_stats(self, tela: pygame.Surface, area: pygame.Rect, pokemon, eventos, exibir_vamp_base: bool):
        col_esq = ["Atk", "Def", "Mag", "Vel", "Int"]
        col_dir = ["SpA", "SpD", "Ene", "Per", "Vamp" if exibir_vamp_base else "+"]
        linha_h = max(20, area.height // 6)
        y = area.y + 8
        x1 = area.x + 8
        x2 = area.centerx + 8

        for i in range(5):
            for idx, (x, chave) in enumerate(((x1, col_esq[i]), (x2, col_dir[i]))):
                if chave == "+":
                    self._toggle_extra.rect = pygame.Rect(x, y, 28, 20)
                    self._toggle_extra.render(tela, eventos or [], 0.0, None)
                    continue
                valor = pokemon.obter_valor_ficha(chave)
                ico = self._icone_stat(chave, 16)
                if ico is not None:
                    tela.blit(ico, (x, y + 2))
                    tx = x + 18
                else:
                    tx = x
                texto = f"{int(round(float(valor)))}" if isinstance(valor, (int, float)) else str(valor)
                Texto(texto, pos=(tx, y + 10), style={"size": 12, "align": "left", "outline": True}).draw(tela)
            y += linha_h

    def _desenhar_extensao_esquerda(self, tela: pygame.Surface, area: pygame.Rect, pokemon, eventos):
        pygame.draw.rect(tela, (14, 20, 34, 242), area, border_radius=14)
        pygame.draw.rect(tela, (108, 136, 188), area, 2, border_radius=14)
        col_esq = ["Vida", "Peso", "Amplificacao", "CrC", "+"]
        col_dir = ["EnergiaMaxima", "Escala", "Durabilidade", "CrD", "Barreira"]
        linha_h = max(20, area.height // 6)
        y = area.y + 8
        x1 = area.x + 8
        x2 = area.centerx + 8
        for i in range(5):
            for x, chave in ((x1, col_esq[i]), (x2, col_dir[i])):
                if chave == "+":
                    self._toggle_extra.rect = pygame.Rect(x, y, 28, 20)
                    self._toggle_extra.render(tela, eventos or [], 0.0, None)
                    continue
                valor = pokemon.obter_valor_ficha(chave)
                ico = self._icone_stat(chave, 16)
                if ico is not None:
                    tela.blit(ico, (x, y + 2))
                    tx = x + 18
                else:
                    tx = x
                texto = f"{int(round(float(valor)))}" if isinstance(valor, (int, float)) else str(valor)
                Texto(texto, pos=(tx, y + 10), style={"size": 12, "align": "left", "outline": True}).draw(tela)
            y += linha_h

    def _desenhar_ataques(self, tela: pygame.Surface, area: pygame.Rect, pokemon, eventos) -> None:
        ataques = list(getattr(pokemon, "ListaAtaques", []) or [])
        botoes = [{"_id": "mover", "Ataque": "Mover", "Nome": "Mover", "Tipo": "Diversos", "Estilo": "movimento", "_acao_padrao": True}]
        for i, ataque in enumerate(ataques):
            item = dict(ataque) if isinstance(ataque, dict) else {"Ataque": str(ataque), "Nome": str(ataque), "Tipo": "Normal"}
            item["_id"] = f"atk:{i}:{str(item.get('Ataque') or item.get('Nome') or i)}"
            botoes.append(item)
        self._opcoes_acao = botoes
        total = max(1, len(botoes))
        gap = 8
        lado = min(area.height - 12, int((area.width - gap * (total - 1)) / total))
        x = area.x + (area.width - (lado * total + gap * (total - 1))) // 2
        y = area.y + (area.height - lado) // 2

        for atk in botoes:
            rect = pygame.Rect(x, y, lado, lado)
            chave = str(atk.get("_id") or "")
            if chave not in self._botoes_ataque:
                self._botoes_ataque[chave] = BotaoSelecao(
                    rect,
                    "",
                    style={
                        "radius": 8,
                        "border_width": 2,
                        "bg": (18, 24, 38),
                        "bg_hover": (30, 40, 62),
                        "bg_pressed": (14, 20, 32),
                        "border": (120, 144, 188),
                        "border_hover": (170, 196, 236),
                        "text_style": {"size": 1, "outline_thickness": 0, "shadow": False},
                    },
                )
            botao = self._botoes_ataque[chave]
            botao.rect = rect
            botao.set_selecionado(chave == self._acao_selecionada)
            botao.render(tela, eventos or [], 0.0, None)
            if botao.clicado:
                self._acao_selecionada = chave
            icone = self._icone_ataque(atk, lado)
            if icone is not None:
                tela.blit(icone, icone.get_rect(center=rect.center))
            else:
                pygame.draw.rect(tela, (35, 46, 70), rect.inflate(-4, -4), border_radius=8)
                Texto(str(atk.get("Ataque") or atk.get("Nome") or "Atk")[:2], pos=rect.center, style={"size": 12, "align": "center", "outline": True}).draw(tela)
            x += lado + gap

    def _desenhar_barras_e_itens(self, tela: pygame.Surface, area: pygame.Rect, pokemon, dt: float):
        barras_w = int(area.width * 0.62)
        bx = area.x + 10
        by = area.y + 10
        bh = max(16, int((area.height - 24) * 0.34))

        self._barra_vida = Barra((bx, by, barras_w, bh), "", valor=float(pokemon.VidaAtual), minimo=0, maximo=max(1.0, float(pokemon.VidaMax)), mostrar_rotulo=False)
        self._barra_vida.cor_preenchimento = (52, 205, 72)
        self._barra_vida.render(tela, [], dt)

        self._barra_energia = Barra((bx, by + bh + 8, barras_w, bh), "", valor=float(pokemon.Energia), minimo=0, maximo=max(1.0, float(pokemon.EnergiaMax)), mostrar_rotulo=False)
        self._barra_energia.cor_preenchimento = (60, 150, 255)
        self._barra_energia.render(tela, [], dt)
        if self._previsao_custo > 0.01:
            proporcao = max(0.0, min(1.0, float(self._previsao_custo) / max(1.0, float(pokemon.EnergiaMax))))
            if proporcao > 0.0:
                pisca = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 120.0))
                largura = max(1, int((self._barra_energia.rect.width - 2) * proporcao))
                x0 = self._barra_energia.rect.right - 1 - largura
                base = (255, 255, 255) if self._previsao_pode else (255, 184, 184)
                alpha = int(85 + 120 * pisca)
                camada = pygame.Surface((largura, max(2, self._barra_energia.rect.height - 2)), pygame.SRCALPHA)
                camada.fill((*base, alpha))
                tela.blit(camada, (x0, self._barra_energia.rect.y + 1))

        Texto(f"{int(pokemon.VidaAtual)}/{int(pokemon.VidaMax)}", pos=(bx + barras_w - 6, by + (bh // 2)), style={"size": 13, "align": "right", "outline": True}).draw(tela)
        Texto(f"{int(pokemon.Energia)}/{int(pokemon.EnergiaMax)}", pos=(bx + barras_w - 6, by + bh + 8 + (bh // 2)), style={"size": 13, "align": "right", "outline": True}).draw(tela)

        itens = list(getattr(pokemon, "ItensBuild", []) or [])
        area_itens = pygame.Rect(bx + barras_w + 12, area.y + 6, area.width - barras_w - 18, area.height - 12)
        if not itens:
            return
        lado = min(34, max(20, area_itens.height // 2))
        gap = 6
        total_w = len(itens) * lado + max(0, len(itens) - 1) * gap
        x = area_itens.x + max(0, (area_itens.width - total_w) // 2)
        y = area_itens.y + (area_itens.height - lado) // 2
        for item in itens:
            rect = pygame.Rect(x, y, lado, lado)
            pygame.draw.rect(tela, (15, 20, 30), rect, border_radius=6)
            icone = ItemInventario.surface_item(item, lado_px=lado - 2) if isinstance(item, dict) else None
            if icone is not None:
                tela.blit(icone, icone.get_rect(center=rect.center))
            else:
                pygame.draw.rect(tela, (230, 230, 230), rect.inflate(-8, -8), border_radius=4)
            pygame.draw.rect(tela, (120, 144, 188), rect, 2, border_radius=6)
            x += lado + gap

    def _desenhar_direita(self, tela: pygame.Surface, area: pygame.Rect, pokemon):
        Texto(str(getattr(pokemon, "Nome", "Pokemon")), pos=(area.centerx, area.y + 12), style={"size": 20, "align": "center", "outline": True}).draw(tela)
        lado_img = max(54, int(area.height * 0.45))
        img = PokemonInventario.surface_pokemon(getattr(pokemon, "Dados", {}), lado_img)
        if img is not None:
            tela.blit(img, img.get_rect(center=(area.centerx, area.centery + 2)))
        Texto(f"Lv {int(getattr(pokemon, 'Nivel', 1))}", pos=(area.centerx, area.bottom - 38), style={"size": 16, "align": "center", "outline": True}).draw(tela)
        tipos = PokemonInventario.tipos_pokemon(getattr(pokemon, "Dados", {}))
        x = area.centerx - (len(tipos) * 24) // 2
        for tipo in tipos:
            ico = PokemonInventario.icone_tipo(tipo, 22)
            if ico is not None:
                tela.blit(ico, (x, area.bottom - 26))
            x += 24

    def render(self, tela: pygame.Surface, pokemon, t_visivel: float, eventos, dt: float):
        if pokemon is None:
            return
        self._garantir_layout(tela)
        t = max(0.0, min(1.0, t_visivel))
        offset = int((1.0 - t) * (self.rect.height + 26))
        rect = self.rect.move(0, offset)

        ext_w = int(rect.width * 0.26) if self._toggle_extra.estado else 0
        if ext_w > 0:
            area_ext = pygame.Rect(rect.x - ext_w - 8, rect.y, ext_w, rect.height)
            self._desenhar_extensao_esquerda(tela, area_ext, pokemon, eventos)

        painel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(painel, (14, 20, 34, 242), painel.get_rect(), border_radius=14)
        pygame.draw.rect(painel, (108, 136, 188), painel.get_rect(), 2, border_radius=14)

        esq_w = int(rect.width * 0.30)
        dir_w = int(rect.width * 0.24)
        meio_w = rect.width - esq_w - dir_w

        area_esq = pygame.Rect(0, 0, esq_w, rect.height)
        area_meio = pygame.Rect(esq_w, 0, meio_w, rect.height)
        area_dir = pygame.Rect(esq_w + meio_w, 0, dir_w, rect.height)

        topo_meio = pygame.Rect(area_meio.x + 4, area_meio.y + 4, area_meio.width - 8, int(area_meio.height * 0.54))
        baixo_meio = pygame.Rect(area_meio.x + 4, topo_meio.bottom + 2, area_meio.width - 8, area_meio.bottom - topo_meio.bottom - 6)
        pygame.draw.line(painel, (72, 90, 128), (area_meio.x, topo_meio.bottom), (area_meio.right, topo_meio.bottom), 1)

        self._desenhar_bloco_stats(painel, area_esq.inflate(-8, -6), pokemon, eventos, exibir_vamp_base=self._toggle_extra.estado)
        self._desenhar_ataques(painel, topo_meio, pokemon, eventos)
        self._desenhar_barras_e_itens(painel, baixo_meio, pokemon, dt)
        self._desenhar_direita(painel, area_dir.inflate(-6, -6), pokemon)

        tela.blit(painel, rect.topleft)

    def ataque_selecionado(self) -> Optional[dict]:
        for item in self._opcoes_acao:
            if str(item.get("_id") or "") == self._acao_selecionada:
                return None if item.get("_acao_padrao") else dict(item)
        return None

    def atualizar_previsao(self, custo: float, pode: bool) -> None:
        self._previsao_custo = max(0.0, float(custo or 0.0))
        self._previsao_pode = bool(pode)

    def contem_ponto(self, pos) -> bool:
        return bool(self.rect.width > 0 and self.rect.height > 0 and self.rect.collidepoint(pos))
