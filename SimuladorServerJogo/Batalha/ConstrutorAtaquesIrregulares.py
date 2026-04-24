from __future__ import annotations

from copy import deepcopy
from typing import Dict, Iterable


def _ponto(valor) -> tuple[float, float]:
    if not isinstance(valor, (tuple, list)) or len(valor) != 2:
        raise ValueError("ponto deve conter duas coordenadas")
    return float(valor[0]), float(valor[1])


def construir_parede(*, ataque: Dict[str, object], executor_id: object, ponto_a, ponto_b) -> Dict[str, object]:
    props = deepcopy(ataque or {})
    parede = props.get("parede") if isinstance(props.get("parede"), dict) else {}
    return {
        "tipo": "parede",
        "executor_id": str(executor_id or ""),
        "ataque_id": props.get("id"),
        "ponto_a": _ponto(ponto_a),
        "ponto_b": _ponto(ponto_b),
        "largura": float((parede or {}).get("largura", 0.25) or 0.25),
        "fixa": True,
        "propriedades": props,
    }


def construir_explosivo(*, ataque: Dict[str, object], executor_id: object, origem, direcao) -> Dict[str, object]:
    props = deepcopy(ataque or {})
    projetil = props.get("projetil") if isinstance(props.get("projetil"), dict) else {}
    explosivo = props.get("explosivo") if isinstance(props.get("explosivo"), dict) else {}
    zona = explosivo.get("zona") if isinstance(explosivo.get("zona"), dict) else {}
    return {
        "tipo": "explosivo",
        "executor_id": str(executor_id or ""),
        "ataque_id": props.get("id"),
        "origem": _ponto(origem),
        "direcao": _ponto(direcao),
        "projetil": dict(projetil or {}),
        "detona_ao_colidir_com": list(explosivo.get("detona_ao_colidir_com") or ["pokemon", "parede", "construto", "projetil"]),
        "zona": dict(zona or {}),
        "imunes_ao_subfluxo": list(explosivo.get("imunes_ao_subfluxo") or []),
        "propriedades": props,
    }


def normalizar_irregular(*, ataque: Dict[str, object], executor_id: object, payload: Dict[str, object] | None = None) -> Dict[str, object]:
    props = deepcopy(ataque or {})
    estilo = str(props.get("estilo") or "").strip().casefold()
    dados = dict(payload or {})
    if estilo == "parede":
        return construir_parede(
            ataque=props,
            executor_id=executor_id,
            ponto_a=dados.get("ponto_a"),
            ponto_b=dados.get("ponto_b"),
        )
    if estilo == "explosivo":
        return construir_explosivo(
            ataque=props,
            executor_id=executor_id,
            origem=dados.get("origem") or dados.get("origem_mundo") or (0.0, 0.0),
            direcao=dados.get("direcao") or dados.get("destino_mundo") or (1.0, 0.0),
        )
    raise ValueError(f"Estilo irregular nao suportado: {estilo!r}")


__all__: Iterable[str] = ("construir_parede", "construir_explosivo", "normalizar_irregular")
