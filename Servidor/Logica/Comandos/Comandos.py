from __future__ import annotations

import time
import unicodedata

from Servidor.Gerais.EstadoServidor import garantir_bootstrap_op, obter_nivel_op
from Servidor.Logica.Comandos.ComandosBatalha import CATALOGO_COMANDOS_BATALHA
from Servidor.Logica.Comandos.ComandosGeral import CATALOGO_COMANDOS_GERAL
from Servidor.Logica.Comandos.ComandosMundo import CATALOGO_COMANDOS_MUNDO


def _normalizar_nome(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return sem_acento.lstrip("/")


def _montar_catalogo():
    catalogo = {}
    aliases = {}
    for item in [*CATALOGO_COMANDOS_GERAL, *CATALOGO_COMANDOS_MUNDO, *CATALOGO_COMANDOS_BATALHA]:
        cmd = dict(item)
        nome = _normalizar_nome(cmd.get("nome"))
        cmd["nome"] = nome
        cmd["aliases"] = [_normalizar_nome(a) for a in list(cmd.get("aliases") or []) if _normalizar_nome(a)]
        cmd["nivel"] = int(cmd.get("nivel", 1) or 1)
        catalogo[nome] = cmd
    for nome, cmd in catalogo.items():
        aliases[nome] = nome
        for alias in list(cmd.get("aliases") or []):
            aliases[alias] = nome
    return catalogo, aliases


CATALOGO_COMANDOS, ALIASES_COMANDOS = _montar_catalogo()


def catalogo_comandos() -> dict:
    return {nome: dict(cmd) for nome, cmd in CATALOGO_COMANDOS.items()}


def parsear_comando(texto: str) -> tuple[str, list[str]]:
    bruto = str(texto or "").strip()
    if not bruto.startswith("/"):
        return "", []
    partes = bruto[1:].split()
    if not partes:
        return "", []
    nome = _normalizar_nome(partes[0])
    return nome, partes[1:]


def comando_existe(nome: str) -> bool:
    return _normalizar_nome(nome) in ALIASES_COMANDOS


def _erro(feedback: str, extras=None):
    ret = {"ok": False, "feedback": str(feedback or ""), "autor": "Servidor", "timestamp": time.time()}
    if isinstance(extras, dict):
        ret.update(extras)
    return ret


def _ok(feedback: str, extras=None):
    ret = {"ok": True, "feedback": str(feedback or "Comando processado").strip()[:1200], "autor": "Servidor", "timestamp": time.time()}
    if isinstance(extras, dict):
        ret.update(extras)
    return ret


def _validar_contexto(cmd: dict, contexto: str) -> str:
    ctx_cmd = str(cmd.get("contexto") or "geral").strip().lower()
    ctx = str(contexto or "mundo").strip().lower()
    if ctx_cmd == "geral" or ctx_cmd == ctx:
        return ""
    return f"Comando /{cmd.get('nome')} não disponível no contexto {ctx}"


def _validar_permissao(autor: str, cmd: dict) -> str:
    nivel_req = int(cmd.get("nivel", 1) or 1)
    if nivel_req >= 2:
        try:
            garantir_bootstrap_op(autor)
        except Exception:
            pass
    try:
        nivel = obter_nivel_op(autor)
    except Exception:
        nivel = 1
    if nivel <= 0:
        return "Você não tem permissão para usar comandos"
    if nivel < nivel_req:
        return f"Permissão insuficiente para /{cmd.get('nome')}: nível {nivel_req} necessário"
    return ""


def executar_comando_terminal(autor: str, texto: str, contexto: str = "mundo", meta: dict | None = None) -> dict:
    bruto = str(texto or "").strip()
    if not bruto.startswith("/"):
        return _erro("")
    nome_raw, args = parsear_comando(bruto)
    if not nome_raw:
        return _ok("Comando inexistente: /")
    nome = ALIASES_COMANDOS.get(nome_raw)
    if not nome:
        return _erro(f"Comando inexistente: /{nome_raw}", {"comando_inexistente": True})
    cmd = CATALOGO_COMANDOS[nome]
    erro_ctx = _validar_contexto(cmd, contexto)
    if erro_ctx:
        return _erro(erro_ctx, {"contexto_invalido": True})
    erro_perm = _validar_permissao(str(autor or "anon"), cmd)
    if erro_perm:
        return _erro(erro_perm, {"permissao_negada": True})
    try:
        retorno = cmd["funcao"](str(autor or "anon"), args, contexto=contexto, meta=dict(meta or {}), catalogo=CATALOGO_COMANDOS)
    except Exception as exc:
        return _erro(f"Erro no /{nome}. Uso: {cmd.get('uso')}. Detalhe: {exc}")
    if isinstance(retorno, dict):
        feedback = str(retorno.get("feedback") or "Comando processado")
        extras = {k: v for k, v in retorno.items() if k != "feedback"}
        return _ok(feedback, extras)
    return _ok(str(retorno))
