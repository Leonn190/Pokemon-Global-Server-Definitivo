from __future__ import annotations

from SimuladorServerJogo.Batalha.Combate.DebugCombate import dbg_combate
from SimuladorServerJogo.Batalha.Combate.MotorFisica import (
    Vetor2,
    colisao_circulo_arena,
    como_vetor2,
    distancia,
    dot,
    estimar_impulso_colisao,
    normal_colisao_circulo,
    ponto_em_capsula,
    ponto_em_cone,
    ponto_em_trapezio,
    varredura_circulo_vs_circulo,
)
from SimuladorServerJogo.Batalha.Combate.ObjetosCombate import CorpoCombate, EventoColisao, ObjetoCombateAtivo


class DetectorColisoes:
    def __init__(self, arena=None):
        self.arena = arena

    def detectar_objeto(self, objeto: ObjetoCombateAtivo, corpos: list[CorpoCombate], arena=None) -> list[EventoColisao]:
        forma = (objeto.forma or "").strip()
        if forma in {"projetil", "projetil_explosivo", "dash", "impulso"}:
            return self.detectar_projetil(objeto, corpos, arena=arena)
        if forma in {"laser", "corredor", "linha"}:
            return self.detectar_corredor(objeto, corpos)
        return []

    def detectar_projetil(self, objeto: ObjetoCombateAtivo, corpos: list[CorpoCombate], arena=None) -> list[EventoColisao]:
        eventos: list[EventoColisao] = []
        ar = self.arena if arena is None else arena
        inicio = como_vetor2(objeto.posicao_anterior)
        fim = como_vetor2(objeto.posicao)

        colidiu_parede, normal_parede, lado = colisao_circulo_arena(fim, objeto.raio, ar)
        if colidiu_parede and normal_parede is not None:
            vel_rel = dot(objeto.velocidade, normal_parede)
            eventos.append(
                EventoColisao(
                    tipo="parede",
                    objeto_id=objeto.id,
                    alvo_id=None,
                    ponto=fim,
                    normal=normal_parede,
                    distancia=distancia(inicio, fim),
                    velocidade_relativa=abs(vel_rel),
                    massa_objeto=float(objeto.dados.get("massa", 1.0)),
                    massa_alvo=10_000_000.0,
                    impulso_estimado=abs(vel_rel) * float(objeto.dados.get("massa", 1.0)),
                    dados={"lado": lado},
                )
            )

        for alvo in list(corpos or []):
            if not objeto.pode_atingir(alvo) or objeto.ja_atingiu(alvo.id):
                continue
            colidiu, t_hit, normal = varredura_circulo_vs_circulo(inicio, fim, objeto.raio, alvo.posicao, alvo.raio)
            if not colidiu:
                continue
            ponto = Vetor2(inicio.x + (fim.x - inicio.x) * t_hit, inicio.y + (fim.y - inicio.y) * t_hit)
            vel_rel_vec = (objeto.velocidade.x - alvo.velocidade.x, objeto.velocidade.y - alvo.velocidade.y)
            impulso = estimar_impulso_colisao(vel_rel_vec, float(objeto.dados.get("massa", 1.0)), alvo.massa, normal)
            eventos.append(
                EventoColisao(
                    tipo="pokemon" if alvo.tipo == "pokemon" else "objeto",
                    objeto_id=objeto.id,
                    alvo_id=alvo.id,
                    ponto=ponto,
                    normal=normal,
                    distancia=distancia(inicio, ponto),
                    velocidade_relativa=abs(dot(vel_rel_vec, normal)),
                    massa_objeto=float(objeto.dados.get("massa", 1.0)),
                    massa_alvo=alvo.massa,
                    impulso_estimado=impulso,
                    dados={"tempo_colisao": t_hit, "alvo_tipo": alvo.tipo},
                )
            )

        eventos.sort(key=lambda e: (e.distancia, e.alvo_id or "", e.tipo))
        dbg_combate("DetectorColisoes", "colisoes detectadas", quantidade=len(eventos))
        if objeto.atravessa_pokemons:
            return eventos
        for evento in eventos:
            if evento.tipo in {"pokemon", "objeto"}:
                return [evento]
            if evento.tipo == "parede" and not objeto.atravessa_paredes:
                return [evento]
        return eventos

    def detectar_corredor(self, objeto: ObjetoCombateAtivo, corpos: list[CorpoCombate]) -> list[EventoColisao]:
        origem = como_vetor2(objeto.posicao_anterior)
        fim = como_vetor2(objeto.posicao)
        raio_capsula = max(0.0, float(objeto.largura) * 0.5)
        eventos: list[EventoColisao] = []
        for alvo in list(corpos or []):
            if not objeto.pode_atingir(alvo):
                continue
            if not ponto_em_capsula(alvo.posicao, origem, fim, raio_capsula + alvo.raio):
                continue
            n = normal_colisao_circulo(origem, alvo.posicao)
            eventos.append(
                EventoColisao(
                    tipo="pokemon" if alvo.tipo == "pokemon" else "objeto",
                    objeto_id=objeto.id,
                    alvo_id=alvo.id,
                    ponto=como_vetor2(alvo.posicao),
                    normal=n,
                    distancia=distancia(origem, alvo.posicao),
                    velocidade_relativa=abs(dot(objeto.velocidade, n)),
                    massa_objeto=float(objeto.dados.get("massa", 1.0)),
                    massa_alvo=alvo.massa,
                    impulso_estimado=estimar_impulso_colisao(objeto.velocidade, float(objeto.dados.get("massa", 1.0)), alvo.massa, n),
                    dados={"forma": "corredor"},
                )
            )
        eventos.sort(key=lambda e: (e.distancia, e.alvo_id or ""))
        return eventos

    def detectar_cone(self, origem, direcao, alcance: float, angulo: float, corpos: list[CorpoCombate], objeto_id: str = "cone") -> list[EventoColisao]:
        eventos: list[EventoColisao] = []
        for alvo in list(corpos or []):
            if ponto_em_cone(alvo.posicao, origem, direcao, alcance + alvo.raio, angulo):
                n = normal_colisao_circulo(origem, alvo.posicao)
                eventos.append(
                    EventoColisao(
                        tipo="pokemon" if alvo.tipo == "pokemon" else "objeto",
                        objeto_id=objeto_id,
                        alvo_id=alvo.id,
                        ponto=como_vetor2(alvo.posicao),
                        normal=n,
                        distancia=distancia(origem, alvo.posicao),
                        velocidade_relativa=0.0,
                        massa_objeto=0.0,
                        massa_alvo=alvo.massa,
                        impulso_estimado=0.0,
                        dados={"forma": "cone"},
                    )
                )
        eventos.sort(key=lambda e: (e.distancia, e.alvo_id or ""))
        return eventos

    def detectar_cone_invertido(self, origem, direcao, alcance: float, largura_base: float, largura_topo: float, corpos: list[CorpoCombate], objeto_id: str = "cone_invertido") -> list[EventoColisao]:
        eventos: list[EventoColisao] = []
        for alvo in list(corpos or []):
            if ponto_em_trapezio(alvo.posicao, origem, direcao, alcance, largura_base + alvo.raio * 2.0, largura_topo + alvo.raio * 2.0):
                n = normal_colisao_circulo(origem, alvo.posicao)
                eventos.append(
                    EventoColisao(
                        tipo="pokemon" if alvo.tipo == "pokemon" else "objeto",
                        objeto_id=objeto_id,
                        alvo_id=alvo.id,
                        ponto=como_vetor2(alvo.posicao),
                        normal=n,
                        distancia=distancia(origem, alvo.posicao),
                        velocidade_relativa=0.0,
                        massa_objeto=0.0,
                        massa_alvo=alvo.massa,
                        impulso_estimado=0.0,
                        dados={"forma": "cone_invertido"},
                    )
                )
        eventos.sort(key=lambda e: (e.distancia, e.alvo_id or ""))
        return eventos

    def detectar_area_circular(self, centro, raio: float, corpos: list[CorpoCombate], objeto_id: str = "area") -> list[EventoColisao]:
        eventos: list[EventoColisao] = []
        for alvo in list(corpos or []):
            if distancia(centro, alvo.posicao) <= float(raio) + alvo.raio:
                n = normal_colisao_circulo(centro, alvo.posicao)
                eventos.append(
                    EventoColisao(
                        tipo="pokemon" if alvo.tipo == "pokemon" else "objeto",
                        objeto_id=objeto_id,
                        alvo_id=alvo.id,
                        ponto=como_vetor2(alvo.posicao),
                        normal=n,
                        distancia=distancia(centro, alvo.posicao),
                        velocidade_relativa=0.0,
                        massa_objeto=0.0,
                        massa_alvo=alvo.massa,
                        impulso_estimado=0.0,
                        dados={"forma": "area"},
                    )
                )
        eventos.sort(key=lambda e: (e.distancia, e.alvo_id or ""))
        return eventos

    def detectar_alvo_por_alcance(self, origem, alvo: CorpoCombate, alcance: float, objeto_id: str = "alvo") -> list[EventoColisao]:
        d = distancia(origem, alvo.posicao)
        if d > float(alcance) + alvo.raio:
            return []
        return [
            EventoColisao(
                tipo="pokemon" if alvo.tipo == "pokemon" else "objeto",
                objeto_id=objeto_id,
                alvo_id=alvo.id,
                ponto=como_vetor2(alvo.posicao),
                normal=normal_colisao_circulo(origem, alvo.posicao),
                distancia=d,
                velocidade_relativa=0.0,
                massa_objeto=0.0,
                massa_alvo=alvo.massa,
                impulso_estimado=0.0,
                dados={"forma": "alvo", "no_alcance": True},
            )
        ]
