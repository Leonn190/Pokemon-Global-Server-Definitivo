from __future__ import annotations

import csv
import random
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Tuple

from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import criar_pokemon_inicial_materializado, materializar_pokemon

ARQUIVO_POKEMONS = Path(__file__).resolve().parents[2] / "Dados" / "Pokemon Global Server - Pokemons.csv"


class InicializadorBatalha:
    def __init__(self, contexto: Dict[str, object] | None = None) -> None:
        self.Contexto = dict(contexto or {})
        self._base_pokemons = self._carregar_base_pokemons()
        self._base_por_nome = {
            self._normalizar_texto(row.get("Nome")): row
            for row in self._base_pokemons
            if self._normalizar_texto(row.get("Nome"))
        }

    @staticmethod
    def _normalizar_time(bruto: object, slots_por_time: int = 6) -> Dict[str, object]:
        if isinstance(bruto, dict):
            nome = str(bruto.get("Nome") or bruto.get("nome") or "Time")
            slots = [deepcopy(p) for p in list(bruto.get("Slots") or bruto.get("slots") or []) if isinstance(p, dict)]
        elif isinstance(bruto, list):
            nome = "Time"
            slots = [deepcopy(p) for p in list(bruto) if isinstance(p, dict)]
        else:
            nome = "Time"
            slots = []
        return {"Nome": nome, "Slots": slots[: max(1, int(slots_por_time))]}

    @staticmethod
    def _contar_pokemons_time(time: object) -> int:
        return len([p for p in InicializadorBatalha._normalizar_time(time).get("Slots", []) if isinstance(p, dict)])

    @staticmethod
    def _estado_pokemon(pokemon: Dict[str, object] | None) -> Dict[str, object]:
        if not isinstance(pokemon, dict):
            return {}
        return pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon

    @classmethod
    def pokemon_tem_vida(cls, pokemon: Dict[str, object] | None) -> bool:
        estado = cls._estado_pokemon(pokemon)
        for chave in ("VidaAtual", "vida_atual", "vidaatual"):
            try:
                if float(estado.get(chave, 0) or 0) > 0.0:
                    return True
            except (TypeError, ValueError):
                continue
        return False

    @classmethod
    def time_tem_pokemon_vivo(cls, time: object) -> bool:
        slots = cls._normalizar_time(time).get("Slots", [])
        return any(cls.pokemon_tem_vida(pokemon) for pokemon in slots if isinstance(pokemon, dict))

    @staticmethod
    def times_completos(times: List[object], slots_por_time: int = 6) -> List[Dict[str, object]]:
        alvo = max(1, int(slots_por_time))
        completos: List[Dict[str, object]] = []
        for time in list(times or []):
            normalizado = InicializadorBatalha._normalizar_time(time, slots_por_time=alvo)
            if len(normalizado.get("Slots", [])) == alvo and InicializadorBatalha.time_tem_pokemon_vivo(normalizado):
                completos.append(normalizado)
        return completos

    @staticmethod
    def escolher_time_confronto_com_indice(times: List[object], pokemons_jogador: List[object], slots_por_time: int = 6) -> Tuple[int, Dict[str, object]]:
        alvo = max(1, int(slots_por_time))
        norm = [InicializadorBatalha._normalizar_time(t, slots_por_time=alvo) for t in list(times or [])]
        completos_vivos = [(indice, time) for indice, time in enumerate(norm) if len(time.get("Slots", [])) == alvo and InicializadorBatalha.time_tem_pokemon_vivo(time)]
        if completos_vivos:
            return completos_vivos[0]

        vivos = [(indice, time) for indice, time in enumerate(norm) if InicializadorBatalha.time_tem_pokemon_vivo(time)]
        if vivos:
            indice, escolhido = max(vivos, key=lambda item: len(item[1].get("Slots", [])))
            return indice, escolhido

        lista_pokemons = [deepcopy(p) for p in list(pokemons_jogador or []) if isinstance(p, dict) and InicializadorBatalha.pokemon_tem_vida(p)]
        return -1, {"Nome": "Time improvisado", "Slots": lista_pokemons[:alvo]}

    @staticmethod
    def escolher_time_confronto(times: List[object], pokemons_jogador: List[object], slots_por_time: int = 6) -> Dict[str, object]:
        _, escolhido = InicializadorBatalha.escolher_time_confronto_com_indice(times, pokemons_jogador, slots_por_time=slots_por_time)
        return escolhido

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
        jogador_slots = self._padronizar_uids_batalha(
            [deepcopy(p) for p in time_jogador.get("Slots", []) if isinstance(p, dict)],
            origem="time",
        )
        inimigo_slots = self._padronizar_uids_batalha(
            [deepcopy(p) for p in time_inimigo.get("Slots", []) if isinstance(p, dict)],
            origem="npc",
        )
        return {
            "tipo": "treinador",
            "jogador": jogador_slots,
            "inimigo": inimigo_slots,
            "time_jogador": {**deepcopy(time_jogador), "Slots": jogador_slots},
            "time_inimigo": {**deepcopy(time_inimigo), "Slots": inimigo_slots},
        }

    def _inicializar_confronto(self) -> Dict[str, object]:
        time_jogador = self.escolher_time_confronto(
            times=self.Contexto.get("times_jogador") if isinstance(self.Contexto.get("times_jogador"), list) else [],
            pokemons_jogador=self.Contexto.get("pokemons_jogador") if isinstance(self.Contexto.get("pokemons_jogador"), list) else [],
            slots_por_time=6,
        )
        poke_mundo = self.Contexto.get("pokemon_colisao") if isinstance(self.Contexto.get("pokemon_colisao"), dict) else {}
        jogador_slots = self._padronizar_uids_batalha(
            [deepcopy(p) for p in time_jogador.get("Slots", []) if isinstance(p, dict)],
            origem="time",
        )
        inimigos_brutos = self.criar_bando(poke_mundo)
        inimigos = []
        if inimigos_brutos:
            inimigos.extend(self._padronizar_uids_batalha([inimigos_brutos[0]], origem="mundo"))
            if len(inimigos_brutos) > 1:
                inimigos.extend(self._padronizar_uids_batalha(inimigos_brutos[1:], origem="bando"))
        return {
            "tipo": "confronto",
            "jogador": jogador_slots,
            "inimigo": inimigos,
            "time_jogador": {**deepcopy(time_jogador), "Slots": jogador_slots},
            "time_inimigo": {"Nome": "Bando", "Slots": inimigos},
        }

    def _carregar_base_pokemons(self) -> List[Dict[str, object]]:
        if not ARQUIVO_POKEMONS.exists():
            return []
        base: List[Dict[str, object]] = []
        with ARQUIVO_POKEMONS.open("r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                nome = str(row.get("Nome") or "").strip()
                if not nome:
                    continue
                raridade = self._int(row.get("Raridade"), 0)
                estagio = self._int(row.get("Estagio"), 0)
                if raridade < 1 or raridade > 10 or estagio <= 0:
                    continue
                base.append(dict(row))
        return base

    @staticmethod
    def _int(v, default: int = 0) -> int:
        try:
            return int(float(v))
        except Exception:
            return int(default)

    @staticmethod
    def _normalizar_texto(v: object) -> str:
        return str(v or "").strip().casefold()

    @staticmethod
    def _gerar_uid_batalha() -> str:
        return f"P-{uuid.uuid4().hex[:10].upper()}"

    @classmethod
    def _padronizar_uids_batalha(cls, pokemons: List[Dict[str, object]], origem: str) -> List[Dict[str, object]]:
        saida: List[Dict[str, object]] = []
        usados: set[str] = set()
        origem_norm = str(origem or "time").strip().casefold() or "time"
        for indice, pokemon in enumerate(list(pokemons or []), start=1):
            if not isinstance(pokemon, dict):
                continue
            bruto = deepcopy(pokemon)
            estado = bruto.get("estado") if isinstance(bruto.get("estado"), dict) else None
            uid_original = str(bruto.get("uid") or bruto.get("id") or bruto.get("ID") or "")
            uid = cls._gerar_uid_batalha()
            while uid in usados:
                uid = cls._gerar_uid_batalha()
            usados.add(uid)
            bruto["uid"] = uid
            bruto["origem_batalha"] = origem_norm
            if uid_original:
                bruto["uid_original"] = uid_original
            bruto["indice_origem_batalha"] = int(indice - 1)
            if isinstance(estado, dict):
                estado["uid"] = uid
                estado["origem_batalha"] = origem_norm
                if uid_original:
                    estado["uid_original"] = uid_original
                estado["indice_origem_batalha"] = int(indice - 1)
            saida.append(bruto)
        return saida

    def _buscar_row_por_especie(self, especie: object) -> Dict[str, object] | None:
        return self._base_por_nome.get(self._normalizar_texto(especie))

    def _candidatos_linhagem(self, linhagem: str, estagio_max: int) -> List[Dict[str, object]]:
        linhagem_norm = self._normalizar_texto(linhagem)
        if not linhagem_norm:
            return []
        out: List[Dict[str, object]] = []
        for row in self._base_pokemons:
            if self._normalizar_texto(row.get("Linhagem")) != linhagem_norm:
                continue
            if self._int(row.get("Estagio"), 1) <= int(estagio_max):
                out.append(row)
        return out

    def _especie_pokemon(self, pokemon: Dict[str, object]) -> str:
        estado = self._estado_pokemon(pokemon)
        return str(
            estado.get("especie")
            or estado.get("Especie")
            or estado.get("nome")
            or estado.get("Nome")
            or pokemon.get("nome")
            or pokemon.get("Nome")
            or ""
        ).strip()

    def _metadados_confrontado(self, pokemon_base: Dict[str, object]) -> Dict[str, object]:
        estado = self._estado_pokemon(pokemon_base)
        especie = self._especie_pokemon(pokemon_base)
        row = self._buscar_row_por_especie(especie)
        linhagem = str(estado.get("linhagem") or estado.get("Linhagem") or (row or {}).get("Linhagem") or "").strip()
        estagio = self._int(estado.get("estagio", estado.get("Estagio")), self._int((row or {}).get("Estagio"), 1))
        return {"especie": especie, "linhagem": linhagem, "estagio": max(1, estagio)}

    def _materializar_confrontado(self, pokemon_base: Dict[str, object]) -> Dict[str, object] | None:
        if not isinstance(pokemon_base, dict):
            return None
        especie = self._especie_pokemon(pokemon_base)
        if isinstance(pokemon_base.get("estado"), dict) and especie:
            return materializar_pokemon(deepcopy(pokemon_base))
        if especie:
            return criar_pokemon_inicial_materializado(especie)
        return None

    def _sortear_especies_extras(self, especie_base: str, linhagem: str, estagio_max: int) -> List[str]:
        candidatos = self._candidatos_linhagem(linhagem, estagio_max)
        if not candidatos:
            row_base = self._buscar_row_por_especie(especie_base)
            candidatos = [row_base] if isinstance(row_base, dict) else []

        contagem_inicial: Dict[str, int] = {}
        especie_base_norm = self._normalizar_texto(especie_base)
        if especie_base_norm:
            contagem_inicial[especie_base_norm] = 1

        pool: List[str] = []
        for row in candidatos:
            nome = str(row.get("Nome") or "").strip()
            if not nome:
                continue
            nome_norm = self._normalizar_texto(nome)
            vagas = 3 - int(contagem_inicial.get(nome_norm, 0))
            if vagas <= 0:
                continue
            pool.extend([nome] * vagas)

        if not pool:
            return []

        quantidade_extras = random.randint(0, min(5, len(pool)))
        if quantidade_extras <= 0:
            return []

        random.shuffle(pool)
        return pool[:quantidade_extras]

    def criar_bando(self, pokemon_base: Dict[str, object]) -> List[Dict[str, object]]:
        confrontado = self._materializar_confrontado(pokemon_base)
        if not isinstance(confrontado, dict):
            return []

        metadados = self._metadados_confrontado(confrontado)
        especie_base = str(metadados.get("especie") or "").strip()
        linhagem = str(metadados.get("linhagem") or "").strip()
        estagio = self._int(metadados.get("estagio"), 1)

        inimigos = [confrontado]
        for especie_extra in self._sortear_especies_extras(especie_base, linhagem, estagio):
            inimigos.append(criar_pokemon_inicial_materializado(especie_extra))
        return inimigos


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
