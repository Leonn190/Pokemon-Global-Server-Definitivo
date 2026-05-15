from __future__ import annotations

import unicodedata

from Servidor.Batalha.FraquezasResistencia import obter_multiplicador


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


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def aplicar_dano(usuario, alvo, dados_dano, contexto=None):
    if alvo is None or not alvo.esta_vivo():
        return {"aplicado": False, "motivo": "alvo_invalido", "dano_vida": 0.0}
    contexto = dict(contexto or {})
    dados = dict(dados_dano or {})
    dano = max(0.0, _f(dados.get("dano_bruto", dados.get("dano", 0.0)), 0.0))
    calculo = [f"Dano bruto = {round(dano, 4)}"]
    usuario._disparar_flag(
        "AntesAplicarDano",
        {
            "partida": usuario.partida,
            "usuario": usuario,
            "alvo": alvo,
            "pokemon_evento": usuario,
            "dados_dano": dados,
            **contexto,
        },
        reativos=contexto.get("reativos_acao"),
    )
    for item in list(dados.get("multiplicadores_condicionais") or []):
        if not isinstance(item, dict):
            continue
        mult = _f(item.get("multiplicador", item.get("valor", 1.0)), 1.0)
        if abs(mult - 1.0) <= 0.001:
            continue
        antes = dano
        dano *= mult
        label = "Multiplicador Condicional"
        calculo.append(f"{label}: {round(antes, 4)} * {round(mult, 4)} = {round(dano, 4)}")
    for item in list(dados.get("ajustes_condicionais") or []):
        if not isinstance(item, dict):
            continue
        valor = _f(item.get("valor"), 0.0)
        if abs(valor) <= 0.001:
            continue
        antes = dano
        op = str(item.get("op") or "add").strip().lower()
        dano = max(0.0, dano - valor) if op in {"sub", "subtract", "-"} else max(0.0, dano + valor)
        sinal = "-" if op in {"sub", "subtract", "-"} else "+"
        label = "Ajuste Condicional"
        calculo.append(f"{label}: {round(antes, 4)} {sinal} {round(valor, 4)} = {round(dano, 4)}")
    dano_pos_condicional = dano
    tipo = dados.get("tipo") or contexto.get("tipo_ataque") or "normal"
    categoria = _normalizar(dados.get("categoria") or "normal")
    if usuario.partida is not None and hasattr(usuario.partida, "aplicar_modificadores_dano_clima"):
        antes = dano
        dano, mult_clima = usuario.partida.aplicar_modificadores_dano_clima(tipo, dano)
        if abs(mult_clima - 1.0) > 0.001:
            calculo.append(f"Clima: {round(antes, 4)} * {round(mult_clima, 4)} = {round(dano, 4)}")
    mult_amp = 1.0 + (usuario.obter_atributo("Amp") / 100.0)
    if abs(mult_amp - 1.0) > 0.001:
        antes = dano
        dano *= mult_amp
        calculo.append(f"Amplificacao: {round(antes, 4)} * {round(mult_amp, 4)} = {round(dano, 4)}")
    mult_tipo = obter_multiplicador(tipo, alvo.tipos)
    if abs(mult_tipo - 1.0) > 0.001:
        antes = dano
        dano *= mult_tipo
        calculo.append(f"Tipo: {round(antes, 4)} * {round(mult_tipo, 4)} = {round(dano, 4)}")
    if _normalizar(tipo) in {_normalizar(t) for t in usuario.tipos}:
        antes = dano
        dano *= 1.20
        calculo.append(f"STAB: {round(antes, 4)} * 1.2 = {round(dano, 4)}")
    rng = contexto.get("rng") or getattr(getattr(usuario, "partida", None), "rng", None)
    chance_crit_bruta = _f(dados.get("chance_critico", usuario.obter_atributo("CrC")), 0.0) + _f(dados.get("bonus_critico_acerto", contexto.get("bonus_critico_acerto", 0.0)), 0.0)
    chance_crit_bruta = min(chance_crit_bruta, _f(dados.get("chance_critico_max", 999.0), 999.0))
    excedente_crit = max(0.0, chance_crit_bruta - 100.0)
    chance_crit = _clamp(chance_crit_bruta, 0.0, 100.0)
    critico = False
    if not usuario.possui_efeito("Cauterizado") and chance_crit > 0:
        sorte = rng.random() * 100.0 if rng is not None else 100.0
        critico = sorte <= chance_crit
    if critico:
        crd_contexto = usuario.obter_atributo("CrD") + (excedente_crit / 2.0)
        mult_crit = 1.0 + (crd_contexto / 100.0)
        antes = dano
        dano *= mult_crit
        calculo.append(f"Critico: {round(antes, 4)} * {round(mult_crit, 4)} = {round(dano, 4)}")
    defesa_chave = "SpD" if categoria in {"especial", "spa", "magico"} else "Def"
    defesa = alvo.obter_atributo(defesa_chave)
    ignora_defesa = bool(dados.get("ignorar_defesa") or dados.get("ignora_defesa"))
    usar_per_no_dano = not (dados.get("usar_per_no_dano") is False or dados.get("ignorar_perfuracao") or dados.get("sem_per"))
    perfuracao = usuario.obter_atributo("Per") / 2.0 if usar_per_no_dano else 0.0
    defesa_efetiva = 0.0 if ignora_defesa else max(0.0, defesa - perfuracao)
    calculo.append(f"Defesa bruta ({defesa_chave}) = {round(defesa, 4)}")
    if ignora_defesa:
        calculo.append("Defesa ignorada = 0")
    elif usar_per_no_dano and usuario.obter_atributo("Per") > 0:
        calculo.append(f"Defesa apos perfuracao = {round(defesa, 4)} - {round(perfuracao, 4)} = {round(defesa_efetiva, 4)}")
    elif not usar_per_no_dano:
        calculo.append("Perfuracao por Per ignorada")
    mult_defesa = 100.0 / (100.0 + defesa_efetiva)
    antes = dano
    dano *= mult_defesa
    calculo.append(f"Defesa: {round(antes, 4)} * {round(mult_defesa, 4)} = {round(dano, 4)}")
    dur_alvo = alvo.obter_atributo("Dur")
    if dur_alvo > 0:
        antes = dano
        mult_dur = max(0.0, 1.0 - (dur_alvo / 100.0))
        dano *= mult_dur
        calculo.append(f"Durabilidade: {round(antes, 4)} * {round(mult_dur, 4)} = {round(dano, 4)}")
    calculo.append(f"Dano final = {round(dano, 4)}")
    detalhes = {
        "dano_bruto": round(_f(dados.get("dano_bruto", dados.get("dano", 0.0)), 0.0), 4),
        "dano_pos_condicional": round(dano_pos_condicional, 4),
        "multiplicador_amp": round(mult_amp, 4),
        "multiplicador_tipo": round(mult_tipo, 4),
        "multiplicador_stab": 1.2 if _normalizar(tipo) in {_normalizar(t) for t in usuario.tipos} else 1.0,
        "multiplicador_critico": round(1.0 + (usuario.obter_atributo("CrD") / 100.0), 4) if critico else 1.0,
        "chance_critico": round(chance_crit, 4),
        "bonus_crd_excedente": round(excedente_crit / 2.0, 4),
        "defesa_base": round(defesa, 4),
        "defesa_aplicada": round(defesa_efetiva, 4),
        "ignora_defesa": ignora_defesa,
        "usar_per_no_dano": usar_per_no_dano,
        "multiplicador_defesa": round(mult_defesa, 4),
        "durabilidade": round(dur_alvo, 4),
        "multiplicador_durabilidade": round(max(0.0, 1.0 - (dur_alvo / 100.0)), 4),
    }
    recebido = alvo.ReceberDano(dano, origem=usuario, dados={**dados, "critico": critico, "tipo": tipo, "detalhes": detalhes, "calculo": calculo})
    dano_vida = _f(recebido.get("dano_vida"), 0.0)
    if dano_vida > 0 and usuario.obter_atributo("Vamp") > 0:
        usuario.ReceberCura(dano_vida * (usuario.obter_atributo("Vamp") / 100.0), origem=usuario, dados={"vampirismo": True})
    usuario.estatisticas_batalha["dano_causado"] = _f(usuario.estatisticas_batalha.get("dano_causado"), 0.0) + dano_vida
    recebido.update({"critico": critico, "dano_calculado": round(dano, 4)})
    usuario._disparar_flag(
        "AoAplicarDano",
        {"partida": usuario.partida, "usuario": usuario, "alvo": alvo, "pokemon_evento": usuario, "resultado": dict(recebido), "dados_dano": dict(dados), **contexto},
        reativos=contexto.get("reativos_acao"),
    )
    return recebido
