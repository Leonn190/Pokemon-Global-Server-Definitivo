from __future__ import annotations

import copy

from SimuladorServerJogo.Logica.Executes.ExecuteAtaques import executar_alvificacao, executar_execute_principal
from SimuladorServerJogo.Logica.Executes.PassivaAtaques import processar_passivas_ataque
from SimuladorServerJogo.Logica.Executes.PassivaItens import processar_passivas_itens


class RodadorTurno:
    def __init__(self, partida):
        self.partida = partida
        self.avisos = []
        self.erros_acoes = []
        self.acoes_falhas = []
        self._ataques_executados = 0

    def rodar(self, acoes_ordenadas, acoes_invalidas=None):
        self.avisos = []
        self.erros_acoes = list(acoes_invalidas or [])
        self.acoes_falhas = []
        self._ataques_executados = 0
        for acao in list(acoes_ordenadas or []):
            self.partida.passo_atual += 1
            self.executar_passo(acao)
        return {
            "avisos": list(self.avisos),
            "erros_acoes": list(self.erros_acoes),
            "acoes_falhas": list(self.acoes_falhas),
        }

    def executar_passo(self, acao):
        pokemon = self.partida.obter_pokemon((acao or {}).get("pokemon_id"))
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
        pokemon.GastarEnergia(custo, dados={"acao_id": acao.get("id_acao")})
        tipo = str(acao.get("tipo") or "")
        if tipo == "movimento":
            self._executar_movimento(pokemon, acao)
        elif tipo == "troca_posicao":
            self._executar_troca_posicao(pokemon, acao)
        elif tipo == "troca_reserva":
            self._executar_troca_reserva(pokemon, acao)
        elif tipo == "ataque":
            self._executar_ataque(pokemon, acao)
        else:
            self._falhar(acao, "tipo_sem_executor")
        self._fim_passo()

    def _validar_estado_atual(self, pokemon, acao):
        if pokemon is None:
            return "pokemon_inexistente_execucao"
        if not pokemon.esta_vivo():
            return "pokemon_morto_execucao"
        if int(pokemon.lado_id) != int((acao or {}).get("lado_id", -1)):
            return "lado_divergente_execucao"
        if pokemon.estados_transitorios.get("entrou_na_rodada"):
            return "pokemon_entrou_na_rodada"
        if pokemon.estados_transitorios.get("recuado"):
            return "pokemon_recuado"
        if not pokemon.esta_apto_para_agir():
            return "pokemon_inapto"
        if str((acao or {}).get("tipo")) in {"ataque", "movimento", "troca_posicao", "troca_reserva"} and (not pokemon.ativo or pokemon.reserva):
            return "pokemon_nao_ativo_execucao"
        return None

    def _executar_movimento(self, pokemon, acao):
        if pokemon.possui_efeito("Enraizado") or pokemon.possui_efeito("Congelado") or pokemon.possui_efeito("Dormindo"):
            self._falhar(acao, "movimento_bloqueado_por_efeito")
            return
        destino = acao.get("destino") if isinstance(acao.get("destino"), dict) else {}
        area_id = destino.get("area_id")
        ocupante = self.partida.pokemon_na_area(area_id)
        if ocupante is None:
            if not self.partida.mover_pokemon_para_area(pokemon, area_id):
                self._falhar(acao, "movimento_falhou")
            return
        if int(ocupante.lado_id) == int(pokemon.lado_id):
            if not self.partida.trocar_posicao(pokemon, ocupante):
                self._falhar(acao, "troca_posicao_convertida_falhou")
            return
        self._falhar(acao, "area_ocupada_por_oponente")

    def _executar_troca_posicao(self, pokemon, acao):
        outro = self.partida.obter_pokemon(acao.get("pokemon_destino_id"))
        if outro is None or not outro.esta_vivo():
            self._falhar(acao, "troca_posicao_alvo_morto")
            return
        if not self.partida.trocar_posicao(pokemon, outro):
            self._falhar(acao, "troca_posicao_falhou")

    def _executar_troca_reserva(self, pokemon, acao):
        reserva = self.partida.obter_pokemon(acao.get("pokemon_reserva_id") or acao.get("troca_reserva_id"))
        if reserva is None or not reserva.esta_vivo():
            self._falhar(acao, "reserva_morta_ou_inexistente")
            return
        if not self.partida.trocar_reserva(pokemon, reserva):
            self._falhar(acao, "troca_reserva_falhou")

    def _executar_ataque(self, pokemon, acao):
        props = acao.get("propriedades") if isinstance(acao.get("propriedades"), dict) else None
        if not props:
            self._falhar(acao, "ataque_sem_propriedades")
            return
        contexto = {
            "partida": self.partida,
            "usuario": pokemon,
            "acao": acao,
            "propriedades": props,
            "ataque": acao.get("ataque") if isinstance(acao.get("ataque"), dict) else {},
            "custo_real": float(acao.get("custo_real") or 0.0),
            "passo": self.partida.passo_atual,
            "rng": self.partida.rng,
            "alvos": [],
            "primeiro_ataque_da_rodada": self._ataques_executados == 0,
        }
        alvos = executar_alvificacao(props.get("nome") or (contexto["ataque"] or {}).get("nome") or (contexto["ataque"] or {}).get("Code"), contexto)
        contexto["alvos"] = list(alvos or [])
        if not contexto["alvos"] and str(props.get("estilo_logico") or "").lower() != "ativo":
            self._falhar(acao, "sem_alvo_real")
            return
        atingiu = False
        if str(props.get("estilo_logico") or "").lower() == "ativo":
            retorno = executar_execute_principal(props.get("nome"), contexto, alvo=None)
            if retorno.get("falha"):
                self._falhar(acao, str(retorno.get("motivo") or "execute_falhou"))
            else:
                atingiu = True
        else:
            for alvo in contexto["alvos"]:
                if alvo is None or not alvo.esta_vivo():
                    continue
                ctx_alvo = dict(contexto)
                ctx_alvo["alvo"] = alvo
                processar_passivas_ataque(ctx_alvo, "antes_receber_ataque")
                processar_passivas_itens(ctx_alvo, "antes_receber_ataque")
                if not self._acertou(pokemon, alvo):
                    self._falhar(acao, "ataque_errou", alvo_id=alvo.id_batalha)
                    continue
                retorno = executar_execute_principal(props.get("nome"), ctx_alvo, alvo=alvo)
                if retorno.get("falha"):
                    self._falhar(acao, str(retorno.get("motivo") or "execute_falhou"), alvo_id=alvo.id_batalha)
                else:
                    atingiu = True
        if atingiu:
            self._ataques_executados += 1

    def _acertou(self, usuario, alvo):
        acuracia = usuario.obter_atributo("Acuracia", 100.0) / 100.0
        assertividade = alvo.obter_atributo("Assertividade", 100.0) / 100.0
        chance = acuracia * assertividade
        vel_usuario = usuario.obter_atributo("Vel", 0.0)
        vel_alvo = alvo.obter_atributo("Vel", 0.0)
        media = (vel_usuario + vel_alvo) / 2.0
        escudo = 10.0
        if vel_usuario > media + escudo:
            chance += (vel_usuario - media - escudo) / 100.0
        elif vel_usuario < media - escudo:
            chance -= (media - escudo - vel_usuario) / 100.0
        if vel_alvo > media + escudo:
            chance -= (vel_alvo - media - escudo) / 100.0
        elif vel_alvo < media - escudo:
            chance += (media - escudo - vel_alvo) / 100.0
        chance = max(0.0, chance)
        return self.partida.rng.random() <= chance

    def _fim_passo(self):
        for pokemon in list(self.partida.pokemons_por_id.values()):
            pokemon.Verificar()
        for pokemon in list(self.partida.pokemons_por_id.values()):
            if pokemon.esta_vivo():
                pokemon.decrementar_efeitos(self.partida.passo_atual)
        self.partida.verificar_fim_batalha()

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

