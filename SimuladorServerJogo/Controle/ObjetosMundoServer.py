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


class BauServer(EntidadeServer):
    def __init__(
        self,
        id_objeto: int,
        tipo_bau: str,
        itens: list,
        posicao: Vector2 = (0.0, 0.0),
        aberto: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(id_objeto=id_objeto, posicao=posicao, **kwargs)
        self.estado_extra.update(
            {
                "subtipo": "bau",
                "tipo_bau": str(tipo_bau),
                "itens": list(itens),
                "aberto": bool(aberto),
                "aberto_em": 0.0,
            }
        )

    def abrir(self) -> bool:
        if bool(self.estado_extra.get("aberto", False)):
            return False
        self.estado_extra["aberto"] = True
        self.estado_extra["aberto_em"] = time.monotonic()
        return True


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
                "dificuldade_captura": 50.0,
                "tamanho_barra_captura": 0.32,
                "velocidade_barra_captura": 90.0,
                "tentativas_falhas_captura": 0,
                "frutas_aplicadas": [],
                "estado_frutificacao": {"multiplicador_doces": 1.0, "bonus_captura_frutas": 0.0, "bonus_captura_bioma": {}, "limite_frutas": 2},
                "captura_fase": "nenhuma",
                "captura": {
                    "fase": "nenhuma",
                    "ativa": False,
                    "agenda": [],
                    "inicio_ms_servidor": 0,
                    "fase_inicio_ms": 0,
                    "tremida_atual": 0,
                    "bola_nome": "",
                    "dono_id": 0,
                },
            }
        )


    def aplicar_tamanho(self) -> None:
        tamanho = self.estado_extra.get("tamanho")
        try:
            tamanho_tiles = float(tamanho)
        except (TypeError, ValueError):
            altura = float(self.estado_extra.get("altura", 1.0) or 1.0)
            progresso = max(0.0, min(1.0, (altura - 0.5) / 2.5))
            tamanho_tiles = max(1.0, min(3.0, 1.0 + (2.0 * progresso)))
        tamanho_tiles = max(1.0, min(3.0, tamanho_tiles))
        self.estado_extra["tamanho"] = float(tamanho_tiles)
        self.raio_colisao = float(tamanho_tiles * 0.5)
        self.raio_interacao = max(float(self.raio_colisao), float(tamanho_tiles) * 0.75)

    def serializar(self) -> Dict[str, object]:
        dados = super().serializar()
        estado = dados.get("estado", {}) if isinstance(dados.get("estado", {}), dict) else {}
        captura = estado.get("captura") if isinstance(estado.get("captura"), dict) else {}
        estado["captura_fase"] = str(captura.get("fase", estado.get("captura_fase", "nenhuma")))
        estado["captura_pendente"] = bool(captura.get("captura_pendente", False))
        estado["captura_resultado"] = str(captura.get("resultado", "pendente") or "pendente")
        agora = time.monotonic()
        estado["movendo"] = bool(agora < float(estado.get("movendo_ate", 0.0)))

        self.aplicar_tamanho()
        dados["raio_colisao"] = float(self.raio_colisao)
        dados["raio_interacao"] = float(self.raio_interacao)

        if bool(captura.get("captura_pendente", False)):
            dados["raio_colisao"] = 0.0
            dados["raio_interacao"] = 0.0

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



class ProjetilServer(EntidadeServer):
    def __init__(
        self,
        id_objeto: int,
        posicao: Vector2,
        dono_id: int,
        tipo_projetil: str,
        subtipo: str,
        item_base_id: str,
        token_arremesso: str,
        direcao: Vector2,
        velocidade: float,
        alcance: float,
        raio_colisao: float = 0.18,
    ) -> None:
        super().__init__(id_objeto=id_objeto, posicao=posicao, raio_colisao=raio_colisao, raio_interacao=raio_colisao)
        dx, dy = float(direcao[0]), float(direcao[1])
        n = (dx * dx + dy * dy) ** 0.5 or 1.0
        self.estado_extra.update(
            {
                "subtipo": "projetil",
                "tipo_projetil": str(tipo_projetil or "item"),
                "nome_item": str(subtipo or "item"),
                "item_base_id": str(item_base_id or ""),
                "dono_id": int(dono_id or 0),
                "token_arremesso": str(token_arremesso or ""),
                "posicao_inicial": [float(posicao[0]), float(posicao[1])],
                "direcao": [dx / n, dy / n],
                "velocidade": max(0.1, float(velocidade or 10.0)),
                "alcance": max(0.1, float(alcance or 6.0)),
                "distancia": 0.0,
                "tempo_vida": 0.0,
                "rotacao": 0.0,
                "terminado": False,
                "autoritativo": True,
            }
        )

    def atualizar(self, dt: float) -> None:
        if bool(self.estado_extra.get("terminado", False)):
            return
        dt = max(0.0, float(dt))
        direcao = self.estado_extra.get("direcao", [1.0, 0.0])
        dx = float(direcao[0]) if isinstance(direcao, (list, tuple)) and len(direcao) == 2 else 1.0
        dy = float(direcao[1]) if isinstance(direcao, (list, tuple)) and len(direcao) == 2 else 0.0
        velocidade = float(self.estado_extra.get("velocidade", 10.0) or 10.0)
        passo = velocidade * dt
        self.definir_posicao(self.posicao[0] + dx * passo, self.posicao[1] + dy * passo)
        self.estado_extra["distancia"] = float(self.estado_extra.get("distancia", 0.0) or 0.0) + passo
        self.estado_extra["tempo_vida"] = float(self.estado_extra.get("tempo_vida", 0.0) or 0.0) + dt
        self.estado_extra["rotacao"] = (float(self.estado_extra.get("rotacao", 0.0) or 0.0) + 560.0 * dt) % 360.0
        if float(self.estado_extra.get("distancia", 0.0) or 0.0) >= float(self.estado_extra.get("alcance", 6.0) or 6.0):
            self.estado_extra["terminado"] = True

    def terminar(self, motivo: str = "") -> None:
        self.estado_extra["terminado"] = True
        if motivo:
            self.estado_extra["motivo_termino"] = str(motivo)


    def serializar(self) -> Dict[str, object]:
        dados = super().serializar()
        dados["tipo"] = "entidade_projetil"
        dados["tipo_projetil"] = str(self.estado_extra.get("tipo_projetil", "item"))
        dados["subtipo"] = str(self.estado_extra.get("nome_item", "item"))
        dados["item_base_id"] = str(self.estado_extra.get("item_base_id", ""))
        dados["dono_id"] = int(self.estado_extra.get("dono_id", 0) or 0)
        dados["token_arremesso"] = str(self.estado_extra.get("token_arremesso", ""))
        return dados
