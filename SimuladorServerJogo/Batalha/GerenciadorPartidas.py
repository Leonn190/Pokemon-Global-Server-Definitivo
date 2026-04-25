from __future__ import annotations

from SimuladorServerJogo.Batalha.Partida import Partida


class GerenciadorPartidas:
    def __init__(self):
        self.partidas_ativas = {}

    def criar_partida(self, dados_inicializacao):
        partida_id = str((dados_inicializacao or {}).get("id_partida") or f"partida_{len(self.partidas_ativas)+1}")
        partida = Partida(partida_id, dados_inicializacao or {})
        self.partidas_ativas[partida_id] = partida
        return partida

    def obter_partida(self, id_partida):
        return self.partidas_ativas.get(str(id_partida or ""))

    def receber_jogada(self, id_partida, lado_id, jogada):
        partida = self.obter_partida(id_partida) or self.criar_partida({"id_partida": id_partida})
        return partida.receber_jogada(lado_id, jogada)

    def receber_jogadas_modo_teste(self, id_partida, jogadas):
        partida = self.obter_partida(id_partida) or self.criar_partida({"id_partida": id_partida})
        return partida.receber_jogadas_modo_teste(jogadas)

    def finalizar_partida(self, id_partida, motivo=None, dados=None):
        _ = dados
        partida = self.obter_partida(id_partida)
        if partida is None:
            return {"status": "erro", "mensagem": "Partida não encontrada", "id_partida": str(id_partida or ""), "estado_finalizacao": "ausente", "avisos": [], "erros": ["partida_inexistente"]}
        retorno = partida.finalizar(motivo)
        self.partidas_ativas.pop(str(id_partida), None)
        return retorno


GERENCIADOR_PARTIDAS = GerenciadorPartidas()
