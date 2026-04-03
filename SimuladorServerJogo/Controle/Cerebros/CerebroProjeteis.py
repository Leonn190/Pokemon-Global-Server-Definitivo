"""Subcérebro de projéteis (lógica real)."""

from __future__ import annotations

import math
import random
from typing import Dict, Tuple

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.EstadoServidor import obter_personagem_para_entrada
from SimuladorServerJogo.Logica.AutoridadeCaptura import resolver_captura, resolver_fruta

Vector2 = Tuple[float, float]


class CerebroProjeteis:
    def __init__(self, core) -> None:
        self._core = core

    def registrar_lancamento(self, client_id: str, payload: Dict[str, object]) -> bool:
        from SimuladorServerJogo.Rotas.Ativador import registrar_diff

        token = str(payload.get("token") or "").strip()
        if not token:
            return False
        dono_id = int(payload.get("dono_id", 0) or 0)
        dono_obj = BANCO_DADOS.obter_objeto(dono_id)
        if dono_obj is None:
            return False

        subtipo = str(payload.get("subtipo_projetil") or "pokebola").strip().lower()
        variante = str(payload.get("variante") or "pokebola").strip().lower()
        if subtipo == "fruta":
            velocidade, alcance = 6.0, 6.0
        elif variante == "sniperball":
            velocidade, alcance = 8.0, 9.0
        elif variante == "fastball":
            velocidade, alcance = 10.0, 7.0
        else:
            velocidade, alcance = 7.0, 7.0

        p0 = payload.get("pos_inicial") if isinstance(payload.get("pos_inicial"), (list, tuple)) and len(payload.get("pos_inicial")) == 2 else [dono_obj.posicao[0], dono_obj.posicao[1]]
        p1 = payload.get("pos_final") if isinstance(payload.get("pos_final"), (list, tuple)) and len(payload.get("pos_final")) == 2 else list(p0)
        dx = float(p1[0]) - float(p0[0]); dy = float(p1[1]) - float(p0[1])
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist
        dist_final = min(float(alcance), dist)
        destino = [float(p0[0]) + ux * dist_final, float(p0[1]) + uy * dist_final]

        registrar_diff("spawn", payload={"token": token, "subtipo_projetil": subtipo, "variante": variante, "item": str(payload.get("item") or ""), "item_nome": str(payload.get("item_nome") or payload.get("item") or variante), "item_base_id": str(payload.get("item_base_id") or ""), "pos_inicial": [float(p0[0]), float(p0[1])], "pos_final": [float(destino[0]), float(destino[1])], "velocidade_tiles_s": float(velocidade), "dono_id": int(dono_id), "dono_nome": str(payload.get("dono_nome") or client_id)}, escopo={"centro": [float(p0[0]), float(p0[1])], "raio": 120}, objeto_id=int(dono_id), autor=client_id, categoria="projetil_lancamento")

        impacto = self._simular_lancamento_servidor(tuple(p0), tuple(destino), dono_id=dono_id)
        if impacto is None:
            return True

        if subtipo == "fruta":
            resolver_fruta(impacto, str(payload.get("item") or variante), contexto={"dono_id": dono_id})
            BANCO_DADOS.atualizar_objeto(impacto.Id, {"estado": impacto.estado_extra})
            registrar_diff("update", payload=impacto.serializar(), escopo={"centro": [impacto.posicao[0], impacto.posicao[1]], "raio": 120}, objeto_id=impacto.Id, autor="server", categoria="pokemon")
            return True

        ret = resolver_captura(impacto, str(payload.get("item") or variante), contexto={
            "dono_id": dono_id,
            "dono_posicao": [dono_obj.posicao[0], dono_obj.posicao[1]],
            "distancia_arremesso_tiles": dist_final,
            "tentativas_falhas_anteriores": int(impacto.estado_extra.get("tentativas_falhas_captura", 0) or 0),
            "bioma": str(impacto.estado_extra.get("bioma", "")),
            "maestria": self._maestria_jogador(client_id),
            "token_arremesso": token,
            "tick_atual": int(self._core._tick_contador),
            "cooldown_movimento_ticks": int(self._core._i("cooldown_movimento_apos_tentativa_captura_ticks", 36)),
        })
        if bool(ret.get("iniciada", False)):
            cap = impacto.estado_extra.get("captura") if isinstance(impacto.estado_extra.get("captura"), dict) else {}
            cap["token_arremesso"] = token
            BANCO_DADOS.atualizar_objeto(impacto.Id, {"estado": impacto.estado_extra})
            registrar_diff("update", payload=impacto.serializar(), escopo={"centro": [impacto.posicao[0], impacto.posicao[1]], "raio": 120}, objeto_id=impacto.Id, autor="server", categoria="pokemon")
            if bool(ret.get("sucesso", False)):
                self._core.agendar_pokemon_capturado_inventario(
                    dono_id=int(dono_id),
                    poke=impacto,
                    atraso_ticks=int(self._core._i("atraso_inventario_captura_ticks", 24)),
                )
                self._core._cerebro_xp_mundo.agendar_burst(
                    origem=(float(impacto.posicao[0]), float(impacto.posicao[1])),
                    total_particulas=random.randint(int(self._core._i("xp_captura_particulas_min", 3)), int(self._core._i("xp_captura_particulas_max", 4))),
                    tamanhos_possiveis=["pequeno", "medio"],
                    atraso_ticks=int(self._core._i("atraso_spawn_xp_captura_ticks", 56)),
                )
                removido = BANCO_DADOS.remover_objeto(int(impacto.Id))
                self._core._pokemons_ids.discard(int(impacto.Id))
                self._core._movimento_estado.pop(int(impacto.Id), None)
                if removido is not None:
                    registrar_diff("despawn", payload={"id": removido.Id, "motivo": "captura_sucesso"}, escopo={"centro": [removido.posicao[0], removido.posicao[1]], "raio": 120}, objeto_id=removido.Id, autor="server", categoria="pokemon")
        return True

    def _maestria_jogador(self, client_id: str) -> float:
        dados = obter_personagem_para_entrada(str(client_id))
        if not isinstance(dados, dict):
            return 0.0
        try:
            return float(dados.get("maestria", 0.0) or 0.0)
        except Exception:
            return 0.0

    def _simular_lancamento_servidor(self, origem: Vector2, destino: Vector2, dono_id: int):
        raio_proj = 0.18
        dist_total = max(0.001, math.hypot(destino[0] - origem[0], destino[1] - origem[1]))
        passo_tiles = max(0.08, raio_proj * 0.5)
        passos = max(8, int(math.ceil(dist_total / passo_tiles)))
        for i in range(1, passos + 1):
            t = float(i) / float(passos)
            px = float(origem[0]) + (float(destino[0]) - float(origem[0])) * t
            py = float(origem[1]) + (float(destino[1]) - float(origem[1])) * t
            for obj in BANCO_DADOS.buscar_proximos((px, py), 2.2):
                if int(getattr(obj, "Id", 0) or 0) == int(dono_id):
                    continue
                subt = str(getattr(obj, "estado_extra", {}).get("subtipo", "")).strip().lower()
                tipo = str(getattr(obj, "tipo_classe", "")).strip().lower()
                if subt not in {"pokemon", "bau", "player"} and not tipo.startswith("estrutura"):
                    continue
                raio_alvo = float(getattr(obj, "raio_colisao", 0.35) or 0.35)
                limite = raio_proj + max(0.05, raio_alvo)
                dx = float(getattr(obj, "posicao", (0.0, 0.0))[0]) - px
                dy = float(getattr(obj, "posicao", (0.0, 0.0))[1]) - py
                if (dx * dx + dy * dy) > (limite * limite):
                    continue
                if subt == "pokemon":
                    return obj
                return None
        return None
