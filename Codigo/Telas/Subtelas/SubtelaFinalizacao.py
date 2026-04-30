from __future__ import annotations

from typing import Callable, Dict, List, Optional

import pygame

from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import NumeroVariavel, Texto
from Codigo.Telas.Subtelas.Subtela import Subtela


class SubtelaFinalizacao(Subtela):
    alpha_overlay = 190

    def __init__(self, itens: List[Dict[str, object]], rodadas_totais: int, vencedor: str = "", ao_continuar: Optional[Callable[[], None]] = None):
        super().__init__()
        self.Ativa = True
        self._itens = [dict(item) for item in list(itens or []) if isinstance(item, dict)]
        self._rodadas_totais = max(0, int(rodadas_totais or 0))
        self._vencedor = str(vencedor or "")
        self._ao_continuar = ao_continuar

        self._cache_tamanho = None
        self._rect = pygame.Rect(0, 0, 0, 0)
        self._botao_rect = pygame.Rect(0, 0, 0, 0)
        self._botao_continuar: Optional[Botao] = None

        self._titulo = Texto("Final da batalha", style={"size": 34, "color": (240, 246, 255), "align": "center", "outline": True, "outline_color": (8, 12, 20), "outline_thickness": 2})
        self._subtitulo = Texto("", style={"size": 18, "color": (190, 210, 228), "align": "center", "outline": True, "outline_color": (8, 12, 20), "outline_thickness": 2})
        self._resultado = Texto("", style={"size": 42, "color": (92, 226, 118), "align": "center", "outline": True, "outline_color": (8, 12, 20), "outline_thickness": 3})

        for item in self._itens:
            xp = int(item.get("xp_batalha", 0) or 0)
            duracao = 0.9 + min(1.6, xp / 120.0)
            item["texto_nome"] = Texto(str(item.get("nome") or "Pokemon"), style={"size": 18, "color": (234, 240, 252), "align": "center", "outline": True, "outline_color": (8, 12, 20), "outline_thickness": 2})
            item["texto_dano"] = Texto("", style={"size": 13, "color": (186, 199, 218), "align": "center", "outline": True, "outline_color": (8, 12, 20), "outline_thickness": 1})
            item["texto_abates"] = Texto("", style={"size": 13, "color": (186, 199, 218), "align": "center", "outline": True, "outline_color": (8, 12, 20), "outline_thickness": 1})
            item["texto_energia"] = Texto("", style={"size": 13, "color": (186, 199, 218), "align": "center", "outline": True, "outline_color": (8, 12, 20), "outline_thickness": 1})
            item["numero_xp"] = NumeroVariavel(
                xp,
                prefixo="XP +",
                duracao=duracao,
                style={
                    "size": 21,
                    "color": (92, 226, 118),
                    "align": "center",
                    "outline": True,
                    "outline_color": (8, 12, 20),
                    "outline_thickness": 2,
                    "shadow": False,
                },
            )

    def _garantir_layout(self, tela: pygame.Surface) -> None:
        tamanho = tuple(tela.get_size())
        if self._cache_tamanho == tamanho and self._botao_continuar is not None:
            return
        self._cache_tamanho = tamanho
        w, h = tamanho
        largura = min(1660, int(w * 0.94))
        altura = min(760, int(h * 0.84))
        self._rect = pygame.Rect((w - largura) // 2, (h - altura) // 2, largura, altura)
        self._botao_rect = pygame.Rect(self._rect.centerx - 110, self._rect.bottom - 70, 220, 46)
        if self._botao_continuar is None:
            self._botao_continuar = Botao(
                self._botao_rect,
                "Continuar",
                execute=lambda _jogo, _botao: self._continuar(),
                style={
                    "radius": 12,
                    "border_width": 2,
                    "bg": (34, 70, 46),
                    "bg_hover": (46, 94, 60),
                    "bg_pressed": (28, 56, 38),
                    "border": (170, 226, 178),
                    "border_hover": (218, 244, 222),
                    "text_style": {"size": 24, "outline_thickness": 2, "outline_color": (8, 12, 20), "shadow": False},
                },
            )
        else:
            self._botao_continuar.base_rect = pygame.Rect(self._botao_rect)
            self._botao_continuar.rect = pygame.Rect(self._botao_rect)

    def _continuar(self) -> None:
        if not self._xp_animado():
            return
        if callable(self._ao_continuar):
            self._ao_continuar()
        self.Ativa = False
        self.encerrada = True

    def _xp_animado(self) -> bool:
        return all(bool(item.get("numero_xp").finalizado) for item in self._itens if isinstance(item.get("numero_xp"), NumeroVariavel))

    def processar_eventos(self, _jogo, _eventos):
        return bool(self.Ativa)

    def atualizar(self, dt):
        for item in self._itens:
            numero = item.get("numero_xp")
            if isinstance(numero, NumeroVariavel):
                numero.atualizar(dt)

    def _desenhar_card(self, tela: pygame.Surface, item: Dict[str, object], rect: pygame.Rect) -> None:
        fundo = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(fundo, (18, 24, 34, 236), fundo.get_rect(), border_radius=14)
        pygame.draw.rect(fundo, (58, 88, 130), fundo.get_rect(), 2, border_radius=14)
        tela.blit(fundo, rect.topleft)

        nome = item.get("texto_nome")
        if isinstance(nome, Texto):
            nome.set_text(str(item.get("nome") or "Pokemon"))
            nome.set_pos((rect.centerx, rect.y + 28))
            nome.draw(tela)

        visual = item.get("visual")
        area_sprite = pygame.Rect(rect.x + 10, rect.y + 46, rect.width - 20, 82)
        if visual is not None:
            lado_sprite = max(56, min(76, rect.width - 20))
            frame = None
            if hasattr(visual, "_frame_atual"):
                frame = visual._frame_atual(lado_sprite)
            elif hasattr(visual, "_frame_atual_escalado"):
                frame = visual._frame_atual_escalado(None)
                if frame is not None:
                    escala = min(lado_sprite / max(1, frame.get_width()), 88 / max(1, frame.get_height()), 1.0)
                    frame = pygame.transform.smoothscale(frame, (max(1, int(frame.get_width() * escala)), max(1, int(frame.get_height() * escala))))
            if frame is not None:
                frame = frame.copy()
                if bool(item.get("morto", False)):
                    frame.fill((190, 190, 190, 255), special_flags=pygame.BLEND_RGBA_MULT)
                tela.blit(frame, frame.get_rect(center=area_sprite.center))

        numero_xp = item.get("numero_xp")
        if isinstance(numero_xp, NumeroVariavel):
            numero_xp.set_pos((rect.centerx, area_sprite.bottom + 14))
            numero_xp.draw(tela)

        dano = int(round(float(item.get("dano", 0.0) or 0.0)))
        abates = int(item.get("abates", 0) or 0)
        energia = int(round(float(item.get("energia_gasta", 0.0) or 0.0)))
        texto_dano = item.get("texto_dano")
        if isinstance(texto_dano, Texto):
            texto_dano.set_text(f"Dano {dano}")
            texto_dano.set_pos((rect.centerx, area_sprite.bottom + 42))
            texto_dano.draw(tela)
        texto_abates = item.get("texto_abates")
        if isinstance(texto_abates, Texto):
            texto_abates.set_text(f"Abates {abates}")
            texto_abates.set_pos((rect.centerx, area_sprite.bottom + 60))
            texto_abates.draw(tela)
        texto_energia = item.get("texto_energia")
        if isinstance(texto_energia, Texto):
            texto_energia.set_text(f"Energia {energia}")
            texto_energia.set_pos((rect.centerx, area_sprite.bottom + 78))
            texto_energia.draw(tela)

    def render(self, tela, eventos, dt, JOGO=None):
        _ = (dt, JOGO)
        self._garantir_layout(tela)

        pygame.draw.rect(tela, (10, 15, 24), self._rect, border_radius=18)
        pygame.draw.rect(tela, (102, 132, 168), self._rect, 2, border_radius=18)

        self._titulo.set_pos((self._rect.centerx, self._rect.y + 28))
        self._titulo.draw(tela)
        self._subtitulo.set_text(f"Rodadas: {self._rodadas_totais}")
        self._subtitulo.set_pos((self._rect.centerx, self._rect.y + 60))
        self._subtitulo.draw(tela)

        if self._vencedor:
            vitoria = self._vencedor == "jogador"
            self._resultado.set_text("Vitoria" if vitoria else "Derrota")
            self._resultado.set_style(color=(92, 226, 118) if vitoria else (238, 88, 88))
            self._resultado.set_pos((self._rect.centerx, self._rect.y + 106))
            self._resultado.draw(tela)

        area = pygame.Rect(self._rect.x + 16, self._rect.y + 146, self._rect.width - 32, self._rect.height - 236)
        total = max(1, len(self._itens))
        espaco_min = 12
        largura_setor = int((area.width - (espaco_min * (total + 1))) / total)
        largura_setor = max(96, min(154, largura_setor))
        espaco = max(espaco_min, int((area.width - (largura_setor * total)) / (total + 1)))
        total_largura = (largura_setor * total) + (espaco * (total + 1))
        origem_x = area.x + max(0, (area.width - total_largura) // 2) + espaco
        altura_card = max(210, area.height - 8)

        for indice, item in enumerate(self._itens):
            x = origem_x + (indice * (largura_setor + espaco))
            rect_card = pygame.Rect(x, area.y + 4, largura_setor, altura_card)
            self._desenhar_card(tela, item, rect_card)

        if self._botao_continuar is not None:
            self._botao_continuar.set_habilitado(self._xp_animado())
            self._botao_continuar.render(tela, eventos or [], dt, JOGO)

    @property
    def ativa(self):
        return bool(self.Ativa) and not self.encerrada
