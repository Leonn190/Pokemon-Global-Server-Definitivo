"""Controlador dedicado ao player local."""

from __future__ import annotations

from typing import Dict, Optional, Tuple
import math
import time
import uuid

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Geradores.Player.Controle import Controle
from Codigo.Geradores.Player.Inventario import Inventario
from Codigo.Geradores.Player.Perfil import Perfil
from Codigo.Modulos.Colisor import Colisor
from Codigo.Prefabs.Fluxos import Fluxo


class ControladorPlayer:
    def __init__(self, controlador_objetos):
        self._objetos = controlador_objetos
        self._player_local = None
        self._client_id_local = ""
        self._fluxo_mira = Fluxo("bolinhas")
        self._seq_id_projetil_predito = -1
        self._bloqueio_correcao_servidor_ate = 0.0
        self._janela_bloqueio_correcao_s = 0.12
        self._arremesso_pendente: Optional[Dict[str, object]] = None

        self._snapshot_player_supervisao_rapida: Optional[Dict[str, object]] = None
        self._snapshot_player_supervisao_lenta: Optional[Dict[str, object]] = None
        self._ultimo_envio_supervisao_rapida = 0.0
        self._ultimo_envio_supervisao_lenta = 0.0
        self._intervalo_supervisao_rapida_s = 0.05
        self._intervalo_supervisao_lenta_s = 1.5
        self._ultimo_pivo_visual_local_tela: Optional[Tuple[float, float]] = None
        self._coleta_tapa_enviada = False
        self._colisao_pokemon_pendente: Optional[Dict[str, object]] = None

    @property
    def player_local(self):
        return self._player_local

    def definir_identidade_cliente(self, client_id: str) -> None:
        self._client_id_local = str(client_id or "").strip()

    def client_id_local(self) -> str:
        return str(self._client_id_local or "")

    def _hidratar_ator_payload(self, ator: Optional[Ator], dados: Dict[str, object], com_controle: bool) -> Ator:
        pos = dados.get("posicao", (0.0, 0.0))
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            pos = (0.0, 0.0)
        if ator is None:
            ator = Ator(nome_skin=str(dados.get("skin", "S1")), posicao=(float(pos[0]), float(pos[1])), escala_skin_tiles=1.0, tile_px=50)
        if dados.get("id") is not None:
            ator.Id = int(dados.get("id"))
        ator.definir_posicao(float(pos[0]), float(pos[1]))
        nome = dados.get("nome") or dados.get("usuario")
        if nome:
            ator.Nome = str(nome)
        skin = dados.get("skin")
        if skin and str(skin) != str(getattr(ator, "NomeSkin", "")):
            ator.set_nome_skin(str(skin))

        estado = dados.get("estado") if isinstance(dados.get("estado"), dict) else {}
        if "angulo" in estado:
            ator.definir_angulo_olhar(float(estado.get("angulo", 0.0)))
        if bool(estado.get("tapa")):
            ator.iniciar_tapa()

        if ator.Perfil is None:
            ator.Perfil = Perfil()
        if ator.Inventario is None:
            ator.Inventario = Inventario()
        perfil_serializado = dados.get("perfil") if isinstance(dados.get("perfil"), dict) else dados
        ator.Perfil.aplicar_serializado(perfil_serializado)
        if isinstance(dados.get("inventario"), dict):
            ator.Inventario.aplicar_serializado(dados.get("inventario"))

        ator.Controle = Controle(ator=ator, velocidade_tiles=getattr(ator.Perfil, "VelocidadeBaseTiles", 5.0)) if com_controle else None
        return ator

    def montar_player_local(self, dados_player):
        dados = dados_player if isinstance(dados_player, dict) else {}
        estado = dados.get("estado") if isinstance(dados.get("estado"), dict) else {}
        dim_inicial = str(estado.get("dimensao") or dados.get("dimensao") or "Mundo")
        self._player_local = self._hidratar_ator_payload(None, dados, com_controle=True)
        setattr(self._player_local, "DimensaoAtual", dim_inicial)
        self._objetos.definir_player_local_info(self._player_local)
        self._sincronizar_player_local()
        return self._player_local

    def _correcao_servidor_bloqueando(self) -> bool:
        return time.monotonic() < float(self._bloqueio_correcao_servidor_ate)

    def _ativar_bloqueio_correcao(self) -> None:
        self._bloqueio_correcao_servidor_ate = time.monotonic() + float(self._janela_bloqueio_correcao_s)

    def _resolver_colisao_player_local(self, posicao_antes: Tuple[float, float], dt: float) -> None:
        ator = self._player_local
        if ator is None:
            return
        depois = tuple(ator.Posicao)
        player_id = getattr(ator, "Id", None)
        raio_ator = max(0.0, float(getattr(getattr(ator, "Colisor", None), "raio_colisao", 0.35)))
        colisores_brutos = [c for c in self._objetos.iter_colisores_proximos_por_raio(depois, raio_tiles=10.0) if c[0] != player_id]
        if colisores_brutos:
            margem = 0.25
            filtrados = []
            for c in colisores_brutos:
                oid, sx, sy, raio_obj, tipo_obj, *_ = c
                d2 = ((float(sx) - float(depois[0])) ** 2 + (float(sy) - float(depois[1])) ** 2)
                if str(tipo_obj).strip().lower() in {"entidade_pokemon", "pokemon"}:
                    limite_real = float(raio_ator + raio_obj)
                    if d2 <= (limite_real * limite_real):
                        self._colisao_pokemon_pendente = {"id": int(oid), "posicao": [float(sx), float(sy)]}
                    continue
                limite = float(raio_ator + raio_obj + margem)
                if d2 <= (limite * limite):
                    filtrados.append(c)
            if len(filtrados) > 24:
                filtrados.sort(key=lambda c: ((float(c[1]) - float(depois[0])) ** 2 + (float(c[2]) - float(depois[1])) ** 2))
                colisores = filtrados[:24]
            else:
                colisores = filtrados
        else:
            colisores = []
        px, py = Colisor.resolver_movimento_com_colisores(
            posicao_antes=posicao_antes,
            posicao_depois=depois,
            raio_entidade=raio_ator,
            colisores=colisores,
            dt=dt,
        )
        ator.definir_posicao(px, py)

    def consumir_colisao_pokemon(self) -> Optional[Dict[str, object]]:
        evento = dict(self._colisao_pokemon_pendente) if isinstance(self._colisao_pokemon_pendente, dict) else None
        self._colisao_pokemon_pendente = None
        return evento

    def _spec_projetil(self, item: Dict[str, object]) -> Tuple[str, float, float]:
        estilo = str(item.get("Estilo") or item.get("estilo") or "item").strip().lower()
        nome = str(item.get("Nome") or "").strip().lower()
        if estilo == "fruta":
            return ("fruta", 6.0, 6.0)

        variante = "pokebola"
        velocidade = 7.0
        alcance = 7.0
        if "sniperball" in nome:
            variante = "sniperball"
            velocidade = 8.0
            alcance = 9.0
        elif "fastball" in nome:
            variante = "fastball"
            velocidade = 10.0
            alcance = 7.0
        return (variante, velocidade, alcance)

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

        variante, velocidade, alcance = self._spec_projetil(item)
        if bool(acao.get("mirando", False)):
            velocidade *= 1.10
            alcance += 1.0
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
            "categoria": "projetil_lancamento",
            "payload": {
                "token": token,
                "subtipo_projetil": "fruta" if variante == "fruta" else "pokebola",
                "variante": variante,
                "item": str(item.get("Nome") or ""),
                "item_base_id": str(item.get("Code") or ""),
                "item_nome": str(item.get("Nome") or ""),
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
        velocidade = 3.0
        quantidade = max(1, int(item.get("quantidade", 1) or 1))

        token = str(uuid.uuid4())

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
        dim = str(self._objetos._dimensao_player_local() or estado_player.get("dimensao") or player_payload.get("dimensao") or "Mundo")

        if dim != "Mundo":
            estadio_atual = self._objetos.EstadiosPorId.get(int(estado_player.get("estadio_atual_id", 0) or 0), {}) if isinstance(getattr(self._objetos, "EstadiosPorId", {}), dict) else {}
            estado_est = estadio_atual.get("estado") if isinstance(estadio_atual.get("estado"), dict) else {}
            saida = estado_est.get("saida_interna_pos") if isinstance(estado_est.get("saida_interna_pos"), (list, tuple)) and len(estado_est.get("saida_interna_pos")) == 2 else [25.0, 47.0]
            dxs = float(pos[0]) - float(saida[0]); dys = float(pos[1]) - float(saida[1])
            if (dxs * dxs + dys * dys) > (2.0 * 2.0):
                return
            self._objetos.EnfileirarDiffRapida({
                "tipo": "evento",
                "categoria": "interacao_estadio",
                "payload": {
                    "acao": "sair",
                    "instante_cliente_ms": int(time.time() * 1000),
                    "pos_player": [float(pos[0]), float(pos[1])],
                },
            })
            return

        melhor = None
        melhor_d2 = None
        for estadio in list(getattr(self._objetos, "EstadiosPorId", {}).values()):
            if not isinstance(estadio, dict):
                continue
            estado = estadio.get("estado") if isinstance(estadio.get("estado"), dict) else {}
            entrada = estado.get("entrada_pos") if isinstance(estado.get("entrada_pos"), (list, tuple)) and len(estado.get("entrada_pos")) == 2 else None
            if entrada is None:
                ep = estadio.get("posicao") if isinstance(estadio.get("posicao"), (list, tuple)) and len(estadio.get("posicao")) == 2 else [0.0, 0.0]
                off = estado.get("entrada_offset") if isinstance(estado.get("entrada_offset"), (list, tuple)) and len(estado.get("entrada_offset")) == 2 else [0.0, 25.0]
                entrada = [float(ep[0]) + float(off[0]), float(ep[1]) + float(off[1])]
            dx = float(pos[0]) - float(entrada[0])
            dy = float(pos[1]) - float(entrada[1])
            d2 = dx * dx + dy * dy
            lim = 2.0
            if d2 > (lim * lim):
                continue
            if melhor_d2 is None or d2 < melhor_d2:
                melhor_d2 = d2
                melhor = (estadio, entrada)
        if melhor is None:
            return
        estadio, entrada = melhor
        estado = estadio.get("estado") if isinstance(estadio.get("estado"), dict) else {}
        self._objetos.EnfileirarDiffRapida({
            "tipo": "evento",
            "categoria": "interacao_estadio",
            "payload": {
                "acao": "entrar",
                "estadio_id": int(estadio.get("id", 0) or 0),
                "dimensao_destino": str(estado.get("dimensao_destino") or "EstadioNormal"),
                "entrada_pos": [float(entrada[0]), float(entrada[1])],
                "instante_cliente_ms": int(time.time() * 1000),
            },
        })
    def _processar_intencao_subir_nivel_pokemon(self) -> None:
        if self._player_local is None or self._player_local.Controle is None:
            return
        acao = self._player_local.Controle.consumir_acao_subir_nivel_pokemon()
        if not isinstance(acao, dict):
            return
        chave = str(acao.get("chave_pokemon") or "").strip()
        if not chave:
            return
        self._objetos.EnfileirarDiffRapida({
            "tipo": "evento",
            "categoria": "pokemon_subir_nivel",
            "payload": {
                "chave_pokemon": chave,
                "instante_cliente_ms": int(time.time() * 1000),
            },
        })

    def atualizar_frame(self, eventos, dt, camera, bloqueado: bool) -> None:
        if self._player_local is None:
            return
        dt = max(0.0, float(dt))
        perfil = getattr(self._player_local, "Perfil", None)
        if perfil is not None:
            perfil.registrar_tempo_jogo(dt)

        if self._correcao_servidor_bloqueando():
            if self._player_local.Controle is not None:
                self._player_local.Controle.atualizar_bloqueado(dt)
            self._objetos.atualizar_projeteis_visuais(dt)
            self._fluxo_mira.atualizar(dt)
            return

        if not bloqueado:
            mouse_tela_px = pygame.mouse.get_pos()
            mouse_mundo_tiles = camera.tela_para_mundo_tiles(mouse_tela_px)
            # Usa exatamente o pivô visual real que foi usado no último render do ator local.
            # Fallback no primeiro frame: mesma conversão usada no render.
            ator_pos_tela_px = self._ultimo_pivo_visual_local_tela
            if ator_pos_tela_px is None:
                pivo = camera.mundo_para_tela_px(self._player_local.Posicao)
                ator_pos_tela_px = (float(pivo[0]), float(pivo[1]))
            posicao_antes = tuple(self._player_local.Posicao)
            self._player_local.Controle.atualizar(
                eventos,
                dt,
                mouse_mundo_tiles,
                mouse_pos_tela_px=mouse_tela_px,
                ator_pos_tela_px=ator_pos_tela_px,
            )
            self._resolver_colisao_player_local(posicao_antes, dt)
            posicao_depois = tuple(self._player_local.Posicao)
            if perfil is not None:
                perfil.registrar_movimento(math.hypot(posicao_depois[0] - posicao_antes[0], posicao_depois[1] - posicao_antes[1]))
            self._processar_intencao_arremesso_local()
            self._processar_intencao_drop_item_mundo()
            self._processar_intencao_coleta_estrutura()
            self._processar_intencao_subir_nivel_pokemon()
            self._processar_intencao_interacao_estadio()
        elif self._player_local.Controle is not None:
            self._player_local.Controle.atualizar_bloqueado(dt)

        self._objetos.atualizar_projeteis_visuais(dt)
        self._fluxo_mira.atualizar(dt)

    def sincronizar_regras_mundo(self, leitor_mundo) -> None:
        if self._player_local is not None:
            leitor_mundo.atualizar_regras_mundo(self._player_local.Controle)

    def _snapshot_player_local_rapido(self) -> Dict[str, object]:
        ator = self._player_local
        controle = getattr(ator, "Controle", None)
        return {
            "id": int(getattr(ator, "Id", 0) or 0),
            "tipo": "entidade_player",
            "posicao": [float(ator.Posicao[0]), float(ator.Posicao[1])],
            "raio_colisao": float(getattr(getattr(ator, "Colisor", None), "raio_colisao", 0.35) or 0.35),
            "estado": {
                "angulo": float(getattr(ator, "AnguloOlhar", 0.0) or 0.0),
                "tapa": bool(ator.esta_tapando() if hasattr(ator, "esta_tapando") else False),
                "mirando": bool(getattr(controle, "_mirando", False)) if controle is not None else False,
                "inventario_aberto": bool(getattr(controle, "InventarioAberto", False)) if controle is not None else False,
                "correndo": bool(getattr(controle, "_tentando_correr", False)) if controle is not None else False,
            },
        }

    def _snapshot_player_local_lento(self) -> Dict[str, object]:
        ator = self._player_local
        perfil = getattr(ator, "Perfil", None)
        inventario = getattr(ator, "Inventario", None)
        return {
            "id": int(getattr(ator, "Id", 0) or 0),
            "tipo": "entidade_player",
            "nome": str(getattr(ator, "Nome", "") or ""),
            "skin": str(getattr(ator, "NomeSkin", "S1") or "S1"),
            "perfil": perfil.serializar() if perfil is not None else {},
            "inventario": inventario.serializar() if inventario is not None else {},
        }

    def _delta_snapshot(self, anterior: Optional[Dict[str, object]], atual: Dict[str, object]) -> Dict[str, object]:
        if not isinstance(anterior, dict):
            return dict(atual)
        delta: Dict[str, object] = {}
        for k, v in atual.items():
            av = anterior.get(k)
            if isinstance(v, dict) and isinstance(av, dict):
                if v != av:
                    delta[k] = dict(v)
            elif v != av:
                delta[k] = v
        return delta

    def supervisionar_envio(self) -> None:
        if self._player_local is None:
            return
        agora = time.monotonic()
        ator_id = int(getattr(self._player_local, "Id", 0) or 0)
        if ator_id <= 0:
            return
        perfil = getattr(self._player_local, "Perfil", None)
        forcar_sync_perfil = bool(getattr(perfil, "_habilidades_aprendidas_dirty", False))

        if (agora - self._ultimo_envio_supervisao_rapida) >= self._intervalo_supervisao_rapida_s:
            s = self._snapshot_player_local_rapido()
            d = self._delta_snapshot(self._snapshot_player_supervisao_rapida, s)
            self._snapshot_player_supervisao_rapida = s
            if d:
                d.setdefault("id", ator_id)
                d.setdefault("tipo", "entidade_player")
                self._objetos.EnfileirarDiffRapida({"tipo": "update", "objeto_id": ator_id, "payload": d})
            self._ultimo_envio_supervisao_rapida = agora

        if forcar_sync_perfil or (agora - self._ultimo_envio_supervisao_lenta) >= self._intervalo_supervisao_lenta_s:
            s = self._snapshot_player_local_lento()
            d = self._delta_snapshot(self._snapshot_player_supervisao_lenta, s)
            self._snapshot_player_supervisao_lenta = s
            if d:
                d.setdefault("id", ator_id)
                d.setdefault("tipo", "entidade_player")
                self._objetos.EnfileirarDiffRapida({"tipo": "update", "objeto_id": ator_id, "payload": d})
            if forcar_sync_perfil and perfil is not None:
                setattr(perfil, "_habilidades_aprendidas_dirty", False)
            self._ultimo_envio_supervisao_lenta = agora

    def is_diff_player_local(self, diff: Dict[str, object]) -> bool:
        return self._player_local is not None and int(diff.get("objeto_id", -1) or -1) == int(getattr(self._player_local, "Id", -1))

    def aplicar_diff_player(self, diff: dict) -> None:
        if self._player_local is None or not isinstance(diff, dict):
            return
        tipo = str(diff.get("tipo", "")).strip().lower()
        autor = str(diff.get("autor", "")).strip().lower()
        payload = diff.get("payload", {}) if isinstance(diff.get("payload"), dict) else {}
        if not payload:
            return

        if tipo == "spawn":
            return
        if tipo != "update":
            return
        if autor != "server":
            return

        dados = dict(payload)
        teleporte = bool(dados.get("teleporte", False))
        estado_servidor = dados.get("estado") if isinstance(dados.get("estado"), dict) else {}
        payload_local = self._objetos.ObjetosPorId.get(int(getattr(self._player_local, "Id", 0) or 0), {}) if isinstance(self._objetos.ObjetosPorId, dict) else {}
        estado_local = payload_local.get("estado") if isinstance(payload_local.get("estado"), dict) else {}
        dim_antiga = str(estado_local.get("dimensao") or payload_local.get("dimensao") or "Mundo")
        estadio_antigo = int(estado_local.get("estadio_atual_id", payload_local.get("estadio_atual_id", 0)) or 0)

        estado_estrutural = {}
        if estado_servidor:
            ignorar_visual = {"angulo", "tapa", "mirando", "inventario_aberto", "correndo"}
            estado_estrutural = {k: v for k, v in estado_servidor.items() if k not in ignorar_visual}

        cache_payload = {"id": int(getattr(self._player_local, "Id", 0) or 0), "tipo": "entidade_player"}
        if "posicao" in dados and isinstance(dados.get("posicao"), (list, tuple)):
            cache_payload["posicao"] = list(dados.get("posicao"))
        if estado_estrutural:
            cache_payload["estado"] = estado_estrutural
        for chave in ("dimensao", "estadio_atual_id"):
            if chave in dados:
                cache_payload[chave] = dados.get(chave)
        if cache_payload.get("estado") or "posicao" in cache_payload or "dimensao" in cache_payload or "estadio_atual_id" in cache_payload:
            self._objetos.aplicar_diff({"tipo": "update", "objeto_id": int(cache_payload["id"]), "payload": cache_payload})
        dim_nova = str(estado_servidor.get("dimensao") or dados.get("dimensao") or dim_antiga)
        estadio_novo = int(estado_servidor.get("estadio_atual_id", dados.get("estadio_atual_id", estadio_antigo)) or 0)
        setattr(self._player_local, "DimensaoAtual", dim_nova)
        houve_transicao_estadio = (dim_nova != dim_antiga) or (estadio_novo != estadio_antigo)

        if teleporte or houve_transicao_estadio:
            dados["hard"] = True
            self._player_local.update(dados)
            self._ativar_bloqueio_correcao()
            return

        # Sincronizações autoritativas (inventário/perfil/estado visual) do próprio
        # player não devem mover posição local, mas precisam ser aplicadas na hora.
        dados.pop("posicao", None)
        # Para o próprio player, estado visual/entrada (ângulo, tapa, mirando etc.)
        # é controlado localmente e não deve sobrescrever o input do cliente.
        dados.pop("estado", None)
        if dados:
            self._player_local.update(dados)

    def _sincronizar_player_local(self) -> None:
        ator = self._player_local
        if ator is None or getattr(ator, "Id", None) is None:
            return
        self._objetos.aplicar_diff({
            "tipo": "update",
            "objeto_id": int(ator.Id),
            "payload": {
                "id": int(ator.Id),
                "tipo": "entidade_player",
                "nome": getattr(ator, "Nome", ""),
                "skin": str(getattr(ator, "NomeSkin", "S1")),
                "posicao": [ator.Posicao[0], ator.Posicao[1]],
                "raio_colisao": getattr(ator.Colisor, "raio_colisao", 0.35),
            },
        })

    def renderizar(self, tela, camera):
        ator = self._player_local
        if ator is None:
            return
        ator.set_tile_px(getattr(camera, "TilePx", 50))
        pos_tela = camera.mundo_para_tela_px(ator.Posicao)
        self._ultimo_pivo_visual_local_tela = (float(pos_tela[0]), float(pos_tela[1]))
        respiracao_tempo = getattr(getattr(ator, "Controle", None), "_tempo_respiracao", 0.0)
        ator.desenhar(tela, posicao_tela=pos_tela, respiracao_tempo=respiracao_tempo)
        estado_mira = ator.Controle.estado_mira(camera.tela_para_mundo_tiles(pygame.mouse.get_pos())) if ator.Controle else None
        if estado_mira:
            self._fluxo_mira.desenhar(tela, camera.mundo_para_tela_px(estado_mira["inicio"]), camera.mundo_para_tela_px(estado_mira["fim"]))
        if getattr(ator, "Nome", ""):
            Ator.desenhar_nome(tela, pos_tela, ator.Nome)
