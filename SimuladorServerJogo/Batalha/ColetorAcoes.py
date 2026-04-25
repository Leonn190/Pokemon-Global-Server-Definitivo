from __future__ import annotations

import copy
import json
import unicodedata
from pathlib import Path


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


class ColetorAcoes:
    TIPOS_VALIDOS = {"ataque", "movimento", "troca_posicao", "troca_reserva"}

    def __init__(self, partida):
        self.partida = partida
        self.propriedades_ataques = self._carregar_propriedades_ataques()

    def _carregar_propriedades_ataques(self):
        caminho = Path(__file__).resolve().parents[2] / "Dados" / "Pokemon Global Server - PropriedadesAtaques.json"
        if not caminho.exists():
            return {}
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except Exception:
            return {}
        ataques = dados.get("ataques") if isinstance(dados, dict) else {}
        return ataques if isinstance(ataques, dict) else {}

    def buscar_propriedades_ataque(self, ataque):
        if not isinstance(ataque, dict):
            return None
        code = str(ataque.get("Code") or ataque.get("ID") or ataque.get("code") or "").strip()
        if code:
            try:
                code = str(int(float(code)))
            except (TypeError, ValueError):
                pass
            if code in self.propriedades_ataques:
                return self.propriedades_ataques.get(code)
        nome = _normalizar(ataque.get("nome") or ataque.get("Nome") or ataque.get("Ataque"))
        if nome:
            for item in self.propriedades_ataques.values():
                if _normalizar(item.get("nome")) == nome:
                    return item
        return None

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
        out["id_acao"] = str(out.get("id_acao") or out.get("id") or out.get("id_local") or f"A{contador_global}")
        out["ordem_local"] = int(out.get("ordem_local", ordem_local) or ordem_local)
        out["lado_id"] = int(out.get("lado_id", lado_id) or lado_id)
        out["ordem_global"] = contador_global
        tipo = str(out.get("tipo") or "").strip().lower()
        out["tipo"] = tipo
        if tipo not in self.TIPOS_VALIDOS:
            return self._invalidar(out, "tipo_acao_invalido")
        if out["lado_id"] != int(lado_id):
            return self._invalidar(out, "lado_acao_divergente")
        pid = str(out.get("pokemon_id") or "").strip()
        pokemon = self.partida.obter_pokemon(pid)
        if pokemon is None:
            return self._invalidar(out, "pokemon_inexistente")
        if int(pokemon.lado_id) != int(lado_id):
            return self._invalidar(out, "pokemon_de_outro_lado")
        if not pokemon.esta_vivo():
            return self._invalidar(out, "pokemon_morto")
        exige_ativo = tipo in {"ataque", "movimento", "troca_posicao", "troca_reserva"}
        if exige_ativo and (not pokemon.ativo or pokemon.reserva):
            return self._invalidar(out, "pokemon_nao_ativo")
        contagem_pokemon[pid] = contagem_pokemon.get(pid, 0) + 1
        out["ordem_pokemon"] = contagem_pokemon[pid]
        if contagem_pokemon[pid] > 2:
            return self._invalidar(out, "limite_2_acoes_por_pokemon")
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
                area_id = alvo.get("area_id")
                if not area_id:
                    return self._invalidar(out, "ataque_sem_area_alvo")
                if not self._area_permitida_para_ataque(pokemon, area_id, props):
                    return self._invalidar(out, "area_alvo_nao_permitida")
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
            return None
        mult = 1.10 if int(acao.get("ordem_pokemon", 1) or 1) >= 2 else 1.0
        return base * mult

    def _invalidar(self, acao, motivo):
        out = dict(acao)
        out["motivo_invalidacao"] = motivo
        return out

    def _area_permitida_para_ataque(self, pokemon, area_id, props):
        area = self.partida.areas.get(str(area_id or ""))
        if not isinstance(area, dict):
            return False
        alvo_cfg = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
        if bool(alvo_cfg.get("exige_area_ocupada")) and self.partida.pokemon_na_area(area_id) is None:
            return False
        permitidos = alvo_cfg.get("lados_permitidos")
        if not isinstance(permitidos, (list, tuple, set)) or not permitidos:
            return True
        lado_area = int(area.get("lado_id", -999))
        lado_origem = int(getattr(pokemon, "lado_id", -998))
        area_origem = str(getattr(pokemon, "area_id", ""))
        for item in permitidos:
            token = str(item or "").strip().lower()
            if token in {"qualquer", "qualquer_lado", "todos", "ambos"}:
                return True
            if token in {"lado_oposto", "oposto", "inimigo", "inimigos", "adversario", "adversarios"} and lado_area != lado_origem:
                return True
            if token in {"mesmo_lado", "aliado", "aliados", "proprio_lado"} and lado_area == lado_origem:
                return True
            if token in {"usuario", "proprio", "si_mesmo"} and str(area_id) == area_origem:
                return True
        return False

    def ordenar_acoes(self, acoes):
        def chave(acao):
            pokemon = self.partida.obter_pokemon(acao.get("pokemon_id"))
            int_val = pokemon.obter_atributo("Int") if pokemon is not None else 0.0
            vel_val = pokemon.obter_atributo("Vel") if pokemon is not None else 0.0
            return (-int_val, -vel_val, str(acao.get("pokemon_id") or ""), int(acao.get("ordem_pokemon") or 1), int(acao.get("ordem_global") or 0))

        ordenadas = sorted(acoes, key=chave)
        for idx, acao in enumerate(ordenadas, start=1):
            acao["ordem_global"] = idx
        return ordenadas
