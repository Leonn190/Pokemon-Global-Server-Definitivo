"""Subcérebro de projéteis (lógica real)."""

from __future__ import annotations

import math
import random
from typing import Dict

from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Gerais.LoaderRegras import calcular_parametros_projetil
from SimuladorServerJogo.Gerais.EstadoServidor import obter_personagem_para_entrada
from SimuladorServerJogo.Mundo.AutoridadeCaptura import resolver_captura, resolver_fruta

class CerebroProjeteis:
    def __init__(self, core) -> None:
        self._core = core
        self._tokens_arremesso_visual: Dict[str, Dict[str, object]] = {}
        self._tokens_impacto_processados: set[str] = set()
        self._max_tokens_cache = 4000

    def _limpar_caches_token(self) -> None:
        while len(self._tokens_arremesso_visual) > self._max_tokens_cache:
            self._tokens_arremesso_visual.pop(next(iter(self._tokens_arremesso_visual)), None)
        if len(self._tokens_impacto_processados) > self._max_tokens_cache:
            self._tokens_impacto_processados = set(list(self._tokens_impacto_processados)[-self._max_tokens_cache :])

    def registrar_lancamento(self, client_id: str, payload: Dict[str, object]) -> bool:
        from SimuladorServerJogo.Gerais.Rotas.Ativador import registrar_diff

        token = str(payload.get("token") or "").strip()
        if not token:
            return False
        dono_id = int(payload.get("dono_id", 0) or 0)
        dono_obj = BANCO_DADOS.obter_objeto(dono_id)
        if dono_obj is None:
            return False

        subtipo = str(payload.get("subtipo_projetil") or "pokebola").strip().lower()
        variante = str(payload.get("variante") or "pokebola").strip().lower()
        mirando = bool(payload.get("mirando", False))
        velocidade, alcance = calcular_parametros_projetil(self._core._regras, subtipo, variante, mirando=mirando)

        p0 = payload.get("pos_inicial") if isinstance(payload.get("pos_inicial"), (list, tuple)) and len(payload.get("pos_inicial")) == 2 else [dono_obj.posicao[0], dono_obj.posicao[1]]
        p1 = payload.get("pos_final") if isinstance(payload.get("pos_final"), (list, tuple)) and len(payload.get("pos_final")) == 2 else list(p0)
        dx = float(p1[0]) - float(p0[0]); dy = float(p1[1]) - float(p0[1])
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist
        dist_final = min(float(alcance), dist)
        destino = [float(p0[0]) + ux * dist_final, float(p0[1]) + uy * dist_final]
        usuario = str(BANCO_DADOS.usuario_por_objeto_id(int(dono_id)) or client_id or "").strip()
        if not usuario:
            return False
        dados_jogador = obter_personagem_para_entrada(usuario) or {}
        inventario = dict(dados_jogador.get("inventario", {})) if isinstance(dados_jogador.get("inventario"), dict) else {}
        item_base_id = str(payload.get("item_base_id") or "").strip()
        item_nome = str(payload.get("item_nome") or payload.get("item") or variante).strip()
        if not self._core._servico_inventario.consumir_um(inventario, item_base_id, item_nome):
            return False
        self._core._servico_inventario.persistir_jogador(usuario, int(dono_id), inventario, registrar_diff)

        registrar_diff("spawn", payload={"token": token, "subtipo_projetil": subtipo, "variante": variante, "item": str(payload.get("item") or ""), "item_nome": str(payload.get("item_nome") or payload.get("item") or variante), "item_base_id": str(payload.get("item_base_id") or ""), "pos_inicial": [float(p0[0]), float(p0[1])], "pos_final": [float(destino[0]), float(destino[1])], "velocidade_tiles_s": float(velocidade), "dono_id": int(dono_id), "dono_nome": str(payload.get("dono_nome") or client_id)}, escopo={"centro": [float(p0[0]), float(p0[1])], "raio": 120}, objeto_id=int(dono_id), autor=client_id, categoria="arremesso_visual")
        self._tokens_arremesso_visual[token] = {"dono_id": int(dono_id), "item_nome": item_nome, "item_base_id": item_base_id, "variante": variante, "subtipo": subtipo}
        self._limpar_caches_token()
        return True

    def registrar_impacto_cliente(self, client_id: str, payload: Dict[str, object], fruta: bool = False) -> bool:
        from SimuladorServerJogo.Gerais.Rotas.Ativador import registrar_diff
        token = str(payload.get("token") or "").strip()
        pokemon_id = int(payload.get("pokemon_id", 0) or 0)
        dono_id = int(payload.get("dono_id", 0) or 0)
        if not token or pokemon_id <= 0 or dono_id <= 0:
            return False
        lanc = self._tokens_arremesso_visual.get(token)
        if not isinstance(lanc, dict):
            return False
        if int(lanc.get("dono_id", 0) or 0) != int(dono_id):
            return False
        if token in self._tokens_impacto_processados:
            return False
        poke = BANCO_DADOS.obter_objeto(pokemon_id)
        dono_obj = BANCO_DADOS.obter_objeto(dono_id)
        if dono_obj is None:
            return False
        if poke is None or str(getattr(poke, "estado_extra", {}).get("subtipo", "")).lower() != "pokemon":
            return False
        cap = poke.estado_extra.get("captura") if isinstance(poke.estado_extra.get("captura"), dict) else {}
        if bool(cap.get("captura_pendente", False)) or str(cap.get("token_arremesso") or "") == token:
            return False
        if fruta:
            resolver_fruta(poke, str(payload.get("item_nome") or lanc.get("item_nome") or payload.get("variante") or "fruta"), contexto={"dono_id": dono_id, "limite_frutas": int(self._core._i("captura_limite_frutas", 2))})
            BANCO_DADOS.atualizar_objeto(poke.Id, {"estado": poke.estado_extra})
            registrar_diff("update", payload=poke.serializar(), escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 120}, objeto_id=poke.Id, autor="server", categoria="pokemon")
            self._tokens_impacto_processados.add(token)
            self._tokens_arremesso_visual.pop(token, None)
            self._limpar_caches_token()
            return True
        ret = resolver_captura(poke, str(payload.get("item_nome") or lanc.get("item_nome") or payload.get("variante") or "pokeball"), contexto={
            "dono_id": dono_id,
            "dono_posicao": [float(dono_obj.posicao[0]), float(dono_obj.posicao[1])],
            "distancia_arremesso_tiles": float(payload.get("distancia_arremesso_tiles", 0.0) or 0.0),
            "tentativas_falhas_anteriores": int(poke.estado_extra.get("tentativas_falhas_captura", 0) or 0),
            "bioma": str(poke.estado_extra.get("bioma", "")),
            "captura_critica_cliente": bool(payload.get("captura_critica_cliente", False)),
            "maestria": self._maestria_jogador(client_id),
            "token_arremesso": token,
            "tick_atual": int(self._core._tick_contador),
            "cooldown_movimento_ticks": int(self._core._i("captura_cooldown_movimento_ticks", 36)),
            "captura_bonus_maestria": float(self._core._f("captura_bonus_maestria", 10.0)),
            "captura_chance_min": float(self._core._f("captura_chance_min", 2.0)),
            "captura_chance_max": float(self._core._f("captura_chance_max", 95.0)),
            "captura_poder_poder_base_captura": float(self._core._f("captura_poder_poder_base_captura", 5.0)),
            "captura_poder_maestria_max": float(self._core._f("captura_poder_maestria_max", 10.0)),
            "captura_poder_bonus_maestria_max": float(self._core._f("captura_poder_bonus_maestria_max", 30.0)),
            "captura_poder_expoente_maestria": float(self._core._f("captura_poder_expoente_maestria", 0.70)),
            "captura_poder_multiplicador_critico": float(self._core._f("captura_poder_multiplicador_critico", 1.35)),
            "captura_chance_base_check": float(self._core._f("captura_chance_base_check", 58.0)),
            "captura_chance_escala_diferenca": float(self._core._f("captura_chance_escala_diferenca", 0.82)),
            "captura_chance_check_min": float(self._core._f("captura_chance_check_min", 3.0)),
            "captura_chance_check_max": float(self._core._f("captura_chance_check_max", 98.0)),
            "captura_chance_checks_necessarios": int(self._core._i("captura_chance_checks_necessarios", 3)),
        })
        if bool(ret.get("iniciada", False)):
            if not bool(ret.get("sucesso", False)):
                self._core.registrar_falha_captura_pokemon(poke)
            cap = poke.estado_extra.get("captura") if isinstance(poke.estado_extra.get("captura"), dict) else {}
            cap["token_arremesso"] = token
            BANCO_DADOS.atualizar_objeto(poke.Id, {"estado": poke.estado_extra})
            registrar_diff("update", payload=poke.serializar(), escopo={"centro": [poke.posicao[0], poke.posicao[1]], "raio": 120}, objeto_id=poke.Id, autor="server", categoria="pokemon")
            if bool(ret.get("sucesso", False)):
                self._core.agendar_pokemon_capturado_inventario(
                    dono_id=int(dono_id),
                    poke=poke,
                    atraso_ticks=int(self._core._i("captura_atraso_inventario_ticks", 24)),
                )
                self._core._cerebro_xp_mundo.agendar_burst(
                    origem=(float(poke.posicao[0]), float(poke.posicao[1])),
                    total_particulas=random.randint(int(self._core._i("captura_xp_particulas_min", 3)), int(self._core._i("captura_xp_particulas_max", 4))),
                    tamanhos_possiveis=["pequeno", "medio"],
                    atraso_ticks=int(self._core._i("captura_atraso_spawn_xp_ticks", 16)),
                )
                removido = BANCO_DADOS.remover_objeto(int(poke.Id))
                self._core._pokemons_ids.discard(int(poke.Id))
                self._core._movimento_estado.pop(int(poke.Id), None)
                if removido is not None:
                    registrar_diff("despawn", payload={"id": removido.Id, "motivo": "captura_sucesso"}, escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 120}, objeto_id=removido.Id, autor="server", categoria="pokemon")
            self._tokens_impacto_processados.add(token)
            self._tokens_arremesso_visual.pop(token, None)
            self._limpar_caches_token()
        return True

    def _maestria_jogador(self, client_id: str) -> float:
        dados = obter_personagem_para_entrada(str(client_id))
        if not isinstance(dados, dict):
            return 0.0
        try:
            return float(dados.get("maestria", 0.0) or 0.0)
        except Exception:
            return 0.0
