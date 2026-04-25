from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.PassivaAtaques import processar_passivas_ataque


def obter_execute_principal(nome):
    return _EXECUTES.get(str(nome or "").casefold())


def executar_execute_principal(nome, contexto, alvo=None):
    fn = obter_execute_principal(nome)
    if not callable(fn):
        return {"ok": False, "motivo": "execute_inexistente"}
    return fn(dict(contexto or {}), alvo)


def executar_alvificacao(nome, contexto):
    fn = _ALVIFICACOES.get(str(nome or "").casefold())
    if not callable(fn):
        return {}
    return fn(dict(contexto or {}))


def obter_executes_perifericos(*_args, **_kwargs):
    return []


def _dano(usuario, alvo, bruto, tipo="normal", categoria="normal", extra=None):
    dados = {"dano_bruto": bruto, "tipo": tipo, "categoria": categoria}
    if extra:
        dados.update(extra)
    return usuario.AplicarDano(alvo, dados, contexto={})


def _investida(ctx, alvo):
    u = ctx["usuario"]
    r = _dano(u, alvo, u.atributos_finais.get("Atk", 0) * 1.2, tipo="normal", categoria="normal")
    dano_vida = float(r.get("dano_vida", 0.0))
    if dano_vida > 0:
        u.ReceberDano(dano_vida * 0.2, origem=u, dados={"motivo": "recuo"})
    return r


def _biscoito(ctx, alvo):
    u = ctx["usuario"]
    stacks = int(alvo.contadores_especiais.get("biscoito", 0))
    crit = bool(ctx.get("critico_ativo", False))
    mult = 0.15 if crit else 0.10
    cura = u.atributos_finais.get("Mag", 0.0) * (0.55 + stacks * mult)
    ret = u.AplicarCura(alvo, cura, dados={"origem": "biscoito"})
    alvo.contadores_especiais["biscoito"] = stacks + 1
    if alvo.id_batalha != u.id_batalha:
        u.contadores_especiais["biscoito"] = int(u.contadores_especiais.get("biscoito", 0)) + 1
    return ret


def _enraivecer(ctx, _alvo):
    u = ctx["usuario"]
    if u.VidaAtual / max(1.0, u.atributos_finais.get("Vida", 1.0)) < 0.40:
        return u.AplicarEfeito(u, {"code": 26, "nome": "Amplificado", "duracao": 3, "categoria": "positivo"})
    return {"sem_efeito": True}


def _provocar(ctx, _alvo):
    u = ctx["usuario"]
    return u.AplicarEfeito(u, {"code": 28, "nome": "Provocando", "duracao": 2, "categoria": "positivo"})


def _proteger(ctx, alvo):
    alvo.adicionar_estado_transitorio("protegido", {"rodada": ctx["partida"].rodada_atual})
    return {"protegido": True}


def _arranhar(ctx, alvo):
    return _dano(ctx["usuario"], alvo, ctx["usuario"].atributos_finais.get("Atk", 0) * 1.35)


def _recarga(ctx, _alvo):
    u = ctx["usuario"]
    custo = float(ctx.get("acao", {}).get("custo_real", 0.0))
    u.GanharEnergia(custo * 2.0)
    return {"energia_ganha": custo * 2.0}


def _energia(ctx, alvo):
    return _dano(ctx["usuario"], alvo, ctx["usuario"].atributos_finais.get("SpA", 0) * 1.15, categoria="especial")


def _hiper_raio(ctx, alvo):
    qtd = int(ctx.get("alvos_atingidos", 1))
    spa = ctx["usuario"].atributos_finais.get("SpA", 0)
    bruto = max(0.0, spa * 1.50 - ((qtd - 1) * spa * 0.15))
    return _dano(ctx["usuario"], alvo, bruto, categoria="especial")


def _guilhotina(ctx, alvo):
    r = _dano(ctx["usuario"], alvo, ctx["usuario"].atributos_finais.get("Atk", 0) * 0.80)
    if r.get("critico") and alvo.lado_id != ctx["usuario"].lado_id and alvo.VidaAtual < alvo.atributos_finais.get("Vida", 1.0) * 0.25:
        alvo.Morrer()
        r["execucao_critica"] = True
    return r


def _disparo(ctx, alvo):
    return _dano(ctx["usuario"], alvo, ctx["usuario"].atributos_finais.get("Atk", 0) * 1.00)


def _chifrada(ctx, alvo):
    u = ctx["usuario"]
    return _dano(u, alvo, u.atributos_finais.get("Atk", 0) * 0.90 + u.atributos_finais.get("Per", 0) * 0.40)


def _resetar(ctx, alvo):
    alvo.variacoes_permanentes = {k: 0.0 for k in alvo.variacoes_permanentes}
    alvo.Verificar()
    return {"resetado": True}


def _tankar(ctx, _alvo):
    u = ctx["usuario"]
    u.AplicarEfeito(u, {"code": 27, "nome": "Fortificado", "duracao": 3, "categoria": "positivo"})
    bonus = u.atributos_finais.get("Mag", 0) * 0.2
    if u.atributos_finais.get("Def", 0) <= u.atributos_finais.get("SpD", 0):
        u.variacoes_temporarias["Def"] += bonus
    else:
        u.variacoes_temporarias["SpD"] += bonus
    if bool(ctx.get("critico_ativo", False)):
        u.ReceberBarreira(u.atributos_finais.get("Mag", 0) * 0.2)
    return {"tankar": True}


def _estocada(ctx, alvo):
    bruto = ctx["usuario"].atributos_finais.get("Atk", 0) * 1.05
    if bool(ctx.get("primeiro_ataque_rodada", False)):
        bruto *= 1.25
    return _dano(ctx["usuario"], alvo, bruto)


def _bola_climatica(ctx, alvo):
    p = ctx["partida"]
    spa = ctx["usuario"].atributos_finais.get("SpA", 0)
    bruto = spa * (1.30 if p.clima_atual is not None else 1.05)
    r = _dano(ctx["usuario"], alvo, bruto, categoria="especial")
    splash = float(r.get("dano_vida", 0.0)) * 0.5
    if splash > 0:
        for adj in p.obter_adjacentes_mesmo_lado(alvo.area_id):
            poke = p.pokemon_na_area(adj)
            if poke and poke.lado_id != ctx["usuario"].lado_id and poke.id_batalha != alvo.id_batalha:
                poke.ReceberDano(splash, origem=ctx["usuario"], dados={"tipo": "splash"})
    return r


def _hiper_presa(ctx, alvo):
    r = _dano(ctx["usuario"], alvo, ctx["usuario"].atributos_finais.get("Atk", 0) * 1.40, extra={"chance_crit": min(80.0, ctx["usuario"].atributos_finais.get("CrC", 0.0))})
    if r.get("critico"):
        alvo.adicionar_estado_transitorio("recuado", {"rodada": ctx["partida"].rodada_atual})
    return r


def _acumulador(_ctx, _alvo):
    return {"passivo": True}


def _alv_linha(ctx):
    partida = ctx["partida"]
    area = str((ctx.get("acao", {}).get("alvo") or {}).get("area_id") or "")
    return {"areas": partida.obter_linha_area(area)}


_EXECUTES = {
    "investida": _investida,
    "biscoito": _biscoito,
    "enraivecer": _enraivecer,
    "provocar": _provocar,
    "proteger": _proteger,
    "arranhar": _arranhar,
    "recarga": _recarga,
    "energia": _energia,
    "hiper raio": _hiper_raio,
    "guilhotina": _guilhotina,
    "disparo": _disparo,
    "chifrada": _chifrada,
    "resetar": _resetar,
    "tankar": _tankar,
    "estocada": _estocada,
    "bola climática": _bola_climatica,
    "bola climatica": _bola_climatica,
    "hiper presa": _hiper_presa,
    "acumulador": _acumulador,
}

_ALVIFICACOES = {"hiper raio": _alv_linha}


def processar_passivas_no_alvo(contexto):
    eventos = processar_passivas_ataque(contexto, "AoSerAtacado")
    return eventos
