"""Subcérebro de estruturas naturais."""

from __future__ import annotations

import math
import random
import uuid
from SimuladorServerJogo.Gerais.LoaderTabelas import carregar_csv_dict
from typing import Dict, Tuple

from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Gerais.EstadoServidor import obter_personagem_para_entrada, registrar_estrutura_natural_tocada_estado
from SimuladorServerJogo.Mundo.ObjetosMundoServer import AtorServer, EstruturaNaturalServer, ItemMundoServer
from SimuladorServerJogo.Gerais.LoaderRegras import carregar_regras_estruturas_naturais


def _carregar_fatores_ferramenta() -> Dict[str, int]:
    by_code: Dict[str, int] = {}
    for row in carregar_csv_dict("Pokemon Global Server - Itens.csv", encoding="utf-8"):
            code = str(row.get("Code", "")).strip()
            if not code:
                continue
            try:
                fator = int(float(row.get("Fator", 1) or 1))
            except Exception:
                fator = 1
            by_code[code] = fator
    return by_code


_FATOR_POR_CODE = _carregar_fatores_ferramenta()
_REGRAS_ESTRUTURA = carregar_regras_estruturas_naturais().get("tipos", {})
_BERRY_BIOMA_POR_TILE = {
    2: "Field Berry",
    3: "Jungle Berry",
    5: "Desert Berry",
    6: "Frozen Berry",
    7: "Magic Berry",
    8: "Lava Berry",
    9: "Secret Berry",
}


class CerebroEstruturasNaturais:
    def __init__(self, cerebro_core) -> None:
        self._core = cerebro_core

    def executar_tick(self) -> None:
        return None

    @staticmethod
    def _estilo_ferramenta(item: Dict[str, object]) -> Tuple[str, int]:
        if not isinstance(item, dict):
            return "", 1
        code = str(item.get("Code") or "").strip()
        nome = str(item.get("Nome") or "").strip()
        fator = int(item.get("Fator", (_FATOR_POR_CODE.get(code, 1) if code else 1)) or 1)
        primeira = nome.split(" ", 1)[0].strip().lower() if nome else ""
        if primeira == "machado":
            return "machado", fator
        if primeira in {"picarte", "picareta"}:
            return "picareta", fator
        if primeira == "balde":
            return "balde", 1
        return "", 1

    @staticmethod
    def _agrupar_drops_arbusto(estrutura: EstruturaNaturalServer, quantidade: int) -> Dict[str, int]:
        qtd = max(1, int(quantidade or 1))
        tile = BANCO_DADOS.tile_em(int(math.floor(float(estrutura.posicao[0]))), int(math.floor(float(estrutura.posicao[1]))))
        berry_bioma = _BERRY_BIOMA_POR_TILE.get(int(tile), "Field Berry")
        saida: Dict[str, int] = {}
        for _ in range(qtd):
            nome = "Simp Berry" if random.random() < 0.75 else berry_bioma
            saida[nome] = int(saida.get(nome, 0)) + 1
        return saida

    def registrar_coleta(self, client_id: str, payload: Dict[str, object]) -> bool:
        from SimuladorServerJogo.Gerais.Rotas.Ativador import registrar_diff

        usuario = str(client_id or "").strip()
        if not usuario:
            return False
        player_id = int(BANCO_DADOS.objeto_id_por_usuario(usuario) or 0)
        player = BANCO_DADOS.obter_objeto(player_id)
        if not isinstance(player, AtorServer):
            return False

        estrutura_id = int(payload.get("estrutura_id", 0) or 0)
        estrutura = BANCO_DADOS.obter_objeto(estrutura_id)
        if not isinstance(estrutura, EstruturaNaturalServer):
            return False

        mao = payload.get("pos_mao") if isinstance(payload.get("pos_mao"), (list, tuple)) and len(payload.get("pos_mao")) == 2 else None
        mx, my = (float(mao[0]), float(mao[1])) if mao else (float(player.posicao[0]), float(player.posicao[1]))
        limite = float(player.raio_interacao) + float(estrutura.raio_colisao) + 0.35
        if math.hypot(float(estrutura.posicao[0]) - mx, float(estrutura.posicao[1]) - my) > limite:
            return False

        perfil = obter_personagem_para_entrada(usuario) or {}
        inventario = perfil.get("inventario") if isinstance(perfil.get("inventario"), dict) else {}
        itens = inventario.get("itens") if isinstance(inventario.get("itens"), list) else []
        slot = int(inventario.get("slot_selecionado", player.estado_extra.get("slot_selecionado", 0)) or 0)
        item_mao = itens[slot] if 0 <= slot < len(itens) and isinstance(itens[slot], dict) else {}

        estilo_ferramenta, fator = self._estilo_ferramenta(item_mao)
        subtipo = str(estrutura.estado_extra.get("subtipo", "")).strip().lower()
        coletado = estrutura.tentar_coleta(fator_ferramenta=fator, estilo_ferramenta=estilo_ferramenta)
        if coletado <= 0:
            return False

        restante = estrutura.quantidade_restante
        BANCO_DADOS.registrar_quantidade_estrutura(estrutura.Id, restante)
        self._persistir_estrutura_tocada_imediato(estrutura.Id, restante)
        if restante <= 0:
            if subtipo == "dungeon":
                estrutura.estado_extra["porta_ativa"] = True
                estrutura.estado_extra["estrutura_quebrada"] = True
                estrutura.estado_extra["quantidade"] = 0
                estrutura.raio_colisao = 0.0
                estrutura.Colisor.raio_colisao = 0.0
                BANCO_DADOS.atualizar_objeto(estrutura.Id, {"estado": estrutura.estado_extra})
                registrar_diff("update", payload=estrutura.serializar(), escopo={"centro": [estrutura.posicao[0], estrutura.posicao[1]], "raio": 90.0}, objeto_id=estrutura.Id, autor="server", categoria="estrutura")
            else:
                regra_xp = _REGRAS_ESTRUTURA.get(str(int(getattr(estrutura, "codigo_natural", 0) or 0)), {}) if isinstance(_REGRAS_ESTRUTURA, dict) else {}
                particulas_cfg = regra_xp.get("particulasXP") if isinstance(regra_xp.get("particulasXP"), list) else []
                tamanhos_cfg = regra_xp.get("tamanhosXP") if isinstance(regra_xp.get("tamanhosXP"), list) else []
                pool_particulas = [max(1, int(v)) for v in particulas_cfg if isinstance(v, (int, float, str)) and str(v).strip().lstrip("-").isdigit()]
                pool_tamanhos = [str(v).strip().lower() for v in tamanhos_cfg if str(v).strip().lower() in {"pequeno", "medio", "grande"}]
                self._core._cerebro_xp_mundo.agendar_burst(
                    origem=(float(estrutura.posicao[0]), float(estrutura.posicao[1])),
                    total_particulas=random.choice(pool_particulas) if pool_particulas else 3,
                    tamanhos_possiveis=(pool_tamanhos if pool_tamanhos else ["pequeno", "medio"]),
                    atraso_ticks=0,
                )
                removido = BANCO_DADOS.remover_objeto(estrutura.Id)
                if removido is not None:
                    registrar_diff("despawn", payload={"id": removido.Id, "motivo": "estrutura_esgotada"}, escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 90.0}, objeto_id=removido.Id, autor="server", categoria="estrutura")
        else:
            BANCO_DADOS.atualizar_objeto(estrutura.Id, {"estado": {"quantidade": restante}})
            registrar_diff("update", payload=estrutura.serializar(), escopo={"centro": [estrutura.posicao[0], estrutura.posicao[1]], "raio": 90.0}, objeto_id=estrutura.Id, autor="server", categoria="estrutura")

        drops: Dict[str, int]
        if not bool(estrutura.estado_extra.get("drop_ativo", True)):
            drops = {}
        elif subtipo == "arbusto":
            drops = self._agrupar_drops_arbusto(estrutura, coletado)
        else:
            material = str(estrutura.estado_extra.get("material", "") or "").strip()
            drops = {material: int(max(1, coletado))}

        houve_persistencia = False
        for nome_material, qtd_drop in drops.items():
            adicionado, sobra = self._core._servico_inventario.adicionar_item(inventario, {"Nome": str(nome_material)}, int(qtd_drop), dados_personagem=perfil)
            if adicionado > 0:
                houve_persistencia = True
            if sobra > 0:
                self._spawn_item_mundo(str(nome_material), sobra, player, estrutura, registrar_diff)
        if houve_persistencia:
            self._core._servico_inventario.persistir_jogador(usuario, int(player.Id), inventario, registrar_diff)
        return True

    def _spawn_item_mundo(self, nome_material: str, quantidade: int, player: AtorServer, estrutura: EstruturaNaturalServer, registrar_diff) -> None:
        qtd = max(1, int(quantidade or 1))
        item = self._core._servico_inventario.normalizar_item({"Nome": str(nome_material or "Item"), "quantidade": qtd}, quantidade_padrao=qtd)
        novo_id = BANCO_DADOS.gerar_id()
        p0 = (float(player.posicao[0]), float(player.posicao[1]))
        p1 = (float(estrutura.posicao[0]) + 0.22, float(estrutura.posicao[1]) + 0.08)
        obj = ItemMundoServer(
            id_objeto=novo_id,
            posicao=p0,
            dono_id=int(getattr(player, "Id", 0) or 0),
            item_nome=str(item.get("Nome") or "Item"),
            item_base_id=str(item.get("Code") or ""),
            quantidade=qtd,
            pos_inicial=p0,
            pos_final=p1,
            velocidade=4.2,
            tick_spawn=int(self._core._tick_contador),
            token_drop=str(uuid.uuid4()),
            item_dados=item,
        )
        BANCO_DADOS.inserir_objeto(obj)
        self._core.registrar_spawn_manual(obj)
        registrar_diff("spawn", payload=obj.serializar(), escopo={"centro": [p1[0], p1[1]], "raio": 80.0}, objeto_id=obj.Id, autor="server", categoria="item_mundo")

    @staticmethod
    def _persistir_estrutura_tocada_imediato(estrutura_id: int, quantidade_restante: int) -> None:
        registrar_estrutura_natural_tocada_estado(int(estrutura_id), int(quantidade_restante or 0), force=True)
