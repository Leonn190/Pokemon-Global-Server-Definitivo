"""Clones server-side das classes base de GameObject para simulação de mundo online."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
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
    def __init__(
        self,
        id_objeto: int,
        tipo: str,
        nome: str,
        sprite: str,
        posicao: Vector2 = (0.0, 0.0),
        raio_colisao: float = 20.0,
        raio_interacao: float = 26.0,
        campo: float = 0.0,
        intensidade: float = 0.0,
        recursos: Optional[Dict[str, int]] = None,
        codigo_natural: int = 0,
    ):
        super().__init__(id_objeto=id_objeto, posicao=posicao, raio_colisao=raio_colisao, raio_interacao=raio_interacao)
        super().__init__(
            id_objeto=id_objeto,
            posicao=posicao,
            raio_colisao=raio_colisao,
            raio_interacao=raio_interacao,
            campo=campo,
            intensidade=intensidade,
        )
        self.estado_extra.update({"subtipo": tipo, "recursos": dict(recursos or {})})
        self.nome = str(nome)
        self.sprite = str(sprite)
        self.codigo_natural = int(codigo_natural)

    def serializar(self) -> Dict[str, object]:
        dados = super().serializar()
        dados["nome"] = self.nome
        dados["sprite"] = self.sprite
        dados["codigo_natural"] = self.codigo_natural
        return dados


class PokemonServer(EntidadeServer):
    def __init__(self, id_objeto: int, especie: str, posicao: Vector2 = (0.0, 0.0), **kwargs) -> None:
        super().__init__(id_objeto=id_objeto, posicao=posicao, raio_colisao=0.45, raio_interacao=1.2, **kwargs)
        self.estado_extra.update(
            {
                "subtipo": "pokemon",
                "especie": str(especie),
                "nome": str(especie),
                "ativo": True,
                "movendo": False,
                "movendo_ate": 0.0,
            }
        )

    def serializar(self) -> Dict[str, object]:
        dados = super().serializar()
        estado = dados.get("estado", {}) if isinstance(dados.get("estado", {}), dict) else {}
        agora = time.monotonic()
        estado["movendo"] = bool(agora < float(estado.get("movendo_ate", 0.0)))
        dados["estado"] = estado
        dados["nome"] = str(estado.get("nome") or estado.get("especie") or "Pokemon")
        stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}
        dados["vida"] = float(stats.get("Vida", 0.0))
        dados["atk"] = float(stats.get("Atk", 0.0))
        dados["def"] = float(stats.get("Def", 0.0))
        return dados

    def mover(self, deslocamento: Vector2, colisor_cb=None, velocidade_tiles_s: float = 1.0) -> bool:
        if not bool(self.estado_extra.get("ativo", True)):
            return False
        if time.monotonic() < float(self.estado_extra.get("movendo_ate", 0.0)):
            return False
        dx = float(deslocamento[0]) if isinstance(deslocamento, (list, tuple)) and len(deslocamento) > 0 else 0.0
        dy = float(deslocamento[1]) if isinstance(deslocamento, (list, tuple)) and len(deslocamento) > 1 else 0.0
        destino = (float(self.posicao[0]) + dx, float(self.posicao[1]) + dy)
        if callable(colisor_cb) and not bool(colisor_cb(destino, self.raio_colisao)):
            return False
        self.definir_posicao(destino[0], destino[1])
        distancia = max(0.0, ((dx * dx) + (dy * dy)) ** 0.5)
        velocidade = max(0.01, float(velocidade_tiles_s))
        duracao_mov = distancia / velocidade
        agora = time.monotonic()
        self.estado_extra["movendo"] = bool(duracao_mov > 0.0)
        self.estado_extra["movendo_ate"] = agora + duracao_mov
        self.estado_extra["ultimo_movimento"] = [dx, dy]
        return True

    def sumir(self) -> None:
        self.estado_extra["ativo"] = False
        self.estado_extra["despawnado"] = True

    def capturar(self, capturador: str = "") -> None:
        self.estado_extra["ativo"] = False
        self.estado_extra["capturado"] = True
        self.estado_extra["capturador"] = str(capturador or "")
