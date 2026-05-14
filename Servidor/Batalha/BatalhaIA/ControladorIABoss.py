from __future__ import annotations

from .ControladorIA import ControladorIA


class ControladorIABoss(ControladorIA):
    """Extensao pequena da IA comum para batalhas de boss."""

    def finalizar_jogada_com_hacker(self, partida, lado_id, jogada_base, config_ia=None):
        jogada = super().finalizar_jogada_com_hacker(partida, lado_id, jogada_base, config_ia=config_ia)
        acoes = list(jogada.get("acoes") or [])
        ataques = [dict(a) for a in acoes if str((a or {}).get("tipo") or "") == "ataque"]
        if ataques and len(acoes) < 3:
            extra = dict(ataques[0])
            extra["id_acao"] = f"{extra.get('id_acao', 'boss_acao')}_extra"
            extra["boss_acao_extra"] = True
            acoes.append(extra)
        if len(acoes) < 3:
            try:
                getattr(partida, "avisos", []).append({"motivo": "boss_invocar_servo_pendente", "lado_id": int(lado_id or 0)})
            except Exception:
                pass
        jogada["acoes"] = acoes[:3]
        meta = dict(jogada.get("meta_ia") or {})
        meta["boss_ia"] = True
        meta["boss_acoes_max"] = 3
        jogada["meta_ia"] = meta
        return jogada
