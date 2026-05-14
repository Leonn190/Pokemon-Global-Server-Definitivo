from __future__ import annotations

import json
import time
import unicodedata
from pathlib import Path

from Servidor.Gerais.EstadoServidor import garantir_bootstrap_op, obter_nivel_op
from Servidor.Logica.Comandos.ComandosBatalha import MAPA_FUNCOES_COMANDOS_BATALHA
from Servidor.Logica.Comandos.ComandosGeral import MAPA_FUNCOES_COMANDOS_GERAL
from Servidor.Logica.Comandos.ComandosMundo import MAPA_FUNCOES_COMANDOS_MUNDO


_RAIZ_PROJETO = Path(__file__).resolve().parents[3]
_CAMINHO_CATALOGO_COMANDOS = _RAIZ_PROJETO / "Dados" / "Catalogo" / "Comandos.json"
_CAMPOS_CATALOGO = ("nome", "aliases", "contexto", "nivel", "uso", "descricao", "argumentos", "exemplos")

MAPA_FUNCOES_COMANDOS = {
    **MAPA_FUNCOES_COMANDOS_GERAL,
    **MAPA_FUNCOES_COMANDOS_MUNDO,
    **MAPA_FUNCOES_COMANDOS_BATALHA,
}

_FALLBACK_CATALOGO_MINIMO = {
    "help": {"aliases": ["ajuda"], "contexto": "geral", "nivel": 1, "uso": "/help [mundo|batalha|geral|all|comando]"},
    "gamerule": {"aliases": [], "contexto": "geral", "nivel": 1, "uso": "/gamerule list|search|nome [valor|reset]"},
    "kick": {"aliases": [], "contexto": "geral", "nivel": 2, "uso": "/kick jogador"},
    "ban": {"aliases": [], "contexto": "geral", "nivel": 2, "uso": "/ban jogador"},
    "desban": {"aliases": ["unban"], "contexto": "geral", "nivel": 2, "uso": "/desban jogador"},
    "op": {"aliases": [], "contexto": "geral", "nivel": 2, "uso": "/op nivel jogador"},
    "give": {"aliases": [], "contexto": "mundo", "nivel": 1, "uso": "/give [alvo] item quantidade"},
    "tp": {"aliases": [], "contexto": "mundo", "nivel": 1, "uso": "/tp alvo x y | /tp destino"},
    "locate": {"aliases": [], "contexto": "mundo", "nivel": 1, "uso": "/locate nome | /locate dungeon code"},
    "spawn": {"aliases": ["summon"], "contexto": "mundo", "nivel": 1, "uso": "/spawn pokemon [x y]"},
    "chest": {"aliases": ["bau", "baú"], "contexto": "mundo", "nivel": 1, "uso": "/chest tipo [x y]"},
    "count": {"aliases": ["contar"], "contexto": "mundo", "nivel": 1, "uso": "/count chunks|chests|pokemons"},
    "xp": {"aliases": [], "contexto": "mundo", "nivel": 1, "uso": "/xp quantidade [jogador]"},
    "chuva": {"aliases": [], "contexto": "mundo", "nivel": 1, "uso": "/chuva [intensidade]"},
    "win": {"aliases": ["vencer"], "contexto": "batalha", "nivel": 1, "uso": "/win"},
    "lose": {"aliases": ["loose", "perder"], "contexto": "batalha", "nivel": 1, "uso": "/lose"},
    "revert": {"aliases": [], "contexto": "batalha", "nivel": 1, "uso": "/revert"},
    "test": {"aliases": [], "contexto": "batalha", "nivel": 1, "uso": "/test [on|off|status]"},
    "heal": {"aliases": [], "contexto": "batalha", "nivel": 1, "uso": "/heal valor [A1]"},
    "dmg": {"aliases": [], "contexto": "batalha", "nivel": 1, "uso": "/dmg valor [N|E|V] [A1]"},
    "kill": {"aliases": ["matar"], "contexto": "batalha", "nivel": 1, "uso": "/kill A1"},
}


def _normalizar_nome(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return sem_acento.lstrip("/")


def _lista_texto(valor) -> list[str]:
    if isinstance(valor, (list, tuple)):
        return [str(v).strip() for v in valor if str(v).strip()]
    if valor in (None, ""):
        return []
    return [str(valor).strip()]


def _normalizar_aliases(valor) -> list[str]:
    aliases = []
    for alias in _lista_texto(valor):
        alias_norm = _normalizar_nome(alias)
        if alias_norm and alias_norm not in aliases:
            aliases.append(alias_norm)
    return aliases


def _metadados_minimos(nome: str) -> dict:
    base = dict(_FALLBACK_CATALOGO_MINIMO.get(nome, {}))
    return {
        "nome": nome,
        "aliases": list(base.get("aliases") or []),
        "contexto": str(base.get("contexto") or "geral"),
        "nivel": int(base.get("nivel", 1) or 1),
        "uso": str(base.get("uso") or f"/{nome}"),
        "descricao": f"Comando /{nome}.",
        "argumentos": [],
        "exemplos": [str(base.get("uso") or f"/{nome}").split(" | ", 1)[0]],
    }


def _itens_catalogo_json() -> list[dict]:
    try:
        dados = json.loads(_CAMINHO_CATALOGO_COMANDOS.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[Comandos] Falha ao carregar catalogo JSON {_CAMINHO_CATALOGO_COMANDOS}: {exc}")
        return []
    if isinstance(dados, dict):
        itens = dados.get("comandos", [])
    else:
        itens = dados
    if not isinstance(itens, list):
        print(f"[Comandos] Catalogo JSON invalido: campo 'comandos' deve ser lista")
        return []
    return [item for item in itens if isinstance(item, dict)]


def _carregar_metadados_comandos() -> list[dict]:
    itens_json = _itens_catalogo_json()
    catalogo = {}
    for item in itens_json:
        nome = _normalizar_nome(item.get("nome"))
        if not nome or nome not in MAPA_FUNCOES_COMANDOS:
            continue
        fallback = _metadados_minimos(nome)
        cmd = {}
        for campo in _CAMPOS_CATALOGO:
            valor = item.get(campo, fallback.get(campo))
            cmd[campo] = fallback.get(campo) if valor in (None, "") else valor
        cmd["nome"] = nome
        catalogo[nome] = cmd
    if not catalogo:
        catalogo = {nome: _metadados_minimos(nome) for nome in MAPA_FUNCOES_COMANDOS}
    for nome in MAPA_FUNCOES_COMANDOS:
        if nome not in catalogo:
            catalogo[nome] = _metadados_minimos(nome)
    return [catalogo[nome] for nome in catalogo]


def _montar_catalogo():
    catalogo = {}
    aliases = {}
    for item in _carregar_metadados_comandos():
        cmd = dict(item)
        nome = _normalizar_nome(cmd.get("nome"))
        cmd["nome"] = nome
        cmd["aliases"] = _normalizar_aliases(cmd.get("aliases"))
        cmd["nivel"] = int(cmd.get("nivel", 1) or 1)
        cmd["argumentos"] = _lista_texto(cmd.get("argumentos"))
        cmd["exemplos"] = _lista_texto(cmd.get("exemplos"))
        cmd["funcao"] = MAPA_FUNCOES_COMANDOS.get(nome)
        if cmd["funcao"] is None:
            continue
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
