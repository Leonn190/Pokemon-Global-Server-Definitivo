"""Mixin de intencoes e interacoes do ControladorPlayer."""

from __future__ import annotations

from typing import Dict, Optional, Tuple
import math
import time
import uuid

import pygame


class InteracoesPlayerMixin:
    @staticmethod
    def _ator_bloqueia_batalha(ator) -> bool:
        if ator is None:
            return True
        if bool(getattr(ator, "GameOverServidor", False) or getattr(ator, "Morto", False) or getattr(ator, "SobreBuraco", False)):
            return True
        return bool(getattr(ator, "ImuneCombateAtiva", False)) or int(pygame.time.get_ticks()) < int(getattr(ator, "ImuneCombateAteMs", 0) or 0)

    def consumir_colisao_pokemon(self) -> Optional[Dict[str, object]]:
        evento = dict(self._colisao_pokemon_pendente) if isinstance(self._colisao_pokemon_pendente, dict) else None
        self._colisao_pokemon_pendente = None
        return evento

    def _detectar_colisao_pokemon_proxima(self) -> None:
        ator = self._player_local
        if ator is None:
            return
        if self._ator_bloqueia_batalha(ator):
            self._colisao_pokemon_pendente = None
            return
        pos = tuple(ator.Posicao)
        player_id = getattr(ator, "Id", None)
        raio_ator = max(0.0, float(getattr(getattr(ator, "Colisor", None), "raio_colisao", 0.35)))
        for c in self._objetos.iter_colisores_proximos_por_raio(pos, raio_tiles=2.0):
            oid, sx, sy, raio_obj, tipo_obj, *_ = c
            if int(oid) == int(player_id or -1):
                continue
            if str(tipo_obj).strip().lower() not in {"entidade_pokemon", "pokemon"}:
                continue
            payload = self._objetos.snapshot_objeto_por_id(int(oid))
            estado = payload.get("estado") if isinstance(payload, dict) and isinstance(payload.get("estado"), dict) else {}
            comportamento = str(estado.get("comportamento_mundo") or estado.get("comportamento") or estado.get("tipo_batalha") or "").strip().lower()
            ameacador = bool(estado.get("esta_irritado", False)) or comportamento in {"perseguindo", "servo", "boss"}
            limite = raio_ator + float(raio_obj) + (0.70 if ameacador else 0.05)
            d2 = (float(sx) - float(pos[0])) ** 2 + (float(sy) - float(pos[1])) ** 2
            if d2 <= limite * limite:
                if isinstance(payload, dict) and payload:
                    self._colisao_pokemon_pendente = payload
                else:
                    self._colisao_pokemon_pendente = {"id": int(oid), "posicao": [float(sx), float(sy)]}
                return

    def _spec_projetil(self, item: Dict[str, object]) -> Tuple[str, float, float]:
        regras = self._regras()
        proj = regras.get("projeteis") if isinstance(regras.get("projeteis"), dict) else {}
        estilo = str(item.get("Estilo") or item.get("estilo") or "item").strip().lower()
        nome = str(item.get("Nome") or "").strip().lower()
        if estilo == "fruta":
            velocidade, alcance = self._calcular_parametros_projetil_client(proj, "fruta", "fruta", mirando=False)
            return ("fruta", velocidade, alcance)

        variante = "pokebola"
        if "sniperball" in nome:
            variante = "sniperball"
        elif "fastball" in nome:
            variante = "fastball"
        velocidade, alcance = self._calcular_parametros_projetil_client(proj, "pokebola", variante, mirando=False)
        return (variante, velocidade, alcance)

    @staticmethod
    def _calcular_parametros_projetil_client(regras: Dict[str, object], subtipo: str, variante: str, mirando: bool = False) -> Tuple[float, float]:
        d = dict(regras or {})

        def _g(chave: str, default: float) -> float:
            try:
                return float(d.get(chave, default))
            except Exception:
                return float(default)

        subtipo_norm = str(subtipo or "").strip().lower()
        variante_norm = str(variante or "").strip().lower()
        if subtipo_norm == "fruta":
            velocidade = _g("velocidade_fruta_tiles_s", 6.0)
            alcance = _g("alcance_fruta_tiles", 6.0)
        elif variante_norm == "sniperball":
            velocidade = _g("velocidade_sniperball_tiles_s", 8.0)
            alcance = _g("alcance_sniperball_tiles", 9.0)
        elif variante_norm == "fastball":
            velocidade = _g("velocidade_fastball_tiles_s", 10.0)
            alcance = _g("alcance_fastball_tiles", 7.0)
        else:
            velocidade = _g("velocidade_pokebola_tiles_s", 7.0)
            alcance = _g("alcance_pokebola_tiles", 7.0)
        if bool(mirando):
            velocidade *= _g("mira_multiplicador_velocidade", 1.10)
            alcance *= _g("mira_multiplicador_alcance", 1.15)
        return (float(velocidade), float(alcance))

    def _processar_intencao_arremesso_local(self) -> None:
        if self._player_local is None or self._player_local.Controle is None:
            return

        acao = self._player_local.Controle.consumir_acao_arremesso()
        if isinstance(acao, dict):
            self._player_local.iniciar_tapa()
            self._arremesso_pendente = {"acao": acao, "ts": time.monotonic()}

        if not isinstance(self._arremesso_pendente, dict):
            return
        if not self._player_local.esta_tapando():
            return

        progresso = float(self._player_local._progresso_tapa()) if hasattr(self._player_local, "_progresso_tapa") else 0.5
        atraso = time.monotonic() - float(self._arremesso_pendente.get("ts", time.monotonic()))
        if progresso < 0.45 and atraso < 0.14:
            return

        acao = dict(self._arremesso_pendente.get("acao") or {})
        self._arremesso_pendente = None

        item = dict(acao.get("item") or {})
        origem_acao = acao.get("origem") if isinstance(acao.get("origem"), (list, tuple)) else tuple(self._player_local.Posicao)
        origem = self._player_local.ponto_mao_direita_mundo(usar_alcance_tapa=True) if hasattr(self._player_local, "ponto_mao_direita_mundo") else tuple(origem_acao)
        destino_click = acao.get("destino") if isinstance(acao.get("destino"), (list, tuple)) else tuple(self._player_local.Posicao)

        variante, _, _ = self._spec_projetil(item)
        regras = self._regras()
        proj = regras.get("projeteis") if isinstance(regras.get("projeteis"), dict) else {}
        subtipo = "fruta" if variante == "fruta" else "pokebola"
        velocidade, alcance = self._calcular_parametros_projetil_client(proj, subtipo, variante, mirando=bool(acao.get("mirando", False)))
        perfil = getattr(self._player_local, "Perfil", None)
        velocidade *= float(getattr(perfil, "MultiplicadorVelocidadeProjetil", 1.0) or 1.0)
        alcance *= float(getattr(perfil, "MultiplicadorAlcanceProjetil", 1.0) or 1.0)
        dx, dy = float(destino_click[0]) - float(origem[0]), float(destino_click[1]) - float(origem[1])
        n = math.hypot(dx, dy) or 1.0
        direcao = (dx / n, dy / n)
        destino = (float(origem[0]) + direcao[0] * alcance, float(origem[1]) + direcao[1] * alcance)
        token = str(uuid.uuid4())

        self._seq_id_projetil_predito -= 1
        oid = self._seq_id_projetil_predito
        payload_pred = {
            "id": oid,
            "tipo": "entidade_projetil",
            "tipo_projetil": "fruta" if variante == "fruta" else "pokebola",
            "subtipo": variante,
            "item_base_id": str(item.get("Code") or ""),
            "item_nome": str(item.get("Nome") or ""),
            "dono_id": int(getattr(self._player_local, "Id", 0) or 0),
            "posicao": [float(origem[0]), float(origem[1])],
            "estado": {
                "direcao": [direcao[0], direcao[1]],
                "velocidade": velocidade,
                "alcance": alcance,
                "predito_local": True,
                "token_arremesso": token,
                "pos_final": [float(destino[0]), float(destino[1])],
            },
            "token_arremesso": token,
        }
        self._objetos.aplicar_diff({"tipo": "spawn", "objeto_id": oid, "payload": payload_pred})

        self._objetos.EnfileirarDiffRapida({
            "tipo": "spawn",
            "categoria": "arremesso_visual",
            "payload": {
                "token": token,
                "subtipo_projetil": "fruta" if variante == "fruta" else "pokebola",
                "variante": variante,
                "item": str(item.get("Nome") or ""),
                "item_base_id": str(item.get("Code") or ""),
                "item_nome": str(item.get("Nome") or ""),
                "mirando": bool(acao.get("mirando", False)),
                "pos_inicial": [float(origem[0]), float(origem[1])],
                "pos_final": [float(destino[0]), float(destino[1])],
                "velocidade_tiles_s": velocidade,
                "instante_cliente_ms": int(time.time() * 1000),
                "dono_id": int(getattr(self._player_local, "Id", 0) or 0),
                "dono_nome": str(getattr(self._player_local, "Nome", "") or ""),
            },
        })

    def _processar_intencao_drop_item_mundo(self) -> None:
        if self._player_local is None or self._player_local.Controle is None:
            return

        acao = self._player_local.Controle.consumir_acao_drop_item_mundo()
        if not isinstance(acao, dict):
            return

        item = dict(acao.get("item") or {})
        if not item:
            return

        origem = acao.get("origem") if isinstance(acao.get("origem"), (list, tuple)) else tuple(self._player_local.Posicao)
        ang = math.radians(float(getattr(self._player_local, "AnguloOlhar", 0.0) or 0.0))
        direcao = (math.cos(ang), -math.sin(ang))
        destino = (float(origem[0]) + direcao[0] * 1.0, float(origem[1]) + direcao[1] * 1.0)
        regras = self._regras()
        proj = regras.get("projeteis") if isinstance(regras.get("projeteis"), dict) else {}
        velocidade = float(proj.get("velocidade_item_mundo_tiles_s", 3.0) or 3.0)
        perfil = getattr(self._player_local, "Perfil", None)
        velocidade *= float(getattr(perfil, "MultiplicadorVelocidadeProjetil", 1.0) or 1.0)
        quantidade = max(1, int(item.get("quantidade", 1) or 1))

        token = str(uuid.uuid4())
        dimensao = str(self._objetos.dimensao_atual_client() or "Mundo")

        self._seq_id_projetil_predito -= 1
        oid = self._seq_id_projetil_predito
        payload_pred = {
            "id": oid,
            "tipo": "entidade_item_mundo",
            "item_nome": str(item.get("Nome") or "Item"),
            "item_base_id": str(item.get("Code") or ""),
            "quantidade": quantidade,
            "dono_id": int(getattr(self._player_local, "Id", 0) or 0),
            "token_drop": token,
            "posicao": [float(origem[0]), float(origem[1])],
            "estado": {
                "subtipo": "item_mundo",
                "dimensao": dimensao,
                "pos_inicial": [float(origem[0]), float(origem[1])],
                "pos_final": [float(destino[0]), float(destino[1])],
                "velocidade": float(velocidade),
                "voando": True,
                "token_drop": token,
                "predito_local": True,
            },
        }
        self._objetos.aplicar_diff({"tipo": "spawn", "objeto_id": oid, "payload": payload_pred})

        self._objetos.EnfileirarDiffRapida({
            "tipo": "spawn",
            "categoria": "item_mundo_drop",
            "payload": {
                "token": token,
                "dono_id": int(getattr(self._player_local, "Id", 0) or 0),
                "item": {
                    "Code": str(item.get("Code") or ""),
                    "Nome": str(item.get("Nome") or "Item"),
                    "quantidade": quantidade,
                },
                "quantidade": quantidade,
                "dimensao": dimensao,
                "pos_inicial": [float(origem[0]), float(origem[1])],
                "pos_final": [float(destino[0]), float(destino[1])],
                "velocidade_tiles_s": float(velocidade),
                "instante_cliente_ms": int(time.time() * 1000),
            },
        })

    def _processar_intencao_coleta_estrutura(self) -> None:
        ator = self._player_local
        if ator is None:
            return
        if not bool(getattr(ator.ColisorMao, "ativo", False)):
            self._coleta_tapa_enviada = False
            return
        if self._coleta_tapa_enviada:
            return
        progresso = float(ator._progresso_tapa()) if hasattr(ator, "_progresso_tapa") else 0.0
        if progresso < 0.40:
            return

        colisor_mao = getattr(ator, "ColisorMao", None)
        if colisor_mao is None:
            return
        alvos = self._objetos.estruturas_colidindo((float(colisor_mao.x), float(colisor_mao.y)), float(colisor_mao.raio_colisao))
        baus = self._objetos.baus_colidindo((float(colisor_mao.x), float(colisor_mao.y)), float(colisor_mao.raio_colisao))
        if not alvos and not baus:
            alvo = self._objetos.alvo_interagivel_atual(
                pos_player=(float(colisor_mao.x), float(colisor_mao.y)),
                dimensao_player=str(self._objetos.dimensao_atual_client() or "Mundo"),
            )
            if isinstance(alvo, dict) and str(alvo.get("tipo") or "") == "dungeon_porta_trancada":
                self._coleta_tapa_enviada = True
                self._objetos.EnfileirarDiffRapida({
                    "tipo": "evento",
                    "categoria": "interacao_dungeon",
                    "payload": {
                        "acao": "destrancar_porta",
                        "porta_id": str(alvo.get("porta_id") or ""),
                        "pos_mao": [float(colisor_mao.x), float(colisor_mao.y)],
                        "instante_cliente_ms": int(time.time() * 1000),
                    },
                })
            return
        self._coleta_tapa_enviada = True
        instante = int(time.time() * 1000)
        for alvo in alvos:
            self._objetos.EnfileirarDiffRapida({
                "tipo": "evento",
                "categoria": "coleta_estrutura_natural",
                "payload": {
                    "estrutura_id": int(alvo.get("id", 0) or 0),
                    "pos_mao": [float(colisor_mao.x), float(colisor_mao.y)],
                    "instante_cliente_ms": instante,
                },
            })
        for bau in baus:
            bau_id = int(bau.get("id", 0) or 0)
            bau_local = self._objetos.BausPorId.get(bau_id)
            if bau_local is not None and (not bool(getattr(bau_local, "Aberto", False))):
                bau_local.AguardandoConfirmacaoAbertura = True
                bau_local._aguardando_desde_ms = int(pygame.time.get_ticks())
            self._objetos.EnfileirarDiffRapida({
                "tipo": "evento",
                "categoria": "interacao_bau",
                "payload": {
                    "bau_id": bau_id,
                    "pos_mao": [float(colisor_mao.x), float(colisor_mao.y)],
                    "instante_cliente_ms": instante,
                },
            })

    def _processar_intencao_interacao_estadio(self) -> None:
        if self._player_local is None or self._player_local.Controle is None:
            return
        acao = self._player_local.Controle.consumir_acao_interacao()
        if not isinstance(acao, dict):
            return
        pos = tuple(self._player_local.Posicao)
        player_payload = self._objetos.ObjetosPorId.get(int(getattr(self._player_local, "Id", 0) or 0), {}) if isinstance(self._objetos.ObjetosPorId, dict) else {}
        estado_player = player_payload.get("estado") if isinstance(player_payload.get("estado"), dict) else {}
        dim = self._objetos._dimensao_player_local()
        alvo = self._objetos.alvo_interagivel_atual(
            pos_player=pos,
            dimensao_player=dim,
            estadio_atual_id=int(estado_player.get("estadio_atual_id", 0) or 0),
        )
        if not isinstance(alvo, dict):
            return
        tipo_alvo = str(alvo.get("tipo") or "")

        if tipo_alvo == "estadio_saida":
            estadio = alvo.get("estadio") if isinstance(alvo.get("estadio"), dict) else {}
            self._objetos.EnfileirarDiffRapida({
                "tipo": "evento",
                "categoria": "interacao_estadio",
                "payload": {
                    "acao": "sair",
                    "estadio_id": int(estadio.get("id", 0) or 0),
                    "instante_cliente_ms": int(time.time() * 1000),
                    "pos_player": [float(pos[0]), float(pos[1])],
                },
            })
            return

        if tipo_alvo != "estadio_entrada":
            return
        estadio = alvo.get("estadio") if isinstance(alvo.get("estadio"), dict) else {}
        estado = estadio.get("estado") if isinstance(estadio.get("estado"), dict) else {}
        self._objetos.EnfileirarDiffRapida({
            "tipo": "evento",
            "categoria": "interacao_estadio",
            "payload": {
                "acao": "entrar",
                "estadio_id": int(estadio.get("id", 0) or 0),
                "dimensao_destino": str(estado.get("dimensao_destino") or "EstadioNormal"),
                "instante_cliente_ms": int(time.time() * 1000),
            },
        })

    def _processar_intencao_evoluir_pokemon(self) -> None:
        if self._player_local is None or self._player_local.Controle is None:
            return
        acao = self._player_local.Controle.consumir_acao_evoluir_pokemon()
        if not isinstance(acao, dict):
            return
        chave = str(acao.get("chave_pokemon") or "").strip()
        if not chave:
            return
        self._objetos.EnfileirarDiffRapida({
            "tipo": "evento",
            "categoria": "pokemon_evoluir",
            "payload": {
                "chave_pokemon": chave,
                "instante_cliente_ms": int(time.time() * 1000),
            },
        })
