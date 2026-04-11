from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pygame

from Codigo.Geradores.PokemonInventario import PokemonInventario
from Codigo.Paineis.FichaPokemon import FichaPokemon
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto


@dataclass
class _PainelItem:
    jogada_id: int
    dados: Dict[str, object]
    ordem: int = 0
    animacao: float = 0.0
    alvo_animacao: float = 1.0
    selecionado: bool = False
    rect: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 0, 0))
    rect_fechar: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 0, 0))
    botao_fechar: Botao | None = None


class PainelJogada:
    def __init__(self) -> None:
        self._itens: Dict[int, _PainelItem] = {}
        self._texto_nome = Texto(
            "",
            style={
                "size": 15,
                "align": "midleft",
                "color": (245, 249, 255),
                "outline": True,
                "outline_thickness": 2,
                "outline_color": (8, 12, 20),
                "shadow": False,
            },
        )
        self._texto_aux = Texto(
            "",
            style={
                "size": 12,
                "align": "midleft",
                "color": (194, 208, 235),
                "outline": True,
                "outline_thickness": 2,
                "outline_color": (8, 12, 20),
                "shadow": False,
            },
        )
        self._comandos: List[Dict[str, object]] = []
        self._hover_jogada_id: int | None = None
        self._cache_icones_diversos: dict[tuple[str, int], pygame.Surface | None] = {}

    @staticmethod
    def _cor_item(dados: Dict[str, object], selecionado: bool) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
        estilo = str(dados.get("estilo") or "movimento").casefold()
        if estilo == "movimento" and dados.get("ataque") is None:
            base = (42, 120, 210)
        elif estilo == "movimento":
            base = (220, 130, 54)
        elif estilo in {"alvo", "status"}:
            base = (190, 76, 76)
        else:
            base = (220, 220, 220)
        borda = tuple(min(255, canal + (55 if selecionado else 20)) for canal in base)
        fundo = tuple(max(18, int(canal * (0.16 if selecionado else 0.12))) for canal in base)
        brilho = tuple(min(255, canal + (80 if selecionado else 40)) for canal in base)
        return fundo, borda, brilho

    @staticmethod
    def _nome_item(dados: Dict[str, object]) -> str:
        if dados.get("troca_reserva_id"):
            return "Trocar"
        ataque = dados.get("ataque")
        if isinstance(ataque, dict):
            nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()
            if nome:
                return nome
        return "Mover"

    @staticmethod
    def _descricao_item(dados: Dict[str, object]) -> str:
        executor = dados.get("executor")
        nome_poke = str(getattr(executor, "Nome", "") or getattr(executor, "Especie", "") or "Pokemon")
        custo = int(round(float(dados.get("custo") or 0.0)))
        return f"{nome_poke}  Ene {custo}"

    @staticmethod
    def _icone_ataque(dados: Dict[str, object], lado: int) -> Optional[pygame.Surface]:
        ataque = dados.get("ataque")
        if not isinstance(ataque, dict):
            return None
        nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()
        tipo = str(ataque.get("Tipo") or ataque.get("tipo") or "Normal").strip() or "Normal"
        caminho = FichaPokemon._icone_ataque_path(nome, tipo)
        if caminho is None:
            return None
        return FichaPokemon._carregar_surface(caminho, (lado, lado), chave_extra="contain")

    def _icone_diverso(self, nome: str, lado: int) -> Optional[pygame.Surface]:
        chave = (str(nome), int(lado))
        if chave in self._cache_icones_diversos:
            return self._cache_icones_diversos[chave]
        arquivo = FichaPokemon._achar_arquivo(Path("Recursos") / "Visual" / "Icones" / "Diversos", nome)
        surf = FichaPokemon._carregar_surface(arquivo, (lado, lado), chave_extra="contain") if arquivo is not None else None
        self._cache_icones_diversos[chave] = surf
        return surf

    def sincronizar(self, jogadas: List[Dict[str, object]], selecionado_id: object | None) -> None:
        ordem_ids = []
        for indice, jogada in enumerate(jogadas or []):
            try:
                jid = int(jogada.get("id") or 0)
            except (TypeError, ValueError):
                continue
            ordem_ids.append(jid)
            item = self._itens.get(jid)
            if item is None:
                item = _PainelItem(jogada_id=jid, dados=dict(jogada))
                item.animacao = 0.0
                item.botao_fechar = Botao(
                    pygame.Rect(0, 0, 18, 18),
                    "X",
                    execute=None,
                    style={
                        "radius": 9,
                        "border_width": 0,
                        "bg": (220, 36, 36),
                        "bg_hover": (236, 54, 54),
                        "bg_pressed": (194, 28, 28),
                        "border": (220, 36, 36),
                        "border_hover": (236, 54, 54),
                        "hover_scale": 1.0,
                        "press_scale": 0.96,
                        "text_style": {
                            "size": 12,
                            "color": (255, 244, 244),
                            "hover_color": (255, 255, 255),
                            "align": "center",
                            "outline": True,
                            "outline_thickness": 2,
                            "outline_color": (40, 6, 10),
                            "shadow": False,
                        },
                    },
                )
                self._itens[jid] = item
            item.dados = dict(jogada)
            item.ordem = indice
            item.alvo_animacao = 1.0
            item.selecionado = (selecionado_id is not None and int(selecionado_id) == jid)

        ids_ativos = set(ordem_ids)
        for jid, item in list(self._itens.items()):
            if jid in ids_ativos:
                continue
            item.alvo_animacao = 0.0
            item.selecionado = False

    def atualizar(self, dt: float) -> None:
        velocidade = min(1.0, max(0.0, float(dt)) * 12.0)
        for jid, item in list(self._itens.items()):
            item.animacao += (item.alvo_animacao - item.animacao) * velocidade
            if item.alvo_animacao <= 0.0 and item.animacao <= 0.03:
                del self._itens[jid]

    def _itens_ordenados(self) -> List[_PainelItem]:
        return sorted(self._itens.values(), key=lambda item: (item.ordem, item.jogada_id))

    def _aplicar_layout(self, tela: pygame.Surface) -> None:
        visiveis = [item for item in self._itens_ordenados() if item.animacao > 0.01 or item.alvo_animacao > 0.0]
        if not visiveis:
            return
        largura = max(168, min(230, int(tela.get_width() * 0.17)))
        altura = 58
        gap = 10
        total_h = len(visiveis) * altura + max(0, len(visiveis) - 1) * gap
        topo = int((tela.get_height() - total_h) * 0.5)
        base_x = 16
        for indice, item in enumerate(visiveis):
            y = topo + indice * (altura + gap)
            deslocamento = int((1.0 - item.animacao) * (largura + 34))
            item.rect = pygame.Rect(base_x - deslocamento, y, largura, altura)
            item.rect_fechar = pygame.Rect(item.rect.right - 28, item.rect.y + 14, 16, 16)
            if item.botao_fechar is not None:
                item.botao_fechar.base_rect = pygame.Rect(item.rect.right - 30, item.rect.y + 12, 20, 20)
                item.botao_fechar.rect = pygame.Rect(item.botao_fechar.base_rect)
                item.rect_fechar = pygame.Rect(item.botao_fechar.rect)

    def recalcular_layout(self, tela: pygame.Surface) -> None:
        self._aplicar_layout(tela)

    def processar_eventos(self, eventos) -> None:
        self._hover_jogada_id = None
        mouse_pos = pygame.mouse.get_pos()
        for evento in eventos or []:
            if evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
                break
        for item in reversed(self._itens_ordenados()):
            if item.animacao <= 0.15:
                continue
            if item.rect.collidepoint(mouse_pos):
                self._hover_jogada_id = item.jogada_id
            if item.botao_fechar is not None and item.botao_fechar.rect.collidepoint(mouse_pos):
                self._hover_jogada_id = item.jogada_id
            for evento in eventos or []:
                if evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
                    continue
                if item.botao_fechar is not None and item.botao_fechar.rect.collidepoint(evento.pos):
                    self._comandos.append({"acao": "remover", "id": item.jogada_id})
                    return
                if item.rect.collidepoint(evento.pos):
                    self._comandos.append({"acao": "selecionar", "id": item.jogada_id})
                    return

    def coletar_comandos(self) -> List[Dict[str, object]]:
        comandos = list(self._comandos)
        self._comandos.clear()
        return comandos

    def retangulos_interativos(self) -> List[pygame.Rect]:
        return [pygame.Rect(item.rect) for item in self._itens_ordenados() if item.animacao > 0.15]

    def jogada_hover(self) -> int | None:
        return self._hover_jogada_id

    def desenhar(self, tela: pygame.Surface, dt: float) -> None:
        self.atualizar(dt)
        self._aplicar_layout(tela)

        for item in self._itens_ordenados():
            if item.animacao <= 0.01:
                continue
            fundo, borda, brilho = self._cor_item(item.dados, item.selecionado)

            base = pygame.Surface(item.rect.size, pygame.SRCALPHA)
            alpha_fundo = int(215 * item.animacao)
            pygame.draw.rect(base, (*fundo, alpha_fundo), base.get_rect(), border_radius=item.rect.height // 2)
            pygame.draw.rect(base, (255, 255, 255, int(245 * item.animacao)), base.get_rect(), 2, border_radius=item.rect.height // 2)
            if item.selecionado:
                pygame.draw.rect(base, (*brilho, int(88 * item.animacao)), base.get_rect().inflate(-10, -16), border_radius=item.rect.height // 2)
            tela.blit(base, item.rect.topleft)

            lado_img = item.rect.height - 16
            executor = item.dados.get("executor")
            img_poke = PokemonInventario.surface_pokemon(getattr(executor, "Dados", {}), lado_img) if executor is not None else None
            rect_poke = pygame.Rect(item.rect.x + 8, item.rect.y + 8, lado_img, lado_img)
            pygame.draw.circle(tela, (18, 24, 38), rect_poke.center, lado_img // 2)
            pygame.draw.circle(tela, brilho, rect_poke.center, lado_img // 2, 2)
            if img_poke is not None:
                tela.blit(img_poke, img_poke.get_rect(center=rect_poke.center))

            rect_icone = pygame.Rect(rect_poke.right + 8, item.rect.y + 11, lado_img - 6, lado_img - 6)
            icone = self._icone_ataque(item.dados, rect_icone.width)
            if icone is None:
                icone = self._icone_diverso("trocar" if item.dados.get("troca_reserva_id") else "mover", rect_icone.width)
            if icone is not None:
                tela.blit(icone, icone.get_rect(center=rect_icone.center))

            self._texto_nome.set_text(self._nome_item(item.dados))
            self._texto_nome.set_pos((rect_icone.right + 8, item.rect.y + 22))
            self._texto_nome.draw(tela)
            self._texto_aux.set_text(self._descricao_item(item.dados))
            self._texto_aux.set_pos((rect_icone.right + 8, item.rect.y + 39))
            self._texto_aux.draw(tela)

            if item.botao_fechar is not None:
                item.botao_fechar.base_rect = pygame.Rect(item.rect.right - 28, item.rect.y + 13, 18, 18)
                item.botao_fechar.rect = pygame.Rect(item.botao_fechar.base_rect)
                item.rect_fechar = pygame.Rect(item.botao_fechar.rect)
                item.botao_fechar.render(tela, [], dt, None)
