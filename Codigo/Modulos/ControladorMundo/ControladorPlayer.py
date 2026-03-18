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
        if isinstance(dados.get("perfil"), dict):
            ator.Perfil.aplicar_serializado(dados.get("perfil"))
        if isinstance(dados.get("inventario"), dict):
            ator.Inventario.aplicar_serializado(dados.get("inventario"))

        ator.Controle = Controle(ator=ator, velocidade_tiles=getattr(ator.Perfil, "VelocidadeBaseTiles", 5.0)) if com_controle else None
        return ator

    def montar_player_local(self, dados_player):
        dados = dados_player if isinstance(dados_player, dict) else {}
        self._player_local = self._hidratar_ator_payload(None, dados, com_controle=True)
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
                _, sx, sy, raio_obj, *_ = c
                limite = float(raio_ator + raio_obj + margem)
                if ((float(sx) - float(depois[0])) ** 2 + (float(sy) - float(depois[1])) ** 2) <= (limite * limite):
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

        token = str(uuid.uuid4())

        self._seq_id_projetil_predito -= 1
        oid = self._seq_id_projetil_predito
        payload_pred = {
            "id": oid,
            "tipo": "entidade_item_mundo",
            "item_nome": str(item.get("Nome") or "Item"),
            "item_base_id": str(item.get("Code") or ""),
            "quantidade": 1,
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
                },
                "quantidade": 1,
                "pos_inicial": [float(origem[0]), float(origem[1])],
                "pos_final": [float(destino[0]), float(destino[1])],
                "velocidade_tiles_s": float(velocidade),
                "instante_cliente_ms": int(time.time() * 1000),
            },
        })

    def atualizar_frame(self, eventos, dt, camera, bloqueado: bool) -> None:
        if self._player_local is None:
            return

        if self._correcao_servidor_bloqueando():
            if self._player_local.Controle is not None:
                self._player_local.Controle.atualizar_bloqueado(dt)
            self._objetos.atualizar_projeteis_visuais(dt)
            self._fluxo_mira.atualizar(dt)
            return

        if not bloqueado:
            mouse_mundo_tiles = camera.tela_para_mundo_tiles(pygame.mouse.get_pos())
            posicao_antes = tuple(self._player_local.Posicao)
            self._player_local.Controle.atualizar(eventos, dt, mouse_mundo_tiles)
            self._resolver_colisao_player_local(posicao_antes, dt)
            self._processar_intencao_arremesso_local()
            self._processar_intencao_drop_item_mundo()
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

        if (agora - self._ultimo_envio_supervisao_rapida) >= self._intervalo_supervisao_rapida_s:
            s = self._snapshot_player_local_rapido()
            d = self._delta_snapshot(self._snapshot_player_supervisao_rapida, s)
            self._snapshot_player_supervisao_rapida = s
            if d:
                d.setdefault("id", ator_id)
                d.setdefault("tipo", "entidade_player")
                self._objetos.EnfileirarDiffRapida({"tipo": "update", "objeto_id": ator_id, "payload": d})
            self._ultimo_envio_supervisao_rapida = agora

        if (agora - self._ultimo_envio_supervisao_lenta) >= self._intervalo_supervisao_lenta_s:
            s = self._snapshot_player_local_lento()
            d = self._delta_snapshot(self._snapshot_player_supervisao_lenta, s)
            self._snapshot_player_supervisao_lenta = s
            if d:
                d.setdefault("id", ator_id)
                d.setdefault("tipo", "entidade_player")
                self._objetos.EnfileirarDiffRapida({"tipo": "update", "objeto_id": ator_id, "payload": d})
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

        if teleporte:
            dados["hard"] = True
            self._player_local.update(dados)
            self._ativar_bloqueio_correcao()
            return

        # Sincronizações autoritativas (inventário/perfil/estado visual) do próprio
        # player não devem mover posição local, mas precisam ser aplicadas na hora.
        dados.pop("posicao", None)
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
        camera_main = getattr(camera, "EntidadeMain", None)
        if camera_main is ator:
            largura_tela, altura_tela = getattr(camera, "TamanhoTelaPx", tela.get_size())
            pos_tela = (float(largura_tela) * 0.5, float(altura_tela) * 0.5)
        else:
            pos_tela = camera.mundo_para_tela_px(ator.Posicao)
        respiracao_tempo = getattr(getattr(ator, "Controle", None), "_tempo_respiracao", 0.0)
        ator.desenhar(tela, posicao_tela=pos_tela, respiracao_tempo=respiracao_tempo)
        estado_mira = ator.Controle.estado_mira(camera.tela_para_mundo_tiles(pygame.mouse.get_pos())) if ator.Controle else None
        if estado_mira:
            self._fluxo_mira.desenhar(tela, camera.mundo_para_tela_px(estado_mira["inicio"]), camera.mundo_para_tela_px(estado_mira["fim"]))
        if getattr(ator, "Nome", ""):
            Ator.desenhar_nome(tela, pos_tela, ator.Nome)
