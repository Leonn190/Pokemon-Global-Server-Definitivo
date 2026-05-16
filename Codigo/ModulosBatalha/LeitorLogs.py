from __future__ import annotations

import copy

from Codigo.ModulosBatalha.AplicadorDiffBatalhaCliente import AplicadorDiffBatalhaCliente


class LeitorLogs:
    ESTADOS = {"parado", "lendo", "aguardando_animacao", "consolidando", "aguardando_resultado", "finalizado"}

    def __init__(self, controlador, controlador_animacoes):
        self.controlador = controlador
        self.controlador_animacoes = controlador_animacoes
        self.log = {}
        self.historico: list[dict[str, object]] = []
        self.resultado = {}
        self.indice = 0
        self.estado = "parado"
        self.avisos: list[str] = []
        self._delay_resultado_s = 0.0
        self.aplicador_diff = AplicadorDiffBatalhaCliente(controlador)

    def carregar_log(self, log):
        self.log = dict(log or {})
        self.historico = [dict(e) for e in list(self.log.get("historico") or []) if isinstance(e, dict)]
        self.historico.sort(key=lambda e: (int(e.get("passo", 0) or 0), int(e.get("ordem", 0) or 0), str(e.get("id_evento") or "")))
        self.resultado = dict(self.log.get("resultado") or {})
        self.indice = 0
        self.estado = "parado"
        return self

    def iniciar_leitura(self):
        self.estado = "lendo" if self.historico else "consolidando"

    def atualizar(self, dt):
        _ = dt
        if self.estado == "aguardando_resultado":
            self._delay_resultado_s = max(0.0, float(self._delay_resultado_s) - max(0.0, float(dt or 0.0)))
            if self._delay_resultado_s <= 0.0:
                self.abrir_resultado_final_pendente()
            return
        if self.estado not in {"lendo", "aguardando_animacao", "consolidando"}:
            return
        if self.estado == "aguardando_animacao":
            proximo = self.historico[self.indice] if self.indice < len(self.historico) else None
            pode_processar = proximo is not None and hasattr(self.controlador_animacoes, "pode_processar_evento_durante_animacao") and self.controlador_animacoes.pode_processar_evento_durante_animacao(proximo)
            if self.controlador_animacoes.esta_ocupado() and not pode_processar:
                return
            self.estado = "lendo"
        if self.estado == "lendo":
            proximo = self.historico[self.indice] if self.indice < len(self.historico) else None
            pode_processar = proximo is not None and hasattr(self.controlador_animacoes, "pode_processar_evento_durante_animacao") and self.controlador_animacoes.pode_processar_evento_durante_animacao(proximo)
            if self.controlador_animacoes.esta_ocupado() and not pode_processar:
                self.estado = "aguardando_animacao"
                return
            if self.indice >= len(self.historico):
                self.estado = "consolidando"
            else:
                self.processar_proximo_evento()
                if self.controlador_animacoes.esta_ocupado():
                    self.estado = "aguardando_animacao"
                return
        if self.estado == "consolidando":
            if self.controlador_animacoes.esta_ocupado():
                self.estado = "aguardando_animacao"
                return
            self.consolidar_resultado()

    def processar_proximo_evento(self):
        if self.indice >= len(self.historico):
            self.estado = "consolidando"
            return
        evento = self.historico[self.indice]
        self.indice += 1
        self.processar_evento(evento)

    def processar_evento(self, evento):
        tipo = str((evento or {}).get("tipo") or "")
        try:
            self.enviar_evento_para_hud(evento)
            delay_visual = float(self.enviar_evento_para_animacao(evento) or 0.0)
            if delay_visual > 0.001 and self._diff_deve_esperar_visual(tipo):
                evento_diff = copy.deepcopy(evento)
                self.controlador_animacoes.agendar_callback(delay_visual, lambda ev=evento_diff: self.aplicar_diff_evento(ev))
            else:
                self.aplicar_diff_evento(evento)
        except Exception as exc:
            self.avisos.append(f"evento_{tipo or 'desconhecido'}_ignorado:{exc}")

    def aplicar_diff_evento(self, evento):
        return self.aplicador_diff.aplicar(evento)

    def enviar_evento_para_hud(self, evento):
        if hasattr(self.controlador, "registrar_evento_visual"):
            self.controlador.registrar_evento_visual(evento)

    def enviar_evento_para_animacao(self, evento):
        return self.controlador_animacoes.receber_evento(evento)

    @staticmethod
    def _diff_deve_esperar_visual(tipo):
        return str(tipo or "") in {
            "pokemon_sofreu_dano",
            "barreira_absorveu",
            "pokemon_recebeu_cura",
            "pokemon_ganhou_barreira",
            "pokemon_recebeu_efeito",
            "pokemon_variou_atributo",
            "atributo_variou",
            "pokemon_alterou_atributo",
        }

    def consolidar_resultado(self):
        if isinstance(self.resultado, dict):
            self.controlador.aplicar_resultado_final(self.resultado)
        self.controlador.limpar_jogada_confirmada()
        if isinstance(getattr(self.controlador, "replay_log_atual", None), dict):
            self.controlador.replay_log_atual["ativo"] = False
        if bool(self.resultado.get("finalizada")):
            self.controlador.estado_batalha = "finalizada"
            self._delay_resultado_s = 1.0
            self.estado = "aguardando_resultado"
            return
        else:
            self.controlador.voltar_para_montagem()
        self.estado = "finalizado"

    def abrir_resultado_final_pendente(self):
        finalizador = getattr(self.controlador, "finalizador", None)
        if finalizador is not None:
            finalizador.finalizar_por_resultado(self.resultado)
        self.estado = "finalizado"

    def terminou(self):
        return self.estado == "finalizado"
