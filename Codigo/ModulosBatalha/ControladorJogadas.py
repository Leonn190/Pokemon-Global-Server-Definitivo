from __future__ import annotations

from typing import Dict, List, Optional

import pygame

from Codigo.ModulosBatalha.IndicadorAtaque import IndicadorAtaque
from Codigo.ModulosBatalha.LeitorAtaquesCombate import LeitorAtaquesCombate
from Codigo.ModulosBatalha.MontadorJogada import MontadorJogada
from Codigo.Server.ServerBatalha import enviar_jogada_batalha_server


class ControladorJogadas:
    TIPOS_PREPARO_DIRECIONAIS = {"direcao", "direcao_intensidade", "cone", "area", "linha", "laser"}

    def __init__(self, controlador_batalha, camera):
        self._controlador = controlador_batalha
        self._camera = camera
        self._leitor = LeitorAtaquesCombate()
        self._indicador = IndicadorAtaque(camera, self._leitor)
        self._montador = MontadorJogada(getattr(controlador_batalha, "obter_regras_batalha", lambda: {})())
        self._preparacao: Optional[Dict[str, object]] = None
        self._ataque_atual = None
        self._hover_jogada_id = None

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

    def _tipo_preparo_atual(self, ataque) -> str:
        spec = self._leitor.obter(ataque)
        preparo = dict(spec.get("preparo") or {})
        return str(preparo.get("tipo") or "").strip()

    def _nova_preparacao(self, ficha):
        executor = getattr(self._controlador, "PokemonSelecionado", None)
        if executor is None:
            return None
        ataque = self._ataque_em_contexto(ficha)
        nome = self._nome_ataque(ataque)
        if not nome:
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
        destino = self._mouse_para_mundo(pygame.mouse.get_pos()) if tipo_preparo in self.TIPOS_PREPARO_DIRECIONAIS else None
        return {
            "executor": executor,
            "executor_id": self._uid_pokemon(executor),
            "ataque": ataque,
            "ataque_id": str(spec.get("id") or ""),
            "spec": spec,
            "tipo_preparo": tipo_preparo,
            "forma": str(execucao.get("forma") or "").strip(),
            "estado": "preparando",
            "origem_mundo": origem,
            "destino_mundo": destino,
            "alvos": [],
            "alvo_ids": [],
            "intensidade": 1.0,
            "custo_base": self._custo_base(executor, ataque),
        }

    def _atualizar_destino_mouse(self):
        if not isinstance(self._preparacao, dict):
            return
        tipo = str(self._preparacao.get("tipo_preparo") or "")
        if tipo not in self.TIPOS_PREPARO_DIRECIONAIS:
            return
        destino = self._mouse_para_mundo(pygame.mouse.get_pos())
        self._preparacao["destino_mundo"] = destino
        if tipo == "direcao_intensidade":
            origem = self._preparacao.get("origem_mundo")
            if isinstance(origem, (tuple, list)) and isinstance(destino, (tuple, list)):
                dx = float(destino[0]) - float(origem[0])
                dy = float(destino[1]) - float(origem[1])
                distancia = (dx * dx + dy * dy) ** 0.5
                spec_preparo = dict(self._preparacao.get("spec", {}).get("preparo") or {})
                alcance = float(spec_preparo.get("alcance") or 1.0)
                minimo = float(spec_preparo.get("intensidade_min") or 0.2)
                maximo = float(spec_preparo.get("intensidade_max") or 1.0)
                intensidade = max(minimo, min(maximo, distancia / max(0.0001, alcance)))
                self._preparacao["intensidade"] = intensidade

    def _montar_jogada(self, preparacao: Dict[str, object]) -> Dict[str, object]:
        executor = preparacao.get("executor")
        tipo_preparo = str(preparacao.get("tipo_preparo") or "")
        ataque = preparacao.get("ataque")
        return {
            "executor": executor,
            "id": 0,
            "executor_id": str(preparacao.get("executor_id") or ""),
            "executor_nome": str(getattr(executor, "Nome", "") or getattr(executor, "Especie", "") or ""),
            "ataque": ataque,
            "ataque_id": str(preparacao.get("ataque_id") or ""),
            "tipo_preparo": tipo_preparo,
            "forma": str(preparacao.get("forma") or ""),
            "origem_mundo": list(preparacao.get("origem_mundo") or [0.0, 0.0]),
            "destino_mundo": list(preparacao.get("destino_mundo")) if isinstance(preparacao.get("destino_mundo"), (tuple, list)) else None,
            "alvo_ids": [str(v) for v in list(preparacao.get("alvo_ids") or [])],
            "intensidade": float(preparacao.get("intensidade") or 1.0),
            "custo_base": float(preparacao.get("custo_base") or 0.0),
            "custo": float(preparacao.get("custo_base") or 0.0),
            "estilo": self._estilo_por_preparo(tipo_preparo, ataque),
        }

    def _confirmar_preparacao(self) -> bool:
        if not isinstance(self._preparacao, dict):
            return False
        jogada, erro = self._montador.adicionar(self._montar_jogada(self._preparacao))
        if jogada is None:
            return False
        self._preparacao = None
        return True

    def _hud_clicado(self, pos, hud_rects) -> bool:
        return any(rect.collidepoint(pos) for rect in list(hud_rects or []))

    def processar_eventos(self, eventos, ficha, hud_rects=None):
        self._atualizar_destino_mouse()
        for evento in eventos or []:
            if evento.type == pygame.MOUSEMOTION:
                self._atualizar_destino_mouse()
                continue
            if evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
                continue
            if self._hud_clicado(evento.pos, hud_rects):
                continue

            poke = self._pokemon_no_mouse(evento.pos)
            if isinstance(self._preparacao, dict):
                tipo = str(self._preparacao.get("tipo_preparo") or "")
                if tipo == "alvo" and poke is not None:
                    uid = self._uid_pokemon(poke)
                    if uid:
                        self._preparacao["alvos"] = [poke]
                        self._preparacao["alvo_ids"] = [uid]
                        self._preparacao["destino_mundo"] = tuple(getattr(poke, "Posicao", self._preparacao.get("origem_mundo") or (0.0, 0.0)))
                        self._confirmar_preparacao()
                    continue
                if tipo in self.TIPOS_PREPARO_DIRECIONAIS:
                    self._preparacao["estado"] = "estabilizado"
                    self._preparacao["destino_mundo"] = self._mouse_para_mundo(evento.pos)
                    self._confirmar_preparacao()
                    continue
                if tipo == "self":
                    self._confirmar_preparacao()
                    continue
            else:
                if poke is not None:
                    if self._controlador is not None and hasattr(self._controlador, "selecionar_pokemon"):
                        self._controlador.selecionar_pokemon(poke)
                elif self._controlador is not None and hasattr(self._controlador, "limpar_selecao"):
                    self._controlador.limpar_selecao()

    def preparar(self, ficha):
        self._preparacao = self._nova_preparacao(ficha)
        if not isinstance(self._preparacao, dict):
            return "sem_ataque"
        if str(self._preparacao.get("tipo_preparo") or "") == "self":
            self._confirmar_preparacao()
            return "ok"
        return "preparando"

    def acao_principal(self, ficha):
        if self._preparacao is not None:
            return self._confirmar_preparacao()
        return self.preparar(ficha)

    def pronto(self):
        jogadas = self._montador.listar()
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
        resposta = enviar_jogada_batalha_server(ip=ip, client_id=client_id, jogadas=jogadas, batalha_id=batalha_id)
        contexto["batalha_servidor_ultimo_envio"] = resposta if isinstance(resposta, dict) else {"status": "erro"}
        self._montador.limpar()
        self._preparacao = None
        return "ok"

    def desenhar(self, tela, dt):
        _ = dt
        selecionado_id = self._montador.selecionado_id()
        mapa = self._controlador.mapa_pokemons() if self._controlador is not None and hasattr(self._controlador, "mapa_pokemons") else {}
        visuais, _ = self._montador.resolver_visuais(mapa)
        for jogada in visuais:
            self._indicador.desenhar_jogada(tela, jogada, selecionada=(jogada.get("id") == selecionado_id), alpha=95)
        if isinstance(self._preparacao, dict):
            self._indicador.desenhar_preparacao(tela, self._preparacao, selecionada=True)

    def atualizar_contexto(self, ataque_atual):
        self._ataque_atual = ataque_atual

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
        return self._montador.remover(jogada_id)

    def definir_hover_jogada(self, jogada_id):
        self._hover_jogada_id = jogada_id

    def selecionar_jogada(self, jogada_id):
        return self._montador.selecionar(jogada_id)

    def jogada_selecionada_id(self):
        return self._montador.selecionado_id()

    def estado_botao_preparar(self, ficha):
        if self._preparacao is not None:
            return "Confirmar", True
        ataque = self._ataque_em_contexto(ficha)
        if not ataque:
            return "Preparar", False
        existe = self._leitor.existe(ataque)
        return "Preparar", bool(existe)
