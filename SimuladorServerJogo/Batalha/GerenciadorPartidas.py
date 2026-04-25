from __future__ import annotations

from SimuladorServerJogo.Batalha.Partida import Partida


class GerenciadorPartidas:
    def __init__(self):
        self.partidas_ativas: dict[str, Partida] = {}
        self.partidas_finalizadas: dict[str, dict] = {}
        self._seq = 1

    def _gerar_id(self):
        self._seq += 1
        return f"0{self._seq:05d}"

    def criar_partida(self, dados_inicializacao):
        dados = dict(dados_inicializacao or {})
        partida_id = str(dados.get("id_partida") or self._gerar_id())
        if partida_id in self.partidas_ativas:
            partida_id = self._gerar_id()
        partida = Partida(partida_id, dados)
        self.partidas_ativas[partida_id] = partida
        return partida

    def obter_partida(self, id_partida):
        return self.partidas_ativas.get(str(id_partida or ""))

    def receber_jogada(self, id_partida, lado_id, jogada):
        partida = self.obter_partida(id_partida)
        if partida is None:
            return {"status": "erro", "mensagem": "Partida não encontrada", "id_partida": str(id_partida or ""), "estado_batalha": "erro", "avisos": [], "erros": ["partida_inexistente"]}
        return partida.receber_jogada(lado_id, jogada)

    def receber_jogadas_modo_teste(self, id_partida, jogadas):
        partida = self.obter_partida(id_partida)
        if partida is None:
            return {"status": "erro", "mensagem": "Partida não encontrada", "id_partida": str(id_partida or ""), "estado_batalha": "erro", "avisos": [], "erros": ["partida_inexistente"]}
        return partida.receber_jogadas_modo_teste(jogadas)

    def finalizar_partida(self, id_partida, motivo=None, dados=None):
        _ = dados
        partida = self.obter_partida(id_partida)
        if partida is None:
            return {"status": "erro", "mensagem": "Partida não encontrada", "id_partida": str(id_partida or ""), "estado_finalizacao": "ausente", "avisos": [], "erros": ["partida_inexistente"]}
        retorno = partida.finalizar(motivo)
        self.partidas_finalizadas[str(id_partida)] = partida.serializar_estado()
        self.partidas_ativas.pop(str(id_partida), None)
        return retorno


GERENCIADOR_PARTIDAS = GerenciadorPartidas()
