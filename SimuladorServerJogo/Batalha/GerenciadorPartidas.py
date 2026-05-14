from __future__ import annotations

import uuid

from SimuladorServerJogo.Batalha.Partida import Partida


class GerenciadorPartidas:
    def __init__(self):
        self.partidas_ativas = {}
        self.partidas_finalizadas = {}

    def criar_partida(self, dados_inicializacao):
        dados = dict(dados_inicializacao or {})
        partida_id = str(dados.get("id_partida") or uuid.uuid4().hex)
        partida = Partida(partida_id, dados)
        self.partidas_ativas[partida_id] = partida
        return partida

    def obter_partida(self, id_partida):
        return self.partidas_ativas.get(str(id_partida or ""))

    def receber_jogada(self, id_partida, lado_id, jogada):
        partida = self.obter_partida(id_partida)
        if partida is None:
            return {"status": "erro", "mensagem": "Partida nao encontrada", "id_partida": str(id_partida or ""), "estado_batalha": "ausente", "avisos": [], "erros": ["partida_inexistente"]}
        return partida.receber_jogada(lado_id, jogada)

    def receber_jogadas_modo_teste(self, id_partida, jogadas):
        partida = self.obter_partida(id_partida)
        if partida is None:
            return {"status": "erro", "mensagem": "Partida nao encontrada", "id_partida": str(id_partida or ""), "estado_batalha": "ausente", "avisos": [], "erros": ["partida_inexistente"]}
        return partida.receber_jogadas_modo_teste(jogadas)

    def finalizar_partida(self, id_partida, motivo=None, dados=None, lado_id=None):
        _ = dados
        partida = self.obter_partida(id_partida)
        if partida is None:
            return {"status": "erro", "mensagem": "Partida nao encontrada", "id_partida": str(id_partida or ""), "estado_finalizacao": "ausente", "avisos": [], "erros": ["partida_inexistente"]}
        retorno = partida.finalizar(motivo, lado_id=lado_id)
        try:
            from SimuladorServerJogo.Gerais.EstadoServidor import registrar_recompensas_batalha_finalizada

            registrar_recompensas_batalha_finalizada(partida)
        except Exception as exc:
            retorno.setdefault("avisos", []).append({"tipo": "recompensa_batalha", "erro": str(exc)})
        self.partidas_ativas.pop(str(id_partida), None)
        self.partidas_finalizadas[str(id_partida)] = partida
        return retorno


GERENCIADOR_PARTIDAS = GerenciadorPartidas()
