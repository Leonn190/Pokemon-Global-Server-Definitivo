from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional
import math

import pygame

from Codigo.ModulosBatalha.MontadorJogada import MontadorJogada
from Codigo.Paineis.FichaPokemonBatalha import FichaPokemonBatalha
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Fluxos import Fluxo, FluxoArea, FluxoTiro


class ElementosHudBatalha:
    def __init__(self, controlador_batalha=None, camera=None, ao_fugir: Optional[Callable[[], None]] = None) -> None:
        self._ao_fugir = ao_fugir
        self._controlador = controlador_batalha
        self._camera = camera
        self._botao_fugir: Optional[Botao] = None
        self._icone_fugir: Optional[pygame.Surface] = None
        self._cache_tamanho: Optional[tuple[int, int]] = None
        self._fuga_pressao = 0.0
        self._fuga_alvo = 8.0
        self._fuga_taxa_clique = 1.65
        self._fuga_taxa_decay = 0.3
        self._fuga_disparada = False
        self._ficha = FichaPokemonBatalha()
        self._anim_ficha = 0.0
        self._pokemon_exibido = None
        self._ataque_selecionado: dict | None = None
        self._botao_preparar: Optional[Botao] = None
        self._botao_pronto: Optional[Botao] = None
        self._mira_ativa = False
        self._mira_inicio = (0.0, 0.0)
        self._mira_fim = (0.0, 0.0)
        self._mira_intensidade = 0.0
        self._alvo_selecionado = None
        self._fluxo_mira = Fluxo("seta")
        self._fluxo_tiro = FluxoTiro()
        self._fluxo_area = FluxoArea()
        self._fluxos_preparados: list[dict] = []
        self._montador = MontadorJogada()
        self._consumo_previsto = 0.0
        self._consumo_bloqueado = False
        self._mira_valida = False

    def _carregar_icone(self, lado: int) -> Optional[pygame.Surface]:
        caminho = Path("Recursos") / "Visual" / "Icones" / "Diversos" / "fugir.png"
        if not caminho.exists():
            return None
        try:
            img = pygame.image.load(str(caminho)).convert_alpha()
            return pygame.transform.smoothscale(img, (lado, lado))
        except pygame.error:
            return None

    def _garantir_layout(self, tela: pygame.Surface) -> None:
        tamanho = tuple(tela.get_size())
        if self._cache_tamanho == tamanho and self._botao_fugir is not None:
            return
        self._cache_tamanho = tamanho
        w, h = tamanho
        lado = max(56, min(80, int(min(w, h) * 0.085)))
        margem = max(16, int(lado * 0.25))
        rect = pygame.Rect(margem, h - lado - margem, lado, lado)
        self._botao_fugir = Botao(
            rect,
            "",
            execute=lambda _jogo, _botao: self._pressionar_fuga(),
            style={
                "radius": max(8, int(lado * 0.20)),
                "border_width": 2,
                "bg": (26, 33, 44),
                "bg_hover": (38, 50, 67),
                "bg_pressed": (16, 23, 34),
                "border": (147, 176, 214),
                "border_hover": (214, 230, 255),
                "text_style": {"size": 1, "outline_thickness": 0, "shadow": False},
            },
        )
        self._icone_fugir = self._carregar_icone(max(24, int(lado * 0.68)))
        bw = max(124, int(lado * 2.0))
        bh = max(36, int(lado * 0.56))
        bx = w - bw - margem
        by = h - (bh * 2) - margem - 8
        estilo = {
            "radius": 8,
            "border_width": 2,
            "bg": (24, 40, 58),
            "bg_hover": (34, 60, 84),
            "bg_pressed": (16, 29, 44),
            "border": (118, 150, 188),
            "border_hover": (214, 230, 255),
            "text_style": {"size": 18, "outline_thickness": 1, "shadow": False},
        }
        self._botao_preparar = Botao(pygame.Rect(bx, by, bw, bh), "Preparar", execute=lambda _j, _b: self._preparar_jogada(), style=estilo)
        self._botao_pronto = Botao(pygame.Rect(bx, by + bh + 8, bw, bh), "Pronto", execute=lambda _j, _b: self._finalizar_pronto(), style=estilo)

    def _pressionar_fuga(self) -> None:
        self._fuga_pressao = min(self._fuga_alvo, self._fuga_pressao + self._fuga_taxa_clique)
        if (not self._fuga_disparada) and self._fuga_pressao >= self._fuga_alvo:
            self._fuga_disparada = True
            if callable(self._ao_fugir):
                self._ao_fugir()

    def _atualizar_fuga(self, dt: float) -> None:
        if self._fuga_disparada:
            return
        fator = max(0.0, min(1.0, float(dt) * 60.0))
        queda = self._fuga_taxa_decay * fator
        self._fuga_pressao = max(0.0, self._fuga_pressao - queda)

    def _desenhar_overlay_fuga(self, tela: pygame.Surface) -> None:
        if self._fuga_pressao <= 0.01:
            return
        t = max(0.0, min(1.0, self._fuga_pressao / max(0.01, self._fuga_alvo)))
        overlay = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(160 * t)))
        tela.blit(overlay, (0, 0))

    def _processar_selecao(self, eventos: List[pygame.event.Event]):
        if self._controlador is None or self._camera is None:
            return
        poke_sel = getattr(self._controlador, "PokemonSelecionado", None)
        estilo = self._estilo_corrente()
        for ev in eventos or []:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self._botao_preparar is not None and self._botao_preparar.rect.collidepoint(ev.pos):
                    continue
                if self._botao_pronto is not None and self._botao_pronto.rect.collidepoint(ev.pos):
                    continue
                if poke_sel is not None and estilo in ("movimento", "tiro", "area"):
                    cx, cy = poke_sel.centro_tela(self._camera)
                    r = poke_sel.raio_px(self._camera)
                    if (ev.pos[0] - cx) ** 2 + (ev.pos[1] - cy) ** 2 <= r * r:
                        continue
                self._controlador.selecionar_por_mouse(ev.pos, self._camera)
                break

    @staticmethod
    def _normalizar_estilo(valor: object) -> str:
        t = str(valor or "").strip().lower()
        mapa = {"movi": "movimento", "mov": "movimento"}
        return mapa.get(t, t)

    @staticmethod
    def _parse_num(valor: object, padrao: float = 0.0) -> float:
        try:
            return float(str(valor).replace(",", "."))
        except Exception:
            return float(padrao)

    def _ataque_info(self) -> dict:
        return dict(self._ataque_selecionado) if isinstance(self._ataque_selecionado, dict) else {}

    def _estilo_corrente(self) -> str:
        info = self._ataque_info()
        estilo = self._normalizar_estilo(info.get("Estilo") or info.get("estilo"))
        return estilo or "movimento"

    def _custo_corrente(self) -> float:
        estilo = self._estilo_corrente()
        if estilo == "movimento":
            sel = getattr(self._controlador, "PokemonSelecionado", None)
            if sel is None:
                return 0.0
            return max(1.0, float(sel.EnergiaMax) * 0.25)
        info = self._ataque_info()
        return max(0.0, self._parse_num(info.get("Custo") or info.get("custo"), 0.0))

    def _id_combatente(self, poke) -> int:
        return int(id(poke)) if poke is not None else -1

    def _energia_disponivel_reservada(self, poke) -> float:
        if poke is None:
            return 0.0
        reservada = self._montador.custo_reservado(self._id_combatente(poke))
        return max(0.0, float(poke.Energia) - reservada)

    def _iniciar_mira(self, poke, mouse_pos):
        self._mira_ativa = True
        self._mira_valida = False
        self._mira_inicio = poke.centro_tela(self._camera)
        self._mira_fim = (float(mouse_pos[0]), float(mouse_pos[1]))

    def _atualizar_mira(self, mouse_pos):
        self._mira_fim = (float(mouse_pos[0]), float(mouse_pos[1]))
        dx = self._mira_fim[0] - self._mira_inicio[0]
        dy = self._mira_fim[1] - self._mira_inicio[1]
        dist = math.hypot(dx, dy)
        self._mira_intensidade = max(0.0, min(1.0, dist / 220.0))

    def _processar_mira(self, eventos: List[pygame.event.Event], dt: float) -> None:
        _ = dt
        poke = getattr(self._controlador, "PokemonSelecionado", None)
        if poke is None:
            self._mira_ativa = False
            return
        estilo = self._estilo_corrente()
        exige_direcao = estilo in ("movimento", "tiro", "area")
        for ev in eventos or []:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and exige_direcao:
                cx, cy = poke.centro_tela(self._camera)
                r = poke.raio_px(self._camera)
                if (ev.pos[0] - cx) ** 2 + (ev.pos[1] - cy) ** 2 <= r * r:
                    self._iniciar_mira(poke, ev.pos)
            elif ev.type == pygame.MOUSEMOTION and self._mira_ativa:
                self._atualizar_mira(ev.pos)
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self._mira_ativa:
                self._atualizar_mira(ev.pos)
                self._mira_ativa = False
                self._mira_valida = math.hypot(self._mira_fim[0] - self._mira_inicio[0], self._mira_fim[1] - self._mira_inicio[1]) > 2.0
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and estilo == "alvo":
                for alvo in (self._controlador.PokemonsAliados + self._controlador.PokemonsInimigos):
                    cx, cy = alvo.centro_tela(self._camera)
                    r = alvo.raio_px(self._camera)
                    if (ev.pos[0] - cx) ** 2 + (ev.pos[1] - cy) ** 2 <= r * r:
                        self._alvo_selecionado = alvo
                        break

    def _cor_intensidade(self, t: float) -> tuple[int, int, int]:
        t = max(0.0, min(1.0, t))
        if t < 0.5:
            k = t / 0.5
            return (int(70 + 185 * k), 235, 90)
        k = (t - 0.5) / 0.5
        return (255, int(235 - 190 * k), 75)

    def _desenhar_fluxos(self, tela: pygame.Surface, dt: float) -> None:
        self._fluxo_mira.atualizar(dt)
        for fluxo in self._fluxos_preparados:
            estilo = str(fluxo.get("estilo") or "")
            inicio = fluxo.get("visual_inicio") or (0, 0)
            fim = fluxo.get("visual_fim") or inicio
            if estilo in ("movimento", "movi", "tiro"):
                if estilo == "tiro":
                    self._fluxo_tiro.desenhar(
                        tela,
                        inicio,
                        float(fluxo.get("direcao_angulo", 0.0)),
                        int(getattr(self._camera, "TilePx", 40) or 40),
                        float(fluxo.get("alcance_tiro", 4.0)),
                        float(fluxo.get("grossura_tiro", 1.0)),
                        float(fluxo.get("diametro_tiro", 0.0)),
                        alpha=62,
                    )
                else:
                    self._fluxo_mira.desenhar(
                        tela,
                        inicio,
                        fim,
                        alpha=70,
                        alpha_trilha=20,
                        cor_principal=fluxo.get("cor_principal", (200, 220, 255)),
                        cor_secundaria=fluxo.get("cor_secundaria", (230, 240, 255)),
                        animado=False,
                        fase_tempo=float(fluxo.get("fase_tempo", 0.0)),
                    )
            elif estilo == "alvo":
                self._fluxo_mira.desenhar(
                    tela,
                    inicio,
                    fim,
                    alpha=60,
                    alpha_trilha=18,
                    cor_principal=fluxo.get("cor_principal", (190, 220, 255)),
                    cor_secundaria=fluxo.get("cor_secundaria", (250, 255, 255)),
                    animado=False,
                    fase_tempo=float(fluxo.get("fase_tempo", 0.0)),
                )
            elif estilo == "area":
                self._fluxo_area.desenhar(
                    tela,
                    inicio,
                    float(fluxo.get("direcao_angulo", 0.0)),
                    float(fluxo.get("raio_pokemon_px", 1.0)),
                    int(getattr(self._camera, "TilePx", 40) or 40),
                    float(fluxo.get("base_area", 0.3)),
                    float(fluxo.get("altura_area", 0.55)),
                    float(fluxo.get("teto_area", 0.0)),
                    alpha=72,
                )

        estilo = self._estilo_corrente()
        if estilo == "alvo":
            for poke in (self._controlador.PokemonsAliados + self._controlador.PokemonsInimigos):
                c = poke.centro_tela(self._camera)
                r = poke.raio_px(self._camera) + 4
                a = int(90 + 80 * abs(math.sin(pygame.time.get_ticks() / 240.0)))
                brilho = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
                pygame.draw.circle(brilho, (255, 232, 90, a), (brilho.get_width() // 2, brilho.get_height() // 2), r, 3)
                tela.blit(brilho, brilho.get_rect(center=c))
            if self._alvo_selecionado is not None and getattr(self._controlador, "PokemonSelecionado", None) is not None:
                self._fluxo_mira.desenhar(
                    tela,
                    self._controlador.PokemonSelecionado.centro_tela(self._camera),
                    self._alvo_selecionado.centro_tela(self._camera),
                    cor_principal=(220, 230, 255),
                    cor_secundaria=(255, 255, 255),
                    alpha=120,
                )

        if self._mira_ativa or self._mira_intensidade > 0.001:
            cor = self._cor_intensidade(self._mira_intensidade)
            if estilo == "tiro":
                info = self._ataque_info()
                self._fluxo_tiro.desenhar(
                    tela,
                    self._mira_inicio,
                    math.atan2(self._mira_fim[1] - self._mira_inicio[1], self._mira_fim[0] - self._mira_inicio[0]),
                    int(getattr(self._camera, "TilePx", 40) or 40),
                    self._parse_num(info.get("Alcance Tiro"), 4.0),
                    self._parse_num(info.get("Grossura Tiro"), 1.0),
                    self._parse_num(info.get("Diametro Tiro"), 0.0),
                )
            elif estilo == "area":
                info = self._ataque_info()
                poke = getattr(self._controlador, "PokemonSelecionado", None)
                if poke is not None:
                    ang = math.atan2(self._mira_fim[1] - self._mira_inicio[1], self._mira_fim[0] - self._mira_inicio[0])
                    self._fluxo_area.desenhar(
                        tela,
                        self._mira_inicio,
                        ang,
                        poke.raio_px(self._camera),
                        int(getattr(self._camera, "TilePx", 40) or 40),
                        self._parse_num(info.get("Base Area"), 30.0) / 100.0,
                        self._parse_num(info.get("Altura Area"), 55.0) / 100.0,
                        self._parse_num(info.get("Teto Area"), 0.0) / 100.0,
                    )
            else:
                self._fluxo_mira.desenhar(tela, self._mira_inicio, self._mira_fim, cor_principal=cor, cor_secundaria=(245, 250, 255))

    def _preparar_jogada(self) -> None:
        poke = getattr(self._controlador, "PokemonSelecionado", None)
        if poke is None or self._consumo_bloqueado:
            return
        estilo = self._estilo_corrente()
        custo = self._custo_corrente()
        if custo > self._energia_disponivel_reservada(poke) + 0.001:
            return
        if estilo in ("movimento", "tiro", "area") and not self._mira_valida:
            return
        if estilo == "alvo" and self._alvo_selecionado is None:
            return
        ang = math.atan2(self._mira_fim[1] - self._mira_inicio[1], self._mira_fim[0] - self._mira_inicio[0]) if self._mira_valida else 0.0
        info = self._ataque_info()
        cor_atual = self._cor_intensidade(self._mira_intensidade)
        registro = {
            "combatente_id": self._id_combatente(poke),
            "pokemon": getattr(poke, "Nome", "Pokemon"),
            "estilo": estilo,
            "ataque": dict(info),
            "custo": float(custo),
            "direcao_angulo": float(ang),
            "intensidade": float(self._mira_intensidade),
            "alvo": getattr(self._alvo_selecionado, "Nome", None),
            "alcance_tiro": self._parse_num(info.get("Alcance Tiro"), 4.0),
            "grossura_tiro": self._parse_num(info.get("Grossura Tiro"), 1.0),
            "diametro_tiro": self._parse_num(info.get("Diametro Tiro"), 0.0),
            "base_area": self._parse_num(info.get("Base Area"), 30.0) / 100.0,
            "altura_area": self._parse_num(info.get("Altura Area"), 55.0) / 100.0,
            "teto_area": self._parse_num(info.get("Teto Area"), 0.0) / 100.0,
            "fase_tempo": float(self._fluxo_mira.tempo),
            "cor_principal": cor_atual,
            "cor_secundaria": (245, 250, 255),
            "raio_pokemon_px": float(poke.raio_px(self._camera)),
        }
        self._montador.adicionar(registro)
        visual = dict(registro)
        visual["visual_inicio"] = tuple(self._mira_inicio if self._mira_valida else poke.centro_tela(self._camera))
        visual["visual_fim"] = tuple(self._mira_fim if self._mira_valida else (self._alvo_selecionado.centro_tela(self._camera) if self._alvo_selecionado is not None else poke.centro_tela(self._camera)))
        self._fluxos_preparados.append(visual)
        self._mira_intensidade = 0.0
        self._mira_valida = False
        self._mira_inicio = (0.0, 0.0)
        self._mira_fim = (0.0, 0.0)
        self._alvo_selecionado = None

    def _finalizar_pronto(self) -> None:
        for acao in self._montador.acoes:
            combatente_id = int(acao.get("combatente_id", -1) or -1)
            custo = max(0.0, float(acao.get("custo", 0.0) or 0.0))
            for poke in (self._controlador.PokemonsAliados + self._controlador.PokemonsInimigos):
                if self._id_combatente(poke) == combatente_id:
                    poke.Energia = max(0.0, float(poke.Energia) - custo)
                    break
        self._montador.limpar()
        self._fluxos_preparados = []
        self._alvo_selecionado = None
        self._mira_ativa = False
        self._mira_valida = False
        self._mira_intensidade = 0.0
        self._mira_inicio = (0.0, 0.0)
        self._mira_fim = (0.0, 0.0)

    def _atualizar_animacao_ficha(self, dt: float):
        selecionado = getattr(self._controlador, "PokemonSelecionado", None)
        if selecionado is not None:
            if self._pokemon_exibido is not None and selecionado is not self._pokemon_exibido:
                self._ataque_selecionado = None
                self._alvo_selecionado = None
                self._mira_intensidade = 0.0
            self._pokemon_exibido = selecionado
        alvo = 1.0 if selecionado is not None else 0.0
        vel = max(0.01, float(dt) * 8.0)
        self._anim_ficha += (alvo - self._anim_ficha) * min(1.0, vel)
        if self._anim_ficha <= 0.01 and selecionado is None:
            self._pokemon_exibido = None

    def desenhar(self, tela: pygame.Surface, eventos: List[pygame.event.Event], dt: float = 0.0) -> None:
        self._garantir_layout(tela)
        self._processar_mira(eventos or [], dt)
        self._processar_selecao(eventos or [])
        self._atualizar_animacao_ficha(dt)
        self._atualizar_fuga(dt)
        self._consumo_previsto = self._custo_corrente()
        poke = getattr(self._controlador, "PokemonSelecionado", None)
        energia_disp = self._energia_disponivel_reservada(poke)
        self._consumo_bloqueado = bool(poke is not None and self._consumo_previsto > energia_disp + 0.001)
        self._ficha.definir_contexto_jogada(self._consumo_previsto, self._consumo_bloqueado, energia_base_previsao=energia_disp if poke is not None else None)
        self._desenhar_fluxos(tela, dt)
        if self._botao_fugir is not None:
            self._botao_fugir.render(tela, eventos or [], dt, None)
            if self._icone_fugir is not None:
                rect = self._icone_fugir.get_rect(center=self._botao_fugir.rect.center)
                tela.blit(self._icone_fugir, rect)
        if self._botao_preparar is not None:
            self._botao_preparar.set_habilitado(not self._consumo_bloqueado)
            self._botao_preparar.render(tela, eventos or [], dt, None)
        if self._botao_pronto is not None:
            self._botao_pronto.render(tela, eventos or [], dt, None)
        ataque_ui = self._ficha.render(tela, self._pokemon_exibido, self._anim_ficha, eventos or [], dt)
        if isinstance(ataque_ui, dict):
            antigo = str((self._ataque_selecionado or {}).get("Ataque") or (self._ataque_selecionado or {}).get("Nome") or (self._ataque_selecionado or {}).get("nome") or "")
            novo = str(ataque_ui.get("Ataque") or ataque_ui.get("Nome") or ataque_ui.get("nome") or "")
            self._ataque_selecionado = ataque_ui
            if antigo != novo:
                self._mira_ativa = False
                self._mira_valida = False
                self._mira_intensidade = 0.0
                self._alvo_selecionado = None
        self._desenhar_overlay_fuga(tela)
