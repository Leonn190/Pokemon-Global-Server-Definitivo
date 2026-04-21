from __future__ import annotations

DEBUG_COMBATE = True


def dbg_combate(origem: str, mensagem: str, **dados) -> None:
    if not DEBUG_COMBATE:
        return
    print(f"[DBG-COMBATE][{origem}] {mensagem} | {dados}")
