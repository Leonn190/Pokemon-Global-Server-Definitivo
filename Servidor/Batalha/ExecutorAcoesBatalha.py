from __future__ import annotations

from Servidor.Batalha.ExecutorAtaquesBatalha import ExecutorAtaquesBatalha
from Servidor.Batalha.ExecutorCapturaBatalha import ExecutorCapturaBatalha


class ExecutorAcoesBatalha:
    def __init__(self, rodador):
        self.rodador = rodador
        self.partida = rodador.partida
        self.executor_ataques = ExecutorAtaquesBatalha(self)
        self.executor_captura = ExecutorCapturaBatalha(self)

    def validar_estado_atual(self, pokemon, acao):
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
        tipo = str((acao or {}).get("tipo") or "")
        if tipo != "captura" and (pokemon.possui_efeito("Dormindo") or pokemon.possui_efeito("Congelado")):
            return "pokemon_inapto"
        if tipo == "ataque" and pokemon.possui_efeito("Paralisado"):
            return "ataque_bloqueado_por_paralisia"
        if tipo in {"movimento", "troca_posicao", "troca_reserva"} and pokemon.possui_efeito("Enraizado"):
            return "movimento_bloqueado_por_enraizado"
        if str((acao or {}).get("tipo")) in {"ataque", "movimento", "troca_posicao", "troca_reserva", "captura"} and (not pokemon.ativo or pokemon.reserva):
            return "pokemon_nao_ativo_execucao"
        return None

    def executar_movimento(self, pokemon, acao):
        if pokemon.possui_efeito("Enraizado") or pokemon.possui_efeito("Congelado") or pokemon.possui_efeito("Dormindo"):
            self.rodador._falhar(acao, "movimento_bloqueado_por_efeito")
            return
        destino = acao.get("destino") if isinstance(acao.get("destino"), dict) else {}
        area_id = destino.get("area_id")
        ocupante = self.partida.pokemon_na_area(area_id)
        if ocupante is None:
            if not self.partida.mover_pokemon_para_area(pokemon, area_id, dados={"reativos_acao": (acao or {}).get("reativos_acao")}):
                self.rodador._falhar(acao, "movimento_falhou")
            return
        if int(ocupante.lado_id) == int(pokemon.lado_id):
            if not self.partida.trocar_posicao(pokemon, ocupante, dados={"reativos_acao": (acao or {}).get("reativos_acao")}):
                self.rodador._falhar(acao, "troca_posicao_convertida_falhou")
            return
        self.rodador._falhar(acao, "area_ocupada_por_oponente")

    def executar_troca_posicao(self, pokemon, acao):
        outro = self.partida.obter_pokemon(acao.get("pokemon_destino_id"))
        if outro is None or not outro.esta_vivo():
            self.rodador._falhar(acao, "troca_posicao_alvo_morto")
            return
        if not self.partida.trocar_posicao(pokemon, outro, dados={"reativos_acao": (acao or {}).get("reativos_acao")}):
            self.rodador._falhar(acao, "troca_posicao_falhou")

    def executar_troca_reserva(self, pokemon, acao):
        reserva = self.partida.obter_pokemon(acao.get("pokemon_reserva_id") or acao.get("troca_reserva_id"))
        if reserva is None or not reserva.esta_vivo():
            self.rodador._falhar(acao, "reserva_morta_ou_inexistente")
            return
        if not self.partida.trocar_reserva(pokemon, reserva, dados={"reativos_acao": (acao or {}).get("reativos_acao")}):
            self.rodador._falhar(acao, "troca_reserva_falhou")

    def executar_ataque(self, pokemon, acao):
        return self.executor_ataques.executar_ataque(pokemon, acao)

    def executar_captura(self, pokemon, acao):
        return self.executor_captura.executar_captura(pokemon, acao)

    def acertou(self, usuario, alvo):
        return self.executor_ataques.acertou(usuario, alvo)

    def bonus_acerto_condicional(self, alvo, parametros):
        return self.executor_ataques.bonus_acerto_condicional(alvo, parametros)

    def condicao_acerto_ativa(self, alvo, condicao):
        return self.executor_ataques.condicao_acerto_ativa(alvo, condicao)

    def calcular_acerto(self, usuario, alvo, props=None):
        return self.executor_ataques.calcular_acerto(usuario, alvo, props)

    def registrar_historico_ataque(self, pokemon, acao, props, alvos):
        return self.executor_ataques.registrar_historico_ataque(pokemon, acao, props, alvos)

    def dados_animacao(self, props):
        return self.executor_ataques.dados_animacao(props)

    @staticmethod
    def ids_unicos(ids):
        return ExecutorAtaquesBatalha.ids_unicos(ids)

    @staticmethod
    def alvos_selecionados(acao):
        return ExecutorAtaquesBatalha.alvos_selecionados(acao)

    def area_alvo_visual(self, acao):
        return self.executor_ataques.area_alvo_visual(acao)

    def dados_ataque(self, pokemon, acao, props, alvo_ids=None, alvo=None, animacao=None, alvo_principal_id=None, alvos_secundarios_ids=None):
        return self.executor_ataques.dados_ataque(pokemon, acao, props, alvo_ids=alvo_ids, alvo=alvo, animacao=animacao, alvo_principal_id=alvo_principal_id, alvos_secundarios_ids=alvos_secundarios_ids)
