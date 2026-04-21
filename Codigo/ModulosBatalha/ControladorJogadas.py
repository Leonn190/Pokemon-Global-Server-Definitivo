from __future__ import annotations

import json
from typing import Dict, Optional

import pygame

from Codigo.ModulosBatalha.DebugCombate import dbg_combate
from Codigo.ModulosBatalha.IndicadorAtaque import IndicadorAtaque
from Codigo.ModulosBatalha.LeitorAtaquesCombate import LeitorAtaquesCombate
from Codigo.ModulosBatalha.MontadorJogada import MontadorJogada
from Codigo.Prefabs.Fluxos import Fluxo
from Codigo.Server.ServerBatalha import enviar_jogada_batalha_server


class ControladorJogadas:
    TIPOS_PREPARO_DIRECIONAIS = {"direcao", "direcao_intensidade", "cone", "area", "linha", "laser"}
    FORMAS_PROJETIL = {"projetil", "projetil_explosivo"}

    def __init__(self, controlador_batalha, camera):
        self._controlador = controlador_batalha
        self._camera = camera
        self._leitor = LeitorAtaquesCombate()
        self._indicador = IndicadorAtaque(camera, self._leitor)
        self._montador = MontadorJogada(getattr(controlador_batalha, "obter_regras_batalha", lambda: {})())
        self._preparacao: Optional[Dict[str, object]] = None
        self._ataque_atual = None
        self._ultimo_ataque_nome = ""
        self._hover_jogada_id = None
        self._drag_pokemon = None
        self._drag_origem = None
        self._drag_destino = None
        self._drag_ativo = False
        self._fluxo_movimento = Fluxo("seta")
        dbg_combate("ControladorJogadas", "init")

    @staticmethod
    def _uid_pokemon(pokemon) -> str:
        if pokemon is None:
            return ""
        uid = str(getattr(pokemon, "Uid", "") or "")
        if uid:
            return uid
        uid = str(getattr(pokemon, "Id", "") or "")
        if uid:
            return uid
        dados = getattr(pokemon, "Dados", {}) if hasattr(pokemon, "Dados") else {}
        if isinstance(dados, dict):
            uid = str(dados.get("uid") or dados.get("id") or dados.get("ID") or "")
            if uid:
                return uid
        return f"pokemon:temp:{id(pokemon)}"

    @staticmethod
    def _nome_ataque(ataque) -> str:
        if isinstance(ataque, dict):
            for chave in ("Ataque", "Nome", "nome", "ataque"):
                nome = str(ataque.get(chave) or "").strip()
                if nome:
                    return nome
        if isinstance(ataque, str):
            return ataque.strip()
        return ""

    @staticmethod
    def _estilo_por_preparo(tipo_preparo: str, ataque) -> str:
        if tipo_preparo == "self":
            return "status"
        if tipo_preparo == "alvo":
            return "alvo"
        if tipo_preparo in {"direcao", "direcao_intensidade", "linha", "laser", "cone", "area"}:
            return "movimento" if ataque is None else "ataque"
        return "movimento"

    @staticmethod
    def _json_seguro(valor):
        if valor is None or isinstance(valor, (str, int, float, bool)):
            return valor
        if isinstance(valor, (set, tuple, list)):
            return [ControladorJogadas._json_seguro(v) for v in list(valor)]
        if isinstance(valor, dict):
            saida = {}
            for k, v in valor.items():
                chave = str(k)
                convertido = ControladorJogadas._json_seguro(v)
                saida[chave] = convertido
            return saida
        if hasattr(valor, "x") and hasattr(valor, "y"):
            try:
                return [float(getattr(valor, "x")), float(getattr(valor, "y"))]
            except (TypeError, ValueError):
                pass
        if hasattr(valor, "Uid"):
            return str(getattr(valor, "Uid"))
        if hasattr(valor, "Id"):
            return str(getattr(valor, "Id"))
        return str(valor)

    def _ataque_em_contexto(self, ficha):
        if ficha is not None and hasattr(ficha, "ataque_selecionado"):
            ataque = ficha.ataque_selecionado()
            if ataque is not None:
                self._ataque_atual = ataque
                return ataque
        return self._ataque_atual

    def _mouse_para_mundo(self, pos_tela):
        if hasattr(self._camera, "tela_para_batalha_tiles"):
            return self._camera.tela_para_batalha_tiles(pos_tela)
        return pos_tela

    def _pokemon_no_mouse(self, pos_tela):
        if self._controlador is None:
            return None
        if hasattr(self._controlador, "pokemon_no_ponto"):
            return self._controlador.pokemon_no_ponto(pos_tela, self._camera)
        return None

    def _custo_base(self, executor, ataque) -> float:
        if executor is None or not isinstance(ataque, dict):
            return 0.0
        if hasattr(executor, "custo_ataque"):
            try:
                return float(executor.custo_ataque(ataque))
            except Exception:
                return 0.0
        return float(ataque.get("Ene") or ataque.get("energia") or 0.0)

    def _alcance_da_spec(self, spec) -> float:
        if not isinstance(spec, dict):
            return 1.0
        preparo = dict(spec.get("preparo") or {})
        execucao = dict(spec.get("execucao") or {})
        dados = dict(execucao.get("dados") or {})
        for valor in (preparo.get("alcance"), execucao.get("alcance"), dados.get("alcance")):
            try:
                alcance = float(valor)
                if alcance > 0:
                    return alcance
            except (TypeError, ValueError):
                continue
        return 1.0

    def _destino_por_alcance_fixo(self, origem, mouse_mundo, spec):
        if not (isinstance(origem, (tuple, list)) and len(origem) == 2):
            return mouse_mundo
        ox, oy = float(origem[0]), float(origem[1])
        mx, my = float(mouse_mundo[0]), float(mouse_mundo[1])
        dx, dy = mx - ox, my - oy
        norma = (dx * dx + dy * dy) ** 0.5
        if norma <= 1e-8:
            prev = (self._preparacao or {}).get("destino_mundo")
            if isinstance(prev, (tuple, list)) and len(prev) == 2:
                dx, dy = float(prev[0]) - ox, float(prev[1]) - oy
                norma = (dx * dx + dy * dy) ** 0.5
        if norma <= 1e-8:
            dx, dy = 1.0, 0.0
            norma = 1.0
        alcance = self._alcance_da_spec(spec)
        destino = (ox + (dx / norma) * alcance, oy + (dy / norma) * alcance)
        dbg_combate("ControladorJogadas", "destino projetil fixo", origem_mundo=[ox, oy], mouse_mundo=[mx, my], alcance=alcance, destino=list(destino))
        return destino

    def _eh_controlavel(self, pokemon) -> bool:
        if pokemon is None or self._controlador is None:
            return False
        fn = getattr(self._controlador, "pokemon_eh_controlavel", None)
        return bool(fn(pokemon)) if callable(fn) else True

    def _iniciar_arrasto(self, pokemon, pos_tela) -> None:
        if not self._eh_controlavel(pokemon):
            return
        self._drag_pokemon = pokemon
        origem = tuple(getattr(pokemon, "Posicao", (0.0, 0.0)))
        self._drag_origem = origem
        self._drag_destino = self._mouse_para_mundo(pos_tela)
        self._drag_ativo = True
        dbg_combate("ControladorJogadas", "arrasto iniciado", executor_id=self._uid_pokemon(pokemon), origem_mundo=self._json_seguro(origem))

    def _atualizar_arrasto(self, pos_tela) -> None:
        if not self._drag_ativo:
            return
        self._drag_destino = self._mouse_para_mundo(pos_tela)

    def _encerrar_arrasto(self, pos_tela) -> bool:
        if not self._drag_ativo:
            return False
        self._drag_destino = self._mouse_para_mundo(pos_tela)
        poke = self._drag_pokemon
        origem = self._drag_origem
        destino = self._drag_destino
        self._drag_ativo = False
        self._drag_pokemon = None
        self._drag_origem = None
        self._drag_destino = None
        if poke is None or not (isinstance(origem, (tuple, list)) and isinstance(destino, (tuple, list))):
            return False
        dx = float(destino[0]) - float(origem[0])
        dy = float(destino[1]) - float(origem[1])
        if (dx * dx + dy * dy) ** 0.5 < 0.2:
            return False
        jogada = {
            "executor_id": self._uid_pokemon(poke),
            "executor_nome": str(getattr(poke, "Nome", "") or getattr(poke, "Especie", "") or ""),
            "ataque": None,
            "ataque_id": "",
            "tipo_movimento": True,
            "tipo_preparo": "linha",
            "forma": "movimento",
            "origem_mundo": self._json_seguro(origem),
            "destino_mundo": self._json_seguro(destino),
            "alvo_ids": [],
            "intensidade": 1.0,
            "custo_base": 0.0,
            "custo": 0.0,
            "estilo": "movimento",
        }
        adicionada, erro = self._montador.adicionar(jogada)
        if adicionada is None:
            dbg_combate("ControladorJogadas", "movimento arrasto ignorado", erro=erro)
            return False
        dbg_combate("ControladorJogadas", "movimento por arrasto adicionado", jogada=adicionada)
        return True

    def _nova_preparacao(self, ficha):
        executor = getattr(self._controlador, "PokemonSelecionado", None)
        if executor is None:
            dbg_combate("ControladorJogadas", "preview nao criado", motivo="sem executor")
            return None
        ataque = self._ataque_em_contexto(ficha)
        nome = self._nome_ataque(ataque)
        if not nome:
            dbg_combate("ControladorJogadas", "preview nao criado", motivo="sem ataque")
            return None
        spec = self._leitor.obter(ataque)
        dbg_combate("ControladorJogadas", "spec carregada", ataque=nome, encontrou=bool(spec))
        if not spec:
            return None

        preparo = dict(spec.get("preparo") or {})
        execucao = dict(spec.get("execucao") or {})
        tipo_preparo = str(preparo.get("tipo") or "").strip()
        if not tipo_preparo:
            return None

        origem = tuple(getattr(executor, "Posicao", (0.0, 0.0)))
        destino = None
        if tipo_preparo in self.TIPOS_PREPARO_DIRECIONAIS:
            mouse_mundo = self._mouse_para_mundo(pygame.mouse.get_pos())
            forma = str(execucao.get("forma") or "").strip()
            destino = self._destino_por_alcance_fixo(origem, mouse_mundo, spec) if forma in self.FORMAS_PROJETIL else mouse_mundo
        prep = {
            "executor": executor,
            "executor_id": self._uid_pokemon(executor),
            "ataque": ataque,
            "ataque_id": str(spec.get("id") or nome),
            "tipo_preparo": tipo_preparo,
            "forma": str(execucao.get("forma") or "").strip(),
            "estado": "preview",
            "origem_mundo": origem,
            "destino_mundo": destino,
            "alvos": [],
            "alvo_ids": [],
            "intensidade": 1.0,
            "custo_base": self._custo_base(executor, ataque),
            "spec_resumo": {
                "id": str(spec.get("id") or ""),
                "nome": str(spec.get("nome") or nome),
                "preparo": dict(spec.get("preparo") or {}),
                "execucao": dict(spec.get("execucao") or {}),
                "tags": list(spec.get("tags") or []),
            },
            "spec": spec,
        }
        dbg_combate("ControladorJogadas", "preview criado", ataque=nome, tipo_preparo=tipo_preparo, forma=prep["forma"]) 
        return prep

    def _atualizar_destino_mouse(self):
        if not isinstance(self._preparacao, dict):
            return
        tipo = str(self._preparacao.get("tipo_preparo") or "")
        if tipo not in self.TIPOS_PREPARO_DIRECIONAIS:
            return
        origem = self._preparacao.get("origem_mundo")
        mouse_mundo = self._mouse_para_mundo(pygame.mouse.get_pos())
        forma = str(self._preparacao.get("forma") or "")
        destino = self._destino_por_alcance_fixo(origem, mouse_mundo, self._preparacao.get("spec") or {}) if forma in self.FORMAS_PROJETIL else mouse_mundo
        anterior = self._preparacao.get("destino_mundo")
        self._preparacao["destino_mundo"] = destino

        if tipo == "direcao_intensidade" and isinstance(origem, (tuple, list)) and isinstance(destino, (tuple, list)):
            dx = float(destino[0]) - float(origem[0])
            dy = float(destino[1]) - float(origem[1])
            distancia = (dx * dx + dy * dy) ** 0.5
            spec_preparo = dict((self._preparacao.get("spec") or {}).get("preparo") or {})
            alcance = float(spec_preparo.get("alcance") or 1.0)
            minimo = float(spec_preparo.get("intensidade_min") or 0.2)
            maximo = float(spec_preparo.get("intensidade_max") or 1.0)
            self._preparacao["intensidade"] = max(minimo, min(maximo, distancia / max(0.0001, alcance)))
        if isinstance(anterior, (tuple, list)) and isinstance(destino, (tuple, list)):
            delta = ((float(destino[0]) - float(anterior[0])) ** 2 + (float(destino[1]) - float(anterior[1])) ** 2) ** 0.5
            if delta < 0.25:
                return
        dbg_combate("ControladorJogadas", "preview atualizado", destino=self._json_seguro(destino), forma=forma)

    def _montar_jogada_serializavel(self, preparacao: Dict[str, object]) -> Dict[str, object]:
        executor = preparacao.get("executor")
        tipo_preparo = str(preparacao.get("tipo_preparo") or "")
        ataque = preparacao.get("ataque")
        ataque_nome = self._nome_ataque(ataque)
        jogada = {
            "id": 0,
            "executor_id": str(preparacao.get("executor_id") or ""),
            "executor_nome": str(getattr(executor, "Nome", "") or getattr(executor, "Especie", "") or ""),
            "ataque": {"Ataque": ataque_nome} if ataque_nome else None,
            "ataque_id": str(preparacao.get("ataque_id") or ataque_nome),
            "tipo_preparo": tipo_preparo,
            "forma": str(preparacao.get("forma") or ""),
            "origem_mundo": self._json_seguro(preparacao.get("origem_mundo") or [0.0, 0.0]),
            "destino_mundo": self._json_seguro(preparacao.get("destino_mundo")) if preparacao.get("destino_mundo") is not None else None,
            "alvo_ids": self._json_seguro(list(preparacao.get("alvo_ids") or [])),
            "intensidade": float(preparacao.get("intensidade") or 1.0),
            "custo_base": float(preparacao.get("custo_base") or 0.0),
            "custo": float(preparacao.get("custo_base") or 0.0),
            "estilo": self._estilo_por_preparo(tipo_preparo, ataque),
            "spec_resumo": self._json_seguro(preparacao.get("spec_resumo") or {}),
        }
        return self._json_seguro(jogada)

    def _confirmar_preparacao(self) -> bool:
        if not isinstance(self._preparacao, dict):
            dbg_combate("ControladorJogadas", "confirmar ignorado", motivo="sem preparacao")
            return False
        jogada_json = self._montar_jogada_serializavel(self._preparacao)
        jogada, erro = self._montador.adicionar(jogada_json)
        if jogada is None:
            dbg_combate("ControladorJogadas", "jogada nao adicionada", erro=erro)
            return False
        dbg_combate("ControladorJogadas", "jogada adicionada", jogada=jogada)
        self._preparacao = self._nova_preparacao(None)
        return True

    def _hud_clicado(self, pos, hud_rects) -> bool:
        return any(rect.collidepoint(pos) for rect in list(hud_rects or []))

    def processar_eventos(self, eventos, ficha, hud_rects=None):
        self._atualizar_destino_mouse()
        for evento in eventos or []:
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if self._hud_clicado(evento.pos, hud_rects):
                    continue
                poke_click = self._pokemon_no_mouse(evento.pos)
                if self._eh_controlavel(poke_click):
                    self._iniciar_arrasto(poke_click, evento.pos)
                    continue
            if evento.type == pygame.MOUSEMOTION:
                self._atualizar_arrasto(getattr(evento, "pos", pygame.mouse.get_pos()))
                self._atualizar_destino_mouse()
                continue
            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                if self._encerrar_arrasto(getattr(evento, "pos", pygame.mouse.get_pos())):
                    continue
            if evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
                continue
            if self._hud_clicado(evento.pos, hud_rects):
                continue
            if not isinstance(self._preparacao, dict):
                continue
            tipo = str(self._preparacao.get("tipo_preparo") or "")
            poke = self._pokemon_no_mouse(evento.pos)
            if tipo == "alvo":
                if poke is None:
                    dbg_combate("ControladorJogadas", "evento ignorado", motivo="alvo ausente")
                    continue
                uid = self._uid_pokemon(poke)
                if uid:
                    self._preparacao["alvos"] = [poke]
                    self._preparacao["alvo_ids"] = [uid]
                    self._preparacao["destino_mundo"] = tuple(getattr(poke, "Posicao", self._preparacao.get("origem_mundo") or (0.0, 0.0)))
                    dbg_combate("ControladorJogadas", "evento consumido por preparacao", tipo=tipo, alvo_id=uid)
                    self._confirmar_preparacao()
                continue

    def preparar(self, ficha):
        dbg_combate("ControladorJogadas", "preparar clicado")
        if not isinstance(self._preparacao, dict):
            self._preparacao = self._nova_preparacao(ficha)
        if not isinstance(self._preparacao, dict):
            return "sem_ataque"
        tipo = str(self._preparacao.get("tipo_preparo") or "")
        if tipo == "alvo" and not self._preparacao.get("alvo_ids"):
            dbg_combate("ControladorJogadas", "jogada nao adicionada", motivo="falta alvo")
            return "falta_alvo"
        self._confirmar_preparacao()
        return "ok"

    def acao_principal(self, ficha):
        return self.preparar(ficha)

    def pronto(self):
        dbg_combate("ControladorJogadas", "pronto clicado")
        jogadas = [self._json_seguro(j) for j in self._montador.listar()]
        dbg_combate("ControladorJogadas", "payload antes de enviar", quantidade=len(jogadas), jogadas=jogadas)
        if not jogadas:
            return "vazio"
        contexto = getattr(getattr(self._controlador, "SistemaBatalha", None), "Contexto", {})
        if not isinstance(contexto, dict) or not contexto:
            contexto = getattr(self._controlador, "Contexto", {})
        if not isinstance(contexto, dict):
            contexto = {}
        ip = str(contexto.get("server_ip") or "")
        client_id = str(contexto.get("client_id") or "")
        batalha_id = str(contexto.get("batalha_id_servidor") or "")
        if not ip or not client_id:
            return "aguardando"
        try:
            json.dumps(jogadas, ensure_ascii=False)
            dbg_combate("ControladorJogadas", "json serializavel ok")
        except TypeError as exc:
            print("[DBG-COMBATE][ControladorJogadas] payload nao serializavel", exc, jogadas)
            raise
        resposta = enviar_jogada_batalha_server(ip=ip, client_id=client_id, jogadas=jogadas, batalha_id=batalha_id)
        dbg_combate("ControladorJogadas", "retorno recebido", retorno=resposta)
        contexto["batalha_servidor_ultimo_envio"] = resposta if isinstance(resposta, dict) else {"status": "erro"}
        self._montador.limpar()
        self._preparacao = None
        return "ok"

    def desenhar(self, tela, dt):
        self._fluxo_movimento.atualizar(float(dt or 0.0))
        selecionado_id = self._montador.selecionado_id()
        mapa = self._controlador.mapa_pokemons() if self._controlador is not None and hasattr(self._controlador, "mapa_pokemons") else {}
        visuais, _ = self._montador.resolver_visuais(mapa)
        for jogada in visuais:
            self._indicador.desenhar_jogada(tela, jogada, selecionada=(jogada.get("id") == selecionado_id), alpha=95)
        if isinstance(self._preparacao, dict):
            self._indicador.desenhar_preparacao(tela, self._preparacao, selecionada=True)
        if self._drag_ativo and isinstance(self._drag_origem, (tuple, list)) and isinstance(self._drag_destino, (tuple, list)):
            origem_tela = self._camera.batalha_para_tela_px(self._drag_origem) if hasattr(self._camera, "batalha_para_tela_px") else self._drag_origem
            destino_tela = self._camera.batalha_para_tela_px(self._drag_destino) if hasattr(self._camera, "batalha_para_tela_px") else self._drag_destino
            self._fluxo_movimento.desenhar(tela, origem_tela, destino_tela, estilo="seta", largura_trilha=4, alpha=170)

    def atualizar_contexto(self, ataque_atual):
        self._ataque_atual = ataque_atual
        nome = self._nome_ataque(ataque_atual)
        if nome != self._ultimo_ataque_nome:
            self._ultimo_ataque_nome = nome
            dbg_combate("ControladorJogadas", "ataque selecionado mudou", ataque=nome)
            self._preparacao = self._nova_preparacao(None) if nome else None
            return
        if nome and self._preparacao is None and getattr(self._controlador, "PokemonSelecionado", None) is not None:
            self._preparacao = self._nova_preparacao(None)

    def cancelar_preparacao(self):
        dbg_combate("ControladorJogadas", "cancelar preparacao")
        self._preparacao = None

    def previsao_consumo(self, pokemon, ataque):
        if pokemon is None:
            return 0.0, False
        custo_base = self._custo_base(pokemon, ataque)
        if hasattr(self._montador, "pode_adicionar"):
            permitido, _, custo_total = self._montador.pode_adicionar({"executor_id": self._uid_pokemon(pokemon), "ataque": ataque, "custo_base": custo_base})
            energia_atual = float(getattr(pokemon, "EnergiaAtual", getattr(pokemon, "Energia", 0.0)) or 0.0)
            energia_reservada = self.energia_reservada_visual(pokemon)
            return custo_total, bool(permitido and energia_atual - energia_reservada >= custo_total)
        return custo_base, True

    def energia_reservada_visual(self, pokemon):
        return self._montador.custo_reservado(self._uid_pokemon(pokemon)) if pokemon is not None else 0.0

    def listar_jogadas(self):
        return self._montador.listar()

    def remover_jogada(self, jogada_id):
        dbg_combate("ControladorJogadas", "remover jogada", jogada_id=jogada_id)
        return self._montador.remover(jogada_id)

    def definir_hover_jogada(self, jogada_id):
        self._hover_jogada_id = jogada_id

    def selecionar_jogada(self, jogada_id):
        return self._montador.selecionar(jogada_id)

    def jogada_selecionada_id(self):
        return self._montador.selecionado_id()

    def estado_botao_preparar(self, ficha):
        ataque = self._ataque_em_contexto(ficha)
        if not ataque:
            return "Preparar", False
        existe = self._leitor.existe(ataque)
        return "Preparar jogada", bool(existe)
