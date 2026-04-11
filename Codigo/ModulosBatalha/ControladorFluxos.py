from __future__ import annotations

import math
import re
from typing import Dict, List, Optional

import pygame

from Codigo.ModulosBatalha.LeitorFluxos import LeitorFluxos
from Codigo.ModulosBatalha.MontadorJogada import MontadorJogada
from Codigo.Prefabs.Fluxos import Fluxo


class ControladorFluxos:
    _REGEX_ALVO = re.compile(r"^alvo(?:(\d+))?([ai])?(\*)?$", re.IGNORECASE)

    def __init__(self, controlador_batalha, camera) -> None:
        self._controlador = controlador_batalha
        self._camera = camera
        self._montador = MontadorJogada()
        self._fluxo_setas = Fluxo(estilo="seta")
        self._fluxo_linha = Fluxo(estilo="linha")
        self._leitor_fluxos = LeitorFluxos()
        self._preparacao: Optional[Dict[str, object]] = None
        self._ataque_atual: Optional[dict] = None
        self._assinatura_contexto: tuple[str, str] = ("", "")
        self._clique_arrasto: Optional[Dict[str, object]] = None
        self._limiar_arrasto_px = 12.0
        self._mouse_pos = (0, 0)
        if hasattr(self._controlador, "definir_provedor_reservas"):
            self._controlador.definir_provedor_reservas(self.energia_reservada_visual)

    def _todos_pokemons(self):
        return list(getattr(self._controlador, "PokemonsAliados", [])) + list(getattr(self._controlador, "PokemonsInimigos", []))

    def _pokemon_por_id(self) -> Dict[str, object]:
        return {self._id_combatente(pokemon): pokemon for pokemon in self._todos_pokemons()}

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

    @staticmethod
    def _numero(valor, padrao=0.0) -> float:
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(padrao)

    @staticmethod
    def _nome_ataque(ataque: Optional[dict]) -> str:
        if not isinstance(ataque, dict):
            return ""
        return str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()

    def _estilo_bruto(self, ataque: Optional[dict]) -> str:
        if not isinstance(ataque, dict):
            return "movimento"
        return str(ataque.get("Estilo") or ataque.get("estilo") or ataque.get("TipoAcao") or "").strip()

    def _estilo_ataque(self, ataque: Optional[dict]) -> str:
        estilo = self._estilo_bruto(ataque).casefold()
        if estilo.startswith("alvo"):
            return "alvo"
        mapa = {
            "movimento": "movimento",
            "mover": "movimento",
            "dash": "movimento",
            "area": "area",
            "zona": "zona",
            "tiro": "tiro",
            "status": "status",
            "buff": "status",
            "habilidade": "habilidade",
            "passivo": "habilidade",
        }
        return mapa.get(estilo, "status")

    def _regra_alvo(self, ataque: Optional[dict]) -> Dict[str, object]:
        bruto = self._estilo_bruto(ataque)
        match = self._REGEX_ALVO.match(bruto or "")
        if not match:
            return {"max": 1, "min": 1, "exato": 1, "time": None}
        quantidade_raw, time_raw, asterisco = match.groups()
        quantidade = max(1, int(quantidade_raw or 1))
        exato = quantidade if (asterisco or not quantidade_raw) else None
        minimo = quantidade if exato else 1
        return {
            "max": quantidade,
            "min": minimo,
            "exato": exato,
            "time": (time_raw or "").upper() or None,
        }

    def _selecionado_aliado(self):
        selecionado = getattr(self._controlador, "PokemonSelecionado", None)
        if selecionado is None:
            return None
        if not getattr(self._controlador, "pokemon_eh_aliado", lambda _p: False)(selecionado):
            return None
        return selecionado

    def _disponivel(self, pokemon) -> float:
        if pokemon is None:
            return 0.0
        reservado = self._montador.custo_reservado(self._id_combatente(pokemon))
        return max(0.0, float(getattr(pokemon, "Energia", 0.0)) - reservado)

    def energia_reservada_visual(self, pokemon) -> float:
        return self._montador.custo_reservado(self._id_combatente(pokemon))

    def _custo_ataque(self, pokemon, ataque: Optional[dict], estilo: str) -> float:
        if estilo == "movimento" and not ataque:
            return max(1.0, float(getattr(pokemon, "EnergiaMax", 0.0)) * 0.25)
        if not isinstance(ataque, dict):
            return 0.0
        for chave in ("Custo", "Custo Energia", "CustoEnergia", "Energia", "Mana"):
            if chave in ataque and str(ataque.get(chave)).strip() != "":
                return max(0.0, self._numero(ataque.get(chave), 0.0))
        return 0.0

    def _simular_adicao(self, pokemon, ataque: Optional[dict], estilo: str) -> tuple[float, bool]:
        if pokemon is None:
            return 0.0, False
        jogada = {
            "executor_id": self._id_combatente(pokemon),
            "ataque": ataque,
            "custo_base": self._custo_ataque(pokemon, ataque, estilo),
        }
        permitido, _motivo, custo_total = self._montador.pode_adicionar(jogada)
        return custo_total, permitido and custo_total <= self._disponivel(pokemon)

    def previsao_consumo(self, pokemon, ataque: Optional[dict]) -> tuple[float, bool]:
        if pokemon is None:
            return 0.0, True
        if ataque is None:
            if self._preparacao is None:
                return 0.0, True
            if self._preparacao.get("executor") is not pokemon:
                return 0.0, True
            if self._preparacao.get("ataque") is not None:
                return 0.0, True
        estilo = self._estilo_ataque(ataque)
        if estilo == "habilidade":
            return 0.0, False
        return self._simular_adicao(pokemon, ataque, estilo)

    def _pokemon_no_ponto(self, pos_tela):
        return self._controlador.pokemon_no_ponto(pos_tela, self._camera)

    def _assinatura(self, executor, ataque: Optional[dict]) -> tuple[str, str]:
        return self._id_combatente(executor), self._nome_ataque(ataque).casefold()

    def _posicao_virtual_executor(self, executor) -> Optional[tuple[float, float]]:
        if executor is None:
            return None
        return self._montador.posicao_virtual_executor(self._id_combatente(executor), self._pokemon_por_id())

    def _criar_preparacao(self, executor, ataque: Optional[dict], estilo: str) -> Dict[str, object]:
        origem = self._posicao_virtual_executor(executor) or getattr(executor, "Posicao", (0.0, 0.0))
        tipo_preparo = "direcao"
        if estilo == "alvo":
            tipo_preparo = "alvo"
        elif estilo in {"area", "tiro", "zona"}:
            tipo_preparo = "complexo"
        return {
            "executor": executor,
            "executor_id": self._id_combatente(executor),
            "ataque": ataque,
            "estilo": estilo,
            "tipo_preparo": tipo_preparo,
            "estado": "preparando",
            "origem_mundo": (float(origem[0]), float(origem[1])),
            "destino_mundo": None,
            "alvos": [],
            "regra_alvo": self._regra_alvo(ataque),
            "tipo_movimento": estilo == "movimento",
            "custo_base": self._custo_ataque(executor, ataque, estilo),
            "origem_arrasto": ataque is None,
        }

    def _garantir_preparacao_contextual(self) -> None:
        executor = self._selecionado_aliado()
        assinatura = self._assinatura(executor, self._ataque_atual)
        if assinatura == self._assinatura_contexto:
            if self._preparacao is not None and self._preparacao.get("executor") is executor:
                origem = self._posicao_virtual_executor(executor)
                if origem is not None:
                    self._preparacao["origem_mundo"] = origem
            return

        self._assinatura_contexto = assinatura
        self._preparacao = None
        self._clique_arrasto = None

        if executor is None or self._ataque_atual is None:
            return
        estilo = self._estilo_ataque(self._ataque_atual)
        if estilo in {"movimento", "alvo", "area", "tiro", "zona"}:
            self._preparacao = self._criar_preparacao(executor, self._ataque_atual, estilo)

    def _atualizar_destino_mouse(self, pos_tela) -> None:
        if self._preparacao is None:
            return
        if self._preparacao.get("tipo_preparo") not in {"direcao", "complexo"}:
            return
        origem = self._posicao_virtual_executor(self._preparacao.get("executor"))
        if origem is not None:
            self._preparacao["origem_mundo"] = origem
        self._preparacao["destino_mundo"] = self._camera.tela_para_mundo_tiles(pos_tela)

    def _alvos_validos(self, preparo: Dict[str, object]) -> List[object]:
        regra = preparo.get("regra_alvo") if isinstance(preparo.get("regra_alvo"), dict) else {}
        executor = preparo.get("executor")
        time_regra = str(regra.get("time") or "").upper()
        saida = []
        for pokemon in self._todos_pokemons():
            if executor is None:
                continue
            if time_regra == "A" and getattr(pokemon, "Lado", None) != getattr(executor, "Lado", None):
                continue
            if time_regra == "I" and getattr(pokemon, "Lado", None) == getattr(executor, "Lado", None):
                continue
            saida.append(pokemon)
        return saida

    def _adicionar_alvo(self, alvo) -> None:
        if self._preparacao is None or self._preparacao.get("tipo_preparo") != "alvo":
            return
        if alvo is None:
            return
        validos = self._alvos_validos(self._preparacao)
        if alvo not in validos:
            return
        alvos = list(self._preparacao.get("alvos") or [])
        if alvo in alvos:
            return
        regra = self._preparacao.get("regra_alvo") if isinstance(self._preparacao.get("regra_alvo"), dict) else {}
        if len(alvos) >= max(1, int(regra.get("max") or 1)):
            return
        alvos.append(alvo)
        self._preparacao["alvos"] = alvos
        self._preparacao["estado"] = "estabilizado"

    def _preparo_pronto(self, preparo: Optional[Dict[str, object]]) -> bool:
        if not isinstance(preparo, dict):
            return False
        estado = str(preparo.get("estado") or "")
        if estado != "estabilizado":
            return False
        if preparo.get("tipo_preparo") in {"direcao", "complexo"}:
            return isinstance(preparo.get("destino_mundo"), (tuple, list))
        if preparo.get("tipo_preparo") == "alvo":
            regra = preparo.get("regra_alvo") if isinstance(preparo.get("regra_alvo"), dict) else {}
            total = len(preparo.get("alvos") or [])
            minimo = max(1, int(regra.get("min") or 1))
            exato = regra.get("exato")
            if exato not in (None, "", 0):
                return total == int(exato)
            return total >= minimo
        return False

    def cancelar_preparacao(self) -> None:
        self._preparacao = None
        self._clique_arrasto = None

    def processar_eventos(self, eventos: List[pygame.event.Event], ficha, hud_rects: List[pygame.Rect] | None = None) -> None:
        self._garantir_preparacao_contextual()
        rects = [pygame.Rect(rect) for rect in (hud_rects or []) if isinstance(rect, pygame.Rect)]
        executor = self._selecionado_aliado()

        for evento in eventos or []:
            if evento.type == pygame.MOUSEMOTION:
                self._mouse_pos = tuple(evento.pos)
                if self._clique_arrasto is not None and self._preparacao is None:
                    origem = self._clique_arrasto.get("pos", evento.pos)
                    dx = float(evento.pos[0] - origem[0])
                    dy = float(evento.pos[1] - origem[1])
                    if math.hypot(dx, dy) >= self._limiar_arrasto_px:
                        self._preparacao = self._criar_preparacao(self._clique_arrasto.get("executor"), None, "movimento")
                        self._preparacao["origem_arrasto"] = True
                if self._preparacao is not None and self._preparacao.get("estado") == "preparando":
                    self._atualizar_destino_mouse(evento.pos)
                continue

            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if any(rect.collidepoint(evento.pos) for rect in rects):
                    continue

                if self._preparacao is not None and self._preparacao.get("tipo_preparo") == "alvo":
                    alvo = self._pokemon_no_ponto(evento.pos)
                    if alvo is not None:
                        self._adicionar_alvo(alvo)
                        continue
                    if self._preparacao.get("estado") == "estabilizado":
                        self.cancelar_preparacao()
                        continue

                if self._preparacao is not None and self._preparacao.get("estado") == "estabilizado":
                    self.cancelar_preparacao()
                    continue

                if self._preparacao is not None and self._preparacao.get("estado") == "preparando" and self._preparacao.get("tipo_preparo") in {"direcao", "complexo"}:
                    self._atualizar_destino_mouse(evento.pos)
                    self._preparacao["estado"] = "estabilizado"
                    continue

                clicado = self._pokemon_no_ponto(evento.pos)
                if executor is not None and self._ataque_atual is None and clicado is executor:
                    self._clique_arrasto = {"executor": executor, "pos": tuple(evento.pos)}
                    continue

                if clicado is not None:
                    self._controlador.selecionar_pokemon(clicado)
                    continue

            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                if self._clique_arrasto is None:
                    continue
                if self._preparacao is not None and self._preparacao.get("origem_arrasto"):
                    self._atualizar_destino_mouse(evento.pos)
                    self._preparacao["estado"] = "estabilizado"
                self._clique_arrasto = None

    def preparar(self, ficha) -> None:
        selecionado = self._selecionado_aliado()
        if selecionado is None:
            return
        ataque = ficha.ataque_selecionado() if ficha else self._ataque_atual
        estilo = self._estilo_ataque(ataque)
        if estilo == "habilidade":
            return

        custo, pode = self.previsao_consumo(selecionado, ataque)
        if not pode:
            return

        if estilo == "status":
            jogada = {
                "executor": selecionado,
                "executor_id": self._id_combatente(selecionado),
                "ataque": ataque,
                "estilo": "status",
                "tipo_movimento": False,
                "custo_base": self._custo_ataque(selecionado, ataque, "status"),
            }
            self._montador.adicionar(jogada)
            self._preparacao = None
            return

        preparo = dict(self._preparacao or {})
        if preparo.get("executor") is not selecionado or not self._preparo_pronto(preparo):
            return

        jogada = {
            "executor": selecionado,
            "executor_id": self._id_combatente(selecionado),
            "ataque": ataque,
            "estilo": estilo,
            "tipo_movimento": bool(preparo.get("tipo_movimento")),
            "destino_mundo": tuple(preparo.get("destino_mundo")) if isinstance(preparo.get("destino_mundo"), (tuple, list)) else None,
            "alvos": list(preparo.get("alvos") or []),
            "alvo_ids": [self._id_combatente(alvo) for alvo in list(preparo.get("alvos") or [])],
            "custo_base": self._custo_ataque(selecionado, ataque, estilo),
        }
        self._montador.adicionar(jogada)
        self._preparacao = None
        self._clique_arrasto = None

    def remover_jogada(self, jogada_id: object) -> None:
        self._montador.remover(jogada_id)

    def selecionar_jogada(self, jogada_id: object | None) -> None:
        atual = self._montador.selecionado_id()
        try:
            novo = int(jogada_id) if jogada_id not in (None, "") else None
        except (TypeError, ValueError):
            novo = None
        if atual is not None and novo == atual:
            self._montador.selecionar(None)
            return
        self._montador.selecionar(novo)

    def jogada_selecionada_id(self) -> Optional[int]:
        return self._montador.selecionado_id()

    def listar_jogadas(self) -> List[Dict[str, object]]:
        return self._montador.listar()

    def pronto(self) -> None:
        por_id = self._pokemon_por_id()
        for jogada in self._montador.listar_referencias():
            poke = por_id.get(str(jogada.get("executor_id") or ""))
            if poke is None:
                continue
            custo = self._numero(jogada.get("custo"), 0.0)
            poke.Energia = max(0.0, float(getattr(poke, "Energia", 0.0)) - custo)
        self._montador.limpar()
        self.cancelar_preparacao()

    def atualizar_contexto(self, ataque_atual: Optional[dict]) -> None:
        self._ataque_atual = ataque_atual

    def _cor_preparo(self, jogada: Dict[str, object], preparada: bool, selecionada: bool = False):
        estilo = str(jogada.get("estilo") or "movimento").casefold()
        ataque = jogada.get("ataque")
        if estilo == "movimento" and ataque is None:
            return (58, 150, 255) if not preparada or selecionada else (80, 220, 120)
        if estilo == "movimento":
            return (235, 72, 72) if not preparada or selecionada else (255, 150, 54)
        if estilo == "alvo":
            return (235, 72, 72)
        if estilo in {"area", "tiro", "zona"}:
            return (255, 255, 255)
        return (235, 72, 72)

    def _desenhar_preparo_direcao(self, tela: pygame.Surface, jogada: Dict[str, object], *, preparada: bool, selecionada: bool = False) -> None:
        origem = jogada.get("origem_mundo")
        destino = jogada.get("destino_mundo")
        if not isinstance(origem, (tuple, list)) or not isinstance(destino, (tuple, list)):
            return
        inicio = self._camera.mundo_para_tela_px((float(origem[0]), float(origem[1])))
        fim = self._camera.mundo_para_tela_px((float(destino[0]), float(destino[1])))
        cor = self._cor_preparo(jogada, preparada, selecionada)
        cor_sec = tuple(min(255, canal + 72) for canal in cor)
        self._fluxo_setas.desenhar(
            tela,
            inicio,
            fim,
            cor_principal=cor,
            cor_secundaria=cor_sec,
            alpha=255 if (selecionada or not preparada) else 124,
            alpha_trilha=90 if (selecionada or not preparada) else 34,
            animado=(selecionada or not preparada),
        )

    def _desenhar_preparo_alvo(self, tela: pygame.Surface, jogada: Dict[str, object], *, preparada: bool, selecionada: bool = False) -> None:
        origem = jogada.get("origem_mundo")
        alvos = list(jogada.get("alvos") or [])
        if not isinstance(origem, (tuple, list)) or not alvos:
            return
        inicio = self._camera.mundo_para_tela_px((float(origem[0]), float(origem[1])))
        cor = self._cor_preparo(jogada, preparada, selecionada)
        cor_sec = tuple(min(255, canal + 52) for canal in cor)
        for alvo in alvos:
            centro_alvo = alvo.centro_tela(self._camera)
            self._fluxo_linha.desenhar(
                tela,
                inicio,
                centro_alvo,
                cor_principal=cor,
                cor_secundaria=cor_sec,
                alpha=255 if (selecionada or not preparada) else 118,
                alpha_trilha=72 if (selecionada or not preparada) else 22,
                animado=(selecionada or not preparada),
            )

    def _desenhar_preparo_complexo(self, tela: pygame.Surface, jogada: Dict[str, object], *, preparada: bool, selecionada: bool = False) -> None:
        origem = jogada.get("origem_mundo")
        destino = jogada.get("destino_mundo")
        if not isinstance(origem, (tuple, list)) or not isinstance(destino, (tuple, list)):
            return
        inicio = self._camera.mundo_para_tela_px((float(origem[0]), float(origem[1])))
        fim = self._camera.mundo_para_tela_px((float(destino[0]), float(destino[1])))
        self._leitor_fluxos.desenhar(
            tela,
            jogada.get("ataque"),
            inicio,
            fim,
            alpha=180 if (selecionada or not preparada) else 92,
            animado=(selecionada or not preparada),
            tile_px=max(16.0, float(getattr(self._camera, "TilePx", 40) or 40)),
        )

    def _desenhar_construtos(self, tela: pygame.Surface, construtos: Dict[str, tuple[float, float]], ativo: Optional[Dict[str, object]]) -> None:
        mapa = self._pokemon_por_id()
        for pid, posicao in construtos.items():
            pokemon = mapa.get(pid)
            if pokemon is None:
                continue
            pokemon.renderizar_construto(tela, self._camera, posicao, alpha=92)
        if ativo and ativo.get("tipo_movimento") and isinstance(ativo.get("destino_mundo"), (tuple, list)):
            pokemon = ativo.get("executor")
            if pokemon is not None:
                pokemon.renderizar_construto(tela, self._camera, ativo.get("destino_mundo"), alpha=72)

    def _desenhar_alvos_possiveis(self, tela: pygame.Surface) -> None:
        if self._preparacao is None or self._preparacao.get("tipo_preparo") != "alvo":
            return
        validos = self._alvos_validos(self._preparacao)
        selecionados = set(self._preparacao.get("alvos") or [])
        pulso = (pygame.time.get_ticks() % 900) / 900.0
        alpha = int(84 + 118 * abs(0.5 - pulso) * 2.0)
        for poke in validos:
            centro = poke.centro_tela(self._camera)
            raio = poke.raio_px(self._camera) + 4
            camada = pygame.Surface((raio * 3, raio * 3), pygame.SRCALPHA)
            cor = (255, 226, 120, alpha) if poke not in selecionados else (255, 114, 114, min(255, alpha + 28))
            pygame.draw.circle(camada, cor, (camada.get_width() // 2, camada.get_height() // 2), raio, 3)
            tela.blit(camada, camada.get_rect(center=centro))

    def desenhar(self, tela: pygame.Surface, dt: float) -> None:
        self._fluxo_setas.atualizar(dt)
        self._fluxo_linha.atualizar(dt)
        self._leitor_fluxos.atualizar(dt)

        visuais, construtos = self._montador.resolver_visuais(self._pokemon_por_id())
        ativo = None
        if self._preparacao is not None:
            ativo = dict(self._preparacao)
            if self._preparacao.get("executor") is not None:
                origem = self._posicao_virtual_executor(self._preparacao.get("executor"))
                if origem is not None:
                    ativo["origem_mundo"] = origem
            if ativo.get("tipo_preparo") == "alvo":
                ativo["alvos"] = list(self._preparacao.get("alvos") or [])

        self._desenhar_construtos(tela, construtos, ativo)
        self._desenhar_alvos_possiveis(tela)

        for jogada in visuais:
            selecionada = self._montador.selecionado_id() == int(jogada.get("id") or 0)
            estilo = str(jogada.get("estilo") or "movimento").casefold()
            if estilo == "alvo":
                self._desenhar_preparo_alvo(tela, jogada, preparada=True, selecionada=selecionada)
            elif estilo in {"area", "tiro", "zona"}:
                self._desenhar_preparo_complexo(tela, jogada, preparada=True, selecionada=selecionada)
            else:
                self._desenhar_preparo_direcao(tela, jogada, preparada=True, selecionada=selecionada)

        if not ativo:
            return
        estilo_ativo = str(ativo.get("estilo") or "movimento").casefold()
        if estilo_ativo == "alvo":
            self._desenhar_preparo_alvo(tela, ativo, preparada=False, selecionada=False)
        elif estilo_ativo in {"area", "tiro", "zona"}:
            self._desenhar_preparo_complexo(tela, ativo, preparada=False, selecionada=False)
        else:
            self._desenhar_preparo_direcao(tela, ativo, preparada=False, selecionada=False)
