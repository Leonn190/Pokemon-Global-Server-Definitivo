from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Codigo.ModulosBatalha.ControladorBatalha import ControladorBatalha


class FluxoBatalha:
    def __init__(self, batalha: "ControladorBatalha"):
        self.batalha = batalha

    def passar_rodada_local(self):
        b = self.batalha
        b.estado_batalha = "passando_rodada"
        b.rodada_atual += 1
        b.limpar_ataque()
        b.timer_rodada = b.timer_rodada_max
        b.logs_locais.append({"rodada": b.rodada_atual, "texto": f"Rodada {b.rodada_atual} iniciada."})
        b.estado_batalha = "montando_jogada"

    def enviar_jogada_pronta(self):
        b = self.batalha
        if b.estado_batalha != "montando_jogada":
            return
        if b.montador_jogadas is None:
            return
        if b.modo_teste:
            pacote = b.montador_jogadas.gerar_pacote_jogadas_modo_teste()
        else:
            pacote = b.montador_jogadas.gerar_pacote_jogada()
            if not b.batalha_usa_ia():
                pacote["resolver_lados_ausentes"] = True
        b._ocultar_montagem_visual()
        b.estado_batalha = "aguardando_servidor"
        resposta = b.server_batalha.enviar_jogada(b.id_partida, b.lado_jogador, pacote)
        b.tratar_resposta_jogada(resposta)

    def tratar_resposta_jogada(self, resposta):
        b = self.batalha
        status = str((resposta or {}).get("status") or "erro")
        if status == "ok":
            b.estado_batalha = str((resposta or {}).get("estado_batalha") or "recebido_stub")
            b.adicionar_log_local(str((resposta or {}).get("mensagem") or "Jogada aceita"))
            log = (resposta or {}).get("log") if isinstance((resposta or {}).get("log"), dict) else {}
            if isinstance(log, dict) and list(log.get("historico") or []):
                b.receber_log(log)
                return
            resultado = (resposta or {}).get("resultado")
            if not isinstance(resultado, dict):
                resultado = log.get("resultado") if isinstance(log.get("resultado"), dict) else None
            if isinstance(resultado, dict):
                b.aplicar_resultado_final(resultado)
                b.limpar_jogada_confirmada()
                if bool(resultado.get("finalizada")) and b.finalizador is not None:
                    b.finalizador.finalizar_por_resultado(resultado)
                return
            if b.estado_batalha != "aguardando":
                b.limpar_jogada_confirmada()
                b.estado_batalha = "montando_jogada"
            return
        b.estado_batalha = "montando_jogada"
        b.adicionar_log_local(str((resposta or {}).get("mensagem") or "Falha ao enviar jogada"))

    def aplicar_resultado_batalha(self, resultado):
        b = self.batalha
        return b.aplicar_resultado_final(resultado)

    def aplicar_resultado_final(self, resultado):
        b = self.batalha
        pokemons = resultado.get("pokemons") if isinstance(resultado.get("pokemons"), dict) else {}
        for pid, diff in pokemons.items():
            pokemon = b.pokemons_por_id.get(str(pid))
            if pokemon is not None:
                pokemon.atualizar_por_diff(diff)
        if b.arena is not None:
            b.arena.atualizar_ocupacao(b.pokemons)
        if b.pokemon_selecionado is not None and ((not b.pokemon_selecionado.esta_vivo()) or (not b.pokemon_visivel(b.pokemon_selecionado))):
            b.desselecionar_pokemon()
        b.rodada_atual = int(resultado.get("rodada_atual", b.rodada_atual) or b.rodada_atual)
        if "clima_atual" in resultado:
            b.clima_atual = resultado.get("clima_atual")
        if isinstance(resultado.get("inventario_jogador"), dict):
            b.aplicar_inventario_batalha(resultado.get("inventario_jogador"))
        b.estado_batalha = str(resultado.get("estado_batalha") or ("finalizada" if resultado.get("finalizada") else "montando_jogada"))
        if bool(resultado.get("finalizada")):
            b.estado_batalha = "finalizada"
        b.timer_rodada = b.timer_rodada_max

    def batalha_usa_ia(self):
        b = self.batalha
        tipo = str(b.tipo_batalha or "").strip().lower()
        return tipo in {"confronto", "treinador", "trainer", "servo", "boss"} and not bool(b.modo_teste)

    def receber_log(self, log):
        b = self.batalha
        rodada = int((log or {}).get("rodada") or b.rodada_atual or 1)
        b.logs_por_rodada[rodada] = dict(log or {})
        b.logs_visiveis_por_rodada[rodada] = []
        b.replay_log_atual = {"ativo": True, "turno_atual": rodada, "tick_atual": 0, "tick_final": len(list((log or {}).get("historico") or []))}
        b._ocultar_montagem_visual()
        b.bloquear_input_durante_log()
        b.estado_batalha = "animando_rodada"
        if b.leitor_logs is not None:
            b.leitor_logs.carregar_log(log)
            b.leitor_logs.iniciar_leitura()

    def registrar_evento_visual(self, evento):
        b = self.batalha
        rodada = int((evento or {}).get("rodada") or (b.replay_log_atual or {}).get("turno_atual") or b.rodada_atual or 1)
        b.logs_visiveis_por_rodada.setdefault(rodada, []).append(dict(evento or {}))
        if isinstance(b.replay_log_atual, dict) and int(b.replay_log_atual.get("turno_atual", 0) or 0) == rodada:
            b.replay_log_atual["tick_atual"] = len(b.logs_visiveis_por_rodada.get(rodada, []))

    def voltar_para_montagem(self):
        b = self.batalha
        b.desbloquear_input_apos_log()
        b.estado_batalha = "montando_jogada"
        b.timer_rodada = b.timer_rodada_max
        if isinstance(b.replay_log_atual, dict):
            b.replay_log_atual["ativo"] = False

    def bloquear_input_durante_log(self):
        b = self.batalha
        b.limpar_ataque()
        b.area_selecionada = None
        b.pokemon_selecionado = None

    def desbloquear_input_apos_log(self):
        b = self.batalha
        if isinstance(b.replay_log_atual, dict):
            b.replay_log_atual["ativo"] = False

    def _ocultar_montagem_visual(self):
        b = self.batalha
        if b.montador_jogadas is not None:
            b.montador_jogadas.limpar_jogada()
            b.montador_jogadas.cancelar_previa()
        hud = getattr(b, "hud", None)
        painel = getattr(hud, "painel_acoes", None)
        if painel is not None and hasattr(painel, "sincronizar"):
            painel.sincronizar([], None)

    def adicionar_log_local(self, texto):
        b = self.batalha
        b.logs_locais.append({"rodada": b.rodada_atual, "texto": str(texto or "")})

    def limpar_jogada_confirmada(self):
        b = self.batalha
        if b.montador_jogadas is not None:
            b.montador_jogadas.limpar_jogada()
        b.atualizar_previsoes_hud()

    def atualizar_previsoes_hud(self):
        b = self.batalha
        if b.montador_jogadas is not None:
            b.montador_jogadas.recalcular_previsao_energia()

    def estado_visualizador_logs(self):
        b = self.batalha
        ultimo = max([1, b.rodada_atual, *list(b.logs_por_rodada.keys() or [1]), *list(b.logs_visiveis_por_rodada.keys() or [1])])
        return {
            "ultimo_turno_com_log": ultimo,
            "rodada_atual": b.rodada_atual,
            "replay": dict(b.replay_log_atual or {"ativo": False}),
        }

    def obter_log_publico(self, rodada):
        b = self.batalha
        alvo = int(rodada or 1)
        if alvo in b.logs_visiveis_por_rodada:
            return {"historico": [dict(e) for e in b.logs_visiveis_por_rodada.get(alvo, [])]}
        historico = []
        for idx, item in enumerate(b.logs_locais):
            if int(item.get("rodada", 0) or 0) != alvo:
                continue
            historico.append(
                {
                    "tick": idx,
                    "fase": "inicializacao",
                    "evento": {
                        "tipo": "acao",
                        "texto": str(item.get("texto") or ""),
                    },
                }
            )
        return {"historico": historico}

    def fuga_disponivel(self):
        b = self.batalha
        tipo = str(b.tipo_batalha or "").strip().lower()
        if tipo == "boss":
            return False
        if tipo == "servo":
            return int(b.rodada_atual or 1) > 5
        return True

    def iniciar_fuga(self):
        b = self.batalha
        if not b.fuga_disponivel():
            b.adicionar_log_local("Fuga liberada apos 5 turnos." if str(b.tipo_batalha or "").strip().lower() == "servo" else "Fuga bloqueada nesta batalha.")
            return
        b._fuga_alpha = min(255.0, b._fuga_alpha + b._fuga_incremento_clique)
        b.estado_batalha = "fugindo"
        if b._fuga_alpha >= b._fuga_limite_saida:
            if b.finalizador is not None:
                b.finalizador.finalizar_por_fuga()
            else:
                b.solicitou_encerrar_batalha = True

    def atualizar_fuga(self, dt: float):
        b = self.batalha
        dt = max(0.0, float(dt or 0.0))
        if b._fuga_alpha > 0.0:
            b._fuga_alpha = max(0.0, b._fuga_alpha - b._fuga_clarear_por_segundo * dt)

    @staticmethod
    def _resposta_aguardando(resposta):
        return str((resposta or {}).get("status") or "").lower() == "ok" and str((resposta or {}).get("estado_batalha") or "").lower() == "aguardando"
