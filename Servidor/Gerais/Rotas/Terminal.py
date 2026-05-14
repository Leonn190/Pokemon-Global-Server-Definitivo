from __future__ import annotations

import json
import threading
import time

from Servidor.Logica.Comandos.Comandos import executar_comando_terminal

_TERMINAL_LOCK = threading.Lock()
_TERMINAL_ID = 0
_TERMINAL_MENSAGENS = []
_TERMINAL_MAX = 200


def _proximo_id():
    global _TERMINAL_ID
    _TERMINAL_ID += 1
    return _TERMINAL_ID


def _ok(mensagem, **extras):
    payload = {"status": "ok", "mensagem": mensagem}
    payload.update(extras)
    return json.dumps(payload, ensure_ascii=False)


def _erro(mensagem):
    return json.dumps({"status": "erro", "mensagem": mensagem}, ensure_ascii=False)


def processar_terminal_json(requisicao_json: str) -> str:
    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return _erro("JSON inválido")

    acao = str(pacote.get("acao", "")).strip().lower()
    dados = pacote.get("dados", {}) if isinstance(pacote.get("dados", {}), dict) else {}
    contexto = str(dados.get("contexto") or "mundo").strip().lower()
    meta = dados.get("meta") if isinstance(dados.get("meta"), dict) else {}

    if acao == "terminal_enviar":
        autor = str(dados.get("autor", "anon")).strip() or "anon"
        texto = str(dados.get("texto", "")).strip()
        if not texto:
            return _erro("texto obrigatório")
        texto = texto[:220]
        if texto.startswith("/"):
            cmd = {"ok": False, "feedback": "Comandos de batalha desativados"} if contexto == "batalha" else executar_comando_terminal(autor, texto)
            if cmd.get("ok"):
                with _TERMINAL_LOCK:
                    msg = {
                        "id": _proximo_id(),
                        "autor": str(cmd.get("autor", "Servidor"))[:32],
                        "texto": str(cmd.get("feedback", "Comando processado"))[:220],
                        "timestamp": float(cmd.get("timestamp", time.time())),
                        "contexto": contexto,
                        "batalha_id": str(meta.get("batalha_id") or "") if contexto == "batalha" else "",
                    }
                extras = {"contexto": contexto, "meta": dict(meta)}
                if isinstance(cmd.get("batalha_atualizacao"), dict):
                    extras["batalha_atualizacao"] = dict(cmd.get("batalha_atualizacao"))
                return _ok("Comando processado", mensagem_terminal=msg, **extras)
        with _TERMINAL_LOCK:
            msg = {"id": _proximo_id(), "autor": autor[:32], "texto": texto, "timestamp": time.time(), "contexto": contexto, "batalha_id": str(meta.get("batalha_id") or "") if contexto == "batalha" else ""}
            _TERMINAL_MENSAGENS.append(msg)
            if len(_TERMINAL_MENSAGENS) > _TERMINAL_MAX:
                del _TERMINAL_MENSAGENS[:-_TERMINAL_MAX]
        return _ok("Mensagem enviada", mensagem_terminal=msg)

    if acao == "terminal_buscar":
        ultimo_id = int(dados.get("ultimo_id", 0))
        limite = max(1, min(64, int(dados.get("limite", 16))))
        with _TERMINAL_LOCK:
            if contexto == "batalha":
                batalha_id = str(meta.get("batalha_id") or "").strip()
                mensagens_contexto = [
                    m for m in _TERMINAL_MENSAGENS
                    if str(m.get("contexto") or "mundo") == "batalha" and str(m.get("batalha_id") or "").strip() == batalha_id
                ]
            else:
                mensagens_contexto = [m for m in _TERMINAL_MENSAGENS if str(m.get("contexto") or "mundo") == contexto]
            mensagens = [m for m in mensagens_contexto if int(m["id"]) > ultimo_id][-limite:]
            ultimo = int(mensagens_contexto[-1]["id"]) if mensagens_contexto else ultimo_id
        return _ok("Mensagens carregadas", mensagens=mensagens, ultimo_id=ultimo, contexto=contexto, meta=dict(meta))

    return _erro("Ação terminal não suportada")
