from __future__ import annotations

from typing import Any, Dict

from Codigo.ModulosBatalha.LeitorAtaquesCombate import LeitorAtaquesCombate
from Codigo.Prefabs import IndicadoresAtaque as prefabs


class IndicadorAtaque:
    def __init__(self, camera, leitor_ataques=None):
        self._camera = camera
        self._leitor = leitor_ataques if isinstance(leitor_ataques, LeitorAtaquesCombate) else LeitorAtaquesCombate()

    def _mundo_para_tela(self, ponto):
        if ponto is None:
            return None
        if hasattr(self._camera, "batalha_para_tela_px"):
            return self._camera.batalha_para_tela_px(ponto)
        if hasattr(self._camera, "mundo_para_tela_px"):
            return self._camera.mundo_para_tela_px(ponto)
        return ponto

    @staticmethod
    def _ataque_do_payload(payload: Dict[str, Any]):
        ataque = payload.get("ataque")
        if isinstance(ataque, dict):
            return ataque
        ataque_id = payload.get("ataque_id")
        if ataque_id:
            return {"nome": str(ataque_id)}
        return None

    @staticmethod
    def _cor_por_ataque(nome: str, selecionada: bool):
        n = str(nome or "").casefold()
        if n in {"proteger", "resetar"}:
            cor = (102, 198, 255)
        elif n in {"enraivecer", "provocar", "recarga", "tankar"}:
            cor = (164, 124, 255)
        elif n in {"biscoito"}:
            cor = (100, 224, 180)
        elif n in {"energia", "disparo", "hiper raio"}:
            cor = (120, 220, 255)
        elif n in {"bola climatica"}:
            cor = (250, 220, 145)
        else:
            cor = (255, 122, 92)
        if selecionada:
            cor = tuple(min(255, c + 24) for c in cor)
        return cor

    @staticmethod
    def _num(valor, default):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(default)

    def _desenhar(self, tela, payload: Dict[str, Any], *, selecionada=False, alpha=None):
        if not isinstance(payload, dict):
            return
        ataque_obj = self._ataque_do_payload(payload)
        spec = self._leitor.obter(ataque_obj)
        preparo = dict(spec.get("preparo") or {})
        execucao = dict(spec.get("execucao") or {})

        tipo_preparo = str(payload.get("tipo_preparo") or preparo.get("tipo") or "").strip()
        forma = str(payload.get("forma") or execucao.get("forma") or "").strip()

        origem = self._mundo_para_tela(payload.get("origem_mundo"))
        destino = self._mundo_para_tela(payload.get("destino_mundo"))
        if origem is None:
            return
        if destino is None:
            destino = origem

        nome = str(spec.get("nome") or (ataque_obj or {}).get("Ataque") or (ataque_obj or {}).get("nome") or "")
        cor = self._cor_por_ataque(nome, selecionada)
        alpha_base = int(alpha) if alpha is not None else 125

        alcance_px = self._num(execucao.get("alcance") or execucao.get("alcance_max") or preparo.get("alcance"), 3.0) * max(1, int(getattr(self._camera, "TilePx", 32)))
        largura_px = self._num(execucao.get("largura") or preparo.get("largura"), 0.6) * max(1, int(getattr(self._camera, "TilePx", 32)))
        raio_px = self._num(execucao.get("raio") or preparo.get("raio"), 0.35) * max(1, int(getattr(self._camera, "TilePx", 32)))
        angulo = self._num(execucao.get("angulo") or preparo.get("angulo"), 45)

        if forma == "impulso" or tipo_preparo == "direcao_intensidade":
            intensidade = self._num(payload.get("intensidade"), 1.0)
            prefabs.desenhar_impulso(tela, origem, destino, max(6, int(largura_px * max(0.4, intensidade))), cor, alpha=alpha_base)
            return
        if forma == "dash":
            prefabs.desenhar_dash(tela, origem, destino, max(8, int(largura_px)), cor, alpha=alpha_base)
            return
        if forma == "projetil_explosivo":
            prefabs.desenhar_projetil_explosivo(tela, origem, destino, max(4, int(raio_px)), max(12, int(raio_px * 2.0)), cor, alpha=alpha_base)
            return
        if forma == "projetil":
            prefabs.desenhar_projetil(tela, origem, destino, max(3, int(raio_px)), cor, alpha=alpha_base)
            return
        if forma == "laser" or tipo_preparo == "laser":
            prefabs.desenhar_laser(tela, origem, destino, max(8, int(largura_px)), cor, alpha=alpha_base + 20)
            return
        if forma == "cone" or tipo_preparo == "cone":
            prefabs.desenhar_cone(tela, origem, destino, alcance_px, angulo, cor, alpha=alpha_base - 15)
            return
        if forma == "cone_invertido":
            prefabs.desenhar_cone_invertido(tela, origem, destino, alcance_px, max(18, int(largura_px * 1.8)), max(8, int(largura_px * 0.9)), cor, alpha=alpha_base - 10)
            return
        if forma == "area" or tipo_preparo == "area":
            prefabs.desenhar_area_circular(tela, destino, max(10, int(raio_px * 1.8)), cor, alpha=alpha_base - 20)
            return
        if tipo_preparo == "alvo":
            alvos = payload.get("alvos") or []
            if alvos:
                for alvo in alvos:
                    alvo_tela = self._mundo_para_tela(getattr(alvo, "Posicao", None))
                    if alvo_tela is not None:
                        prefabs.desenhar_alvo(tela, origem, alvo_tela, cor, alpha=alpha_base + 20)
            else:
                prefabs.desenhar_alvo(tela, origem, destino, cor, alpha=alpha_base + 20)
            return
        if tipo_preparo == "self" or forma == "self":
            prefabs.desenhar_aro(tela, origem, max(9, int(max(raio_px, largura_px))), cor, alpha=alpha_base)
            return
        prefabs.desenhar_linha(tela, origem, destino, max(4, int(largura_px)), cor, alpha=alpha_base)

    def desenhar_preparacao(self, tela, preparacao, *, selecionada=False, alpha=None):
        self._desenhar(tela, preparacao or {}, selecionada=selecionada, alpha=alpha)

    def desenhar_jogada(self, tela, jogada, *, selecionada=False, alpha=None):
        self._desenhar(tela, jogada or {}, selecionada=selecionada, alpha=alpha)
