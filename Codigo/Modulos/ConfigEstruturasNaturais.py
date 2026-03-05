"""Config compartilhada de tipos de estruturas naturais (cliente e servidor)."""

from __future__ import annotations

from typing import Dict, Optional

ESTRUTURAS_NATURAIS_TIPOS: Dict[int, Dict[str, object]] = {
    1: {
        "subtipo": "arvore",
        "nome": "Árvore",
        "sprite": "Recursos/Visual/Mundo/Objetos/Arvore.png",
        "raio_colisao": 0.55,
        "raio_interacao": 0.75,
    },
    2: {
        "subtipo": "pedra",
        "nome": "Pedra",
        "sprite": "Recursos/Visual/Mundo/Objetos/Pedra.png",
        "raio_colisao": 0.45,
        "raio_interacao": 0.65,
    },
    3: {
        "subtipo": "arbusto",
        "nome": "Arbusto",
        "sprite": "Recursos/Visual/Mundo/Objetos/Arbusto.png",
        "raio_colisao": 0.35,
        "raio_interacao": 0.55,
    },
}


def tipo_estrutura_natural_por_codigo(codigo: object) -> Optional[Dict[str, object]]:
    try:
        chave = int(codigo)
    except (TypeError, ValueError):
        return None
    dados = ESTRUTURAS_NATURAIS_TIPOS.get(chave)
    return dict(dados) if isinstance(dados, dict) else None
