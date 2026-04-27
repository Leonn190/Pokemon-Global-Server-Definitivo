from __future__ import annotations

from pathlib import Path


_PASTA_SERVIDOR_ATIVO: Path | None = None


def definir_servidor_ativo(pasta_server):
    global _PASTA_SERVIDOR_ATIVO
    _PASTA_SERVIDOR_ATIVO = Path(pasta_server).resolve()


def obter_pasta_servidor_ativo() -> Path | None:
    return _PASTA_SERVIDOR_ATIVO


def obter_pasta_estado_mundo() -> Path:
    if _PASTA_SERVIDOR_ATIVO is None:
        raise RuntimeError("Nenhum servidor local ativo definido")
    return _PASTA_SERVIDOR_ATIVO / "EstadoMundo"


def obter_arquivo_estado_servidor() -> Path:
    if _PASTA_SERVIDOR_ATIVO is None:
        raise RuntimeError("Nenhum servidor local ativo definido")
    return _PASTA_SERVIDOR_ATIVO / "EstadoServidor.json"


def limpar_servidor_ativo():
    global _PASTA_SERVIDOR_ATIVO
    _PASTA_SERVIDOR_ATIVO = None
