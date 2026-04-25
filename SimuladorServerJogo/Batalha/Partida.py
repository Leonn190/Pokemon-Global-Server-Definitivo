from __future__ import annotations

import copy
import json


class Partida:
    def __init__(self, id_partida: str, dados_inicializacao: dict | None = None):
        self.id_partida = str(id_partida)
        self.rodada_atual = int((dados_inicializacao or {}).get("rodada", 1) or 1)
        self.lados = set([50, 51])
        self.jogadas_recebidas = {}
        self.historico_recebimentos = []
        self.estado_partida = "recebido_stub"

    def _normalizar_serializavel(self, dados):
        try:
            bruto = json.loads(json.dumps(dados, ensure_ascii=False))
            return bruto, []
        except Exception as exc:
            return None, [f"Pacote não serializável: {exc}"]

    def receber_jogada(self, lado_id, jogada):
        avisos = []
        erros = []
        normalizado, falhas = self._normalizar_serializavel(jogada)
        if falhas:
            return {"status": "erro", "mensagem": "Jogada inválida", "id_partida": self.id_partida, "estado_batalha": self.estado_partida, "avisos": avisos, "erros": falhas}
        try:
            lado = int(lado_id)
        except (TypeError, ValueError):
            return {"status": "erro", "mensagem": "lado_id inválido", "id_partida": self.id_partida, "estado_batalha": self.estado_partida, "avisos": avisos, "erros": ["lado_id_invalido"]}
        self.lados.add(lado)
        self.jogadas_recebidas[lado] = normalizado
        self.historico_recebimentos.append({"lado_id": lado, "jogada": copy.deepcopy(normalizado)})
        return self.serializar_resposta_recebimento(avisos=avisos, erros=erros)

    def receber_jogadas_modo_teste(self, jogadas):
        avisos = []
        erros = []
        normalizado, falhas = self._normalizar_serializavel(jogadas)
        if falhas:
            return {"status": "erro", "mensagem": "Jogadas inválidas", "id_partida": self.id_partida, "estado_batalha": self.estado_partida, "avisos": avisos, "erros": falhas}
        for item in normalizado if isinstance(normalizado, list) else []:
            if not isinstance(item, dict):
                avisos.append("Entrada de jogada ignorada por formato")
                continue
            try:
                lado = int(item.get("lado_id", -1))
            except (TypeError, ValueError):
                avisos.append("Entrada de jogada ignorada por lado_id inválido")
                continue
            self.lados.add(lado)
            self.jogadas_recebidas[lado] = copy.deepcopy(item)
        self.historico_recebimentos.append({"modo_teste": True, "jogadas": copy.deepcopy(normalizado)})
        return self.serializar_resposta_recebimento(avisos=avisos, erros=erros)

    def serializar_resposta_recebimento(self, avisos=None, erros=None):
        return {
            "status": "ok",
            "mensagem": "Jogada recebida",
            "id_partida": self.id_partida,
            "estado_batalha": self.estado_partida,
            "avisos": list(avisos or []),
            "erros": list(erros or []),
        }

    def finalizar(self, motivo=None):
        self.estado_partida = "encerrada"
        return {
            "status": "ok",
            "mensagem": f"Partida finalizada: {motivo or 'sem motivo'}",
            "id_partida": self.id_partida,
            "estado_finalizacao": self.estado_partida,
            "avisos": [],
            "erros": [],
        }
