from __future__ import annotations

from enum import Enum


class EstadoPartida(str, Enum):
    MONTANDO_JOGADAS = "MONTANDO_JOGADAS"
    AGUARDANDO_ENVIO = "AGUARDANDO_ENVIO"
    RODANDO_TURNO = "RODANDO_TURNO"
    ANIMANDO_TURNO = "ANIMANDO_TURNO"
    ENCERRADA = "ENCERRADA"


ESTADOS_PARTIDA_VALIDOS = tuple(estado.value for estado in EstadoPartida)

PREFIXOS_ID_BATALHA = {
    "pokemon": "0",
    "projetil": "1",
    "construto": "2",
    "parede": "3",
    "acao": "4",
    "evento": "5",
    "turno": "6",
    "ataque": "7",
}

ESTILOS_ATAQUE_VALIDOS = (
    "alvo",
    "status",
    "projetil",
    "area",
    "zona",
    "laser",
    "dash",
    "impulso",
    "passiva",
    "irregular",
)


def estado_partida_valido(valor) -> bool:
    return str(valor or "").strip().upper() in ESTADOS_PARTIDA_VALIDOS


def normalizar_estado_partida(valor) -> str:
    texto = str(valor or "").strip().upper()
    if texto not in ESTADOS_PARTIDA_VALIDOS:
        raise ValueError(f"EstadoPartida inválido: {valor!r}")
    return texto


def estilo_ataque_valido(valor) -> bool:
    return str(valor or "").strip().lower() in ESTILOS_ATAQUE_VALIDOS


def prefixo_id_valido(tipo, identificador) -> bool:
    prefixo = PREFIXOS_ID_BATALHA.get(str(tipo or "").strip().lower())
    texto_id = str(identificador or "").strip()
    return bool(prefixo and texto_id.startswith(prefixo))


def formatar_id_pokemon_batalha(lado, slot) -> str:
    lado_i = int(lado)
    slot_i = int(slot)
    if lado_i not in (0, 1):
        raise ValueError("lado deve ser 0 ou 1")
    if slot_i < 0 or slot_i > 5:
        raise ValueError("slot deve ser entre 0 e 5")
    return f"0{lado_i}{slot_i}"
