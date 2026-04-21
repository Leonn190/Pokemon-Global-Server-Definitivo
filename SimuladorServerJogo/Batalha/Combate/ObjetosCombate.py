from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from SimuladorServerJogo.Batalha.Combate.MotorFisica import Vetor2, como_vetor2, comprimento_quadrado, normalizar, somar, multiplicar


@dataclass(slots=True)
class CorpoCombate:
    id: str
    tipo: str = "pokemon"
    lado: str | None = None
    posicao: Vetor2 = field(default_factory=lambda: Vetor2(0.0, 0.0))
    posicao_anterior: Vetor2 = field(default_factory=lambda: Vetor2(0.0, 0.0))
    velocidade: Vetor2 = field(default_factory=lambda: Vetor2(0.0, 0.0))
    aceleracao: Vetor2 = field(default_factory=lambda: Vetor2(0.0, 0.0))
    raio: float = 0.5
    massa: float = 1.0
    movel: bool = True
    dados: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ObjetoCombateAtivo:
    id: str
    ataque_id: str = ""
    forma: str = ""
    dono_id: str = ""
    lado: str | None = None
    posicao: Vetor2 = field(default_factory=lambda: Vetor2(0.0, 0.0))
    posicao_anterior: Vetor2 = field(default_factory=lambda: Vetor2(0.0, 0.0))
    direcao: Vetor2 = field(default_factory=lambda: Vetor2(1.0, 0.0))
    velocidade: Vetor2 = field(default_factory=lambda: Vetor2(0.0, 0.0))
    aceleracao: Vetor2 = field(default_factory=lambda: Vetor2(0.0, 0.0))
    raio: float = 0.2
    largura: float = 0.0
    alcance_restante: float = 0.0
    duracao_ticks: int = 1
    ticks_vividos: int = 0
    ricochetes_paredes: int = 0
    ricochetes_pokemons: int = 0
    atravessa_paredes: bool = False
    atravessa_pokemons: bool = False
    atinge: str = "inimigos"
    alvos_atingidos: set[str] = field(default_factory=set)
    dados: dict[str, Any] = field(default_factory=dict)
    vivo: bool = True

    def avancar(self, dt_ticks: float = 1.0) -> None:
        if not self.vivo:
            return
        dt = float(dt_ticks)
        self.posicao_anterior = self.posicao
        deslocamento = somar(multiplicar(self.velocidade, dt), multiplicar(self.aceleracao, 0.5 * dt * dt))
        self.posicao = somar(self.posicao, deslocamento)
        self.velocidade = somar(self.velocidade, multiplicar(self.aceleracao, dt))
        self.ticks_vividos += 1

        mov = self.dados.get("desaceleracao")
        if mov:
            fator = max(0.0, 1.0 - float(mov) * dt)
            self.velocidade = multiplicar(self.velocidade, fator)

        dist = (comprimento_quadrado(deslocamento)) ** 0.5
        if self.alcance_restante > 0.0:
            self.alcance_restante = max(0.0, self.alcance_restante - dist)
        if self.duracao_ticks > 0 and self.ticks_vividos >= self.duracao_ticks:
            self.marcar_morto()
        if self.alcance_restante == 0.0 and self.dados.get("encerrar_ao_fim_alcance", True):
            self.marcar_morto()

    def marcar_morto(self) -> None:
        self.vivo = False

    def pode_atingir(self, corpo: CorpoCombate) -> bool:
        if not self.vivo or corpo.id == self.dono_id:
            return False
        if self.atinge in {"todos", "qualquer"}:
            return True
        if self.atinge == "aliados":
            return self.lado is not None and corpo.lado == self.lado
        if self.atinge == "inimigos":
            return self.lado is None or corpo.lado != self.lado
        if self.atinge == "usuario":
            return corpo.id == self.dono_id
        return True

    def ja_atingiu(self, corpo_id: str) -> bool:
        return str(corpo_id) in self.alvos_atingidos

    def registrar_alvo(self, corpo_id: str) -> None:
        self.alvos_atingidos.add(str(corpo_id))


@dataclass(slots=True)
class EventoColisao:
    tipo: str
    objeto_id: str
    alvo_id: str | None
    ponto: Vetor2
    normal: Vetor2
    distancia: float
    velocidade_relativa: float
    massa_objeto: float
    massa_alvo: float
    impulso_estimado: float
    dados: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ResultadoForma:
    eventos: list[EventoColisao] = field(default_factory=list)
    objetos_criados: list[ObjetoCombateAtivo] = field(default_factory=list)
    impactos: list[dict[str, Any]] = field(default_factory=list)
    dados: dict[str, Any] = field(default_factory=dict)


def _obter_attr(objeto, nome: str, padrao=None):
    if objeto is None:
        return padrao
    if isinstance(objeto, dict):
        return objeto.get(nome, padrao)
    return getattr(objeto, nome, padrao)


def _uid_pokemon(pokemon) -> str:
    uid = str(_obter_attr(pokemon, "Uid", "") or "")
    if uid:
        return uid
    uid = str(_obter_attr(pokemon, "Id", "") or "")
    if uid:
        return uid
    dados = _obter_attr(pokemon, "Dados", {})
    if isinstance(dados, dict):
        uid = str(dados.get("uid") or "")
        if uid:
            return uid
    return f"pokemon:temp:{id(pokemon)}"


def _massa_fallback(raio: float) -> float:
    return max(0.25, float(raio) * float(raio) * 3.0)


def criar_corpo_de_pokemon(pokemon) -> CorpoCombate:
    pos = _obter_attr(pokemon, "Posicao", (0.0, 0.0))
    vel = _obter_attr(pokemon, "Velocidade", (0.0, 0.0))
    raio = _obter_attr(pokemon, "RaioColisao", None)
    if raio is None:
        diam = _obter_attr(pokemon, "DiametroTiles", None)
        raio = float(diam) * 0.5 if diam is not None else 0.5
    peso = _obter_attr(pokemon, "Massa", None)
    if peso is None:
        peso = _obter_attr(pokemon, "Peso", None)
    if peso is None:
        dados = _obter_attr(pokemon, "Dados", {})
        if isinstance(dados, dict):
            peso = dados.get("Peso")
    massa = float(peso) if isinstance(peso, (int, float)) else _massa_fallback(float(raio))
    return CorpoCombate(
        id=_uid_pokemon(pokemon),
        tipo="pokemon",
        lado=str(_obter_attr(pokemon, "Lado", "") or "") or None,
        posicao=como_vetor2(pos),
        posicao_anterior=como_vetor2(pos),
        velocidade=como_vetor2(vel),
        aceleracao=Vetor2(0.0, 0.0),
        raio=max(0.05, float(raio)),
        massa=max(0.1, float(massa)),
        movel=True,
        dados={"origem_objeto": pokemon},
    )


def criar_corpos_de_pokemons(pokemons) -> list[CorpoCombate]:
    return [criar_corpo_de_pokemon(p) for p in list(pokemons or [])]
