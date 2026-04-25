from __future__ import annotations


def processar_passivas_ataque(contexto: dict, flag: str):
    alvo = contexto.get("alvo")
    if alvo is None:
        return []
    eventos = []
    if flag == "AoSerAtacado":
        for ataque in list(getattr(alvo, "ataques", []) or []):
            code = int((ataque or {}).get("Code") or (ataque or {}).get("ID") or 0)
            if code == 18:
                alvo.variacoes_permanentes["Amp"] = float(alvo.variacoes_permanentes.get("Amp", 0.0)) + 4.0
                eventos.append({"tipo": "passiva_acumulador", "pokemon_id": alvo.id_batalha, "amp_ganho": 4})
                break
    return eventos
