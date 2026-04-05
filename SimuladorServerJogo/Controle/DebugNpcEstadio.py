from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Dict

_LOCK = threading.Lock()
_EVENTOS: list[Dict[str, object]] = []
_MAX_EVENTOS = 6000
_FLUSH_CADA = 25
_CONTADOR_DESDE_FLUSH = 0


def _debug_ativo() -> bool:
    valor = str(os.getenv("DEBUG_NPC_ESTADIO", "1")).strip().lower()
    return valor not in {"0", "false", "off", "nao", "não"}


def _arquivo_saida() -> Path:
    alvo = os.getenv("DEBUG_NPC_ESTADIO_ARQUIVO", "Dados/debug_npc_estadio_trace.json")
    return Path(alvo)


def _serializar_eventos() -> Dict[str, object]:
    return {
        "meta": {
            "total_eventos": len(_EVENTOS),
            "max_eventos": _MAX_EVENTOS,
            "gerado_em_ts": time.time(),
        },
        "eventos": list(_EVENTOS),
    }


def _flush_locked() -> None:
    path = _arquivo_saida()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(_serializar_eventos(), f, ensure_ascii=False, indent=2)


def registrar_evento_npc_estadio(etapa: str, **dados: object) -> None:
    if not _debug_ativo():
        return
    global _CONTADOR_DESDE_FLUSH
    evento = {
        "ts": time.time(),
        "etapa": str(etapa or "desconhecida"),
        "dados": dict(dados or {}),
    }
    with _LOCK:
        _EVENTOS.append(evento)
        if len(_EVENTOS) > _MAX_EVENTOS:
            excesso = len(_EVENTOS) - _MAX_EVENTOS
            del _EVENTOS[0:excesso]
        _CONTADOR_DESDE_FLUSH += 1
        if _CONTADOR_DESDE_FLUSH >= _FLUSH_CADA:
            _flush_locked()
            _CONTADOR_DESDE_FLUSH = 0


def flush_debug_npc_estadio() -> None:
    if not _debug_ativo():
        return
    global _CONTADOR_DESDE_FLUSH
    with _LOCK:
        _flush_locked()
        _CONTADOR_DESDE_FLUSH = 0
