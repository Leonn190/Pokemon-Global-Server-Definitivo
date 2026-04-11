from __future__ import annotations

import math
from typing import List, Optional

import pygame

from Codigo.ModulosBatalha.MontadorJogada import MontadorJogada
from Codigo.Prefabs.Fluxos import Fluxo, FluxoArea, FluxoTiro


class ControladorFluxos:
    def __init__(self, controlador_batalha, camera) -> None:
        self._controlador = controlador_batalha
        self._camera = camera
        self._montador = MontadorJogada()
        self._fluxo_setas = Fluxo(estilo="seta")
        self._fluxo_ligacao = Fluxo(estilo="faixa")
        self._fluxo_tiro = FluxoTiro()
        self._fluxo_area = FluxoArea()
        self._mira_ativa: Optional[dict] = None
        self._preparo_atual: Optional[dict] = None
        self._preparadas_visuais: List[dict] = []
        self._alvo_selecionado = None
        self._id_mira = 0
        self._clique_pendente: Optional[dict] = None
        self._limiar_arrasto_px = 12.0

    def _id_combatente(self, pokemon) -> str:
        if pokemon is None:
            return ""
        dados = getattr(pokemon, "Dados", {}) if hasattr(pokemon, "Dados") else {}
        bruto = None
        if isinstance(dados, dict):
            bruto = dados.get("uid") or dados.get("id") or dados.get("ID")
        if bruto in (None, ""):
            bruto = getattr(pokemon, "Uid", None) or getattr(pokemon, "Id", None)
        if bruto in (None, ""):
            bruto = f"obj:{id(pokemon)}"
        return str(bruto)

    def _estilo_ataque(self, ataque: Optional[dict]) -> str:
        if not isinstance(ataque, dict):
            return "movimento"
        estilo = str(ataque.get("Estilo") or ataque.get("estilo") or ataque.get("TipoAcao") or "").strip().lower()
        mapa = {
            "movimento": "movimento",
            "mover": "movimento",
            "dash": "movimento",
            "tiro": "tiro",
            "projetil": "tiro",
            "status": "status",
            "buff": "status",
            "area": "area",
            "aoe": "area",
            "alvo": "alvo",
            "target": "alvo",
        }
        return mapa.get(estilo, "status")

    @staticmethod
    def _numero(valor, padrao=0.0) -> float:
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(padrao)

    def _selecionado_aliado(self):
        selecionado = getattr(self._controlador, "PokemonSelecionado", None)
        if selecionado is None:
            return None
        if not getattr(self._controlador, "pokemon_eh_aliado", lambda _p: False)(selecionado):
            return None
        return selecionado

    def _custo_ataque(self, pokemon, ataque: Optional[dict], estilo: str) -> float:
        if estilo == "movimento" and not ataque:
            return max(1.0, float(getattr(pokemon, "EnergiaMax", 0.0)) * 0.25)
        if not isinstance(ataque, dict):
            return 0.0
        for k in ("Custo", "Custo Energia", "CustoEnergia", "Energia", "Mana"):
            if k in ataque and str(ataque.get(k)).strip() != "":
                return max(0.0, self._numero(ataque.get(k), 0.0))
        return 0.0

    def _disponivel(self, pokemon) -> float:
        if pokemon is None:
            return 0.0
        pid = self._id_combatente(pokemon)
        reservado = self._montador.custo_reservado(pid)
        return float(getattr(pokemon, "Energia", 0.0)) - reservado

    def previsao_consumo(self, pokemon, ataque: Optional[dict]) -> tuple[float, bool]:
        if pokemon is None:
            return 0.0, True
        estilo = self._estilo_ataque(ataque)
        custo = self._custo_ataque(pokemon, ataque, estilo)
        if custo <= 0.0:
            return 0.0, True
        return custo, custo <= self._disponivel(pokemon)

    def _pokemon_no_ponto(self, pos_tela):
        return self._controlador.pokemon_no_ponto(pos_tela, self._camera)

    def _criar_mira(self, executor, ataque: Optional[dict], mouse_pos, *, arrastando: bool) -> None:
        estilo = self._estilo_ataque(ataque)
        centro = executor.centro_tela(self._camera)
        self._mira_ativa = {
            "executor": executor,
            "ataque": ataque,
            "estilo": estilo,
            "inicio": centro,
            "mouse": tuple(mouse_pos),
            "arrastando": bool(arrastando),
        }

    def _preparo_da_mira(self, mira: Optional[dict], pos) -> Optional[dict]:
        if not mira:
            return None
        executor = mira.get("executor")
        inicio = mira.get("inicio")
        ataque = mira.get("ataque")
        estilo = mira.get("estilo")
        dx = float(pos[0] - inicio[0])
        dy = float(pos[1] - inicio[1])
        dist = math.hypot(dx, dy)
        intensidade = max(0.0, min(1.0, dist / 220.0))
        if dist < 12.0 or intensidade <= 0.01:
            return None
        self._id_mira += 1
        return {
            "executor": executor,
            "executor_id": self._id_combatente(executor),
            "ataque": ataque,
            "estilo": estilo,
            "angulo": math.atan2(dy, dx),
            "direcao": (dx / max(1.0, dist), dy / max(1.0, dist)),
            "intensidade": intensidade,
            "token_mira": self._id_mira,
            "alvo": self._alvo_selecionado,
        }

    def _finalizar_mira(self, pos) -> None:
        self._preparo_atual = self._preparo_da_mira(self._mira_ativa, pos)
        self._mira_ativa = None

    def processar_eventos(self, eventos: List[pygame.event.Event], ficha, hud_rects: List[pygame.Rect] | None = None) -> None:
        ataque = ficha.ataque_selecionado() if ficha else None
        estilo = self._estilo_ataque(ataque)
        rects = list(hud_rects or [])
        executor = self._selecionado_aliado()

        if executor is None and self._mira_ativa and self._mira_ativa.get("ataque") is not None:
            self._mira_ativa = None

        for ev in eventos or []:
            if ev.type == pygame.MOUSEMOTION:
                if self._mira_ativa and self._mira_ativa.get("arrastando"):
                    self._mira_ativa["mouse"] = tuple(ev.pos)
                if self._clique_pendente and self._clique_pendente.get("permite_arrasto") and not self._clique_pendente.get("arrastou"):
                    origem = self._clique_pendente.get("pos", ev.pos)
                    dx = float(ev.pos[0] - origem[0])
                    dy = float(ev.pos[1] - origem[1])
                    if math.hypot(dx, dy) >= self._limiar_arrasto_px:
                        self._clique_pendente["arrastou"] = True
                        if executor is not None and self._clique_pendente.get("pokemon") is executor:
                            self._criar_mira(executor, None, ev.pos, arrastando=True)

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if any(rect.collidepoint(ev.pos) for rect in rects):
                    continue
                clicado = self._pokemon_no_ponto(ev.pos)
                self._clique_pendente = {
                    "pokemon": clicado,
                    "pos": tuple(ev.pos),
                    "arrastou": False,
                    "permite_arrasto": executor is not None and ataque is None and clicado is executor,
                }

            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                if self._mira_ativa and self._mira_ativa.get("arrastando"):
                    self._finalizar_mira(ev.pos)
                    self._clique_pendente = None
                    continue

                pendente = dict(self._clique_pendente or {})
                self._clique_pendente = None
                if any(rect.collidepoint(ev.pos) for rect in rects):
                    continue
                if not pendente or pendente.get("arrastou"):
                    continue

                clicado = pendente.get("pokemon")
                if estilo == "alvo" and executor is not None and ataque is not None and clicado is not None and clicado is not executor:
                    self._alvo_selecionado = clicado
                    self._preparo_atual = {
                        "executor": executor,
                        "executor_id": self._id_combatente(executor),
                        "ataque": ataque,
                        "estilo": "alvo",
                        "alvo": clicado,
                    }
                    continue

                if clicado is not None:
                    self._controlador.selecionar_pokemon(clicado)

        mouse_pos = pygame.mouse.get_pos()
        mouse_bloqueado = any(rect.collidepoint(mouse_pos) for rect in rects)
        if executor is not None and ataque is not None and estilo in {"movimento", "tiro", "area"} and not mouse_bloqueado:
            self._criar_mira(executor, ataque, mouse_pos, arrastando=False)
        elif self._mira_ativa and not self._mira_ativa.get("arrastando"):
            self._mira_ativa = None

    def preparar(self, ficha) -> None:
        selecionado = self._selecionado_aliado()
        if selecionado is None:
            return
        ataque = ficha.ataque_selecionado() if ficha else None
        estilo = self._estilo_ataque(ataque)
        if estilo == "status":
            jogada = {
                "executor": selecionado,
                "executor_id": self._id_combatente(selecionado),
                "ataque": ataque,
                "estilo": "status",
                "custo": self._custo_ataque(selecionado, ataque, "status"),
            }
            if jogada["custo"] > self._disponivel(selecionado):
                return
            self._montador.adicionar(jogada)
            self._preparadas_visuais.append({"tipo": "status", "executor": selecionado, "estilo": "status", "intensidade": 0.2})
            self._preparo_atual = None
            return

        preparo = dict(self._preparo_atual or {})
        if not preparo and estilo in {"movimento", "tiro", "area"} and self._mira_ativa and self._mira_ativa.get("executor") is selecionado:
            preparo = dict(self._preparo_da_mira(self._mira_ativa, self._mira_ativa.get("mouse") or pygame.mouse.get_pos()) or {})
        if not preparo or preparo.get("executor") is not selecionado:
            return
        if estilo in {"movimento", "tiro", "area"}:
            if int(preparo.get("token_mira", 0)) != int(self._id_mira):
                return
            if float(preparo.get("intensidade", 0.0)) <= 0.01:
                return
        if estilo == "alvo" and preparo.get("alvo") is None:
            return

        custo = self._custo_ataque(selecionado, ataque, estilo)
        if custo > self._disponivel(selecionado):
            return

        jogada = {
            "executor": selecionado,
            "executor_id": self._id_combatente(selecionado),
            "ataque": ataque,
            "estilo": estilo,
            "angulo": preparo.get("angulo"),
            "direcao": preparo.get("direcao"),
            "intensidade": preparo.get("intensidade"),
            "alvo": preparo.get("alvo"),
            "alvo_id": self._id_combatente(preparo.get("alvo")) if preparo.get("alvo") is not None else None,
            "custo": custo,
        }
        self._montador.adicionar(jogada)
        self._preparadas_visuais.append(dict(jogada))
        self._preparo_atual = None

    def pronto(self) -> None:
        por_id = {self._id_combatente(p): p for p in (self._controlador.PokemonsAliados + self._controlador.PokemonsInimigos)}
        for jogada in self._montador.listar():
            poke = por_id.get(str(jogada.get("executor_id") or ""))
            if poke is None:
                continue
            custo = self._numero(jogada.get("custo"), 0.0)
            poke.Energia = max(0.0, float(getattr(poke, "Energia", 0.0)) - custo)
        self._montador.limpar()
        self._preparadas_visuais.clear()
        self._preparo_atual = None
        self._mira_ativa = None
        self._alvo_selecionado = None
        self._clique_pendente = None

    def _cor_intensidade(self, intensidade: float):
        if intensidade < 0.34:
            return (78, 220, 108), (220, 255, 225)
        if intensidade < 0.67:
            return (255, 214, 84), (255, 245, 195)
        return (244, 96, 96), (255, 221, 221)

    def _desenhar_mira(self, tela, mira: dict, preparada: bool = False) -> None:
        executor = mira.get("executor")
        if executor is None:
            return
        inicio = executor.centro_tela(self._camera)
        estilo = str(mira.get("estilo") or "movimento")
        alpha = 92 if preparada else 165
        if estilo in {"movimento", "alvo"}:
            fim = None
            alvo = mira.get("alvo")
            if alvo is not None:
                fim = alvo.centro_tela(self._camera)
            elif mira.get("angulo") is not None:
                ang = float(mira.get("angulo") or 0.0)
                inten = max(0.15, float(mira.get("intensidade") or 0.0))
                fim = (inicio[0] + math.cos(ang) * 190 * inten, inicio[1] + math.sin(ang) * 190 * inten)
            elif "mouse" in mira:
                fim = mira.get("mouse")
            if fim is None:
                return
            p, s = self._cor_intensidade(float(mira.get("intensidade") or 0.25))
            self._fluxo_setas.desenhar(tela, inicio, fim, cor_principal=p, cor_secundaria=s, alpha=alpha, alpha_trilha=max(20, alpha // 3))
            return
        if estilo == "tiro":
            ataque = mira.get("ataque") or {}
            ang = float(mira.get("angulo") or 0.0)
            if mira.get("mouse") is not None:
                dx = float(mira["mouse"][0] - inicio[0])
                dy = float(mira["mouse"][1] - inicio[1])
                if abs(dx) + abs(dy) > 0.1:
                    ang = math.atan2(dy, dx)
            tile = max(16, int(getattr(self._camera, "TilePx", 40) or 40))
            alcance = self._numero(ataque.get("Alcance Tiro") or ataque.get("AlcanceTiro"), 4.0) * tile
            grossura = self._numero(ataque.get("Grossura Tiro") or ataque.get("GrossuraTiro"), 1.0) * tile
            diametro = self._numero(ataque.get("Diametro Tiro") or ataque.get("DiametroTiro"), 0.0) * tile
            self._fluxo_tiro.desenhar(tela, inicio, ang, alcance, grossura, diametro, alpha=alpha)
            return
        if estilo == "area":
            ataque = mira.get("ataque") or {}
            ang = float(mira.get("angulo") or 0.0)
            if mira.get("mouse") is not None:
                dx = float(mira["mouse"][0] - inicio[0])
                dy = float(mira["mouse"][1] - inicio[1])
                if abs(dx) + abs(dy) > 0.1:
                    ang = math.atan2(dy, dx)
            raio = executor.raio_px(self._camera)
            base = self._numero(ataque.get("Base Area") or ataque.get("BaseArea"), 30.0)
            altura = self._numero(ataque.get("Altura Area") or ataque.get("AlturaArea"), 50.0)
            teto_raw = ataque.get("Teto Area") if "Teto Area" in ataque else ataque.get("TetoArea")
            teto = None if teto_raw in (None, "") else self._numero(teto_raw, 0.0)
            self._fluxo_area.desenhar(tela, inicio, raio, ang, base, altura, teto, alpha=alpha)

    def desenhar(self, tela: pygame.Surface, dt: float) -> None:
        self._fluxo_setas.atualizar(dt)
        self._fluxo_ligacao.atualizar(dt)
        sel = getattr(self._controlador, "PokemonSelecionado", None)
        ataque = getattr(self, "_ataque_atual", None)
        estilo = self._estilo_ataque(ataque)
        if estilo == "alvo" and sel is not None:
            pulso = (pygame.time.get_ticks() % 900) / 900.0
            alpha = int(90 + 120 * abs(0.5 - pulso) * 2.0)
            for poke in (self._controlador.PokemonsAliados + self._controlador.PokemonsInimigos):
                if poke is sel:
                    continue
                c = poke.centro_tela(self._camera)
                r = poke.raio_px(self._camera) + 3
                camada = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
                pygame.draw.circle(camada, (255, 236, 120, alpha), (camada.get_width() // 2, camada.get_height() // 2), r, 3)
                tela.blit(camada, camada.get_rect(center=c))

        if self._mira_ativa:
            self._desenhar_mira(tela, self._mira_ativa, preparada=False)
        elif self._preparo_atual:
            self._desenhar_mira(tela, self._preparo_atual, preparada=False)

        for jogada in self._preparadas_visuais:
            self._desenhar_mira(tela, jogada, preparada=True)

    def atualizar_contexto(self, ataque_atual: Optional[dict]) -> None:
        self._ataque_atual = ataque_atual
