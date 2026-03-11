"""Controlador de objetos remotos do mundo (pokémons, baús, projéteis, atores remotos)."""

from __future__ import annotations

from typing import Dict

from Codigo.Modulos.ControladorObjetos import ControladorObjetos as _ControladorObjetosBase


class ControladorObjetos(_ControladorObjetosBase):
    """Fachada para manter foco em objetos de mundo e aplicação de diffs."""

    def aplicar_pacote_tick(self, pacote_tick: Dict[str, object]) -> None:
        diffs = pacote_tick.get("diffs", []) if isinstance(pacote_tick, dict) else []
        if not isinstance(diffs, list):
            return
        for diff in diffs:
            if isinstance(diff, dict):
                self.aplicar_diff(diff)
