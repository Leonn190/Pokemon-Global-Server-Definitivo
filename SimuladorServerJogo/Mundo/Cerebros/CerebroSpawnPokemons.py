"""Subcerebro dedicado ao spawn inicial de pokemons selvagens."""

from __future__ import annotations

import math
import random
import unicodedata
from typing import Dict, List, Optional, Set, Tuple

from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import gerar_pokemon_server, listar_candidatos_spawn_pokemon
from SimuladorServerJogo.Gerais.LoaderTabelas import carregar_csv_dict
from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Mundo.ObjetosMundoServer import PokemonServer

Vector2 = Tuple[float, float]
Chunk = Tuple[int, int]

_ARQUIVO_SPAWN_BIOMAS = "Pokemon Global Server - Spawn.csv"
_BIOMA_POR_CODIGO = {
    0: "agua_funda",
    1: "agua_rasa",
    2: "campo",
    3: "floresta",
    4: "deserto",
    5: "neve",
    6: "magico",
    7: "vulcao",
    8: "pantano",
}


def _normalizar_chave(valor: object) -> str:
    texto = "".join(
        c
        for c in unicodedata.normalize("NFKD", str(valor or "").strip().lower())
        if not unicodedata.combining(c)
    )
    for ch in (" ", "-", "."):
        texto = texto.replace(ch, "_")
    return "_".join(parte for parte in texto.split("_") if parte)


def _float_decimal(valor: object, padrao: Optional[float] = None) -> Optional[float]:
    if valor in (None, ""):
        return padrao
    try:
        return float(str(valor).strip().replace(",", "."))
    except (TypeError, ValueError):
        return padrao


def _int_decimal(valor: object, padrao: Optional[int] = None) -> Optional[int]:
    numero = _float_decimal(valor, None)
    if numero is None:
        return padrao
    return int(numero)


class CerebroSpawnPokemons:
    def __init__(self, core) -> None:
        self._core = core
        self._multiplicadores_bioma = self._carregar_multiplicadores_bioma()

    def tentar_spawn(self, chunks_simulados: Set[Chunk]) -> None:
        from SimuladorServerJogo.Gerais.Rotas.Ativador import registrar_diff

        if random.random() >= self._core._f("chance_spawn_pokemon_por_tick", 0.02):
            return
        if len(self._core._spawns_pokemon_ultimos_200) >= self._core._i("limite_spawn_pokemon_200_ticks", 4):
            return
        if self._core.contagem_pokemons_registrados() >= self._core._i("limite_total_pokemons", 100):
            return
        limite_por_chunk = self._core._f("limite_total_pokemons_por_chunk_existente", -1.0)
        if limite_por_chunk >= 0.0:
            chunks_existentes = len(set(chunks_simulados) | set(getattr(self._core, "_chunks_carregados_tick_atual", set())))
            limite_total = int(math.floor(max(0.0, limite_por_chunk) * max(0, chunks_existentes)))
            if self._core.contagem_pokemons_registrados() >= limite_total:
                return

        tentativas = int(self._core._i("tentativas_spawn_pokemon", 5))
        if tentativas <= 0:
            return
        chunk_tamanho = BANCO_DADOS.chunk_tamanho_unidade()
        chunk_list = list(chunks_simulados)
        random.shuffle(chunk_list)
        for _ in range(tentativas):
            if not chunk_list:
                return
            chunk = random.choice(chunk_list)
            if self._core._contar_pokemons_chunk(chunk) >= self._core._i("limite_pokemons_chunk", 2):
                continue
            if self._contar_pokemons_area_3x3(chunk) >= self._core._i("limite_pokemons_chunk_3x3", 7):
                continue

            x0, y0 = chunk[0] * chunk_tamanho, chunk[1] * chunk_tamanho
            px = random.uniform(x0 + 0.2, x0 + chunk_tamanho - 0.2)
            py = random.uniform(y0 + 0.2, y0 + chunk_tamanho - 0.2)
            if not self._core._posicao_spawn_valida((px, py), raio=0.45):
                continue

            row = self._escolher_candidato((px, py))
            if row is None:
                return
            novo_id = BANCO_DADOS.gerar_id()
            poke = gerar_pokemon_server(novo_id=novo_id, posicao=(px, py), chunk_xy=chunk, row_pokemon=row)
            BANCO_DADOS.inserir_objeto(poke)
            self._core._pokemons_ids.add(int(poke.Id))
            self._core._spawns_pokemon_ultimos_200.append(self._core._tick_contador)
            registrar_diff("spawn", payload=poke.serializar(), escopo={"centro": [px, py], "raio": 80}, objeto_id=poke.Id, autor="server", categoria="pokemon")
            return

    def _escolher_candidato(self, posicao: Vector2) -> Optional[Dict[str, str]]:
        bioma = self._bioma_spawn(posicao)
        snapshot = getattr(self._core, "_snapshot_tempo", {})
        dia = self._dia_atual(snapshot)
        candidatos: List[Dict[str, str]] = []
        pesos: List[float] = []
        for row in listar_candidatos_spawn_pokemon():
            raridade = self._raridade_valida(row)
            if raridade is None:
                continue
            if dia is not None and dia < self._dia_minimo_raridade(raridade):
                continue
            peso = self._peso_base_raridade(raridade)
            peso *= self._multiplicador_bioma(row, bioma)
            peso *= self._multiplicador_clima(row, snapshot)
            peso *= self._multiplicador_horario(row, snapshot)
            if peso <= 0.0:
                continue
            candidatos.append(row)
            pesos.append(float(peso))
        if not candidatos or sum(pesos) <= 0.0:
            return None
        return random.choices(candidatos, weights=pesos, k=1)[0]

    def _contar_pokemons_area_3x3(self, chunk: Chunk) -> int:
        area = {
            BANCO_DADOS.normalizar_chunk((int(chunk[0]) + dx, int(chunk[1]) + dy))
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
        }
        total = 0
        for oid in list(self._core._pokemons_ids):
            obj = BANCO_DADOS.obter_objeto(oid)
            if isinstance(obj, PokemonServer) and BANCO_DADOS.chunk_da_posicao(obj.posicao) in area:
                total += 1
        return total

    def _carregar_multiplicadores_bioma(self) -> Dict[str, Dict[str, float]]:
        tabela: Dict[str, Dict[str, float]] = {}
        try:
            linhas = carregar_csv_dict(_ARQUIVO_SPAWN_BIOMAS)
        except OSError:
            return tabela
        for row in linhas:
            bioma = _normalizar_chave(row.get("Bioma", ""))
            if not bioma:
                continue
            tabela[bioma] = {
                _normalizar_chave(tipo): valor
                for tipo, bruto in row.items()
                if _normalizar_chave(tipo) != "bioma"
                for valor in [_float_decimal(bruto, None)]
                if valor is not None
            }
        return tabela

    def _bioma_spawn(self, posicao: Vector2) -> str:
        try:
            gx = int(math.floor(float(posicao[0])))
            gy = int(math.floor(float(posicao[1])))
            codigo = int(BANCO_DADOS.bioma_em(gx, gy))
        except Exception:
            return "campo"
        return _BIOMA_POR_CODIGO.get(codigo, "campo")

    def _raridade_valida(self, row: Dict[str, str]) -> Optional[int]:
        bruto = str(row.get("Raridade", "") or "").strip().upper()
        if bruto in {"", "-", "FF"}:
            return None
        raridade = _int_decimal(bruto, None)
        if raridade is None or raridade < 1 or raridade > 10:
            return None
        return int(raridade)

    def _dia_atual(self, snapshot: object) -> Optional[int]:
        if not isinstance(snapshot, dict) or "dia" not in snapshot:
            return None
        return _int_decimal(snapshot.get("dia"), 0)

    def _dia_minimo_raridade(self, raridade: int) -> int:
        progressao = self._core._regras.get("progressao_raridade", {})
        if not isinstance(progressao, dict):
            return 0
        return int(_int_decimal(progressao.get(str(int(raridade))), 0) or 0)

    @staticmethod
    def _peso_base_raridade(raridade: int) -> float:
        return 1.0 / max(1.0, float(raridade))

    def _tipos_chances(self, row: Dict[str, str]) -> List[Tuple[str, Optional[float]]]:
        tipos: List[Tuple[str, Optional[float]]] = []
        for idx in (1, 2, 3):
            tipo = _normalizar_chave(row.get(f"Tipo{idx}", ""))
            if not tipo:
                continue
            chance = _float_decimal(row.get(f"%{idx}"), None)
            if chance is not None:
                chance = max(0.0, min(100.0, float(chance)))
            tipos.append((tipo, chance))
        return tipos

    def _media_ponderada_tipos(self, row: Dict[str, str], multiplicador_tipo) -> float:
        tipos = self._tipos_chances(row)
        if not tipos:
            return 1.0
        soma = 0.0
        for tipo, chance in tipos:
            mult = multiplicador_tipo(tipo)
            if mult is None or chance is None:
                soma += 1.0
            else:
                soma += max(0.0, float(mult)) * (float(chance) / 100.0)
        return soma / max(1, len(tipos))

    def _multiplicador_bioma(self, row: Dict[str, str], bioma: str) -> float:
        por_tipo = self._multiplicadores_bioma.get(_normalizar_chave(bioma))
        if not isinstance(por_tipo, dict):
            return 1.0
        return self._media_ponderada_tipos(row, lambda tipo: por_tipo.get(tipo))

    def _multiplicador_clima(self, row: Dict[str, str], snapshot: object) -> float:
        if not isinstance(snapshot, dict):
            return 1.0
        intensidade = _int_decimal(snapshot.get("chuva_intensidade"), 0) or 0
        if intensidade <= 0:
            return 1.0
        chuva_cfg = self._multiplicadores_spawn().get("chuva", {})
        if not isinstance(chuva_cfg, dict):
            return 1.0
        agua_mult = self._multiplicador_chuva_agua(chuva_cfg, intensidade)
        return self._media_ponderada_tipos(row, lambda tipo: agua_mult if tipo == "agua" else None)

    @staticmethod
    def _multiplicador_chuva_agua(chuva_cfg: Dict[str, object], intensidade: int) -> Optional[float]:
        escolhido: Optional[float] = None
        limite_escolhido = -1
        for chave, valor in chuva_cfg.items():
            chave_norm = _normalizar_chave(chave)
            prefixo = "agua_intensidade_"
            if not chave_norm.startswith(prefixo):
                continue
            limite = _int_decimal(chave_norm[len(prefixo):], None)
            mult = _float_decimal(valor, None)
            if limite is None or mult is None:
                continue
            if int(intensidade) >= int(limite) > limite_escolhido:
                escolhido = float(mult)
                limite_escolhido = int(limite)
        return escolhido

    def _multiplicador_horario(self, row: Dict[str, str], snapshot: object) -> float:
        minuto_atual = self._minuto_atual(snapshot)
        if minuto_atual is None:
            return 1.0
        horario_cfg = self._multiplicadores_spawn().get("horario", {})
        if not isinstance(horario_cfg, dict):
            return 1.0

        def mult_tipo(tipo: str) -> Optional[float]:
            cfg = horario_cfg.get(tipo)
            if not isinstance(cfg, dict):
                return None
            inicio = self._parse_hora_minuto(cfg.get("inicio"))
            fim = self._parse_hora_minuto(cfg.get("fim"))
            mult = _float_decimal(cfg.get("multiplicador"), None)
            if inicio is None or fim is None or mult is None:
                return None
            return float(mult) if self._horario_em_intervalo(minuto_atual, inicio, fim) else None

        return self._media_ponderada_tipos(row, mult_tipo)

    def _multiplicadores_spawn(self) -> Dict[str, object]:
        bruto = self._core._regras.get("multiplicadores_spawn", {})
        return bruto if isinstance(bruto, dict) else {}

    @staticmethod
    def _minuto_atual(snapshot: object) -> Optional[int]:
        if not isinstance(snapshot, dict) or "hora" not in snapshot:
            return None
        hora = _int_decimal(snapshot.get("hora"), None)
        minuto = _int_decimal(snapshot.get("minuto"), 0)
        if hora is None or minuto is None:
            return None
        return ((int(hora) % 24) * 60) + max(0, min(59, int(minuto)))

    @staticmethod
    def _parse_hora_minuto(valor: object) -> Optional[int]:
        partes = str(valor or "").strip().split(":")
        if len(partes) != 2:
            return None
        hora = _int_decimal(partes[0], None)
        minuto = _int_decimal(partes[1], None)
        if hora is None or minuto is None:
            return None
        return ((int(hora) % 24) * 60) + max(0, min(59, int(minuto)))

    @staticmethod
    def _horario_em_intervalo(atual: int, inicio: int, fim: int) -> bool:
        if inicio <= fim:
            return inicio <= atual <= fim
        return atual >= inicio or atual <= fim
