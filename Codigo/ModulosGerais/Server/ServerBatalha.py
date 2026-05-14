from __future__ import annotations

from Servidor.Gerais.Rotas.RotasBatalha import rota_enviar_jogada, rota_finalizar_batalha, rota_inicializar_batalha


def inicializar_batalha(dados_inicializacao):
    return dict(rota_inicializar_batalha(dados_inicializacao if isinstance(dados_inicializacao, dict) else {}))


def enviar_jogada(id_partida, lado_id, jogada):
    pacote = dict(jogada) if isinstance(jogada, dict) else {}
    pacote.setdefault("id_partida", str(id_partida or ""))
    if not bool(pacote.get("modo_teste")):
        pacote.setdefault("lado_id", int(lado_id or 0))
    return dict(rota_enviar_jogada(pacote))


def finalizar_batalha(id_partida, lado_id=None, motivo=None, dados=None):
    pacote = {"id_partida": str(id_partida or ""), "lado_id": lado_id, "motivo": motivo, "dados": dados}
    return dict(rota_finalizar_batalha(pacote))
