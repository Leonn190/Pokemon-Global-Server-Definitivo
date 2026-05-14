from __future__ import annotations

from Servidor.Gerais.EstadoServidor import (
    banir_usuario,
    definir_nivel_op,
    desbanir_usuario,
    expulsar_usuario,
    listar_regras_servidor,
    obter_nivel_op,
    definir_regra_servidor,
    resetar_regra_servidor,
)
from Servidor.Gerais.LoaderRegras import listar_regras_base_flat


def _resolver_regra(raw: str):
    termo = str(raw or "").strip()
    base = listar_regras_base_flat()
    if termo in base:
        return termo, base[termo]
    termo_norm = termo.lower()
    candidatos = [k for k in base if k.lower() == termo_norm]
    if not candidatos and "." not in termo:
        candidatos = [k for k in base if k.rsplit(".", 1)[-1].lower() == termo_norm]
    if len(candidatos) == 1:
        chave = candidatos[0]
        return chave, base[chave]
    if len(candidatos) > 1:
        return None, f"Regra ambígua: {termo}. Opções: {', '.join(candidatos[:8])}"
    return None, f"Regra não encontrada: {termo}"


def _converter_valor(raw: str, base):
    texto = str(raw or "").strip()
    if isinstance(base, bool):
        mapa = {"true": True, "on": True, "sim": True, "yes": True, "1": True, "false": False, "off": False, "nao": False, "não": False, "no": False, "0": False}
        chave = texto.lower()
        if chave not in mapa:
            raise ValueError("valor booleano inválido")
        return mapa[chave]
    if isinstance(base, int) and not isinstance(base, bool):
        return int(float(texto))
    if isinstance(base, float):
        return float(texto.replace(",", "."))
    if isinstance(base, str):
        return texto
    raise ValueError("tipo de regra não suportado por /gamerule")


def comando_help(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (autor, meta)
    contexto = str(contexto or "mundo").lower()
    catalogo = dict(catalogo or {})
    args = list(args or [])
    aliases = {}
    for nome, cmd in catalogo.items():
        aliases[nome] = nome
        for alias in list(cmd.get("aliases") or []):
            aliases[str(alias).lower()] = nome

    def visiveis(ctx):
        if ctx == "all":
            return sorted({v for v in aliases.values()})
        permitidos = {"geral", ctx}
        return sorted(nome for nome, cmd in catalogo.items() if str(cmd.get("contexto")) in permitidos)

    if not args:
        nomes = visiveis(contexto)
        return "Comandos: " + ", ".join(f"/{n}" for n in nomes)
    alvo = str(args[0] or "").strip().lower().lstrip("/")
    if alvo in {"mundo", "batalha", "geral", "all"}:
        nomes = visiveis(alvo)
        return f"Comandos ({alvo}): " + ", ".join(f"/{n}" for n in nomes)
    nome = aliases.get(alvo)
    if not nome or nome not in catalogo:
        return f"Comando não encontrado: /{alvo}"
    cmd = catalogo[nome]
    partes = [
        f"/{cmd.get('nome', nome)}",
        f"uso: {cmd.get('uso')}",
        f"ctx: {cmd.get('contexto')} | nível: {cmd.get('nivel')}",
        str(cmd.get("descricao") or ""),
    ]
    argumentos = [str(x) for x in list(cmd.get("argumentos") or []) if str(x).strip()]
    exemplos = [str(x) for x in list(cmd.get("exemplos") or []) if str(x).strip()]
    if argumentos:
        partes.append("args: " + "; ".join(argumentos))
    if exemplos:
        partes.append("ex: " + "; ".join(exemplos[:3]))
    return " | ".join(p for p in partes if p)


def comando_op(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (contexto, meta, catalogo)
    args = list(args or [])
    if len(args) < 2:
        return "Erro no /op. Uso: /op nivel jogador"
    try:
        nivel = int(args[0])
    except ValueError:
        return "Erro no /op. Nível deve ser 0, 1 ou 2"
    if nivel not in {0, 1, 2}:
        return "Erro no /op. Nível deve ser 0, 1 ou 2"
    alvo = " ".join(args[1:]).strip()
    if not definir_nivel_op(alvo, nivel):
        return "Erro no /op. Não é permitido remover/rebaixar o último nível 2"
    return f"Permissão de {alvo} definida para nível {nivel} por {autor}"


def comando_kick(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (autor, contexto, meta, catalogo)
    alvo = " ".join(list(args or [])).strip()
    if not alvo:
        return "Erro no /kick. Uso: /kick jogador"
    ok = expulsar_usuario(alvo)
    return f"{alvo} expulso do servidor" if ok else f"Não foi possível expulsar {alvo}"


def comando_ban(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (autor, contexto, meta, catalogo)
    alvo = " ".join(list(args or [])).strip()
    if not alvo:
        return "Erro no /ban. Uso: /ban jogador"
    banir_usuario(alvo)
    return f"{alvo} banido e desconectado"


def comando_desban(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (autor, contexto, meta, catalogo)
    alvo = " ".join(list(args or [])).strip()
    if not alvo:
        return "Erro no /desban. Uso: /desban jogador"
    mudou = desbanir_usuario(alvo)
    return f"{alvo} desbanido" if mudou else f"{alvo} não estava banido"


def comando_gamerule(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (autor, contexto, meta, catalogo)
    args = list(args or [])
    base = listar_regras_base_flat()
    overrides = listar_regras_servidor()
    if not args:
        return "Uso: /gamerule list | search termo | nome [valor|reset]"
    acao = str(args[0]).strip().lower()
    if acao == "list":
        nomes = sorted(base.keys())
        return f"Regras ({len(nomes)}): " + ", ".join(nomes[:40]) + (" ..." if len(nomes) > 40 else "")
    if acao == "search":
        termo = " ".join(args[1:]).strip().lower()
        achados = [k for k in sorted(base.keys()) if termo in k.lower()]
        return f"Regras encontradas ({len(achados)}): " + ", ".join(achados[:40]) + (" ..." if len(achados) > 40 else "")
    chave, valor_base = _resolver_regra(args[0])
    if chave is None:
        return str(valor_base)
    atual = overrides.get(chave, valor_base)
    if len(args) == 1:
        status = "sobrescrita" if chave in overrides else "base"
        return f"{chave}: atual={atual!r} | base={valor_base!r} | {status}"
    novo_raw = " ".join(args[1:]).strip()
    if novo_raw.lower() == "reset":
        resetar_regra_servidor(chave)
        return f"{chave} resetada para {valor_base!r}"
    try:
        novo = _converter_valor(novo_raw, valor_base)
    except ValueError as exc:
        return f"Erro no /gamerule. {exc}"
    definir_regra_servidor(chave, novo)
    return f"{chave}: {atual!r} -> {novo!r}"


CATALOGO_COMANDOS_GERAL = [
    {"nome": "help", "aliases": ["ajuda"], "funcao": comando_help, "contexto": "geral", "nivel": 1, "uso": "/help [mundo|batalha|geral|all|comando]", "descricao": "Mostra comandos ou detalhes de um comando.", "argumentos": ["filtro opcional"], "exemplos": ["/help", "/help batalha", "/help give"]},
    {"nome": "gamerule", "aliases": [], "funcao": comando_gamerule, "contexto": "geral", "nivel": 1, "uso": "/gamerule list|search|nome [valor|reset]", "descricao": "Consulta ou altera regras sobrescritas do servidor ativo.", "argumentos": ["nome: regra namespaced ou única", "valor: bool/int/float/str"], "exemplos": ["/gamerule", "/gamerule player.StaminaMax 120", "/gamerule player.StaminaMax reset"]},
    {"nome": "kick", "aliases": [], "funcao": comando_kick, "contexto": "geral", "nivel": 2, "uso": "/kick jogador", "descricao": "Desconecta jogador sem banir.", "argumentos": ["jogador"], "exemplos": ["/kick Leon19"]},
    {"nome": "ban", "aliases": [], "funcao": comando_ban, "contexto": "geral", "nivel": 2, "uso": "/ban jogador", "descricao": "Bane e desconecta jogador.", "argumentos": ["jogador"], "exemplos": ["/ban Leon19"]},
    {"nome": "desban", "aliases": ["unban"], "funcao": comando_desban, "contexto": "geral", "nivel": 2, "uso": "/desban jogador", "descricao": "Remove jogador da lista de banidos.", "argumentos": ["jogador"], "exemplos": ["/desban Leon19"]},
    {"nome": "op", "aliases": [], "funcao": comando_op, "contexto": "geral", "nivel": 2, "uso": "/op nivel jogador", "descricao": "Define nível de permissão 0, 1 ou 2.", "argumentos": ["nível: 0..2", "jogador"], "exemplos": ["/op 2 Leon19", "/op 1 Jogador"]},
]
