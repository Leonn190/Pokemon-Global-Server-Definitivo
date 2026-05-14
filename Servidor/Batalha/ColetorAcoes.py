from __future__ import annotations

import copy
import unicodedata

from Servidor.Batalha.Alvificacao import (
    area_id_para_selecao,
    area_permitida_para_ataque,
    areas_afetadas_por_alvificacao,
    config_para_selecao,
    pokemon_permitido_para_ataque,
    selecoes_alvo_acao,
    validar_provocando_selecoes,
    validar_quantidade_selecoes,
)
from Servidor.Batalha.PropriedadesAtaques import buscar_por_nome_ou_code, carregar_propriedades_ataques


def _normalizar(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _f(valor: object, default: float = 0.0) -> float:
    try:
        if isinstance(valor, str):
            return float(valor.replace(",", "."))
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def _prioridade_acao(acao) -> float:
    if str((acao or {}).get("tipo") or "") != "ataque":
        return 0.0
    props = (acao or {}).get("propriedades") if isinstance((acao or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    return _f(parametros.get("prioridade_acao", props.get("prioridade_acao", 0.0)), 0.0)


class ColetorAcoes:
    TIPOS_VALIDOS = {"ataque", "movimento", "troca_posicao", "troca_reserva", "captura"}

    def __init__(self, partida):
        self.partida = partida
        self.propriedades_ataques = self._carregar_propriedades_ataques()

    def _carregar_propriedades_ataques(self):
        return carregar_propriedades_ataques()

    def buscar_propriedades_ataque(self, ataque):
        return buscar_por_nome_ou_code(self.propriedades_ataques, ataque)

    def coletar(self, jogadas_recebidas):
        acoes_validas = []
        acoes_invalidas = []
        contador_global = 1
        for lado_id, jogada in sorted((jogadas_recebidas or {}).items(), key=lambda item: str(item[0])):
            jogada = jogada if isinstance(jogada, dict) else {}
            acoes = list(jogada.get("acoes") or [])
            if int(lado_id) not in self.partida.lados:
                acoes_invalidas.append({"lado_id": lado_id, "motivo_invalidacao": "lado_inexistente"})
                continue
            if len(acoes) > 5:
                for excedente in acoes[5:]:
                    inv = dict(excedente) if isinstance(excedente, dict) else {"acao": excedente}
                    inv["motivo_invalidacao"] = "limite_5_acoes_por_lado"
                    acoes_invalidas.append(inv)
                acoes = acoes[:5]
            contagem_pokemon = {}
            for ordem_local, acao in enumerate(acoes, start=1):
                normalizada = self._normalizar_acao(acao, int(lado_id), ordem_local, contador_global, contagem_pokemon)
                contador_global += 1
                if normalizada.get("motivo_invalidacao"):
                    acoes_invalidas.append(normalizada)
                else:
                    acoes_validas.append(normalizada)
        return self.ordenar_acoes(acoes_validas), acoes_invalidas

    def _normalizar_acao(self, acao, lado_id, ordem_local, contador_global, contagem_pokemon):
        if not isinstance(acao, dict):
            return {"lado_id": lado_id, "ordem_local": ordem_local, "motivo_invalidacao": "acao_nao_dict"}
        out = copy.deepcopy(acao)
        out["id_acao"] = str(out.get("id_acao") or out.get("id") or out.get("id_local") or self.partida.novo_id_acao(out.get("lado_id", lado_id)))
        out["ordem_local"] = int(out.get("ordem_local", ordem_local) or ordem_local)
        out["lado_id"] = int(out.get("lado_id", lado_id) or lado_id)
        out["ordem_global"] = contador_global
        tipo = str(out.get("tipo") or "").strip().lower()
        out["tipo"] = tipo
        if tipo not in self.TIPOS_VALIDOS:
            return self._invalidar(out, "tipo_acao_invalido")
        if out["lado_id"] != int(lado_id):
            return self._invalidar(out, "lado_acao_divergente")
        if tipo == "captura":
            contagem_pokemon["__captura__"] = contagem_pokemon.get("__captura__", 0) + 1
            if contagem_pokemon["__captura__"] > 1:
                return self._invalidar(out, "limite_1_captura_por_turno")
            return self._normalizar_captura(out, lado_id)
        pid = str(out.get("pokemon_id") or "").strip()
        pokemon = self.partida.obter_pokemon(pid)
        if pokemon is None:
            return self._invalidar(out, "pokemon_inexistente")
        if int(pokemon.lado_id) != int(lado_id):
            return self._invalidar(out, "pokemon_de_outro_lado")
        if not pokemon.esta_vivo():
            return self._invalidar(out, "pokemon_morto")
        exige_ativo = tipo in {"ataque", "movimento", "troca_posicao", "troca_reserva", "captura"}
        if exige_ativo and (not pokemon.ativo or pokemon.reserva):
            return self._invalidar(out, "pokemon_nao_ativo")
        bloqueio = self._bloqueio_efeito_acao(pokemon, tipo)
        if bloqueio:
            return self._invalidar(out, bloqueio)
        if tipo != "captura":
            contagem_pokemon[pid] = contagem_pokemon.get(pid, 0) + 1
        out["ordem_pokemon"] = contagem_pokemon.get(pid, 1)
        limite_pokemon = 3 if str(getattr(self.partida, "tipo_batalha", "") or "").strip().lower() == "boss" and int(lado_id) != int(getattr(self.partida, "lado_jogador", 50) or 50) else 2
        if tipo != "captura" and contagem_pokemon[pid] > limite_pokemon:
            return self._invalidar(out, "limite_3_acoes_por_pokemon" if limite_pokemon == 3 else "limite_2_acoes_por_pokemon")
        custo = self._calcular_custo(out, pokemon)
        if custo is None:
            return self._invalidar(out, "custo_indefinido")
        out["custo_real"] = round(custo, 2)
        if tipo == "ataque":
            props = self.buscar_propriedades_ataque(out.get("ataque") if isinstance(out.get("ataque"), dict) else {})
            if not isinstance(props, dict):
                return self._invalidar(out, "ataque_sem_json")
            if str(props.get("estilo_logico") or "").strip().lower() == "passivo":
                return self._invalidar(out, "ataque_passivo_manual")
            if str(props.get("estilo_logico") or "").strip().lower() == "ativo":
                if isinstance(out.get("alvo"), dict) and out.get("alvo", {}).get("area_id"):
                    return self._invalidar(out, "ataque_ativo_nao_aceita_alvo")
                out["alvo"] = None
            else:
                alvo = out.get("alvo") if isinstance(out.get("alvo"), dict) else {}
                selecoes = selecoes_alvo_acao(alvo, props)
                if not selecoes:
                    return self._invalidar(out, "ataque_sem_area_alvo")
                motivo_quantidade = validar_quantidade_selecoes(alvo, selecoes, props)
                if motivo_quantidade:
                    return self._invalidar(out, motivo_quantidade)
                vistos = set()
                for selecao in selecoes:
                    alvo_cfg = config_para_selecao(selecao, props)
                    if str(alvo_cfg.get("tipo") or "").strip().lower() == "pokemon":
                        alvo_pokemon = self.partida.obter_pokemon(selecao.get("pokemon_id"))
                        if not pokemon_permitido_para_ataque(self.partida, pokemon, alvo_pokemon, props, alvo_cfg, checar_provocando=False):
                            return self._invalidar(out, "pokemon_alvo_nao_permitido")
                        chave = ("pokemon", str(getattr(alvo_pokemon, "id_batalha", "") or ""))
                    else:
                        area_id = area_id_para_selecao(selecao, alvo_cfg)
                        if not area_id:
                            return self._invalidar(out, "ataque_sem_area_alvo")
                        if not area_permitida_para_ataque(self.partida, pokemon, area_id, props, alvo_cfg, checar_provocando=False):
                            return self._invalidar(out, "area_alvo_nao_permitida")
                        chave = ("area", str(alvo_cfg.get("tipo") or "area"), tuple(areas_afetadas_por_alvificacao(area_id, props, getattr(pokemon, "lado_id", None), alvo_cfg, self.partida)))
                    if chave in vistos:
                        return self._invalidar(out, "alvo_repetido")
                    vistos.add(chave)
                if not validar_provocando_selecoes(self.partida, pokemon, selecoes, props):
                    return self._invalidar(out, "alvo_nao_respeita_provocando")
            out["propriedades"] = copy.deepcopy(props)
        elif tipo == "movimento":
            destino = out.get("destino") if isinstance(out.get("destino"), dict) else {}
            if not self.partida.area_existe(destino.get("area_id")):
                return self._invalidar(out, "destino_invalido")
        elif tipo == "troca_posicao":
            outro = self.partida.obter_pokemon(out.get("pokemon_destino_id"))
            if outro is None or int(outro.lado_id) != int(lado_id) or not outro.ativo or outro.reserva:
                return self._invalidar(out, "troca_posicao_destino_invalido")
        elif tipo == "troca_reserva":
            destino = out.get("destino") if isinstance(out.get("destino"), dict) else {}
            reserva_id = out.get("pokemon_reserva_id") or out.get("troca_reserva_id") or destino.get("pokemon_id")
            reserva = self.partida.obter_pokemon(reserva_id)
            if reserva is None or int(reserva.lado_id) != int(lado_id) or not reserva.reserva or not reserva.esta_vivo():
                return self._invalidar(out, "reserva_invalida")
            out["pokemon_reserva_id"] = reserva.id_batalha
        return out

    def _normalizar_captura(self, out, lado_id):
        tipo_batalha = str(getattr(self.partida, "tipo_batalha", "") or "").strip().lower()
        if tipo_batalha != "confronto" or bool(getattr(self.partida, "modo_teste", False)):
            return self._invalidar(out, "captura_bloqueada_tipo_batalha" if tipo_batalha in {"servo", "boss"} else "captura_fora_de_confronto")
        alvo = out.get("alvo") if isinstance(out.get("alvo"), dict) else {}
        alvo_pokemon = self.partida.obter_pokemon(alvo.get("pokemon_id"))
        if alvo_pokemon is None:
            return self._invalidar(out, "captura_alvo_inexistente")
        if int(alvo_pokemon.lado_id) == int(lado_id):
            return self._invalidar(out, "captura_alvo_aliado")
        if not alvo_pokemon.esta_vivo() or not bool(alvo_pokemon.ativo) or bool(alvo_pokemon.reserva):
            return self._invalidar(out, "captura_alvo_invalido")
        bola = out.get("bola") if isinstance(out.get("bola"), dict) else {}
        item_base_id = str(out.get("item_base_id") or bola.get("item_base_id") or bola.get("Code") or "").strip()
        item_nome = str(out.get("item_nome") or bola.get("Nome") or bola.get("nome") or "Pokeball").strip()
        if not self.partida.tem_pokebola_batalha(lado_id, item_base_id, item_nome):
            return self._invalidar(out, "pokebola_indisponivel")
        out["pokemon_id"] = str(out.get("pokemon_id") or "")
        out["capturador_tipo"] = "jogador"
        out["jogador_nome"] = str(out.get("jogador_nome") or "Jogador")
        out["item_base_id"] = item_base_id
        out["item_nome"] = item_nome
        out["bola"] = {"Nome": item_nome, "Code": item_base_id, "item_base_id": item_base_id, "quantidade": 1}
        out["ordem_pokemon"] = 0
        out["custo_real"] = 0.0
        return out

    def _calcular_custo(self, acao, pokemon):
        tipo = str(acao.get("tipo") or "")
        if tipo == "movimento":
            base = 15.0
        elif tipo in {"troca_posicao", "troca_reserva"}:
            base = 20.0
        elif tipo == "ataque":
            props = self.buscar_propriedades_ataque(acao.get("ataque") if isinstance(acao.get("ataque"), dict) else {})
            if not isinstance(props, dict):
                ataque = acao.get("ataque") if isinstance(acao.get("ataque"), dict) else {}
                base = _f(ataque.get("custo", ataque.get("Custo", 0.0)), 0.0)
                if base <= 0:
                    return None
            else:
                base = _f(props.get("custo"), 0.0)
        else:
            if tipo == "captura":
                return 0.0
            return None
        if tipo == "ataque" and pokemon.possui_efeito("Encharcado"):
            base *= 1.20
        if tipo == "movimento" and _normalizar(getattr(self.partida, "clima_atual", None)) == "gravidadeanomala":
            base *= 2.0
        mult = 1.10 if int(acao.get("ordem_pokemon", 1) or 1) >= 2 else 1.0
        return base * mult

    def _invalidar(self, acao, motivo):
        out = dict(acao)
        out["motivo_invalidacao"] = motivo
        return out

    def _bloqueio_efeito_acao(self, pokemon, tipo):
        tipo = str(tipo or "")
        if tipo == "captura":
            return None
        if pokemon.possui_efeito("Dormindo") or pokemon.possui_efeito("Congelado"):
            return "acao_bloqueada_por_efeito"
        if tipo == "ataque" and pokemon.possui_efeito("Paralisado"):
            return "ataque_bloqueado_por_paralisia"
        if tipo in {"movimento", "troca_posicao", "troca_reserva"} and pokemon.possui_efeito("Enraizado"):
            return "movimento_bloqueado_por_enraizado"
        return None

    def ordenar_acoes(self, acoes):
        desempates = {}
        for acao in list(acoes or []):
            if str((acao or {}).get("tipo") or "") == "captura":
                continue
            pid = str((acao or {}).get("pokemon_id") or "")
            if pid and pid not in desempates:
                desempates[pid] = self.partida.rng.random()

        def chave(acao):
            if str((acao or {}).get("tipo") or "") == "captura":
                return (1, 0, 0, "~jogador", 999, int((acao or {}).get("ordem_global") or 0))
            pokemon = self.partida.obter_pokemon(acao.get("pokemon_id"))
            int_val = pokemon.obter_atributo("Int") if pokemon is not None else 0.0
            vel_val = pokemon.obter_atributo("Vel") if pokemon is not None else 0.0
            pid = str(acao.get("pokemon_id") or "")
            return (0, -_prioridade_acao(acao), -int_val, -vel_val, desempates.get(pid, 0.0), int(acao.get("ordem_pokemon") or 1), int(acao.get("ordem_global") or 0))

        ordenadas = sorted(acoes, key=chave)
        for idx, acao in enumerate(ordenadas, start=1):
            acao["ordem_global"] = idx
        return ordenadas
