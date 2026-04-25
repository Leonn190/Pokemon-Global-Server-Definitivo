from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecuteAtaques import executar_alvificacao, executar_execute_principal, processar_passivas_no_alvo


class RodadorTurno:
    def __init__(self, partida):
        self.partida = partida
        self.primeiro_ataque_executado = False

    def rodar(self, acoes_ordenadas, acoes_invalidas=None):
        self.primeiro_ataque_executado = False
        log = self.partida.construtor_log.novo_log(self.partida.rodada_atual)
        self.partida.log_corrente = log
        for invalida in list(acoes_invalidas or []):
            self.partida.construtor_log.evento(log, "acao_falhou", acao_id=invalida.get("id_acao"), motivo=invalida.get("motivo_invalidacao"), pokemon_id=invalida.get("pokemon_id"))
        for acao in list(acoes_ordenadas or []):
            self.partida.passo_atual += 1
            self.executar_passo(acao, log)
        self.partida.aplicar_fim_de_rodada()
        self.partida.verificar_fim_batalha()
        self.partida.construtor_log.finalizar(log)
        return log

    def executar_passo(self, acao, log):
        pid = str(acao.get("pokemon_id") or "")
        poke = self.partida.obter_pokemon(pid)
        self.partida.construtor_log.evento(log, "acao_iniciada", passo=self.partida.passo_atual, acao_id=acao.get("id_acao"), tipo_acao=acao.get("tipo"), pokemon_id=pid)
        if poke is None or not poke.esta_vivo() or poke.lado_id != int(acao.get("lado_id", -1)):
            self.partida.construtor_log.evento(log, "acao_falhou", passo=self.partida.passo_atual, acao_id=acao.get("id_acao"), motivo="executor_invalido", pokemon_id=pid)
            return self._fim_passo()
        if bool(poke.estados_transitorios.get("entrou_na_rodada")) or bool(poke.estados_transitorios.get("recuado")):
            self.partida.construtor_log.evento(log, "acao_falhou", passo=self.partida.passo_atual, acao_id=acao.get("id_acao"), motivo="estado_transitorio", pokemon_id=pid)
            return self._fim_passo()
        if not poke.esta_apto_para_agir():
            self.partida.construtor_log.evento(log, "acao_falhou", passo=self.partida.passo_atual, acao_id=acao.get("id_acao"), motivo="inapto", pokemon_id=pid)
            return self._fim_passo()
        custo = float(acao.get("custo_real", 0.0))
        if not poke.GastarEnergia(custo):
            self.partida.construtor_log.evento(log, "acao_falhou", passo=self.partida.passo_atual, acao_id=acao.get("id_acao"), motivo="energia_insuficiente", pokemon_id=pid)
            return self._fim_passo()
        self.partida.construtor_log.evento(log, "pokemon_gastou_energia", passo=self.partida.passo_atual, pokemon_id=pid, valor=custo)
        t = str(acao.get("tipo") or "")
        if t == "movimento":
            self._movimento(poke, acao, log)
        elif t == "troca_posicao":
            self._troca_posicao(poke, acao, log)
        elif t == "troca_reserva":
            self._troca_reserva(poke, acao, log)
        elif t == "ataque":
            self._ataque(poke, acao, log)
        self._fim_passo()

    def _movimento(self, poke, acao, log):
        if poke.possui_efeito("Enraizado") or poke.possui_efeito("Congelado") or poke.possui_efeito("Dormindo"):
            return self.partida.construtor_log.evento(log, "acao_falhou", passo=self.partida.passo_atual, acao_id=acao.get("id_acao"), motivo="bloqueado_efeito", pokemon_id=poke.id_batalha)
        area = ((acao.get("destino") or {}).get("area_id") or "")
        outro = self.partida.pokemon_na_area(area)
        if outro is None:
            self.partida.mover_pokemon_para_area(poke, area)
            self.partida.construtor_log.evento(log, "pokemon_moveu", pokemon_id=poke.id_batalha, area_id=area)
        elif outro.lado_id == poke.lado_id:
            self.partida.trocar_posicao(poke, outro)
            self.partida.construtor_log.evento(log, "pokemon_trocou_posicao", pokemon_a=poke.id_batalha, pokemon_b=outro.id_batalha)
        else:
            self.partida.construtor_log.evento(log, "acao_falhou", acao_id=acao.get("id_acao"), motivo="area_ocupada_inimigo", pokemon_id=poke.id_batalha)

    def _troca_posicao(self, poke, acao, log):
        outro = self.partida.obter_pokemon(str(acao.get("pokemon_destino_id") or ""))
        if outro is None or not outro.esta_vivo() or not poke.esta_vivo() or outro.area_id not in self.partida.areas:
            return self.partida.construtor_log.evento(log, "acao_falhou", acao_id=acao.get("id_acao"), motivo="troca_invalida", pokemon_id=poke.id_batalha)
        self.partida.trocar_posicao(poke, outro)
        self.partida.construtor_log.evento(log, "pokemon_trocou_posicao", pokemon_a=poke.id_batalha, pokemon_b=outro.id_batalha)

    def _troca_reserva(self, poke, acao, log):
        res = self.partida.obter_pokemon(str(acao.get("pokemon_reserva_id") or ""))
        if res is None or not res.esta_vivo():
            return self.partida.construtor_log.evento(log, "acao_falhou", acao_id=acao.get("id_acao"), motivo="reserva_invalida", pokemon_id=poke.id_batalha)
        self.partida.trocar_reserva(poke, res)
        res.adicionar_estado_transitorio("entrou_na_rodada", {"rodada": self.partida.rodada_atual})
        self.partida.construtor_log.evento(log, "pokemon_troca_reserva", saiu=poke.id_batalha, entrou=res.id_batalha, area_id=res.area_id)

    def _ataque(self, poke, acao, log):
        props = self.partida.coletor_acoes.obter_ataque(acao)
        if not props:
            return self.partida.construtor_log.evento(log, "acao_falhou", acao_id=acao.get("id_acao"), motivo="ataque_sem_props", pokemon_id=poke.id_batalha)
        if str(props.get("estilo_logico") or "").lower() == "passivo":
            return self.partida.construtor_log.evento(log, "acao_falhou", acao_id=acao.get("id_acao"), motivo="ataque_passivo", pokemon_id=poke.id_batalha)
        estilo = str(props.get("estilo_logico") or "alvo").lower()
        nome = str(props.get("nome") or (acao.get("ataque") or {}).get("nome") or "")
        alvos = [poke]
        if estilo == "alvo":
            area = ((acao.get("alvo") or {}).get("area_id") or "")
            alv = executar_alvificacao(nome, {"partida": self.partida, "acao": acao})
            if isinstance(alv, dict) and alv.get("areas"):
                areas = list(alv.get("areas") or [])
            else:
                areas = [area]
            alvos = [self.partida.pokemon_na_area(a) for a in areas]
            alvos = [a for a in alvos if a is not None]
            if not alvos:
                return self.partida.construtor_log.evento(log, "ataque_sem_alvo_real", pokemon_id=poke.id_batalha, ataque=nome)
        alvos_atingidos = 0
        for alvo in alvos:
            contexto = {"partida": self.partida, "usuario": poke, "acao": acao, "primeiro_ataque_rodada": (not self.primeiro_ataque_executado), "alvo": alvo, "alvos_atingidos": len(alvos)}
            chance = self._chance_acerto(poke, alvo)
            if self.partida.rng.random() * 100.0 > chance:
                self.partida.construtor_log.evento(log, "ataque_errou", pokemon_id=poke.id_batalha, alvo_id=alvo.id_batalha, chance=chance)
                continue
            ret = executar_execute_principal(nome, contexto, alvo=alvo)
            alvos_atingidos += 1
            for ev in processar_passivas_no_alvo(contexto):
                self.partida.construtor_log.evento(log, ev.get("tipo", "passiva"), **{k: v for k, v in ev.items() if k != "tipo"})
            if ret.get("dano_vida", 0) > 0:
                self.partida.construtor_log.evento(log, "pokemon_sofreu_dano", pokemon_id=alvo.id_batalha, valor=ret.get("dano_vida"), ataque=nome, critico=bool(ret.get("critico")))
        self.primeiro_ataque_executado = self.primeiro_ataque_executado or (alvos_atingidos >= 0)

    def _chance_acerto(self, usuario, alvo):
        ac = usuario.atributos_finais.get("Acuracia", 100.0)
        ass = alvo.atributos_finais.get("Assertividade", 100.0)
        vu = usuario.atributos_finais.get("Vel", 0.0)
        va = alvo.atributos_finais.get("Vel", 0.0)
        media = (vu + va) / 2.0
        escudo = 10.0
        if vu > media + escudo:
            ac *= 1.0 + ((vu - media - escudo) / 100.0)
        elif vu < media - escudo:
            ac *= max(0.0, 1.0 - ((media - escudo - vu) / 100.0))
        if va > media + escudo:
            ass *= max(0.0, 1.0 - ((va - media - escudo) / 100.0))
        elif va < media - escudo:
            ass *= 1.0 + ((media - escudo - va) / 100.0)
        return max(0.0, (ac / 100.0) * (ass / 100.0) * 100.0)

    def _fim_passo(self):
        for p in self.partida.pokemons_por_id.values():
            p.decrementar_efeitos(self.partida.passo_atual)
            p.Verificar()
