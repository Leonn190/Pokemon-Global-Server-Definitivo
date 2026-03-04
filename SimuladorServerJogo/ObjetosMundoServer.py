"""Clones server-side das classes base de GameObject para simulação de mundo online."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

Vector2 = Tuple[float, float]


@dataclass
class GameObjetoServer:
    """Clone simplificado da classe mãe GameObjeto para uso no servidor."""

    id_objeto: int
    tipo_classe: str
    posicao: Vector2 = (0.0, 0.0)
    raio_colisao: float = 12.0
    raio_interacao: float = 12.0
    campo: float = 0.0
    intensidade: float = 0.0
    estado_extra: Dict[str, object] = field(default_factory=dict)

    @property
    def Id(self) -> int:
        return int(self.id_objeto)

    def definir_posicao(self, x: float, y: float) -> None:
        self.posicao = (float(x), float(y))

    def serializar(self) -> Dict[str, object]:
        return {
            "id": self.Id,
            "tipo": self.tipo_classe,
            "posicao": [float(self.posicao[0]), float(self.posicao[1])],
            "raio_colisao": float(self.raio_colisao),
            "raio_interacao": float(self.raio_interacao),
            "campo": float(self.campo),
            "intensidade": float(self.intensidade),
            "estado": dict(self.estado_extra),
        }

    @classmethod
    def de_dict(cls, dados: Dict[str, object]) -> "GameObjetoServer":
        pos = dados.get("posicao", [0.0, 0.0])
        return cls(
            id_objeto=int(dados["id"]),
            tipo_classe=str(dados.get("tipo", "objeto")),
            posicao=(float(pos[0]), float(pos[1])),
            raio_colisao=float(dados.get("raio_colisao", 12.0)),
            raio_interacao=float(dados.get("raio_interacao", 12.0)),
            campo=float(dados.get("campo", 0.0)),
            intensidade=float(dados.get("intensidade", 0.0)),
            estado_extra=dict(dados.get("estado", {})),
        )


class EntidadeServer(GameObjetoServer):
    def __init__(self, id_objeto: int, posicao: Vector2 = (0.0, 0.0), velocidade: Vector2 = (0.0, 0.0), **kwargs) -> None:
        super().__init__(id_objeto=id_objeto, tipo_classe="entidade", posicao=posicao, **kwargs)
        self.estado_extra["velocidade"] = [float(velocidade[0]), float(velocidade[1])]


class EstruturaServer(GameObjetoServer):
    def __init__(self, id_objeto: int, posicao: Vector2 = (0.0, 0.0), **kwargs) -> None:
        super().__init__(id_objeto=id_objeto, tipo_classe="estrutura", posicao=posicao, **kwargs)


class AtorServer(EntidadeServer):
    def __init__(self, id_objeto: int, usuario: str, skin: str, posicao: Vector2 = (0.0, 0.0)) -> None:
        super().__init__(id_objeto=id_objeto, posicao=posicao)
        self.estado_extra.update({"subtipo": "player", "usuario": usuario, "skin": skin, "angulo": 0.0})


class EstruturaNaturalServer(EstruturaServer):
    def __init__(self, id_objeto: int, tipo: str, posicao: Vector2 = (0.0, 0.0), recursos: Optional[Dict[str, int]] = None):
        super().__init__(id_objeto=id_objeto, posicao=posicao, raio_colisao=20.0, raio_interacao=26.0)
        self.estado_extra.update({"subtipo": tipo, "recursos": dict(recursos or {})})
