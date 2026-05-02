from __future__ import annotations


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
            if self.controlador_animacoes.esta_ocupado():
                return
            self.estado = "lendo"
        if self.estado == "lendo":
            if self.controlador_animacoes.esta_ocupado():
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
            self.enviar_evento_para_animacao(evento)
            self.aplicar_diff_evento(evento)
        except Exception as exc:
            self.avisos.append(f"evento_{tipo or 'desconhecido'}_ignorado:{exc}")

    def aplicar_diff_evento(self, evento):
        dados = self._dados(evento)
        tipo = str((evento or {}).get("tipo") or "")
        ctrl = self.controlador
        perfil = ctrl.perfil_local() if hasattr(ctrl, "perfil_local") else getattr(getattr(ctrl, "ator", None), "Perfil", None)
        if perfil is not None and hasattr(perfil, "registrar_conhecimento"):
            if tipo in {"acao_iniciada", "ataque_usado", "ataque_acertou", "ataque_errou", "ataque_sem_alvo_real"}:
                perfil.registrar_conhecimento("Ataques", dados.get("ataque_id") or dados.get("ataque_nome") or dados.get("ataque"))
        if perfil is not None and hasattr(perfil, "registrar_conhecimento_efeito"):
            if tipo in {"pokemon_recebeu_efeito", "efeito_tickou", "efeito_expirou"}:
                perfil.registrar_conhecimento_efeito(dados.get("efeito_code") or dados.get("efeito_nome"))
            elif tipo in {"efeito_bloqueado_por_limite", "efeito_bloqueado_por_imunidade"}:
                perfil.registrar_conhecimento_efeito(dados.get("efeito_code") or dados.get("efeito_nome") or dados.get("efeito"))
                perfil.registrar_conhecimento_efeito(dados.get("bloqueador_code") or dados.get("bloqueador_nome"))
            elif tipo in {"clima_aplicado", "clima_alterado", "clima_iniciado"}:
                perfil.registrar_conhecimento_efeito(dados.get("clima_code") or dados.get("clima") or dados.get("clima_nome") or dados.get("nome"))
            elif tipo in {"efeito_area_aplicado", "efeito_area_tickou", "efeito_area_expirou"}:
                perfil.registrar_conhecimento_efeito(dados.get("efeito_code") or dados.get("efeito_nome"))
        if perfil is not None and hasattr(ctrl, "sincronizar_perfil_local"):
            ctrl.sincronizar_perfil_local()
        if tipo == "pokemon_gastou_energia":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None and dados.get("energia_depois") is not None:
                poke.Energia = float(dados.get("energia_depois") or poke.Energia)
        elif tipo == "pokemon_ganhou_energia":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None and dados.get("energia_depois") is not None:
                poke.Energia = float(dados.get("energia_depois") or poke.Energia)
        elif tipo == "pokemon_sofreu_dano":
            poke = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or dados.get("pokemon_id") or ""))
            if poke is not None:
                if dados.get("vida_depois") is not None:
                    poke.VidaAtual = max(0.0, float(dados.get("vida_depois") or 0.0))
                if dados.get("barreira_depois") is not None:
                    poke.BarreiraAtual = max(0.0, float(dados.get("barreira_depois") or 0.0))
        elif tipo == "barreira_absorveu":
            poke = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or ""))
            if poke is not None and dados.get("barreira_depois") is not None:
                poke.BarreiraAtual = max(0.0, float(dados.get("barreira_depois") or 0.0))
        elif tipo == "pokemon_recebeu_cura":
            poke = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or dados.get("pokemon_id") or ""))
            if poke is not None and dados.get("vida_depois") is not None:
                poke.VidaAtual = max(0.0, float(dados.get("vida_depois") or poke.VidaAtual))
        elif tipo in {"pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"}:
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or dados.get("alvo_id") or ""))
            atributo = str(dados.get("atributo") or dados.get("stat") or dados.get("chave") or "")
            if poke is not None and atributo:
                if dados.get("valor_depois") is not None and hasattr(poke, "Atributos"):
                    poke.Atributos[atributo] = float(dados.get("valor_depois") or 0.0)
                    if atributo == "Vida" and hasattr(poke, "VidaMax"):
                        poke.VidaMax = max(1.0, float(dados.get("valor_depois") or poke.VidaMax))
                    elif atributo == "EneM" and hasattr(poke, "EnergiaMax"):
                        poke.EnergiaMax = max(1.0, float(dados.get("valor_depois") or poke.EnergiaMax))
                if dados.get("variacao_total") is not None and hasattr(poke, "Variacoes"):
                    poke.Variacoes[atributo] = float(dados.get("variacao_total") or 0.0)
                if hasattr(poke, "_sincronizar_alias_atributos"):
                    poke._sincronizar_alias_atributos()
        elif tipo == "pokemon_ganhou_barreira":
            poke = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or dados.get("pokemon_id") or ""))
            if poke is not None and dados.get("barreira_depois") is not None:
                poke.BarreiraAtual = max(0.0, float(dados.get("barreira_depois") or 0.0))
        elif tipo == "pokemon_recebeu_efeito":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            efeito = dados.get("efeito") if isinstance(dados.get("efeito"), dict) else {}
            if poke is not None:
                poke.aplicar_efeito_visual(efeito or {"nome": dados.get("efeito_nome"), "code": dados.get("efeito_code"), "passos_restantes": dados.get("passos_restantes"), "tipo": dados.get("tipo")})
        elif tipo == "efeito_tickou":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None:
                poke.atualizar_timer_efeito(dados.get("efeito_code"), dados.get("efeito_nome"), dados.get("passos_depois"))
        elif tipo == "efeito_expirou":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None:
                poke.expirar_efeito_visual(dados.get("efeito_code"), dados.get("efeito_nome"))
        elif tipo == "pokemon_entrou":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None and dados.get("area_id"):
                poke.Ativo = True
                poke.EmReserva = False
                poke.AreaId = dados.get("area_id")
        elif tipo == "captura_batalha_resultado":
            poke = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or ""))
            if poke is not None and bool(dados.get("capturado")):
                poke.Ativo = False
                poke.EmReserva = False
                poke.Vivo = False
                poke.AreaId = None
            if isinstance(dados.get("inventario_jogador"), dict):
                ctrl.aplicar_inventario_batalha(dados.get("inventario_jogador"))
        elif tipo == "inventario_atualizado_batalha":
            if int(dados.get("lado_id", getattr(ctrl, "lado_jogador", 50)) or 0) == int(getattr(ctrl, "lado_jogador", 50)) and isinstance(dados.get("inventario"), dict):
                ctrl.aplicar_inventario_batalha(dados.get("inventario"))
        elif tipo in {"clima_aplicado", "clima_alterado", "clima_iniciado"}:
            ctrl.clima_atual = dados.get("clima") or dados.get("clima_nome") or dados.get("nome") or dados
        elif tipo == "clima_expirou":
            ctrl.clima_atual = None
        ctrl.arena.atualizar_ocupacao(ctrl.pokemons)

    def enviar_evento_para_hud(self, evento):
        if hasattr(self.controlador, "registrar_evento_visual"):
            self.controlador.registrar_evento_visual(evento)

    def enviar_evento_para_animacao(self, evento):
        self.controlador_animacoes.receber_evento(evento)

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

    @staticmethod
    def _dados(evento):
        dados = dict((evento or {}).get("dados") or {})
        for chave, valor in dict(evento or {}).items():
            if chave != "dados" and chave not in dados:
                dados[chave] = valor
        return dados
