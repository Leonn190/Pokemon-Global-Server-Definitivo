from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path


RAIZ_REPOSITORIO = Path(__file__).resolve().parents[3]
PASTA_SERVER_LIST = RAIZ_REPOSITORIO / "ServerList"
ARQUIVO_ESTADO_SERVIDOR = "EstadoServidor.json"
PASTA_ESTADO_MUNDO = "EstadoMundo"


def garantir_pasta_raiz() -> Path:
    PASTA_SERVER_LIST.mkdir(parents=True, exist_ok=True)
    return PASTA_SERVER_LIST


def _agora_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _nome_pasta_seguro(nome: str) -> str:
    limpo = "".join("_" if c in '<>:"/\\|?*' else c for c in str(nome or "").strip())
    return limpo.strip(" .") or "Servidor"


def _pasta_disponivel(nome: str, tipo: str) -> Path:
    raiz = garantir_pasta_raiz()
    sufixo = "(LOCAL)" if tipo == "local" else "(ONLINE)"
    base = _nome_pasta_seguro(f"{nome} {sufixo}")
    pasta = raiz / base
    contador = 2
    while pasta.exists():
        pasta = raiz / f"{base} {contador}"
        contador += 1
    return pasta


def _arquivo_estado(pasta_server: Path) -> Path:
    return Path(pasta_server) / ARQUIVO_ESTADO_SERVIDOR


def carregar_estado_servidor(pasta_server) -> dict:
    arquivo = _arquivo_estado(Path(pasta_server))
    if not arquivo.exists():
        return {}
    try:
        with arquivo.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def salvar_estado_servidor(pasta_server, estado: dict) -> dict:
    pasta = Path(pasta_server)
    pasta.mkdir(parents=True, exist_ok=True)
    dados = dict(estado or {})
    dados["atualizado_em"] = _agora_iso()
    with _arquivo_estado(pasta).open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return dados


def listar_servidores() -> list[dict]:
    raiz = garantir_pasta_raiz()
    servidores = []
    for pasta in sorted((p for p in raiz.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
        estado = carregar_estado_servidor(pasta)
        if not estado:
            continue
        estado = dict(estado)
        estado.setdefault("id", pasta.name)
        estado.setdefault("nome", pasta.name)
        estado.setdefault("tipo", "local" if (pasta / PASTA_ESTADO_MUNDO).exists() else "online")
        if estado.get("tipo") == "online":
            estado["ligado"] = False
            estado["mundo_existente"] = False
        estado["pasta"] = str(pasta)
        estado["server_id"] = estado["id"]
        servidores.append(estado)
    return servidores


def obter_servidor_por_id(server_id: str) -> dict | None:
    alvo = str(server_id or "")
    for server in listar_servidores():
        if str(server.get("id")) == alvo:
            return server
    return None


def criar_servidor_local(nome: str, chave_acesso: str) -> dict:
    nome = str(nome or "").strip()
    chave_acesso = str(chave_acesso or "").strip()
    if not nome or not chave_acesso:
        raise ValueError("Nome e chave de acesso são obrigatórios")
    pasta = _pasta_disponivel(nome, "local")
    (pasta / PASTA_ESTADO_MUNDO).mkdir(parents=True, exist_ok=True)
    agora = _agora_iso()
    estado = {
        "id": uuid.uuid4().hex,
        "tipo": "local",
        "nome": nome,
        "chave_acesso": chave_acesso,
        "ligado": False,
        "mundo_existente": False,
        "banidos": [],
        "criado_em": agora,
        "atualizado_em": agora,
    }
    salvar_estado_servidor(pasta, estado)
    estado["pasta"] = str(pasta)
    estado["server_id"] = estado["id"]
    return estado


def criar_servidor_online(nome: str, ip: str) -> dict:
    nome = str(nome or "").strip()
    ip = str(ip or "").strip()
    if not nome or not ip:
        raise ValueError("Nome e IP são obrigatórios")
    pasta = _pasta_disponivel(nome, "online")
    pasta.mkdir(parents=True, exist_ok=True)
    agora = _agora_iso()
    estado = {
        "id": uuid.uuid4().hex,
        "tipo": "online",
        "nome": nome,
        "ip": ip,
        "ligado": False,
        "mundo_existente": False,
        "criado_em": agora,
        "atualizado_em": agora,
    }
    salvar_estado_servidor(pasta, estado)
    estado["pasta"] = str(pasta)
    estado["server_id"] = estado["id"]
    return estado


def apagar_servidor(server_id: str) -> bool:
    server = obter_servidor_por_id(server_id)
    if not server:
        return False
    pasta = Path(server["pasta"])
    if pasta.exists() and pasta.parent == garantir_pasta_raiz():
        shutil.rmtree(pasta)
    return True


def renomear_servidor(server_id: str, novo_nome: str) -> dict | None:
    server = obter_servidor_por_id(server_id)
    novo_nome = str(novo_nome or "").strip()
    if not server or not novo_nome:
        return None
    pasta_atual = Path(server["pasta"])
    tipo = str(server.get("tipo") or "local")
    nova_pasta = _pasta_disponivel(novo_nome, tipo)
    pasta_atual.rename(nova_pasta)
    estado = carregar_estado_servidor(nova_pasta)
    estado["nome"] = novo_nome
    if tipo == "online":
        estado["ligado"] = False
        estado["mundo_existente"] = False
    estado = salvar_estado_servidor(nova_pasta, estado)
    estado["pasta"] = str(nova_pasta)
    estado["server_id"] = estado["id"]
    return estado


garantir_pasta_raiz()
