from __future__ import annotations

import unicodedata


def normalizar(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def fnum(valor: object, default: float = 0.0) -> float:
    try:
        if isinstance(valor, str):
            return float(valor.replace(",", "."))
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def critico_simples(usuario, ctx, maximo=None):
    chance = float(usuario.obter_atributo("CrC", 0.0))
    if maximo is not None:
        chance = min(chance, float(maximo))
    rng = (ctx or {}).get("rng")
    return bool(chance > 0 and rng is not None and rng.random() * 100.0 <= chance)


def dano_generico(ctx, alvo, bruto, categoria="normal", **extra):
    usuario = (ctx or {}).get("usuario")
    if usuario is None or alvo is None:
        return {"falha": True, "motivo": "alvo_invalido"}
    ataque = (ctx or {}).get("ataque") if isinstance((ctx or {}).get("ataque"), dict) else {}
    props = (ctx or {}).get("propriedades") if isinstance((ctx or {}).get("propriedades"), dict) else {}
    parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
    dados = {
        "dano_bruto": max(0.0, float(bruto or 0.0)),
        "tipo": parametros.get("tipo") or props.get("tipo") or "normal",
        "categoria": categoria,
        "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
        "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome"),
        "reativos_acao": (ctx or {}).get("reativos_acao"),
        **extra,
    }
    return usuario.AplicarDano(alvo, dados, contexto=ctx)


def aplicar_efeito(usuario, alvo, nome, duracao=3, dados=None, valor=0.0, negativo=None):
    efeito = {"nome": nome, "duracao": duracao, "valor": valor}
    if negativo is not None:
        efeito["negativo"] = bool(negativo)
    return usuario.AplicarEfeito(alvo, efeito, dados=dados or {})
