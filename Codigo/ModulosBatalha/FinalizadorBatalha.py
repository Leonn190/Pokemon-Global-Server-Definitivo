from __future__ import annotations

from copy import deepcopy
from typing import Dict, List

import pygame

from Codigo.Geradores.PokemonBatalha import PokemonBatalha
from Codigo.Telas.SubtelaFinalizacao import SubtelaFinalizacao


def _estado_pokemon(pokemon: Dict[str, object]) -> Dict[str, object]:
    return pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon


def _nome_pokemon(pokemon: Dict[str, object]) -> str:
    estado = _estado_pokemon(pokemon)
    return str(
        estado.get("nome")
        or estado.get("Nome")
        or estado.get("especie")
        or estado.get("Especie")
        or pokemon.get("nome")
        or pokemon.get("Nome")
        or "Pokemon"
    ).strip() or "Pokemon"


def _nivel_pokemon(pokemon: Dict[str, object]) -> int:
    estado = _estado_pokemon(pokemon)
    try:
        return int(float(estado.get("nivel", estado.get("Nivel", 0)) or 0))
    except (TypeError, ValueError):
        return 0


def _chaves_origem_pokemon(pokemon: Dict[str, object]) -> List[str]:
    estado = _estado_pokemon(pokemon)
    chaves: List[str] = []
    for valor in (
        pokemon.get("uid_original"),
        pokemon.get("uid"),
        pokemon.get("id"),
        pokemon.get("ID"),
        estado.get("uid_original"),
        estado.get("uid"),
        estado.get("id"),
        estado.get("ID"),
    ):
        chave = str(valor or "").strip()
        if chave and chave not in chaves:
            chaves.append(chave)
    return chaves


def _numero_int(valor: object, default: int = 0) -> int:
    try:
        return int(round(float(valor)))
    except (TypeError, ValueError):
        return int(default)


def _numero_float(valor: object, default: float = 0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def _valor_em_pokemon(pokemon: Dict[str, object], *chaves: str, default=None):
    estado = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else None
    for fonte in (pokemon, estado):
        if not isinstance(fonte, dict):
            continue
        for chave in chaves:
            if chave in fonte and fonte.get(chave) not in (None, ""):
                return fonte.get(chave)
    return default


def _atribuir_valores_pokemon(pokemon: Dict[str, object], valores: Dict[str, object]) -> None:
    estado = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else None
    for chave, valor in dict(valores or {}).items():
        pokemon[str(chave)] = deepcopy(valor)
        if isinstance(estado, dict):
            estado[str(chave)] = deepcopy(valor)


class FinalizadorBatalha:
    def __init__(self, controlador_batalha) -> None:
        self._controlador = controlador_batalha
        self._resumo_cache: Dict[str, object] | None = None
        self._aplicado_resultado_local = False
        self._notificou_derrotado = False
        self._subtela_emitida = False

    def pronto(self) -> bool:
        if self._controlador is None:
            return False
        if bool(getattr(self._controlador, "esta_reproduzindo_logs", lambda: False)()):
            return False
        return bool(getattr(self._controlador, "batalha_encerrada", lambda: False)())

    def criar_subtela(self, jogo):
        if self._subtela_emitida:
            return None
        resumo = self.preparar_resumo(jogo)
        if not isinstance(resumo, dict):
            return None
        self._subtela_emitida = True
        return SubtelaFinalizacao(
            itens=list(resumo.get("itens") or []),
            rodadas_totais=int(resumo.get("rodadas_totais", 0) or 0),
            vencedor=str(resumo.get("vencedor") or ""),
            ao_continuar=lambda: self.concluir(jogo),
        )

    def preparar_resumo(self, jogo) -> Dict[str, object] | None:
        if isinstance(self._resumo_cache, dict):
            if not self._aplicado_resultado_local:
                self._aplicar_resultado_local(jogo, self._resumo_cache)
            return self._resumo_cache

        if not self.pronto():
            return None

        resultado = dict(getattr(self._controlador, "resultado_batalha_atual", lambda: {})() or {})
        if not resultado:
            return None

        mapa_resumo_final = self._mapa_resumo_final(resultado)
        pokemons_base_jogador = list(getattr(self._controlador, "TimeCompletoJogadorInicial", []) or getattr(self._controlador.Jogador, "TimeCompleto", []) or [])
        itens = self._montar_itens_lado("jogador", pokemons_base_jogador, resultado, mapa_resumo_final)

        self._resumo_cache = {
            "encerrada": bool(resultado.get("encerrada", False)),
            "vencedor": str(resultado.get("vencedor") or ""),
            "perdedor": str(resultado.get("perdedor") or ""),
            "rodadas_totais": max(1, int(resultado.get("rodadas_totais", 0) or 1)),
            "itens": itens,
        }
        self._aplicar_resultado_local(jogo, self._resumo_cache)
        return self._resumo_cache

    def concluir(self, jogo) -> None:
        resumo = self.preparar_resumo(jogo)
        contexto = jogo.INFO.get("CombateContexto") if isinstance(jogo.INFO.get("CombateContexto"), dict) else {}
        pokemon_colisao = contexto.get("pokemon_colisao") if isinstance(contexto.get("pokemon_colisao"), dict) else {}
        pokemon_mundo_id = int(pokemon_colisao.get("id", pokemon_colisao.get("Id", pokemon_colisao.get("ID", 0))) or 0)
        player_dados = jogo.INFO.get("PlayerDadosServer") if isinstance(jogo.INFO.get("PlayerDadosServer"), dict) else {}
        inventario = player_dados.get("inventario") if isinstance(player_dados.get("inventario"), dict) else {}
        pendencia = {
            "inventario": deepcopy(inventario),
            "pokemon_mundo_id": int(pokemon_mundo_id),
            "encerrada": bool(isinstance(resumo, dict) and resumo.get("encerrada", False)),
        }
        jogo.INFO["SincronizacaoPosBatalhaMundo"] = pendencia
        jogo.INFO["ImuneCombateAteMs"] = int(pygame.time.get_ticks()) + 3000
        jogo.CenaAlvo = "Mundo"

    def _mapa_resumo_final(self, resultado: Dict[str, object]) -> Dict[str, Dict[str, object]]:
        resumo_final = resultado.get("resumo_final") if isinstance(resultado.get("resumo_final"), dict) else {}
        saida: Dict[str, Dict[str, object]] = {}
        for item in [dict(p) for p in list(resumo_final.get("pokemons") or []) if isinstance(p, dict)]:
            uid = str(item.get("uid") or "")
            if uid:
                saida[uid] = item
        return saida

    def _mapa_pokemons_finais_lado(self, resultado: Dict[str, object], lado: str) -> Dict[str, Dict[str, object]]:
        dados_lado = resultado.get(str(lado)) if isinstance(resultado.get(str(lado)), dict) else {}
        mapa: Dict[str, Dict[str, object]] = {}
        for lista_nome in ("ativos", "reservas"):
            for item in [dict(p) for p in list(dados_lado.get(lista_nome) or []) if isinstance(p, dict)]:
                uid = str(item.get("uid") or "")
                if uid:
                    mapa[uid] = item
        return mapa

    def _montar_itens_lado(
        self,
        lado: str,
        pokemons_base: List[Dict[str, object]],
        resultado: Dict[str, object],
        mapa_resumo_final: Dict[str, Dict[str, object]],
    ) -> List[Dict[str, object]]:
        mapa_finais = self._mapa_pokemons_finais_lado(resultado, lado)
        itens: List[Dict[str, object]] = []
        for indice, base in enumerate([dict(p) for p in pokemons_base if isinstance(p, dict)]):
            uid = str(base.get("uid") or "")
            final = dict(mapa_finais.get(uid) or {})
            resumo = dict(mapa_resumo_final.get(uid) or {})
            estatisticas = final.get("estatisticas_batalha") if isinstance(final.get("estatisticas_batalha"), dict) else {}
            if not estatisticas and resumo:
                estatisticas = {
                    "dano": resumo.get("dano"),
                    "abates": resumo.get("abates"),
                    "energia_gasta": resumo.get("energia_gasta"),
                    "rodadas": resumo.get("rodadas"),
                    "xp_multiplicador": resumo.get("xp_multiplicador"),
                    "xp_batalha": resumo.get("xp_batalha"),
                }
            visual = PokemonBatalha(base, posicao=(0.0, 0.0), lado=lado, regras=getattr(self._controlador, "Contexto", {}))
            if final:
                visual.atualizar(final)
            itens.append(
                {
                    "uid": uid,
                    "indice_time": int(indice),
                    "lado": str(lado),
                    "nome": _nome_pokemon(base),
                    "nivel": _nivel_pokemon(base),
                    "xp_batalha": _numero_int(final.get("xp_batalha", estatisticas.get("xp_batalha", 0))),
                    "dano": _numero_float(estatisticas.get("dano", 0.0), 0.0),
                    "abates": _numero_int(estatisticas.get("abates", 0), 0),
                    "energia_gasta": _numero_float(estatisticas.get("energia_gasta", 0.0), 0.0),
                    "rodadas": _numero_int(estatisticas.get("rodadas", resultado.get("rodadas_totais", 0)), 0),
                    "multiplicador_xp": _numero_float(estatisticas.get("xp_multiplicador", 1.0), 1.0),
                    "morto": bool(final.get("fora_de_combate", False)),
                    "pokemon_base": base,
                    "pokemon_final": final,
                    "visual": visual,
                }
            )
        return itens

    def _aplicar_resultado_local(self, jogo, resumo: Dict[str, object]) -> None:
        if self._aplicado_resultado_local:
            return
        player_dados = jogo.INFO.get("PlayerDadosServer") if isinstance(jogo.INFO.get("PlayerDadosServer"), dict) else {}
        inventario = player_dados.get("inventario") if isinstance(player_dados.get("inventario"), dict) else {}
        if not inventario:
            self._aplicado_resultado_local = True
            return

        contexto = jogo.INFO.get("CombateContexto") if isinstance(jogo.INFO.get("CombateContexto"), dict) else {}
        indice_time = int(contexto.get("time_jogador_indice", 0) or 0)
        times = list(inventario.get("times_pokemon", [])) if isinstance(inventario.get("times_pokemon"), list) else []
        pokemons_inventario = list(inventario.get("pokemons", [])) if isinstance(inventario.get("pokemons"), list) else []

        aliados = [item for item in list(resumo.get("itens") or []) if isinstance(item, dict) and str(item.get("lado") or "") == "jogador"]
        atualizados = [self._pokemon_com_resultado(item) for item in aliados]

        if 0 <= indice_time < len(times) and isinstance(times[indice_time], dict):
            time_escolhido = dict(times[indice_time])
            slots = list(time_escolhido.get("Slots", [])) if isinstance(time_escolhido.get("Slots"), list) else []
            for item, pokemon_atualizado in zip(aliados, atualizados):
                slot_idx = int(item.get("indice_time", 0) or 0)
                if 0 <= slot_idx < len(slots):
                    slots[slot_idx] = deepcopy(pokemon_atualizado)
            time_escolhido["Slots"] = slots
            times[indice_time] = time_escolhido

        usados_inventario: set[int] = set()
        for pokemon_atualizado in atualizados:
            idx = self._indice_pokemon_inventario(pokemons_inventario, pokemon_atualizado, usados_inventario)
            if idx is not None:
                pokemons_inventario[idx] = deepcopy(pokemon_atualizado)
                usados_inventario.add(idx)

        inventario["times_pokemon"] = times
        inventario["pokemons"] = pokemons_inventario
        player_dados["inventario"] = inventario
        jogo.INFO["PlayerDadosServer"] = player_dados
        self._aplicado_resultado_local = True

    def _pokemon_com_resultado(self, item: Dict[str, object]) -> Dict[str, object]:
        pokemon = deepcopy(dict(item.get("pokemon_base") or {}))
        final = dict(item.get("pokemon_final") or {})
        estatisticas = {
            "dano": round(_numero_float(item.get("dano", 0.0), 0.0), 4),
            "abates": _numero_int(item.get("abates", 0), 0),
            "energia_gasta": round(_numero_float(item.get("energia_gasta", 0.0), 0.0), 4),
            "rodadas": _numero_int(item.get("rodadas", 0), 0),
            "xp_multiplicador": round(_numero_float(item.get("multiplicador_xp", 1.0), 1.0), 4),
            "xp_batalha": _numero_int(item.get("xp_batalha", 0), 0),
        }
        xp_atual = _numero_int(_valor_em_pokemon(pokemon, "XP", "xp", default=0), 0)
        xp_total = xp_atual + estatisticas["xp_batalha"]
        _atribuir_valores_pokemon(
            pokemon,
            {
                "XP": int(xp_total),
                "xp": int(xp_total),
                "VidaAtual": _numero_float(final.get("vida_atual", _valor_em_pokemon(pokemon, "VidaAtual", "vida_atual", default=0.0)), 0.0),
                "vida_atual": _numero_float(final.get("vida_atual", _valor_em_pokemon(pokemon, "VidaAtual", "vida_atual", default=0.0)), 0.0),
                "energia": _numero_float(final.get("energia", _valor_em_pokemon(pokemon, "energia", default=0.0)), 0.0),
                "EnergiaAtual": _numero_float(final.get("energia", _valor_em_pokemon(pokemon, "EnergiaAtual", "energia_atual", "energia", default=0.0)), 0.0),
                "energia_atual": _numero_float(final.get("energia", _valor_em_pokemon(pokemon, "EnergiaAtual", "energia_atual", "energia", default=0.0)), 0.0),
                "fora_de_combate": bool(final.get("fora_de_combate", _valor_em_pokemon(pokemon, "fora_de_combate", default=False))),
                "estatisticas_batalha": dict(estatisticas),
                "xp_batalha": int(estatisticas["xp_batalha"]),
            },
        )
        return pokemon

    def _indice_pokemon_inventario(self, pokemons_inventario: List[Dict[str, object]], alvo: Dict[str, object], usados: set[int]) -> int | None:
        chaves_alvo = _chaves_origem_pokemon(alvo)
        for indice, pokemon in enumerate(pokemons_inventario):
            if indice in usados or not isinstance(pokemon, dict):
                continue
            chaves_existentes = _chaves_origem_pokemon(pokemon)
            if chaves_alvo and any(chave in chaves_existentes for chave in chaves_alvo):
                return indice

        nome_alvo = _nome_pokemon(alvo).casefold()
        nivel_alvo = _nivel_pokemon(alvo)
        candidatos: List[int] = []
        for indice, pokemon in enumerate(pokemons_inventario):
            if indice in usados or not isinstance(pokemon, dict):
                continue
            if _nome_pokemon(pokemon).casefold() == nome_alvo and _nivel_pokemon(pokemon) == nivel_alvo:
                candidatos.append(indice)
        if len(candidatos) == 1:
            return candidatos[0]
        return None
