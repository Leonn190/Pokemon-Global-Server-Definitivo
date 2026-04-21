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

        self._drag_ativo = False
        self._drag_candidato = None
        self._drag_origem = None
        self._drag_destino = None
        self._drag_inicio_tela = None
        self._fluxo_movimento = Fluxo("seta")
        self._limiar_drag_px = 6.0
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
        if tipo_preparo == "movimento":
            return "movimento"
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
            return {str(k): ControladorJogadas._json_seguro(v) for k, v in valor.items()}
        if hasattr(valor, "x") and hasattr(valor, "y"):
            try:
                return [float(getattr(valor, "x")), float(getattr(valor, "y"))]
            except Exception:
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

    def _eh_controlavel(self, pokemon) -> bool:
        if pokemon is None or self._controlador is None:
            return False
        fn = getattr(self._controlador, "pokemon_eh_controlavel", None)
        return bool(fn(pokemon)) if callable(fn) else True

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
                f = float(valor)
                if f > 0:
                    return f
            except Exception:
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
            dx, dy, norma = 1.0, 0.0, 1.0
        alcance = self._alcance_da_spec(spec)
        destino = (ox + (dx / norma) * alcance, oy + (dy / norma) * alcance)
        return destino

    def _nova_preparacao(self, ficha):
        executor = getattr(self._controlador, "PokemonSelecionado", None)
        ataque = self._ataque_em_contexto(ficha)
        nome = self._nome_ataque(ataque)
        if executor is None or not nome:
            return None
        spec = self._leitor.obter(ataque)
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
        dbg_combate("ControladorJogadas", "preview criado", ataque=nome, forma=prep.get("forma"))
        return prep

    def _fixar_mira(self, pos_tela) -> bool:
        if not isinstance(self._preparacao, dict):
            return False
        tipo = str(self._preparacao.get("tipo_preparo") or "")
        if tipo not in self.TIPOS_PREPARO_DIRECIONAIS:
            return False
        origem = self._preparacao.get("origem_mundo")
        mouse_mundo = self._mouse_para_mundo(pos_tela)
        forma = str(self._preparacao.get("forma") or "")
        destino = self._destino_por_alcance_fixo(origem, mouse_mundo, self._preparacao.get("spec") or {}) if forma in self.FORMAS_PROJETIL else mouse_mundo
        self._preparacao["destino_mundo"] = destino
        self._preparacao["estado"] = "estabilizado"
        if tipo == "direcao_intensidade" and isinstance(origem, (tuple, list)) and isinstance(destino, (tuple, list)):
            dx = float(destino[0]) - float(origem[0])
            dy = float(destino[1]) - float(origem[1])
            distancia = (dx * dx + dy * dy) ** 0.5
            spec_preparo = dict((self._preparacao.get("spec") or {}).get("preparo") or {})
            alcance = float(spec_preparo.get("alcance") or 1.0)
            minimo = float(spec_preparo.get("intensidade_min") or 0.2)
            maximo = float(spec_preparo.get("intensidade_max") or 1.0)
            self._preparacao["intensidade"] = max(minimo, min(maximo, distancia / max(0.0001, alcance)))
        dbg_combate("ControladorJogadas", "mira fixada", tipo=tipo, destino=self._json_seguro(destino))
        return True

    def _atualizar_destino_mouse(self):
        if not isinstance(self._preparacao, dict):
            return
        if str(self._preparacao.get("estado") or "preview") != "preview":
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
        if isinstance(anterior, (tuple, list)) and isinstance(destino, (tuple, list)):
            delta = ((float(destino[0]) - float(anterior[0])) ** 2 + (float(destino[1]) - float(anterior[1])) ** 2) ** 0.5
            if delta < 0.30:
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

    def _montar_jogada_movimento(self, pokemon, origem, destino):
        return self._json_seguro(
            {
                "executor_id": self._uid_pokemon(pokemon),
                "executor_nome": str(getattr(pokemon, "Nome", "") or getattr(pokemon, "Especie", "") or ""),
                "tipo_movimento": True,
                "tipo_preparo": "movimento",
                "forma": "movimento",
                "origem_mundo": origem,
                "destino_mundo": destino,
                "alvo_ids": [],
                "intensidade": 1.0,
                "custo_base": 0.0,
                "custo": 0.0,
                "estilo": "movimento",
            }
        )

    def _confirmar_preparacao(self, ficha=None) -> bool:
        if not isinstance(self._preparacao, dict):
            return False
        estado = str(self._preparacao.get("estado") or "preview")
        jogada_json = self._montar_jogada_serializavel(self._preparacao)
        jogada, erro = self._montador.adicionar(jogada_json)
        if jogada is None:
            dbg_combate("ControladorJogadas", "jogada nao adicionada", erro=erro)
            return False
        dbg_combate("ControladorJogadas", f"preparar confirmou {estado}", jogada_id=jogada.get("id"))
        self._preparacao = None
        self._ataque_atual = None
        self._ultimo_ataque_nome = ""
        if ficha is not None and hasattr(ficha, "limpar_ataque_selecionado"):
            ficha.limpar_ataque_selecionado()
        return True

    def _hud_clicado(self, pos, hud_rects) -> bool:
        return any(rect.collidepoint(pos) for rect in list(hud_rects or []))

    def _iniciar_drag_candidato(self, pokemon, pos_tela):
        self._drag_candidato = pokemon
        self._drag_inicio_tela = tuple(pos_tela)
        self._drag_origem = tuple(getattr(pokemon, "Posicao", (0.0, 0.0)))
        self._drag_destino = self._drag_origem
        self._drag_ativo = False

    def _atualizar_drag(self, pos_tela):
        if self._drag_candidato is None or self._drag_inicio_tela is None:
            return
        dx = float(pos_tela[0]) - float(self._drag_inicio_tela[0])
        dy = float(pos_tela[1]) - float(self._drag_inicio_tela[1])
        if not self._drag_ativo and (dx * dx + dy * dy) ** 0.5 >= self._limiar_drag_px:
            self._drag_ativo = True
            dbg_combate("ControladorJogadas", "arrasto iniciado", executor_id=self._uid_pokemon(self._drag_candidato))
        if self._drag_ativo:
            self._drag_destino = self._mouse_para_mundo(pos_tela)

    def _encerrar_drag(self, pos_tela) -> bool:
        if self._drag_candidato is None:
            return False
        pokemon = self._drag_candidato
        origem = self._drag_origem
        self._atualizar_drag(pos_tela)
        destino = self._drag_destino if self._drag_ativo else origem
        foi_drag = bool(self._drag_ativo)
        self._drag_candidato = None
        self._drag_inicio_tela = None
        self._drag_ativo = False
        self._drag_origem = None
        self._drag_destino = None
        if not foi_drag or pokemon is None:
            if pokemon is not None and self._controlador is not None and hasattr(self._controlador, "selecionar_pokemon"):
                self._controlador.selecionar_pokemon(pokemon)
            return False
        jogada = self._montar_jogada_movimento(pokemon, self._json_seguro(origem), self._json_seguro(destino))
        adicionada, erro = self._montador.adicionar(jogada)
        if adicionada is None:
            dbg_combate("ControladorJogadas", "movimento por arrasto ignorado", erro=erro)
            return True
        dbg_combate("ControladorJogadas", "movimento por arrasto adicionado", jogada_id=adicionada.get("id"))
        return True

    def processar_eventos(self, eventos, ficha, hud_rects=None):
        self._atualizar_destino_mouse()
        for evento in eventos or []:
            if evento.type == pygame.MOUSEMOTION:
                self._atualizar_drag(getattr(evento, "pos", pygame.mouse.get_pos()))
                self._atualizar_destino_mouse()
                continue

            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if self._hud_clicado(evento.pos, hud_rects):
                    continue
                poke_click = self._pokemon_no_mouse(evento.pos)
                if self._eh_controlavel(poke_click):
                    self._iniciar_drag_candidato(poke_click, evento.pos)
                    continue
                if isinstance(self._preparacao, dict):
                    if str(self._preparacao.get("tipo_preparo") or "") == "alvo" and poke_click is not None:
                        uid = self._uid_pokemon(poke_click)
                        if uid:
                            self._preparacao["alvos"] = [poke_click]
                            self._preparacao["alvo_ids"] = [uid]
                            self._preparacao["destino_mundo"] = tuple(getattr(poke_click, "Posicao", self._preparacao.get("origem_mundo") or (0.0, 0.0)))
                            self._preparacao["estado"] = "estabilizado"
                            dbg_combate("ControladorJogadas", "mira fixada", tipo="alvo", alvo_id=uid)
                    else:
                        self._fixar_mira(evento.pos)
                continue

            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                if self._encerrar_drag(getattr(evento, "pos", pygame.mouse.get_pos())):
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
        return "ok" if self._confirmar_preparacao(ficha) else "erro"

    def acao_principal(self, ficha):
        return self.preparar(ficha)

    def pronto(self, forcar_envio_vazio: bool = False):
        dbg_combate("ControladorJogadas", "pronto clicado")
        jogadas = [self._json_seguro(j) for j in self._montador.listar()]
        dbg_combate("ControladorJogadas", "payload antes de enviar", quantidade=len(jogadas))
        if not jogadas:
            if forcar_envio_vazio:
                dbg_combate("ControladorJogadas", "pronto forçado enviou vazio")
            else:
                dbg_combate("ControladorJogadas", "pronto manual sem jogadas retornou vazio")
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
        json.dumps(jogadas, ensure_ascii=False)
        resposta = enviar_jogada_batalha_server(ip=ip, client_id=client_id, jogadas=jogadas, batalha_id=batalha_id)
        dbg_combate("ControladorJogadas", "retorno recebido", status=str((resposta or {}).get("status")))
        resposta_dict = resposta if isinstance(resposta, dict) else {"status": "erro"}
        if isinstance(resposta_dict, dict) and self._controlador is not None and hasattr(self._controlador, "atualizar_estado_servidor"):
            self._controlador.atualizar_estado_servidor(resposta_dict)
        salvou_controlador = False
        salvou_sistema = False
        if isinstance(getattr(self._controlador, "Contexto", None), dict):
            self._controlador.Contexto["batalha_servidor_ultimo_envio"] = resposta_dict
            salvou_controlador = True
        ctx_sistema = getattr(getattr(self._controlador, "SistemaBatalha", None), "Contexto", None)
        if isinstance(ctx_sistema, dict):
            ctx_sistema["batalha_servidor_ultimo_envio"] = resposta_dict
            salvou_sistema = True
        dbg_combate("ControladorJogadas", "resposta salva nos contextos", controlador=salvou_controlador, sistema=salvou_sistema)
        self._montador.limpar()
        dbg_combate("ControladorJogadas", "montador limpo")
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
        mudou = nome != self._ultimo_ataque_nome
        if mudou:
            self._ultimo_ataque_nome = nome
            dbg_combate("ControladorJogadas", "ataque selecionado mudou", ataque=nome)
        if nome and (mudou or self._preparacao is None) and getattr(self._controlador, "PokemonSelecionado", None) is not None:
            self._preparacao = self._nova_preparacao(None)
        elif not nome and mudou:
            self._preparacao = None

    def cancelar_preparacao(self):
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
        return "Preparar jogada", bool(self._leitor.existe(ataque))
