from __future__ import annotations

import unicodedata


def _normalizar(valor):
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def processar_passivas_ataque(contexto, flag):
    if str(flag) != "antes_receber_ataque":
        return []
    alvo = (contexto or {}).get("alvo")
    if alvo is None:
        return []
    possui = False
    for ataque in list(getattr(alvo, "ataques", []) or []):
        nome = _normalizar((ataque or {}).get("nome") or (ataque or {}).get("Nome") or (ataque or {}).get("Ataque"))
        code = str((ataque or {}).get("Code") or (ataque or {}).get("ID") or "")
        if nome == "acumulador" or code == "18":
            possui = True
            break
    if not possui:
        return []
    alvo.variacoes_permanentes["Amp"] = float(alvo.variacoes_permanentes.get("Amp", 0.0) or 0.0) + 4.0
    alvo.recalcular_atributos()
    return [{"passiva": "Acumulador", "pokemon_id": alvo.id_batalha, "Amp": alvo.variacoes_permanentes["Amp"]}]

