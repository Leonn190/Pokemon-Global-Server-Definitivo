from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Dict, List, Tuple

from SimuladorServerJogo.Geradores.GeradorPokemon import criar_pokemon_inicial_materializado

ARQUIVO_POKEMONS = Path("Dados") / "Pokemon Global Server - Pokemons.csv"


class InicializadorBatalha:
    def __init__(self, contexto: Dict[str, object] | None = None) -> None:
        self.Contexto = dict(contexto or {})
        self._base_pokemons = self._carregar_base_pokemons()

    @staticmethod
    def _normalizar_time(bruto: object, slots_por_time: int = 6) -> Dict[str, object]:
        if isinstance(bruto, dict):
            nome = str(bruto.get("Nome") or bruto.get("nome") or "Time")
            slots = [p for p in list(bruto.get("Slots") or bruto.get("slots") or []) if isinstance(p, dict)]
        elif isinstance(bruto, list):
            nome = "Time"
            slots = [p for p in list(bruto) if isinstance(p, dict)]
        else:
            nome = "Time"
            slots = []
        return {"Nome": nome, "Slots": slots[: max(1, int(slots_por_time))]}

    @staticmethod
    def _contar_pokemons_time(time: object) -> int:
        return len([p for p in InicializadorBatalha._normalizar_time(time).get("Slots", []) if isinstance(p, dict)])

    @staticmethod
    def times_completos(times: List[object], slots_por_time: int = 6) -> List[Dict[str, object]]:
        alvo = max(1, int(slots_por_time))
        completos: List[Dict[str, object]] = []
        for time in list(times or []):
            normalizado = InicializadorBatalha._normalizar_time(time, slots_por_time=alvo)
            if len(normalizado.get("Slots", [])) == alvo:
                completos.append(normalizado)
        return completos

    @staticmethod
    def escolher_time_confronto(times: List[object], pokemons_jogador: List[object], slots_por_time: int = 6) -> Dict[str, object]:
        alvo = max(1, int(slots_por_time))
        norm = [InicializadorBatalha._normalizar_time(t, slots_por_time=alvo) for t in list(times or [])]
        if norm and len(norm[0].get("Slots", [])) == alvo:
            return norm[0]

        if norm:
            idx_mais_completo = max(range(len(norm)), key=lambda i: len(norm[i].get("Slots", [])))
            mais_completo = norm[idx_mais_completo]
            if len(mais_completo.get("Slots", [])) == alvo:
                return mais_completo

        if norm:
            idx_mais_completo = max(range(len(norm)), key=lambda i: len(norm[i].get("Slots", [])))
            if len(norm[idx_mais_completo].get("Slots", [])) > 0:
                return norm[idx_mais_completo]

        lista_pokemons = [p for p in list(pokemons_jogador or []) if isinstance(p, dict)]
        return {"Nome": "Time improvisado", "Slots": lista_pokemons[:alvo]}

    def inicializar(self) -> Dict[str, object]:
        tipo = str(self.Contexto.get("tipo") or "confronto").strip().lower()
        if tipo in {"npc", "treinador", "trainer"}:
            return self._inicializar_treinador()
        if tipo in {"player", "pvp"}:
            return {"tipo": "player", "jogador": [], "inimigo": []}
        return self._inicializar_confronto()

    def _times_jogador(self) -> List[Dict[str, object]]:
        times = self.Contexto.get("times_jogador")
        if not isinstance(times, list):
            times = []
        return [self._normalizar_time(t) for t in times if isinstance(t, (dict, list))]

    def _time_jogador_escolhido(self) -> Dict[str, object]:
        escolhido = self.Contexto.get("time_jogador")
        if isinstance(escolhido, (dict, list)):
            return self._normalizar_time(escolhido)
        times = self._times_jogador()
        return times[0] if times else {"Nome": "Time 1", "Slots": []}

    def _inicializar_treinador(self) -> Dict[str, object]:
        time_jogador = self._time_jogador_escolhido()
        npc_ctx = self.Contexto.get("npc_contexto") if isinstance(self.Contexto.get("npc_contexto"), dict) else {}
        times_npc = npc_ctx.get("times_pokemon") if isinstance(npc_ctx.get("times_pokemon"), list) else []
        batalha_numero = max(1, int(npc_ctx.get("batalha_numero", 1) or 1))
        indice_time = min(len(times_npc) - 1, batalha_numero - 1) if times_npc else 0
        time_inimigo = self._normalizar_time(times_npc[indice_time]) if times_npc else {"Nome": "Inimigo", "Slots": []}
        return {
            "tipo": "treinador",
            "jogador": [p for p in time_jogador.get("Slots", []) if isinstance(p, dict)],
            "inimigo": [p for p in time_inimigo.get("Slots", []) if isinstance(p, dict)],
            "time_jogador": time_jogador,
            "time_inimigo": time_inimigo,
        }

    def _inicializar_confronto(self) -> Dict[str, object]:
        time_jogador = self.escolher_time_confronto(
            times=self.Contexto.get("times_jogador") if isinstance(self.Contexto.get("times_jogador"), list) else [],
            pokemons_jogador=self.Contexto.get("pokemons_jogador") if isinstance(self.Contexto.get("pokemons_jogador"), list) else [],
            slots_por_time=6,
        )
        poke_mundo = self.Contexto.get("pokemon_colisao") if isinstance(self.Contexto.get("pokemon_colisao"), dict) else {}
        inimigos = self.criar_bando(poke_mundo)
        return {
            "tipo": "confronto",
            "jogador": [p for p in time_jogador.get("Slots", []) if isinstance(p, dict)],
            "inimigo": inimigos,
            "time_jogador": time_jogador,
            "time_inimigo": {"Nome": "Bando", "Slots": inimigos},
        }

    def _carregar_base_pokemons(self) -> List[Dict[str, object]]:
        if not ARQUIVO_POKEMONS.exists():
            return []
        base: List[Dict[str, object]] = []
        with ARQUIVO_POKEMONS.open("r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                base.append(dict(row))
        return base

    @staticmethod
    def _int(v, default: int = 0) -> int:
        try:
            return int(float(v))
        except Exception:
            return int(default)

    def _candidatos_linhagem(self, linhagem: str, estagio_max: int) -> List[Dict[str, object]]:
        out: List[Dict[str, object]] = []
        for row in self._base_pokemons:
            if str(row.get("Linhagem") or "").strip() != str(linhagem or "").strip():
                continue
            estagio = self._int(row.get("Estagio"), 1)
            if estagio <= int(estagio_max):
                out.append(row)
        return out

    def criar_bando(self, pokemon_base: Dict[str, object]) -> List[Dict[str, object]]:
        if not isinstance(pokemon_base, dict):
            return []
        estado = pokemon_base.get("estado") if isinstance(pokemon_base.get("estado"), dict) else pokemon_base
        linhagem = str(estado.get("linhagem") or "").strip()
        estagio = self._int(estado.get("estagio"), 1)
        especie = str(estado.get("especie") or estado.get("nome") or "").strip()

        candidatos = self._candidatos_linhagem(linhagem, estagio)
        if not candidatos and especie:
            candidatos = [r for r in self._base_pokemons if str(r.get("Nome") or "").strip().lower() == especie.lower()]
        if not candidatos and especie:
            candidatos = [{"Nome": especie}]
        if not candidatos:
            return []

        quantidade = random.randint(1, 6)
        bando: List[Dict[str, object]] = []
        repeticoes: Dict[str, int] = {}
        tentativas = 0
        while len(bando) < quantidade and tentativas < 80:
            tentativas += 1
            row = random.choice(candidatos)
            nome = str(row.get("Nome") or "").strip()
            if not nome:
                continue
            if repeticoes.get(nome, 0) >= 3:
                continue
            repeticoes[nome] = repeticoes.get(nome, 0) + 1
            bando.append(criar_pokemon_inicial_materializado(nome))
        return bando


def pontos_lados_arena(centro: Tuple[float, float], largura: float, altura: float, total_aliados: int, total_inimigos: int):
    cx, cy = float(centro[0]), float(centro[1])
    margem_x = largura * 0.18
    margem_y = altura * 0.34

    def _linha(x: float, total: int) -> List[Tuple[float, float]]:
        if total <= 0:
            return []
        if total == 1:
            return [(x, cy)]
        passo = (margem_y * 2.0) / max(1, total - 1)
        return [(x, cy - margem_y + (i * passo)) for i in range(total)]

    aliados = _linha(cx - margem_x, total_aliados)
    inimigos = _linha(cx + margem_x, total_inimigos)
    return aliados, inimigos
