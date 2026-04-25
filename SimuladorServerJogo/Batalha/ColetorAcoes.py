from __future__ import annotations

import json
from pathlib import Path


def _i(v, d=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return d


class ColetorAcoes:
    TIPOS = {"ataque", "movimento", "troca_posicao", "troca_reserva"}

    def __init__(self, partida):
        self.partida = partida
        self.ataques = self._carregar_ataques()
        self.seq_acao = 200000

    def _carregar_ataques(self):
        caminho = Path(__file__).resolve().parents[2] / "Dados" / "Pokemon Global Server - PropriedadesAtaques.json"
        try:
            data = json.loads(caminho.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return dict(data.get("ataques") or {})

    def obter_ataque(self, acao):
        at = dict((acao or {}).get("ataque") or {})
        code = str(_i(at.get("Code", at.get("ID")), 0))
        return dict(self.ataques.get(code) or {})

    def coletar(self):
        validas = []
        invalidas = []
        for lado_id, jogada in sorted(self.partida.jogadas_recebidas.items(), key=lambda x: x[0]):
            acoes = list((jogada or {}).get("acoes") or [])[:5]
            ordem_por_pokemon = {}
            for ordem_local, acao in enumerate(acoes, start=1):
                norm = self.normalizar_acao(lado_id, acao, ordem_local, ordem_por_pokemon)
                if norm.get("valida"):
                    validas.append(norm)
                else:
                    invalidas.append(norm)
        validas.sort(key=lambda a: (-a.get("int", 0), -a.get("vel", 0), a.get("tie", ""), a.get("ordem_local", 0)))
        for idx, acao in enumerate(validas, start=1):
            acao["ordem_global"] = idx
        return validas, invalidas

    def normalizar_acao(self, lado_id, acao, ordem_local, ordem_por_pokemon):
        self.seq_acao += 1
        out = dict(acao or {}) if isinstance(acao, dict) else {}
        out.update({"id_acao": str(self.seq_acao), "lado_id": int(lado_id), "ordem_local": int(ordem_local), "ordem_global": 0, "valida": True, "motivo_invalidacao": None})
        if not isinstance(acao, dict):
            out["valida"] = False
            out["motivo_invalidacao"] = "acao_invalida"
            return out
        t = str(out.get("tipo") or "")
        if t not in self.TIPOS:
            out["valida"] = False
            out["motivo_invalidacao"] = "tipo_invalido"
            return out
        pid = str(out.get("pokemon_id") or "")
        poke = self.partida.obter_pokemon(pid)
        out["pokemon"] = pid
        if poke is None or poke.lado_id != int(lado_id):
            out["valida"] = False
            out["motivo_invalidacao"] = "pokemon_invalido"
            return out
        if not poke.esta_vivo():
            out["valida"] = False
            out["motivo_invalidacao"] = "pokemon_morto"
            return out
        ordem_por_pokemon[pid] = ordem_por_pokemon.get(pid, 0) + 1
        out["ordem_pokemon"] = ordem_por_pokemon[pid]
        if ordem_por_pokemon[pid] > 2:
            out["valida"] = False
            out["motivo_invalidacao"] = "limite_pokemon"
        out["custo_real"] = self.calcular_custo(out, poke)
        out["int"] = poke.atributos_finais.get("Int", 0.0)
        out["vel"] = poke.atributos_finais.get("Vel", 0.0)
        out["tie"] = f"{self.partida.seed_partida}-{pid}"
        if t == "ataque":
            at = self.obter_ataque(out)
            if not at:
                out["valida"] = False
                out["motivo_invalidacao"] = "ataque_invalido"
            elif str(at.get("estilo_logico") or "").lower() == "passivo":
                out["valida"] = False
                out["motivo_invalidacao"] = "ataque_passivo"
            elif str(at.get("estilo_logico") or "alvo").lower() == "alvo":
                area = ((out.get("alvo") or {}).get("area_id") or "")
                if area not in self.partida.areas:
                    out["valida"] = False
                    out["motivo_invalidacao"] = "alvo_invalido"
        elif t == "movimento":
            area = ((out.get("destino") or {}).get("area_id") or "")
            if area not in self.partida.areas:
                out["valida"] = False
                out["motivo_invalidacao"] = "destino_invalido"
        elif t == "troca_posicao":
            d = self.partida.obter_pokemon(str(out.get("pokemon_destino_id") or ""))
            if d is None or d.lado_id != poke.lado_id or not d.ativo:
                out["valida"] = False
                out["motivo_invalidacao"] = "troca_posicao_invalida"
        elif t == "troca_reserva":
            d = self.partida.obter_pokemon(str(out.get("pokemon_reserva_id") or ""))
            if d is None or d.lado_id != poke.lado_id or not d.reserva or not d.esta_vivo():
                out["valida"] = False
                out["motivo_invalidacao"] = "reserva_invalida"
        return out

    def calcular_custo(self, acao, pokemon):
        t = str((acao or {}).get("tipo") or "")
        if t == "movimento" or t == "troca_posicao":
            base = 10.0
        elif t == "troca_reserva":
            base = 15.0
        else:
            base = float(self.obter_ataque(acao).get("custo", (acao.get("custo_previsto") or 0.0)) or 0.0)
        if int((acao or {}).get("ordem_pokemon", 1)) >= 2:
            base *= 1.10
        return round(base, 2)
