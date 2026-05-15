"""Controlador dedicado ao player local."""

from __future__ import annotations

from typing import Dict, Optional, Tuple
import math
import time

import pygame

from Codigo.ModulosMundo.MovimentoPlayer import MovimentoPlayerMixin
from Codigo.ModulosMundo.InteracoesPlayer import InteracoesPlayerMixin
from Codigo.ModulosMundo.Geradores.Ator import Ator
from Codigo.ModulosMundo.Geradores.Player.Controle import Controle
from Codigo.ModulosMundo.Geradores.Player.Inventario import Inventario
from Codigo.ModulosMundo.Geradores.Player.Perfil import Perfil
from Codigo.Prefabs.Fluxos import Fluxo


class ControladorPlayer(
    MovimentoPlayerMixin,
    InteracoesPlayerMixin,
):
    def __init__(self, controlador_objetos, jogo=None, callback_transicao_dimensao=None):
        self._objetos = controlador_objetos
        self._jogo = jogo
        self._callback_transicao_dimensao = callback_transicao_dimensao
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
        self._normalizacao_posicao_pendente = False
        self._dt_ultimo_frame = 1.0 / 60.0
        self._estado_player_local_base: Dict[str, object] = {}

    def _regras(self) -> Dict[str, object]:
        info = getattr(self._jogo, "INFO", {}) if self._jogo is not None else {}
        return info.get("RegrasMundo") if isinstance(info.get("RegrasMundo"), dict) else {}

    def _tile_px_base(self) -> int:
        regras = self._regras()
        gerais = regras.get("gerais") if isinstance(regras.get("gerais"), dict) else {}
        perfil = getattr(self._player_local, "Perfil", None)
        if bool(getattr(perfil, "VisaoExpandidaMundo", False)):
            return 45
        return int(gerais.get("camera_px_por_tile", 50))

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
            ator = Ator(nome_skin=str(dados.get("skin", "S1")), posicao=(float(pos[0]), float(pos[1])), escala_skin_tiles=1.0, tile_px=self._tile_px_base())
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
        ator.Inventario.Perfil = ator.Perfil
        perfil_serializado = dados.get("perfil") if isinstance(dados.get("perfil"), dict) else dados
        ator.Perfil.aplicar_serializado(perfil_serializado)
        if isinstance(dados.get("inventario"), dict):
            ator.Inventario.aplicar_serializado(dados.get("inventario"))

        ator.Controle = Controle(ator=ator, velocidade_tiles=getattr(ator.Perfil, "VelocidadeBaseTiles", 5.0)) if com_controle else None
        return ator

    def montar_player_local(self, dados_player):
        dados = dados_player if isinstance(dados_player, dict) else {}
        estado = dict(dados.get("estado") if isinstance(dados.get("estado"), dict) else {})
        dim_inicial = str(estado.get("dimensao") or dados.get("dimensao") or dados.get("dimensao_atual") or "Mundo")
        estado["dimensao"] = dim_inicial
        if "estadio_atual_id" not in estado and dados.get("estadio_atual_id") is not None:
            estado["estadio_atual_id"] = int(dados.get("estadio_atual_id", 0) or 0)
        self._estado_player_local_base = dict(estado)
        dados_hidratados = dict(dados)
        dados_hidratados["estado"] = estado
        self._player_local = self._hidratar_ator_payload(None, dados_hidratados, com_controle=True)
        setattr(self._player_local, "DimensaoAtual", dim_inicial)
        self._objetos.definir_player_local_info(self._player_local)
        self._objetos.definir_dimensao_atual_client(dim_inicial)
        self._sincronizar_player_local()
        return self._player_local

    def atualizar_frame(self, eventos, dt, camera, bloqueado: bool) -> None:
        if self._player_local is None:
            return
        if bool(getattr(self._player_local, "GameOverServidor", False)):
            if hasattr(self._player_local, "atualizar_visual"):
                self._player_local.atualizar_visual(max(0.0, float(dt)))
            return
        if self._normalizacao_posicao_pendente:
            self._normalizar_posicao_player_local()
            self._normalizacao_posicao_pendente = False
        dt = max(0.0, float(dt))
        self._dt_ultimo_frame = dt
        perfil = getattr(self._player_local, "Perfil", None)
        if perfil is not None:
            perfil.registrar_tempo_jogo(dt)

        if self._correcao_servidor_bloqueando():
            if self._player_local.Controle is not None:
                self._player_local.Controle.atualizar_bloqueado(dt)
            if hasattr(self._player_local, "atualizar_visual"):
                self._player_local.atualizar_visual(dt)
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
            self._processar_intencao_evoluir_pokemon()
            self._processar_intencao_interacao_estadio()
            self._detectar_colisao_pokemon_proxima()
        elif self._player_local.Controle is not None:
            self._player_local.Controle.atualizar_bloqueado(dt)
            self._detectar_colisao_pokemon_proxima()

        if hasattr(self._player_local, "atualizar_visual"):
            self._player_local.atualizar_visual(dt)
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
        forcar_sync_perfil = bool(getattr(perfil, "_habilidades_aprendidas_dirty", False) or getattr(perfil, "_perfil_dirty", False))

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
                setattr(perfil, "_perfil_dirty", False)
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
        if estado_servidor:
            self._estado_player_local_base.update({k: v for k, v in estado_servidor.items() if k not in {"angulo", "tapa", "mirando", "inventario_aberto", "correndo"}})
            self._player_local.update({"estado": {k: v for k, v in estado_servidor.items() if k not in {"angulo", "tapa", "mirando", "inventario_aberto", "correndo"}}})
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
        self._objetos.definir_dimensao_atual_client(dim_nova)
        houve_transicao_estadio = (dim_nova != dim_antiga) or (estadio_novo != estadio_antigo)

        if teleporte or houve_transicao_estadio:
            dados["hard"] = True
            self._player_local.update(dados)
            self._normalizacao_posicao_pendente = True
            self._ativar_bloqueio_correcao()
            if callable(self._callback_transicao_dimensao):
                self._callback_transicao_dimensao(dim_nova, True)
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
        estado = dict(self._estado_player_local_base or {})
        estado.setdefault("dimensao", str(getattr(ator, "DimensaoAtual", "") or "Mundo"))
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
                "estado": estado,
            },
        })

    def renderizar(self, tela, camera):
        ator = self._player_local
        if ator is None:
            return
        queda_ativa = int(pygame.time.get_ticks()) < int(getattr(ator, "AnimacaoQuedaAteMs", 0) or 0)
        if bool(getattr(ator, "Morto", False)) and not queda_ativa:
            return
        ator.set_tile_px(getattr(camera, "TilePx", 50))
        pos_tela = camera.mundo_para_tela_px(ator.Posicao)
        self._ultimo_pivo_visual_local_tela = (float(pos_tela[0]), float(pos_tela[1]))
        respiracao_tempo = getattr(getattr(ator, "Controle", None), "_tempo_respiracao", 0.0)
        estado_visual = getattr(ator, "EstadoVisual", None)
        if estado_visual is not None:
            estado_visual.desenhar(tela, pos_tela, respiracao_tempo=respiracao_tempo)
        else:
            ator.desenhar(tela, posicao_tela=pos_tela, respiracao_tempo=respiracao_tempo)
        if queda_ativa:
            return
        ator.renderizar_stamina(tela, camera, float(self._dt_ultimo_frame))
        estado_mira = ator.Controle.estado_mira(camera.tela_para_mundo_tiles(pygame.mouse.get_pos())) if ator.Controle else None
        if estado_mira:
            self._fluxo_mira.desenhar(tela, camera.mundo_para_tela_px(estado_mira["inicio"]), camera.mundo_para_tela_px(estado_mira["fim"]))
        if getattr(ator, "Nome", ""):
            Ator.desenhar_nome(tela, pos_tela, ator.Nome)
