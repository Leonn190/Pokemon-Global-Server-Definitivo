from __future__ import annotations

import json
from pathlib import Path
import unicodedata


def _normalizar(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _code_norm(valor):
    texto = str(valor or "").strip()
    if not texto:
        return ""
    try:
        return str(int(float(texto)))
    except (TypeError, ValueError):
        return texto


def carregar_propriedades_ataques(base_dir: Path | None = None):
    raiz = Path(base_dir or Path(__file__).resolve().parents[2])
    pasta = raiz / "Dados" / "PropriedadesAtaques"
    ataques = {}
    if pasta.exists() and any(pasta.glob("*.json")):
        for arquivo in sorted(pasta.glob("*.json")):
            try:
                dados = json.loads(arquivo.read_text(encoding="utf-8"))
            except Exception:
                continue
            bloco = dados.get("ataques") if isinstance(dados, dict) else {}
            if not isinstance(bloco, dict):
                continue
            for code, props in bloco.items():
                if not isinstance(props, dict):
                    continue
                chave = _code_norm(props.get("ID") or code)
                if chave:
                    chave_mapa = chave
                    if chave_mapa in ataques:
                        nome_norm = _normalizar(props.get("nome"))
                        chave_mapa = f"{chave}:{nome_norm}" if nome_norm else f"{chave}:{len(ataques)}"
                    ataques[chave_mapa] = dict(props)
    return ataques


def buscar_por_nome_ou_code(mapa, ataque):
    if not isinstance(ataque, dict):
        return None
    code = _code_norm(ataque.get("Code") or ataque.get("ID") or ataque.get("code"))
    if code and code in mapa:
        return mapa.get(code)
    nome = _normalizar(ataque.get("nome") or ataque.get("Nome") or ataque.get("Ataque"))
    if nome:
        for item in mapa.values():
            if _normalizar((item or {}).get("nome")) == nome:
                return item
    return None
