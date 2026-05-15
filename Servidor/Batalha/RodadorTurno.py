from __future__ import annotations

import copy

from Servidor.Batalha.ExecutorAcoesBatalha import ExecutorAcoesBatalha


class RodadorTurno:
    def __init__(self, partida):
        self.partida = partida
        self.avisos = []
        self.erros_acoes = []
        self.acoes_falhas = []
        self._ataques_executados = 0
        self.executor_acoes = ExecutorAcoesBatalha(self)

    def __setstate__(self, estado):
        self.__dict__.update(estado)
        self.executor_acoes = ExecutorAcoesBatalha(self)

    def rodar(self, acoes_ordenadas, acoes_invalidas=None):
        self.avisos = []
        self.erros_acoes = list(acoes_invalidas or [])
        self.acoes_falhas = []
        self._ataques_executados = 0
        acoes = list(acoes_ordenadas or [])
        if not acoes:
            self.partida.passo_atual += 1
            self._fim_passo()
        for acao in acoes:
            self.partida.passo_atual += 1
            self.executar_passo(acao)
        return {
            "avisos": list(self.avisos),
            "erros_acoes": list(self.erros_acoes),
            "acoes_falhas": list(self.acoes_falhas),
        }

    def executar_passo(self, acao):
        tipo = str((acao or {}).get("tipo") or "")
        if tipo == "captura":
            self._registrar_acao_iniciada(acao, None)
            self._executar_captura(None, acao)
            self._fim_passo()
            return
        pokemon = self.partida.obter_pokemon((acao or {}).get("pokemon_id"))
        self._registrar_acao_iniciada(acao, pokemon)
        motivo = self._validar_estado_atual(pokemon, acao)
        if motivo:
            self._falhar(acao, motivo)
            self._fim_passo()
            return
        custo = float((acao or {}).get("custo_real") or 0.0)
        if pokemon.EnergiaAtual < custo:
            self._falhar(acao, "energia_insuficiente_execucao")
            self._fim_passo()
            return
        gasto = pokemon.GastarEnergia(custo, dados={"acao_id": acao.get("id_acao")}) if custo > 0 else {"aplicado": False}
        if custo > 0 and isinstance(gasto, dict) and gasto.get("aplicado"):
            self.partida.registrar_evento_log(
                "pokemon_gastou_energia",
                {
                    "pokemon_id": pokemon.id_batalha,
                    "pokemon_nome": pokemon.nome,
                    "valor": gasto.get("valor", custo),
                    "energia_antes": gasto.get("energia_antes"),
                    "energia_depois": gasto.get("energia_depois"),
                    "id_acao": acao.get("id_acao"),
                },
            )
        if tipo == "movimento":
            self._executar_movimento(pokemon, acao)
        elif tipo == "troca_posicao":
            self._executar_troca_posicao(pokemon, acao)
        elif tipo == "troca_reserva":
            self._executar_troca_reserva(pokemon, acao)
        elif tipo == "ataque":
            self._executar_ataque(pokemon, acao)
        elif tipo == "captura":
            self._executar_captura(pokemon, acao)
        else:
            self._falhar(acao, "tipo_sem_executor")
        self._fim_passo()

    def _validar_estado_atual(self, pokemon, acao):
        return self.executor_acoes.validar_estado_atual(pokemon, acao)

    def _executar_movimento(self, pokemon, acao):
        return self.executor_acoes.executar_movimento(pokemon, acao)

    def _executar_troca_posicao(self, pokemon, acao):
        return self.executor_acoes.executar_troca_posicao(pokemon, acao)

    def _executar_troca_reserva(self, pokemon, acao):
        return self.executor_acoes.executar_troca_reserva(pokemon, acao)

    def _executar_ataque(self, pokemon, acao):
        return self.executor_acoes.executar_ataque(pokemon, acao)

    def _executar_captura(self, pokemon, acao):
        return self.executor_acoes.executar_captura(pokemon, acao)

    def _acertou(self, usuario, alvo):
        return self.executor_acoes.acertou(usuario, alvo)

    def _bonus_acerto_condicional(self, alvo, parametros):
        return self.executor_acoes.bonus_acerto_condicional(alvo, parametros)

    def _condicao_acerto_ativa(self, alvo, condicao):
        return self.executor_acoes.condicao_acerto_ativa(alvo, condicao)

    def _calcular_acerto(self, usuario, alvo, props=None):
        return self.executor_acoes.calcular_acerto(usuario, alvo, props)

    def _registrar_historico_ataque(self, pokemon, acao, props, alvos):
        return self.executor_acoes.registrar_historico_ataque(pokemon, acao, props, alvos)

    def _fim_passo(self):
        for pokemon in list(self.partida.pokemons_por_id.values()):
            pokemon.Verificar()
        for pokemon in list(self.partida.pokemons_por_id.values()):
            if pokemon.esta_vivo():
                pokemon.aplicar_efeitos_por_passo()
        if hasattr(self.partida, "processar_clima_por_passo"):
            self.partida.processar_clima_por_passo()
        for pokemon in list(self.partida.pokemons_por_id.values()):
            if pokemon.esta_vivo():
                pokemon.decrementar_efeitos(self.partida.passo_atual)
        self.partida.verificar_fim_batalha()
        self.partida.disparar_flag("AoFimDoPasso", {"partida": self.partida, "passo_atual": self.partida.passo_atual})

    def _falhar(self, acao, motivo, alvo_id=None):
        falha = {
            "id_acao": (acao or {}).get("id_acao"),
            "pokemon_id": (acao or {}).get("pokemon_id"),
            "tipo": (acao or {}).get("tipo"),
            "motivo": str(motivo),
        }
        if alvo_id is not None:
            falha["alvo_id"] = alvo_id
        self.acoes_falhas.append(falha)
        self.partida.registrar_evento_log("acao_falhou", falha)

    def _registrar_acao_iniciada(self, acao, pokemon):
        dados = {
            "id_acao": (acao or {}).get("id_acao"),
            "tipo": (acao or {}).get("tipo"),
            "tipo_acao": (acao or {}).get("tipo"),
            "pokemon_id": (acao or {}).get("pokemon_id"),
            "pokemon_nome": getattr(pokemon, "nome", None),
            "jogador_nome": (acao or {}).get("jogador_nome") if str((acao or {}).get("tipo") or "") == "captura" else None,
            "lado_id": (acao or {}).get("lado_id"),
            "ordem_local": (acao or {}).get("ordem_local"),
            "custo_real": (acao or {}).get("custo_real"),
        }
        ataque = (acao or {}).get("ataque") if isinstance((acao or {}).get("ataque"), dict) else None
        alvo = (acao or {}).get("alvo") if isinstance((acao or {}).get("alvo"), dict) else None
        destino = (acao or {}).get("destino") if isinstance((acao or {}).get("destino"), dict) else None
        if ataque:
            dados["ataque"] = copy.deepcopy(ataque)
        if alvo:
            dados["alvo"] = copy.deepcopy(alvo)
        if destino:
            dados["destino"] = copy.deepcopy(destino)
        self.partida.registrar_evento_log("acao_iniciada", dados)

    def _dados_animacao(self, props):
        return self.executor_acoes.dados_animacao(props)

    @staticmethod
    def _ids_unicos(ids):
        return ExecutorAcoesBatalha.ids_unicos(ids)

    @staticmethod
    def _alvos_selecionados(acao):
        return ExecutorAcoesBatalha.alvos_selecionados(acao)

    def _area_alvo_visual(self, acao):
        return self.executor_acoes.area_alvo_visual(acao)

    def _dados_ataque(self, pokemon, acao, props, alvo_ids=None, alvo=None, animacao=None, alvo_principal_id=None, alvos_secundarios_ids=None):
        return self.executor_acoes.dados_ataque(pokemon, acao, props, alvo_ids=alvo_ids, alvo=alvo, animacao=animacao, alvo_principal_id=alvo_principal_id, alvos_secundarios_ids=alvos_secundarios_ids)
