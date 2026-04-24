from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pygame

from Codigo.ModulosBatalha.IndicadoresAcoes import IndicadoresAcoes
from Codigo.ModulosBatalha.MontadorJogada import MontadorJogada
from Codigo.Paineis.FichaPokemonBatalha import FichaPokemonBatalha
from Codigo.Paineis.PainelAcoes import PainelAcoes
from Codigo.Paineis.VisualizadorLog import VisualizadorLog
from Codigo.Prefabs.Barra import Barra
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto


class ElementosHudBatalha:
    TECLAS_ATAQUE = [pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_a, pygame.K_s]
    TECLAS_POKEMON = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6]
    LIMIAR_ARRASTO_PX = 12.0

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
        self._fuga_taxa_decay = 0.08
        self._fuga_disparada = False
        self._ficha = FichaPokemonBatalha()
        self._painel_jogada = PainelAcoes()
        self._visualizador_log = VisualizadorLog(controlador_batalha)
        self._anim_ficha = 0.0
        self._pokemon_exibido = None
        self._botao_pronto: Optional[Botao] = None
        self._barra_tempo = Barra((0, 0, 1, 1), texto="", valor=50, minimo=0, maximo=50, mostrar_rotulo=False, suavizacao=30.0)
        self._texto_rodada = Texto("Rodada 1", style={"size": 20, "align": "topleft", "outline": True, "outline_thickness": 2, "outline_color": (8, 12, 20), "shadow": False, "color": (245, 249, 255)})
        self._tempo_total_rodada = 50.0
        self._tempo_restante_rodada = self._tempo_total_rodada
        self._rodada_referencia = int(getattr(self._controlador, "_rodada_atual", 1) or 1) if self._controlador is not None else 1
        self._aguardando_resultado_rodada = False

        self._montador = MontadorJogada(getattr(self._controlador, "obter_regras_batalha", lambda: {})())
        self._indicadores = IndicadoresAcoes()
        self._drag: Dict[str, object] = {}
        self._preview: Dict[str, object] = {}
        self._parede_ponto_a = None
        if self._controlador is not None:
            self._controlador.definir_provedor_reservas(lambda p: self._montador.custo_reservado(getattr(p, "Uid", "")))

    def filtrar_eventos_camera(self, tela: pygame.Surface, eventos: List[pygame.event.Event], dt: float = 0.0) -> List[pygame.event.Event]:
        self._garantir_layout(tela)
        self._visualizador_log.preparar(tela, dt)
        if not self._visualizador_log.captura_scroll(pygame.mouse.get_pos()):
            return list(eventos or [])
        filtrados: List[pygame.event.Event] = []
        for evento in eventos or []:
            if evento.type == pygame.MOUSEWHEEL:
                continue
            if evento.type == pygame.MOUSEBUTTONDOWN and getattr(evento, "button", 0) in (4, 5):
                continue
            filtrados.append(evento)
        return filtrados

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
        self._botao_fugir = Botao(rect, "", execute=lambda _jogo, _botao: self._pressionar_fuga())
        self._icone_fugir = self._carregar_icone(max(24, int(lado * 0.68)))

        bw = max(138, int(lado * 2.2))
        bh = max(44, int(lado * 0.82))
        bx = w - bw - margem
        by = h - (bh + margem)
        self._botao_pronto = Botao(pygame.Rect(bx, by, bw, bh), "Pronto", execute=lambda _jogo, _botao: self._confirmar_jogadas())
        self._barra_tempo.configurar(rect=pygame.Rect(18, 38, max(180, int(w * 0.20)), 18), minimo=0.0, maximo=50.0)

    def _pressionar_fuga(self) -> None:
        self._fuga_pressao = min(self._fuga_alvo, self._fuga_pressao + self._fuga_taxa_clique)
        if (not self._fuga_disparada) and self._fuga_pressao >= self._fuga_alvo:
            self._fuga_disparada = True
            if callable(self._ao_fugir):
                self._ao_fugir()

    def _atualizar_fuga(self, dt: float) -> None:
        if self._fuga_disparada:
            return
        self._fuga_pressao = max(0.0, self._fuga_pressao - self._fuga_taxa_decay * max(0.0, min(1.0, float(dt) * 60.0)))

    def _atualizar_tempo_rodada(self, dt: float) -> None:
        if not self._aguardando_resultado_rodada:
            self._tempo_restante_rodada = max(0.0, float(self._tempo_restante_rodada) - max(0.0, float(dt)))

    def _sincronizar_tempo_rodada(self) -> None:
        rodada_atual = int(getattr(self._controlador, "_rodada_atual", 1) or 1) if self._controlador is not None else 1
        if rodada_atual != self._rodada_referencia:
            self._rodada_referencia = rodada_atual
            self._tempo_restante_rodada = self._tempo_total_rodada
            self._aguardando_resultado_rodada = False
            self._montador.limpar()

    def _desenhar_overlay_fuga(self, tela: pygame.Surface) -> None:
        if self._fuga_pressao <= 0.01:
            return
        t = max(0.0, min(1.0, self._fuga_pressao / max(0.01, self._fuga_alvo)))
        overlay = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(160 * t)))
        tela.blit(overlay, (0, 0))

    def _confirmar_jogadas(self) -> None:
        self._aguardando_resultado_rodada = True

    def _atualizar_animacao_ficha(self, dt: float):
        selecionado = getattr(self._controlador, "PokemonSelecionado", None)
        if selecionado is not None:
            self._pokemon_exibido = selecionado
        alvo = 1.0 if selecionado is not None else 0.0
        self._anim_ficha += (alvo - self._anim_ficha) * min(1.0, max(0.01, float(dt) * 8.0))
        if self._anim_ficha <= 0.01 and selecionado is None:
            self._pokemon_exibido = None

    def _energia_disponivel(self, pokemon) -> float:
        return float(getattr(pokemon, "Energia", 0.0) or 0.0)

    def _modo_energia_infinita(self) -> bool:
        if self._controlador is None:
            return False
        if self._controlador.modo_teste_ativo() and bool(getattr(self._controlador, "Contexto", {}).get("energia_infinita_teste", False)):
            return True
        return False

    def _origem_virtual(self, pokemon):
        mapa = getattr(self._controlador, "mapa_pokemons", lambda: {})()
        return self._montador.posicao_virtual_executor(getattr(pokemon, "Uid", ""), mapa) or tuple(getattr(pokemon, "Posicao", (0.0, 0.0)))

    def _build_preview_ataque(self, pokemon, ataque, mouse_pos_px):
        origem = self._origem_virtual(pokemon)
        destino = tuple(self._camera.tela_para_batalha_tiles(mouse_pos_px))
        props = self._montador.obter_propriedades_ataque(ataque if isinstance(ataque, dict) else None)
        estilo = self._montador.estilo_ataque(props)
        prev = {"executor": pokemon, "executor_id": getattr(pokemon, "Uid", ""), "ataque": props, "estilo": estilo, "origem_mundo": origem, "destino_mundo": destino, "invalido": False}
        if estilo == "alvo":
            alcance = float(((props or {}).get("alvo") or {}).get("alcance", 3.0))
            prev["alcance"] = alcance
            alvo = self._controlador.pokemon_no_ponto(mouse_pos_px, self._camera)
            if alvo is None:
                prev["invalido"] = True
            else:
                prev["alvo_ids"] = [getattr(alvo, "Uid", "")]
                prev["invalido"] = math.dist(tuple(getattr(alvo, "Posicao", (0.0, 0.0))), origem) > alcance
        elif estilo == "status":
            prev["autouso"] = True
            prev["invalido"] = self._controlador.pokemon_no_ponto(mouse_pos_px, self._camera) is not pokemon
        elif estilo == "zona":
            prev["raio"] = float(((props or {}).get("zona") or {}).get("raio", 1.0))
            alcance = float(((props or {}).get("zona") or {}).get("alcance_max_centro", ((props or {}).get("zona") or {}).get("alcance", 6.0)))
            prev["alcance"] = alcance
            if math.dist(origem, destino) > alcance:
                prev["invalido"] = True
        elif estilo == "laser":
            prev["alcance"] = float(((props or {}).get("laser") or {}).get("alcance", 8.0))
            prev["grossura"] = float(((props or {}).get("laser") or {}).get("grossura", 0.8))
        elif estilo == "projetil":
            prev["alcance"] = float(((props or {}).get("projetil") or {}).get("alcance", 8.0))
            prev["raio"] = float(((props or {}).get("projetil") or {}).get("raio", 0.35))
        elif estilo == "dash":
            mov = (props or {}).get("movimento_ofensivo") if isinstance(props, dict) else {}
            prev["distancia_min"] = float((mov or {}).get("distancia_min", 0.0) or 0.0)
            prev["distancia_max"] = float((mov or {}).get("distancia_max", 6.0) or 6.0)
            distancia = max(0.0, math.dist(origem, destino))
            max_dist = max(0.01, prev["distancia_max"])
            if distancia > max_dist:
                fator = max_dist / distancia
                destino = (origem[0] + (destino[0] - origem[0]) * fator, origem[1] + (destino[1] - origem[1]) * fator)
                prev["destino_mundo"] = destino
        elif estilo == "impulso":
            mov = (props or {}).get("movimento_ofensivo") if isinstance(props, dict) else {}
            prev["distancia_min"] = float((mov or {}).get("distancia_min", 0.0) or 0.0)
            prev["distancia_max"] = float((mov or {}).get("distancia_max", 6.0) or 6.0)
            distancia = max(0.0, math.dist(origem, destino))
            max_dist = max(0.01, prev["distancia_max"])
            distancia_ajustada = min(distancia, max_dist)
            if distancia > max_dist:
                fator = max_dist / distancia
                destino = (origem[0] + (destino[0] - origem[0]) * fator, origem[1] + (destino[1] - origem[1]) * fator)
                prev["destino_mundo"] = destino
            prev["intensidade"] = max(0.0, min(1.0, distancia_ajustada / max_dist))
        elif estilo == "irregular":
            irregular = (props or {}).get("irregular") if isinstance(props, dict) else {}
            distancia_max = float((irregular or {}).get("distancia_max_entre_pontos", 4.0) or 4.0)
            prev["distancia_max_entre_pontos"] = distancia_max
            prev["largura"] = float((irregular or {}).get("largura", 0.25) or 0.25)
            if self._parede_ponto_a is None:
                prev["ponto_a"] = destino
            else:
                prev["ponto_a"] = self._parede_ponto_a
                prev["ponto_b"] = destino
                prev["invalido"] = not self._montador.validar_segundo_ponto_parede(self._parede_ponto_a, destino, distancia_max)
        return prev

    def _montar_jogada_de_preview(self, preview: Dict[str, object]) -> Dict[str, object]:
        ataque = preview.get("ataque")
        executor = preview.get("executor")
        estilo = str(preview.get("estilo") or "")
        return {
            "executor": executor,
            "executor_id": getattr(executor, "Uid", ""),
            "ataque": ataque,
            "estilo": estilo,
            "destino_mundo": preview.get("destino_mundo"),
            "tipo_movimento": estilo in {"dash", "impulso"},
            "custo_base": self._montador.custo_base_ataque(ataque, 0.0),
            "payload": {k: preview.get(k) for k in ["alvo_ids", "autouso", "ponto_a", "ponto_b"] if k in preview},
        }

    def _tentar_adicionar(self, jogada: Dict[str, object]) -> bool:
        executor = jogada.get("executor")
        energia = self._energia_disponivel(executor)
        ignorar = self._modo_energia_infinita()
        item, _ = self._montador.adicionar(jogada, energia_disponivel=energia, ignorar_custo=ignorar)
        return item is not None

    def _finalizar_preview_ataque(self) -> None:
        if not self._preview or self._preview.get("invalido"):
            return
        estilo = str(self._preview.get("estilo") or "")
        if estilo == "irregular" and self._parede_ponto_a is None:
            self._parede_ponto_a = self._preview.get("destino_mundo")
            return
        if estilo == "irregular" and self._parede_ponto_a is not None:
            self._preview["ponto_a"] = self._parede_ponto_a
            self._preview["ponto_b"] = self._preview.get("destino_mundo")
        if self._tentar_adicionar(self._montar_jogada_de_preview(self._preview)):
            self._ficha.limpar_ataque_selecionado()
        self._preview = {}
        self._parede_ponto_a = None

    def _iniciar_drag(self, pokemon, pos):
        self._drag = {"pokemon": pokemon, "inicio_px": tuple(pos), "inicio_mundo": self._origem_virtual(pokemon), "ativo": False}

    def _preview_drag(self, pos):
        if not self._drag:
            return
        if not self._drag.get("ativo"):
            inicio_px = self._drag.get("inicio_px")
            if not self._montador.atingiu_limiar_arrasto(inicio_px, pos, self.LIMIAR_ARRASTO_PX):
                self._preview = {}
                return
            self._drag["ativo"] = True
        poke = self._drag.get("pokemon")
        destino = tuple(self._camera.tela_para_batalha_tiles(pos))
        reserva = self._controlador.pokemon_no_ponto(pos, self._camera)
        estilo = "movimento"
        invalido = False
        if reserva is not None and self._controlador.pokemon_eh_reserva(reserva):
            estilo = "troca"
            invalido = not (self._controlador.pokemon_eh_aliado(reserva) and bool(getattr(reserva, "VidaAtual", 1.0) > 0.0))
        elif not self._controlador.ponto_dentro_arena(destino):
            invalido = True
        self._preview = {"estilo": estilo, "executor": poke, "executor_id": getattr(poke, "Uid", ""), "origem_mundo": self._drag.get("inicio_mundo"), "destino_mundo": getattr(reserva, "Posicao", destino), "troca_reserva_id": getattr(reserva, "Uid", None) if estilo == "troca" else None, "tipo_movimento": estilo == "movimento", "invalido": invalido}

    def _finalizar_drag(self):
        if not self._drag:
            return
        if self._drag.get("ativo") and self._preview and not self._preview.get("invalido"):
            poke = self._preview.get("executor")
            jogada = self._montador.resolver_arrasto_para_jogada(
                executor=poke,
                executor_id=getattr(poke, "Uid", ""),
                origem_mundo=self._drag.get("inicio_mundo"),
                destino_mundo=self._preview.get("destino_mundo"),
                dentro_arena=bool(self._controlador.ponto_dentro_arena(self._preview.get("destino_mundo"))),
                reserva_id=self._preview.get("troca_reserva_id"),
                reserva_valida=not bool(self._preview.get("invalido")),
            )
            if isinstance(jogada, dict):
                self._tentar_adicionar(jogada)
        self._drag = {}
        self._preview = {}

    def _processar_atalhos_teclado(self, eventos: List[pygame.event.Event]) -> None:
        if self._controlador is None:
            return
        for evento in eventos or []:
            if evento.type != pygame.KEYDOWN:
                continue
            if evento.key in self.TECLAS_POKEMON:
                self._controlador.selecionar_slot_aliado(self.TECLAS_POKEMON.index(evento.key))
            elif evento.key in self.TECLAS_ATAQUE:
                self._ficha.selecionar_ataque_indice(self.TECLAS_ATAQUE.index(evento.key), getattr(self._controlador, "PokemonSelecionado", None))
            elif evento.key == pygame.K_ESCAPE:
                self._ficha.limpar_ataque_selecionado()
                self._preview = {}
                self._parede_ponto_a = None

    def _processar_mouse(self, eventos, rects_hud):
        if self._controlador is None or self._camera is None:
            return
        selecionado = getattr(self._controlador, "PokemonSelecionado", None)
        ataque = self._ficha.ataque_selecionado()
        for ev in eventos or []:
            if ev.type == pygame.MOUSEMOTION and self._drag:
                self._preview_drag(ev.pos)
                continue
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if any(r.collidepoint(ev.pos) for r in rects_hud):
                    continue
                clicado = self._controlador.pokemon_no_ponto(ev.pos, self._camera)
                if ataque is None and clicado is not None and self._controlador.pokemon_eh_controlavel(clicado):
                    if clicado is not selecionado:
                        self._controlador.selecionar_pokemon(clicado)
                    self._iniciar_drag(clicado, ev.pos)
                elif ataque is not None and selecionado is not None:
                    self._preview = self._build_preview_ataque(selecionado, ataque, ev.pos)
                    self._finalizar_preview_ataque()
                elif clicado is not None:
                    self._controlador.selecionar_pokemon(clicado)
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self._drag:
                if self._drag.get("ativo"):
                    self._preview_drag(ev.pos)
                self._finalizar_drag()

    def _atualizar_preview_continuo(self):
        if self._controlador is None or self._camera is None:
            return
        if self._drag:
            self._preview_drag(pygame.mouse.get_pos())
            return
        selecionado = getattr(self._controlador, "PokemonSelecionado", None)
        ataque = self._ficha.ataque_selecionado()
        if ataque is not None and selecionado is not None:
            self._preview = self._build_preview_ataque(selecionado, ataque, pygame.mouse.get_pos())
        elif not self._parede_ponto_a:
            self._preview = {}

    def _previsao_ficha(self):
        poke = self._pokemon_exibido
        ataque = self._ficha.ataque_selecionado()
        if poke is None or ataque is None:
            return 0.0, True
        prev = self._build_preview_ataque(poke, ataque, pygame.mouse.get_pos())
        jogada = self._montar_jogada_de_preview(prev)
        return self._montador.calcular_previsao(getattr(poke, "Uid", ""), jogada, self._energia_disponivel(poke), ignorar_custo=self._modo_energia_infinita())

    def desenhar(self, tela: pygame.Surface, eventos: List[pygame.event.Event], dt: float = 0.0) -> None:
        self._garantir_layout(tela)
        self._visualizador_log.preparar(tela, dt)
        replay_ativo = bool(getattr(self._controlador, "esta_reproduzindo_logs", lambda: False)()) if self._controlador is not None else False
        interacao_bloqueada = bool(self._aguardando_resultado_rodada or replay_ativo)
        if not interacao_bloqueada:
            self._processar_atalhos_teclado(eventos or [])
        self._sincronizar_tempo_rodada()
        self._atualizar_animacao_ficha(dt)
        self._atualizar_fuga(dt)
        self._atualizar_tempo_rodada(dt)
        if self._tempo_restante_rodada <= 0.0 and not interacao_bloqueada:
            self._confirmar_jogadas()

        rects_hud = [self._ficha.rect, self._botao_pronto.rect if self._botao_pronto else pygame.Rect(0, 0, 0, 0), self._botao_fugir.rect if self._botao_fugir else pygame.Rect(0, 0, 0, 0)]
        self._painel_jogada.sincronizar(self._montador.listar(), self._montador.selecionado_id())
        self._painel_jogada.recalcular_layout(tela)
        if not interacao_bloqueada:
            self._painel_jogada.processar_eventos(eventos or [])
            for cmd in self._painel_jogada.coletar_comandos():
                if cmd.get("acao") == "remover":
                    self._montador.remover(cmd.get("id"))
                elif cmd.get("acao") == "selecionar":
                    self._montador.selecionar(cmd.get("id"))
        else:
            self._painel_jogada.coletar_comandos()
        rects_hud.extend(self._painel_jogada.retangulos_interativos())
        rects_hud.extend(self._visualizador_log.retangulos_interativos())

        if not interacao_bloqueada:
            self._processar_mouse(eventos or [], rects_hud)
            self._atualizar_preview_continuo()

        if self._botao_fugir is not None:
            self._botao_fugir.render(tela, eventos or [], dt, None)
            if self._icone_fugir is not None:
                tela.blit(self._icone_fugir, self._icone_fugir.get_rect(center=self._botao_fugir.rect.center))
        if self._botao_pronto is not None:
            self._botao_pronto.render(tela, eventos or [], dt, None)

        self._texto_rodada.set_text(f"Rodada {int(getattr(self._controlador, '_rodada_atual', 1) or 1)}")
        self._texto_rodada.set_pos((18, 14))
        self._texto_rodada.draw(tela)
        self._barra_tempo.set_valor(self._tempo_restante_rodada, animar=True)
        self._barra_tempo.render(tela, [], dt)

        previsao, pode = self._previsao_ficha()
        self._ficha.atualizar_previsao(previsao, pode or self._modo_energia_infinita())

        if self._controlador is not None and self._camera is not None:
            visuais, _ = self._montador.resolver_visuais(self._controlador.mapa_pokemons())
            self._indicadores.desenhar_preparadas(tela, self._camera, visuais)
            if self._preview:
                self._indicadores.desenhar_preparando(tela, self._camera, self._preview)

        self._painel_jogada.desenhar(tela, dt)
        self._ficha.definir_controle_inimigo(bool(getattr(self._controlador, "modo_teste_ativo", lambda: False)()))
        self._ficha.render(tela, self._pokemon_exibido, self._anim_ficha, eventos or [], dt)
        self._visualizador_log.desenhar(tela, eventos or [], dt)
        self._desenhar_overlay_fuga(tela)
