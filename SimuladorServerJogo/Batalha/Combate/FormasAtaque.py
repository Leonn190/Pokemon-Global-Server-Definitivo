from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from SimuladorServerJogo.Batalha.Combate.DetectorColisoes import DetectorColisoes
from SimuladorServerJogo.Batalha.Combate.MotorFisica import (
    Vetor2,
    como_vetor2,
    comprimento,
    multiplicar,
    normalizar,
    refletir_vetor,
    resolver_impulso_colisao,
    somar,
    subtrair,
)
from SimuladorServerJogo.Batalha.Combate.ObjetosCombate import (
    CorpoCombate,
    ObjetoCombateAtivo,
    ResultadoForma,
    criar_corpo_de_pokemon,
)


class ResolvedorFormasAtaque:
    def __init__(self, detector=None):
        self.detector = detector or DetectorColisoes()

    def resolver(self, ataque_spec, jogada, executor, corpos, contexto=None) -> ResultadoForma:
        spec = _spec_para_dict(ataque_spec)
        jog = jogada if isinstance(jogada, dict) else {}
        execucao = spec.get("execucao") if isinstance(spec.get("execucao"), dict) else {}
        forma = str(jog.get("forma") or execucao.get("forma") or "").strip()

        corpo_executor = criar_corpo_de_pokemon(executor)
        lista_corpos = [c for c in list(corpos or []) if c.id != corpo_executor.id]

        if forma == "self":
            return self._resolver_self(corpo_executor, spec, jog)
        if forma == "alvo":
            return self._resolver_alvo(corpo_executor, lista_corpos, spec, jog)
        if forma == "impulso":
            return self._resolver_impulso(corpo_executor, lista_corpos, spec, jog)
        if forma == "dash":
            return self._resolver_dash(corpo_executor, lista_corpos, spec, jog)
        if forma == "projetil":
            return self._resolver_projetil(corpo_executor, lista_corpos, spec, jog)
        if forma == "projetil_explosivo":
            return self._resolver_projetil_explosivo(corpo_executor, lista_corpos, spec, jog)
        if forma == "cone":
            return self._resolver_cone(corpo_executor, lista_corpos, spec, jog)
        if forma == "cone_invertido":
            return self._resolver_cone_invertido(corpo_executor, lista_corpos, spec, jog)
        if forma == "area":
            return self._resolver_area(corpo_executor, lista_corpos, spec, jog)
        if forma == "laser":
            return self._resolver_laser(corpo_executor, lista_corpos, spec, jog)

        return ResultadoForma(dados={"erro": "forma_nao_suportada", "forma": forma, "contexto": contexto or {}})

    def _resolver_self(self, executor: CorpoCombate, spec: dict[str, Any], jogada: dict[str, Any]) -> ResultadoForma:
        return ResultadoForma(impactos=[{"tipo": "self", "executor_id": executor.id, "ataque_id": _ataque_id(spec, jogada)}])

    def _resolver_alvo(self, executor: CorpoCombate, corpos: list[CorpoCombate], spec: dict[str, Any], jogada: dict[str, Any]) -> ResultadoForma:
        alcance = _spec_num(spec, "execucao", "alcance", 1.0)
        alvo_ids = set(str(v) for v in list(jogada.get("alvo_ids") or []))
        eventos = []
        for corpo in corpos:
            if alvo_ids and corpo.id not in alvo_ids:
                continue
            eventos.extend(self.detector.detectar_alvo_por_alcance(executor.posicao, corpo, alcance, objeto_id=executor.id))
        impactos = [{"tipo": "alvo", "alvo_id": e.alvo_id, "distancia": e.distancia} for e in eventos]
        return ResultadoForma(eventos=eventos, impactos=impactos)

    def _resolver_impulso(self, executor: CorpoCombate, corpos: list[CorpoCombate], spec: dict[str, Any], jogada: dict[str, Any]) -> ResultadoForma:
        obj = _objeto_movimento(executor, spec, jogada, forma="impulso", desacelerar=True)
        eventos = self.detector.detectar_projetil(obj, corpos)

        for evento in eventos:
            if evento.tipo == "parede":
                vel_refletida = refletir_vetor(obj.velocidade, evento.normal)
                evento.dados["velocidade_executor_pos"] = (vel_refletida.x, vel_refletida.y)
                evento.dados["ricochete"] = "parede"
                continue
            if evento.alvo_id is None:
                continue
            alvo = next((c for c in corpos if c.id == evento.alvo_id), None)
            if alvo is None:
                continue
            nova_vel_exec, nova_vel_alvo = resolver_impulso_colisao(
                obj.velocidade,
                executor.massa,
                alvo.velocidade,
                alvo.massa,
                evento.normal,
                restituicao=0.35,
            )
            evento.dados["velocidade_executor_pos"] = (nova_vel_exec.x, nova_vel_exec.y)
            evento.dados["velocidade_alvo_pos"] = (nova_vel_alvo.x, nova_vel_alvo.y)

        return ResultadoForma(eventos=eventos, objetos_criados=[obj], impactos=[{"tipo": "impulso", "evento": e.tipo, "alvo": e.alvo_id} for e in eventos])

    def _resolver_dash(self, executor: CorpoCombate, corpos: list[CorpoCombate], spec: dict[str, Any], jogada: dict[str, Any]) -> ResultadoForma:
        obj = _objeto_movimento(executor, spec, jogada, forma="dash", desacelerar=False)
        eventos = self.detector.detectar_projetil(obj, corpos)
        for evento in eventos:
            if evento.tipo == "parede":
                vel_refletida = refletir_vetor(obj.velocidade, evento.normal)
                evento.dados["velocidade_executor_pos"] = (vel_refletida.x, vel_refletida.y)
                evento.dados["ricochete"] = "parede"
        return ResultadoForma(eventos=eventos, objetos_criados=[obj], impactos=[{"tipo": "dash", "alvo": e.alvo_id} for e in eventos])

    def _resolver_projetil(self, executor: CorpoCombate, corpos: list[CorpoCombate], spec: dict[str, Any], jogada: dict[str, Any]) -> ResultadoForma:
        obj = _objeto_projetil(executor, spec, jogada)
        eventos = self.detector.detectar_projetil(obj, corpos)
        if eventos:
            primeiro = eventos[0]
            if primeiro.tipo == "parede" and obj.ricochetes_paredes > 0:
                obj.velocidade = refletir_vetor(obj.velocidade, primeiro.normal)
                obj.ricochetes_paredes -= 1
                primeiro.dados["ricochete"] = "parede"
            elif primeiro.tipo in {"pokemon", "objeto"} and obj.ricochetes_pokemons > 0:
                obj.velocidade = refletir_vetor(obj.velocidade, primeiro.normal)
                obj.ricochetes_pokemons -= 1
                primeiro.dados["ricochete"] = "pokemon"
            elif not obj.atravessa_pokemons:
                obj.marcar_morto()
        return ResultadoForma(eventos=eventos, objetos_criados=[obj], impactos=[{"tipo": "projetil", "alvo": e.alvo_id} for e in eventos])

    def _resolver_projetil_explosivo(self, executor: CorpoCombate, corpos: list[CorpoCombate], spec: dict[str, Any], jogada: dict[str, Any]) -> ResultadoForma:
        base = self._resolver_projetil(executor, corpos, spec, jogada)
        if not base.eventos:
            return base
        raio_explosao = _spec_num_multi(spec, "execucao", ("raio_explosao", "raio_area", "explosao_raio", "raio"), 1.0)
        centro = base.eventos[0].ponto
        eventos_area = self.detector.detectar_area_circular(centro, raio_explosao, corpos, objeto_id=f"{executor.id}:explosao")
        base.eventos.extend(eventos_area)
        base.impactos.append({"tipo": "explosao", "centro": (centro.x, centro.y), "raio": raio_explosao, "alvos": [e.alvo_id for e in eventos_area]})
        return base

    def _resolver_cone(self, executor: CorpoCombate, corpos: list[CorpoCombate], spec: dict[str, Any], jogada: dict[str, Any]) -> ResultadoForma:
        origem, direcao = _origem_direcao(executor, jogada)
        alcance = _spec_num(spec, "execucao", "alcance", 1.0)
        angulo = _spec_num(spec, "execucao", "angulo", 60.0)
        eventos = self.detector.detectar_cone(origem, direcao, alcance, angulo, corpos, objeto_id=executor.id)
        return ResultadoForma(eventos=eventos, impactos=[{"tipo": "cone", "alvo": e.alvo_id} for e in eventos])

    def _resolver_cone_invertido(self, executor: CorpoCombate, corpos: list[CorpoCombate], spec: dict[str, Any], jogada: dict[str, Any]) -> ResultadoForma:
        origem, direcao = _origem_direcao(executor, jogada)
        alcance = _spec_num(spec, "execucao", "alcance", 1.0)
        largura_base = _spec_num(spec, "execucao", "largura", executor.raio * 2.0)
        largura_topo = _spec_num(spec, "execucao", "largura_topo", executor.raio)
        eventos = self.detector.detectar_cone_invertido(origem, direcao, alcance, largura_base, largura_topo, corpos, objeto_id=executor.id)
        return ResultadoForma(eventos=eventos, impactos=[{"tipo": "cone_invertido", "alvo": e.alvo_id} for e in eventos])

    def _resolver_area(self, executor: CorpoCombate, corpos: list[CorpoCombate], spec: dict[str, Any], jogada: dict[str, Any]) -> ResultadoForma:
        centro = como_vetor2(jogada.get("destino_mundo", executor.posicao))
        raio = _spec_num(spec, "execucao", "raio", 1.0)
        eventos = self.detector.detectar_area_circular(centro, raio, corpos, objeto_id=executor.id)
        return ResultadoForma(eventos=eventos, impactos=[{"tipo": "area", "alvo": e.alvo_id} for e in eventos])

    def _resolver_laser(self, executor: CorpoCombate, corpos: list[CorpoCombate], spec: dict[str, Any], jogada: dict[str, Any]) -> ResultadoForma:
        origem, direcao = _origem_direcao(executor, jogada)
        alcance = _spec_num(spec, "execucao", "alcance", 5.0)
        largura = _spec_num(spec, "execucao", "largura", executor.raio)
        fim = somar(origem, multiplicar(normalizar(direcao), alcance))
        laser = ObjetoCombateAtivo(
            id=f"laser:{executor.id}:{_ataque_id(spec, jogada)}",
            ataque_id=_ataque_id(spec, jogada),
            forma="laser",
            dono_id=executor.id,
            lado=executor.lado,
            posicao=fim,
            posicao_anterior=origem,
            direcao=normalizar(direcao),
            velocidade=Vetor2(0.0, 0.0),
            raio=0.0,
            largura=largura,
            alcance_restante=0.0,
            duracao_ticks=1,
            atinge=str(_spec_texto(spec, "execucao", "atinge", "inimigos")),
            dados={"massa": 0.0},
        )
        eventos = self.detector.detectar_corredor(laser, corpos)
        return ResultadoForma(eventos=eventos, objetos_criados=[laser], impactos=[{"tipo": "laser", "ordem_alvos": [e.alvo_id for e in eventos]}])


def _spec_para_dict(ataque_spec) -> dict[str, Any]:
    if isinstance(ataque_spec, dict):
        return dict(ataque_spec)
    if is_dataclass(ataque_spec):
        return asdict(ataque_spec)
    bruto = getattr(ataque_spec, "bruto", None)
    if isinstance(bruto, dict):
        return dict(bruto)
    return {}


def _spec_num(spec: dict[str, Any], secao: str, chave: str, padrao: float) -> float:
    bloco = spec.get(secao) if isinstance(spec.get(secao), dict) else {}
    val = bloco.get(chave, padrao)
    try:
        return float(val)
    except (TypeError, ValueError):
        return float(padrao)


def _spec_texto(spec: dict[str, Any], secao: str, chave: str, padrao: str) -> str:
    bloco = spec.get(secao) if isinstance(spec.get(secao), dict) else {}
    return str(bloco.get(chave, padrao) or padrao)


def _spec_num_multi(spec: dict[str, Any], secao: str, chaves: tuple[str, ...], padrao: float) -> float:
    bloco = spec.get(secao) if isinstance(spec.get(secao), dict) else {}
    for chave in chaves:
        if chave not in bloco:
            continue
        try:
            return float(bloco.get(chave))
        except (TypeError, ValueError):
            continue
    return float(padrao)


def _ataque_id(spec: dict[str, Any], jogada: dict[str, Any]) -> str:
    return str(jogada.get("ataque_id") or spec.get("id") or "")


def _origem_direcao(executor: CorpoCombate, jogada: dict[str, Any]) -> tuple[Vetor2, Vetor2]:
    origem = como_vetor2(jogada.get("origem_mundo", executor.posicao))
    destino = como_vetor2(jogada.get("destino_mundo", origem))
    direcao = subtrair(destino, origem)
    if comprimento(direcao) <= 1e-8:
        direcao = executor.velocidade if comprimento(executor.velocidade) > 1e-8 else Vetor2(1.0, 0.0)
    return origem, normalizar(direcao)


def _objeto_movimento(executor: CorpoCombate, spec: dict[str, Any], jogada: dict[str, Any], forma: str, desacelerar: bool) -> ObjetoCombateAtivo:
    origem, direcao = _origem_direcao(executor, jogada)
    alcance = _spec_num(spec, "execucao", "alcance", 1.5)
    intensidade = float(jogada.get("intensidade") or 1.0)
    vel_pct = _spec_num(spec, "execucao", "velocidade_pct", 1.0)
    speed = max(0.0, vel_pct * intensidade)
    deslocamento = multiplicar(direcao, alcance)

    obj = ObjetoCombateAtivo(
        id=f"{forma}:{executor.id}:{_ataque_id(spec, jogada)}",
        ataque_id=_ataque_id(spec, jogada),
        forma=forma,
        dono_id=executor.id,
        lado=executor.lado,
        posicao=somar(origem, deslocamento),
        posicao_anterior=origem,
        direcao=direcao,
        velocidade=multiplicar(direcao, speed),
        aceleracao=Vetor2(0.0, 0.0),
        raio=executor.raio,
        alcance_restante=alcance,
        duracao_ticks=1,
        atinge="inimigos",
        dados={"massa": executor.massa, "desaceleracao": _spec_num(spec, "execucao", "desaceleracao", 0.35) if desacelerar else 0.0},
    )
    return obj


def _objeto_projetil(executor: CorpoCombate, spec: dict[str, Any], jogada: dict[str, Any]) -> ObjetoCombateAtivo:
    origem, direcao = _origem_direcao(executor, jogada)
    alcance = _spec_num(spec, "execucao", "alcance", 5.0)
    velocidade_tiles_tick = _spec_num(spec, "execucao", "velocidade_tiles_tick", 1.0)
    raio = _spec_num(spec, "execucao", "raio", 0.2)
    fim = somar(origem, multiplicar(direcao, min(alcance, velocidade_tiles_tick)))
    return ObjetoCombateAtivo(
        id=f"projetil:{executor.id}:{_ataque_id(spec, jogada)}",
        ataque_id=_ataque_id(spec, jogada),
        forma=str(_spec_texto(spec, "execucao", "forma", "projetil")),
        dono_id=executor.id,
        lado=executor.lado,
        posicao=fim,
        posicao_anterior=origem,
        direcao=direcao,
        velocidade=multiplicar(direcao, velocidade_tiles_tick),
        raio=raio,
        alcance_restante=alcance,
        duracao_ticks=1,
        ricochetes_paredes=int(_spec_num(spec, "execucao", "ricochetes_paredes", 0)),
        ricochetes_pokemons=int(_spec_num(spec, "execucao", "ricochetes_pokemons", 0)),
        atravessa_paredes=bool(spec.get("execucao", {}).get("atravessa_paredes") or False),
        atravessa_pokemons=bool(spec.get("execucao", {}).get("atravessa_pokemons") or False),
        atinge=str(_spec_texto(spec, "execucao", "atinge", "inimigos")),
        dados={"massa": max(0.1, raio * raio), "encerrar_ao_fim_alcance": False},
    )
