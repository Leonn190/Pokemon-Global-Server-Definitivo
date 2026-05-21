from __future__ import annotations

from typing import Dict, List

import pygame

from Codigo.ModulosBatalha.FormatadorEventosLogBatalha import FormatadorEventosLogBatalha
from Codigo.ModulosGerais.Auxiliares import criar_botao_expandir, renderizar_botao_expandir
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Painel import PainelRolavel
from Codigo.Prefabs.Texto import Texto, TextoRegistroLog
from Codigo.Prefabs.Tooltip import Tooltip


class _ListaRegistrosLog(PainelRolavel):
    def __init__(self, rect):
        super().__init__(
            rect,
            area_real=(0, 0, rect[2], rect[3]),
            cor_fundo=(0, 0, 0, 0),
            cor_borda=(0, 0, 0, 0),
            borda=0,
            raio=14,
            velocidade_scroll=34,
        )
        self.Padding = 10
        self.Gap = 10
        self.Registros: list[dict[str, object]] = []
        self._assinatura_registros = None
        self._layout_registros: list[dict[str, object]] = []
        self._areas_tooltip: list[dict[str, object]] = []
        self._texto_medidor = TextoRegistroLog(
            rect=(0, 0, 10, 10),
            linhas=10,
            caracteres_por_linha=120,
            style={
                "size": 16,
                "color": (234, 240, 250),
                "outline": True,
                "outline_color": (7, 10, 18),
                "outline_thickness": 1,
                "shadow": False,
            },
        )

    def configurar_rect(self, rect):
        novo = pygame.Rect(rect)
        if self.rect == novo:
            return
        self.rect = novo
        self.atualizar_area_real()
        self.marcar_sujo()

    def definir_registros(self, registros: List[Dict[str, object]]):
        novos = [dict(item) for item in list(registros or []) if isinstance(item, dict)]
        assinatura = self._assinar_registros(novos)
        if self._assinatura_registros == assinatura:
            return
        self.Registros = novos
        self._assinatura_registros = assinatura
        self.atualizar_area_real()
        self.marcar_sujo()

    @staticmethod
    def _assinar_registros(registros: list[dict[str, object]]) -> tuple:
        assinatura = []
        for registro in registros:
            assinatura.append(
                (
                    str(registro.get("tipo") or ""),
                    int(registro.get("tick", 0) or 0),
                    str(registro.get("fase_label") or ""),
                    tuple(
                        (
                            str(segmento.get("texto") or ""),
                            str(segmento.get("atributo") or ""),
                            str(segmento.get("titulo_tooltip") or ""),
                            str(segmento.get("descricao_tooltip") or ""),
                        )
                        for segmento in list(registro.get("segmentos") or [])
                        if isinstance(segmento, dict)
                    ),
                )
            )
        return tuple(assinatura)

    def atualizar_area_real(self):
        largura = max(160, self.rect.width)
        altura = self.Padding
        self._layout_registros = []
        y = self.Padding
        for registro in self.Registros:
            altura_registro = self._altura_registro(registro)
            self._layout_registros.append({"registro": registro, "y": y, "altura": altura_registro})
            altura += altura_registro + self.Gap
            y += altura_registro + self.Gap
        altura = max(self.rect.height, altura + self.Padding - self.Gap)
        self.definir_area_real(largura, altura)

    def _largura_cartao(self) -> int:
        return max(120, self.rect.width - self.Padding * 2 - 8)

    def _altura_registro(self, registro: Dict[str, object]) -> int:
        largura = self._largura_cartao() - 28
        self._texto_medidor.Rect = pygame.Rect(0, 0, largura, 10)
        self._texto_medidor.set_segmentos([dict(item) for item in list(registro.get("segmentos") or []) if isinstance(item, dict)])
        altura_texto = max(20, self._texto_medidor.medir_altura())
        altura = 18 + altura_texto + 18
        return max(58, altura)

    def draw(self, tela):
        tela.fill((0, 0, 0, 0))
        self._areas_tooltip = []

        largura_cartao = self._largura_cartao()
        topo_visivel = max(0, int(self.ScrollY) - 80)
        base_visivel = max(0, int(self.ScrollY) + int(self.rect.height) + 80)

        for item_layout in self._layout_registros:
            registro = dict(item_layout.get("registro") or {})
            y = int(item_layout.get("y", 0) or 0)
            altura = int(item_layout.get("altura", 0) or 0)
            if (y + altura) < topo_visivel or y > base_visivel:
                continue
            rect = pygame.Rect(self.Padding, y, largura_cartao, altura)

            fundo = tuple(registro.get("cor_fundo") or (19, 28, 46, 228))
            borda = tuple(registro.get("cor_borda") or (96, 124, 176))
            faixa = tuple(registro.get("cor_faixa") or borda)

            cartao = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(cartao, fundo, cartao.get_rect(), border_radius=14)
            pygame.draw.rect(cartao, borda, cartao.get_rect(), 2, border_radius=14)
            pygame.draw.rect(cartao, faixa, pygame.Rect(0, 0, 6, rect.height), border_radius=14)
            tela.blit(cartao, rect.topleft)

            self._texto_medidor.Rect = pygame.Rect(rect.x + 16, rect.y + 14, rect.width - 32, rect.height - 26)
            self._texto_medidor.set_segmentos([dict(item) for item in list(registro.get("segmentos") or []) if isinstance(item, dict)])
            self._texto_medidor.draw(tela)
            for area in self._texto_medidor.obter_areas_tooltip():
                rect_area = area.get("rect")
                if not isinstance(rect_area, pygame.Rect):
                    continue
                self._areas_tooltip.append(
                    {
                        "rect": pygame.Rect(rect_area),
                        "tooltip": str(area.get("tooltip") or ""),
                        "titulo": str(area.get("titulo") or ""),
                        "descricao": str(area.get("descricao") or ""),
                    }
                )

    def tooltip_no_mouse(self, mouse_pos) -> dict[str, object] | None:
        if not self.rect.collidepoint(mouse_pos):
            return None
        for area in reversed(self._areas_tooltip):
            rect_local = area.get("rect")
            if not isinstance(rect_local, pygame.Rect):
                continue
            rect_tela = pygame.Rect(
                self.rect.x + rect_local.x - self.ScrollX,
                self.rect.y + rect_local.y - self.ScrollY,
                rect_local.width,
                rect_local.height,
            )
            if rect_tela.collidepoint(mouse_pos) and rect_tela.colliderect(self.rect):
                saida = dict(area)
                saida["rect_tela"] = rect_tela
                return saida
        return None


class VisualizadorLog:
    def __init__(self, controlador=None) -> None:
        self._controlador = controlador
        self._aberto = False
        self._animacao = 0.0
        self._cache_tamanho = None
        self._rect_painel = pygame.Rect(0, 0, 0, 0)
        self._rect_tab = pygame.Rect(0, 0, 0, 0)
        self._rodada_selecionada = 1
        self._rodada_manual = False
        self._estado_logs: Dict[str, object] = {}
        self._formatador = FormatadorEventosLogBatalha()

        self._texto_titulo = Texto(
            "Rodada 1",
            style={
                "size": 21,
                "align": "midleft",
                "color": (244, 248, 255),
                "outline": True,
                "outline_color": (6, 10, 18),
                "outline_thickness": 2,
                "shadow": False,
            },
        )
        self._texto_subtitulo = Texto(
            "",
            style={
                "size": 13,
                "align": "topleft",
                "color": (172, 188, 214),
                "outline": True,
                "outline_color": (6, 10, 18),
                "outline_thickness": 1,
                "shadow": False,
            },
        )
        self._tooltip = Tooltip("", largura_max=360, padding=10, raio=12, style={"size": 14})
        self._lista = _ListaRegistrosLog((0, 0, 10, 10))

        estilo_seta = {
            "radius": 9,
            "border_width": 2,
            "bg": (25, 38, 60),
            "bg_hover": (39, 58, 88),
            "bg_pressed": (16, 26, 42),
            "border": (126, 156, 208),
            "border_hover": (220, 236, 255),
            "hover_scale": 1.02,
            "press_scale": 0.98,
            "text_style": {
                "size": 20,
                "color": (245, 248, 255),
                "align": "center",
                "outline": True,
                "outline_color": (6, 10, 18),
                "outline_thickness": 2,
                "shadow": False,
            },
        }
        self._botao_prev = Botao(pygame.Rect(0, 0, 34, 34), "<", execute=lambda _jogo, _botao: self._navegar(-1), style=estilo_seta)
        self._botao_next = Botao(pygame.Rect(0, 0, 34, 34), ">", execute=lambda _jogo, _botao: self._navegar(1), style=estilo_seta)
        self._botao_tab = criar_botao_expandir(execute=lambda _jogo, _botao: self._alternar(), rect=(0, 0, 44, 118), style={"radius": 12, "hover_scale": 1.01})

    def _alternar(self):
        self._aberto = not self._aberto

    def _navegar(self, delta: int):
        max_rodada = max(1, int(self._estado_logs.get("ultimo_turno_com_log", 0) or 0))
        self._rodada_selecionada = max(1, min(max_rodada, int(self._rodada_selecionada) + int(delta)))
        self._rodada_manual = True

    def _sincronizar_estado(self):
        if self._controlador is None or not hasattr(self._controlador, "estado_visualizador_logs"):
            self._estado_logs = {"ultimo_turno_com_log": 0, "replay": {}}
            return
        self._estado_logs = dict(self._controlador.estado_visualizador_logs() or {})
        replay = dict(self._estado_logs.get("replay") or {})
        turno_replay = int(replay.get("turno_atual", 0) or 0)
        ultimo_turno = max(1, int(self._estado_logs.get("ultimo_turno_com_log", 0) or 0))
        rodada_atual = max(1, int(self._estado_logs.get("rodada_atual", ultimo_turno) or ultimo_turno))
        if bool(replay.get("ativo", False)) and turno_replay > 0:
            self._rodada_selecionada = turno_replay
            self._rodada_manual = False
        elif not self._rodada_manual or int(self._rodada_selecionada or 1) > ultimo_turno:
            self._rodada_selecionada = max(1, min(ultimo_turno, rodada_atual - 1 if rodada_atual > 1 else 1))

        log = self._controlador.obter_log_publico(self._rodada_selecionada) if hasattr(self._controlador, "obter_log_publico") else None
        registros = self._formatador.registros_rodada(self._rodada_selecionada, log, replay)
        self._lista.definir_registros(registros)

    def _atualizar_layout(self, tela: pygame.Surface, dt: float):
        w, h = tela.get_size()
        alvo = 1.0 if self._aberto else 0.0
        self._animacao += (alvo - self._animacao) * min(1.0, max(0.0, float(dt)) * 11.0)
        if abs(self._animacao - alvo) <= 0.002:
            self._animacao = alvo

        largura = max(277, min(356, int(w * 0.225)) - 5)
        altura = max(330, min(int(h * 0.65), h - 40) - 12)
        margem = 16
        y = max(18, (h - altura) // 2)
        x_aberto = w - largura - margem
        x_fechado = w + 8
        x = int(x_fechado + (x_aberto - x_fechado) * self._animacao)

        self._rect_painel = pygame.Rect(x, y, largura, altura)
        tab_largura = 44
        tab_altura = 116
        tab_x = self._rect_painel.x - tab_largura + 3
        tab_y = y + 28
        self._rect_tab = pygame.Rect(tab_x, tab_y, tab_largura, tab_altura)

        self._botao_prev.base_rect = pygame.Rect(self._rect_painel.right - 90, self._rect_painel.y + 14, 34, 34)
        self._botao_prev.rect = pygame.Rect(self._botao_prev.base_rect)
        self._botao_next.base_rect = pygame.Rect(self._rect_painel.right - 48, self._rect_painel.y + 14, 34, 34)
        self._botao_next.rect = pygame.Rect(self._botao_next.base_rect)

        conteudo_rect = pygame.Rect(self._rect_painel.x + 12, self._rect_painel.y + 64, self._rect_painel.width - 24, self._rect_painel.height - 78)
        self._lista.configurar_rect(conteudo_rect)

        ultimo_turno = max(1, int(self._estado_logs.get("ultimo_turno_com_log", 0) or 0))
        self._botao_prev.set_habilitado(self._rodada_selecionada > 1)
        self._botao_next.set_habilitado(self._rodada_selecionada < ultimo_turno)

    def retangulos_interativos(self) -> List[pygame.Rect]:
        saida = [pygame.Rect(self._rect_tab)] if self._rect_tab.width > 0 else []
        if self._animacao > 0.04:
            saida.extend([
                pygame.Rect(self._rect_painel),
                pygame.Rect(self._botao_prev.rect),
                pygame.Rect(self._botao_next.rect),
                pygame.Rect(self._lista.rect),
            ])
        return saida

    def captura_scroll(self, mouse_pos) -> bool:
        if not isinstance(mouse_pos, (tuple, list)) or len(mouse_pos) < 2:
            return False
        ponto = (int(mouse_pos[0]), int(mouse_pos[1]))
        if self._rect_tab.collidepoint(ponto):
            return True
        if self._animacao > 0.04 and self._rect_painel.collidepoint(ponto):
            return True
        return False

    def preparar(self, tela: pygame.Surface, dt: float = 0.0) -> None:
        self._sincronizar_estado()
        self._atualizar_layout(tela, dt)

    def desenhar(self, tela: pygame.Surface, eventos, dt: float = 0.0) -> None:
        self.preparar(tela, dt)

        renderizar_botao_expandir(self._botao_tab, tela, eventos or [], dt, self._rect_tab, self._aberto, None)

        if self._animacao <= 0.02:
            return

        alpha = int(242 * max(0.0, min(1.0, self._animacao)))
        painel = pygame.Surface(self._rect_painel.size, pygame.SRCALPHA)
        pygame.draw.rect(painel, (10, 16, 28, alpha), painel.get_rect(), border_radius=18)
        pygame.draw.rect(painel, (114, 144, 196, alpha), painel.get_rect(), 2, border_radius=18)
        pygame.draw.line(painel, (52, 74, 110, alpha), (12, 60), (self._rect_painel.width - 12, 60), 1)
        tela.blit(painel, self._rect_painel.topleft)

        self._texto_titulo.set_text(f"Rodada {int(self._rodada_selecionada or 1)}")
        self._texto_titulo.set_pos((self._rect_painel.x + 16, self._rect_painel.y + 31))
        self._texto_titulo.draw(tela)

        replay = dict(self._estado_logs.get("replay") or {})
        if bool(replay.get("ativo", False)) and int(replay.get("turno_atual", 0) or 0) == int(self._rodada_selecionada):
            tick_atual = max(0, int(replay.get("tick_atual", 0) or 0))
            tick_final = max(0, int(replay.get("tick_final", 0) or 0))
            self._texto_subtitulo.set_text(f"Reproduzindo ações: {tick_atual}/{tick_final}")
        else:
            self._texto_subtitulo.set_text("Histórico da batalha")
        self._texto_subtitulo.set_pos((self._rect_painel.x + 16, self._rect_painel.y + 44))
        self._texto_subtitulo.draw(tela)

        self._botao_prev.render(tela, eventos or [], dt, None)
        self._botao_next.render(tela, eventos or [], dt, None)
        self._lista.render(tela, eventos or [], dt, None)

        tooltip = self._lista.tooltip_no_mouse(pygame.mouse.get_pos())
        if tooltip:
            titulo = str(tooltip.get("titulo") or "").strip()
            descricao = str(tooltip.get("descricao") or tooltip.get("tooltip") or "").strip()
            self._tooltip.definir_conteudo(titulo=titulo, descricao=descricao)
            rect_tela = tooltip.get("rect_tela")
            if isinstance(rect_tela, pygame.Rect):
                self._tooltip.definir_area(rect_tela)
                self._tooltip.definir_posicao_fixa((rect_tela.right + 10, rect_tela.top - 6))
            self._tooltip.render(tela, mouse_pos=pygame.mouse.get_pos(), forcar=True)
