"""Setoriza regras dimensionais do client (camera + limites de player)."""

from __future__ import annotations


class ControladorDimensoes:
    def aplicar(self, leitor_mundo, player_local) -> None:
        """Sincroniza limites do mundo e garante bloqueio nas bordas quando não toroidal."""
        controle = getattr(player_local, "Controle", None) if player_local is not None else None
        leitor_mundo.atualizar_regras_mundo(controle)
        if player_local is None or controle is None:
            return

        limites = getattr(controle, "LimitesMundoTiles", None)
        toroidal = bool(getattr(controle, "LimitesToroidais", True))
        if not limites or toroidal:
            return

        largura, altura = float(limites[0]), float(limites[1])
        px, py = tuple(getattr(player_local, "Posicao", (0.0, 0.0)))
        margem = 1e-4
        px = max(0.0, min(max(0.0, largura - margem), float(px)))
        py = max(0.0, min(max(0.0, altura - margem), float(py)))
        player_local.definir_posicao(px, py)
