from __future__ import annotations

import math
from typing import Dict, Iterable, List, Tuple

from SimuladorServerJogo.Batalha.ObjetoBatalha import ObjetoBatalha

Vec2 = Tuple[float, float]


class DetectorColisoes:
    EPS = 1e-4

    def __init__(self, fisica) -> None:
        self._fisica = fisica

    def _vec(self, valor, default=(0.0, 0.0)) -> Vec2:
        return self._fisica._vec(valor, default)

    def _normalizar(self, valor: Vec2) -> Vec2:
        return self._fisica._normalizar(valor)

    def _somar(self, a: Vec2, b: Vec2) -> Vec2:
        return self._fisica._somar(a, b)

    def _sub(self, a: Vec2, b: Vec2) -> Vec2:
        return self._fisica._sub(a, b)

    def _mul(self, a: Vec2, s: float) -> Vec2:
        return self._fisica._mul(a, s)

    def _dot(self, a: Vec2, b: Vec2) -> float:
        return self._fisica._dot(a, b)

    def _dist(self, a: Vec2, b: Vec2) -> float:
        return self._fisica._dist(a, b)

    def _fnum(self, valor, padrao=0.0) -> float:
        return self._fisica._fnum(valor, padrao)

    def detectar_colisoes_pokemon_pokemon(self, pokemon, origem: Vec2, destino: Vec2, *, ignorar_ids: Iterable[str] | None = None) -> List[Dict[str, object]]:
        eventos: List[Dict[str, object]] = []
        ignorados = {str(valor) for valor in list(ignorar_ids or []) if str(valor)}
        for outro in self._fisica._sistema.listar_pokemons():
            if outro is pokemon or outro.ForaDeCombate or str(outro.Uid) in ignorados:
                continue
            interseccao = self._fisica._interseccao_segmento_circulo(origem, destino, outro.Posicao, float(pokemon.RaioColisao) + float(outro.RaioColisao))
            if interseccao is None:
                continue
            eventos.append(
                {
                    "tipo": "pokemon_pokemon",
                    "a": pokemon,
                    "b": outro,
                    "outro": outro,
                    "normal": interseccao.get("normal"),
                    "ponto": interseccao.get("ponto"),
                    "interseccao": interseccao,
                    "penetracao": max(0.0, (float(pokemon.RaioColisao) + float(outro.RaioColisao)) - self._dist(pokemon.Posicao, outro.Posicao)),
                }
            )
        return eventos

    def detectar_colisoes_pokemon_campo(self, pokemon) -> List[Dict[str, object]]:
        posicao, normal = self._fisica.limitar_ao_campo(pokemon.Posicao, raio=pokemon.RaioColisao)
        pokemon.Posicao = posicao
        if abs(normal[0]) <= 1e-9 and abs(normal[1]) <= 1e-9:
            return []
        return [{"tipo": "pokemon_campo", "normal": normal, "ponto": posicao, "bloqueante": True, "ricocheteavel": False}]

    def detectar_colisoes_pokemon_objetos(self, pokemon) -> List[Dict[str, object]]:
        eventos = []
        for objeto in self._fisica.objetos_estaticos():
            centro = self._vec(objeto.get("posicao"))
            raio = self._fnum(objeto.get("raio"), 0.6)
            if not self._fisica.circulos_colidem(pokemon.Posicao, pokemon.RaioColisao, centro, raio):
                continue
            delta = self._sub(pokemon.Posicao, centro)
            normal = self._normalizar(delta if self._dist(pokemon.Posicao, centro) > 1e-9 else (1.0, 0.0))
            penetracao = (float(pokemon.RaioColisao) + float(raio)) - self._dist(pokemon.Posicao, centro)
            eventos.append(
                {
                    "tipo": "pokemon_objeto",
                    "objeto_id": objeto.get("id"),
                    "normal": normal,
                    "penetracao": max(0.0, penetracao),
                    "alvo": objeto,
                    "bloqueante": True,
                    "ricocheteavel": False,
                }
            )
        return eventos

    def _interseccao_segmento_circulo(self, inicio: Vec2, direcao: Vec2, dist_max: float, centro: Vec2, raio: float):
        fim = self._somar(inicio, self._mul(direcao, dist_max))
        hit = self._fisica._interseccao_segmento_circulo(inicio, fim, centro, raio)
        if not hit:
            return None
        t = float(hit.get("t", 0.0))
        return {
            "distancia": max(0.0, min(dist_max, dist_max * t)),
            "ponto": self._vec(hit.get("ponto"), inicio),
            "normal": self._normalizar(self._vec(hit.get("normal"), (1.0, 0.0))),
        }

    def _colisao_projetil_campo(self, origem: Vec2, direcao: Vec2, dist_max: float, raio: float):
        x0, y0, x1, y1 = self._fisica.limites_fluxo()
        min_x = float(x0) + float(raio)
        min_y = float(y0) + float(raio)
        max_x = float(x1) - float(raio)
        max_y = float(y1) - float(raio)
        candidatos = []
        dx, dy = float(direcao[0]), float(direcao[1])
        if abs(dx) > 1e-9:
            if dx > 0:
                t = (max_x - float(origem[0])) / dx
                candidatos.append((t, (-1.0, 0.0)))
            else:
                t = (min_x - float(origem[0])) / dx
                candidatos.append((t, (1.0, 0.0)))
        if abs(dy) > 1e-9:
            if dy > 0:
                t = (max_y - float(origem[1])) / dy
                candidatos.append((t, (0.0, -1.0)))
            else:
                t = (min_y - float(origem[1])) / dy
                candidatos.append((t, (0.0, 1.0)))
        melhor = None
        for t, normal in candidatos:
            if t < 0.0 or t > dist_max:
                continue
            ponto = self._somar(origem, self._mul(direcao, t))
            if ponto[0] < min_x - 1e-6 or ponto[0] > max_x + 1e-6 or ponto[1] < min_y - 1e-6 or ponto[1] > max_y + 1e-6:
                continue
            if melhor is None or t < melhor["distancia"]:
                melhor = {
                    "tipo": "projetil_campo",
                    "ponto": ponto,
                    "normal": normal,
                    "distancia": float(t),
                    "alvo": "arena",
                    "bloqueante": True,
                    "ricocheteavel": True,
                }
        return melhor

    def _colisao_projetil_pokemon(self, objeto: ObjetoBatalha, origem: Vec2, direcao: Vec2, dist_max: float, *, ignorar_ids: Iterable[str] | None = None):
        ignorados = {str(v) for v in list(ignorar_ids or []) if str(v)}
        melhor = None
        for pokemon in self._fisica._sistema.listar_pokemons():
            if pokemon is None or pokemon.ForaDeCombate:
                continue
            pokemon_id = str(getattr(pokemon, "Uid", ""))
            if pokemon_id in ignorados:
                continue
            if pokemon_id == str(objeto.DonoId) and not objeto.AtingeSiMesmo:
                continue
            if pokemon_id in objeto.AlvosAtingidos:
                continue
            hit = self._interseccao_segmento_circulo(origem, direcao, dist_max, self._vec(pokemon.Posicao), float(objeto.Raio) + float(getattr(pokemon, "RaioColisao", 0.0)))
            if not hit:
                continue
            if melhor is None or float(hit["distancia"]) < float(melhor["distancia"]):
                melhor = {
                    "tipo": "projetil_pokemon",
                    "ponto": hit["ponto"],
                    "normal": hit["normal"],
                    "distancia": float(hit["distancia"]),
                    "alvo": pokemon,
                    "alvo_id": pokemon_id,
                    "bloqueante": not bool(objeto.AtravessaPokemons),
                    "ricocheteavel": bool(objeto.Fluxo.get("ricocheteia_pokemons", False)),
                }
        return melhor

    def _colisao_projetil_objeto(self, objeto: ObjetoBatalha, origem: Vec2, direcao: Vec2, dist_max: float):
        melhor = None
        for estatico in self._fisica.objetos_estaticos():
            hit = self._interseccao_segmento_circulo(origem, direcao, dist_max, self._vec(estatico.get("posicao")), float(objeto.Raio) + self._fnum(estatico.get("raio"), 0.6))
            if not hit:
                continue
            if melhor is None or float(hit["distancia"]) < float(melhor["distancia"]):
                melhor = {
                    "tipo": "projetil_objeto",
                    "ponto": hit["ponto"],
                    "normal": hit["normal"],
                    "distancia": float(hit["distancia"]),
                    "alvo": estatico,
                    "alvo_id": str(estatico.get("id") or ""),
                    "bloqueante": not bool(objeto.AtravessaObjetos),
                    "ricocheteavel": bool(objeto.Fluxo.get("ricocheteia_objetos", objeto.Fluxo.get("ricocheteia_paredes", False))),
                }
        return melhor

    def detectar_colisao_projetil(self, objeto: ObjetoBatalha, origem: Vec2, direcao: Vec2, dist_max: float, *, ignorar_pokemon_ids: Iterable[str] | None = None):
        candidatos = [
            self._colisao_projetil_pokemon(objeto, origem, direcao, dist_max, ignorar_ids=ignorar_pokemon_ids),
            self._colisao_projetil_objeto(objeto, origem, direcao, dist_max),
            self._colisao_projetil_campo(origem, direcao, dist_max, float(objeto.Raio)),
        ]
        candidatos = [c for c in candidatos if isinstance(c, dict)]
        if not candidatos:
            return None
        return sorted(candidatos, key=lambda item: float(item.get("distancia", 1e9)))[0]

    def simular_projetil_tick(self, objeto: ObjetoBatalha) -> Dict[str, object]:
        objeto.avancar_tick()
        origem_inicial = self._vec(objeto.PosicaoAnterior)
        posicao = origem_inicial
        direcao = self._normalizar(self._vec(objeto.Direcao, (1.0, 0.0)))
        restante = max(0.0, float(objeto.VelocidadeTilesTick))
        ricochetes = int(objeto.RicochetesRestantes)
        ativo = bool(objeto.Ativo)
        eventos: List[Dict[str, object]] = []
        ignorar_tick: set[str] = set()

        max_iter = 8
        iteracao = 0
        while ativo and restante > self.EPS and iteracao < max_iter:
            iteracao += 1
            colisao = self.detectar_colisao_projetil(objeto, posicao, direcao, restante, ignorar_pokemon_ids=ignorar_tick)
            if colisao is None:
                posicao = self._somar(posicao, self._mul(direcao, restante))
                restante = 0.0
                break

            distancia = max(0.0, float(colisao.get("distancia") or 0.0))
            posicao = self._somar(posicao, self._mul(direcao, distancia))
            restante = max(0.0, restante - distancia)

            tipo = str(colisao.get("tipo") or "")
            tipo_evento = {
                "projetil_pokemon": "colisao_projetil_pokemon",
                "projetil_campo": "colisao_projetil_campo",
                "projetil_objeto": "colisao_projetil_objeto",
            }.get(tipo, "colisao_projetil")
            eventos.append({**colisao, "tipo_evento": tipo_evento})

            pode_ricochetear = bool(colisao.get("ricocheteavel")) and ricochetes > 0
            if pode_ricochetear:
                ricochetes = max(0, ricochetes - 1)
                direcao = self._fisica.refletir_vetor(direcao, self._vec(colisao.get("normal"), (1.0, 0.0)))
                posicao = self._somar(posicao, self._mul(direcao, self.EPS * 5.0))
                restante = max(0.0, restante - self.EPS * 5.0)
                ricochete_tipo = {
                    "projetil_pokemon": "ricochete_pokemon",
                    "projetil_campo": "ricochete_campo",
                    "projetil_objeto": "ricochete_objeto",
                }.get(tipo, "ricochete")
                eventos.append({**colisao, "tipo_evento": ricochete_tipo, "ricochetes_restantes": int(ricochetes)})
                if tipo == "projetil_pokemon":
                    ignorar_tick.add(str(colisao.get("alvo_id") or ""))
                continue

            if tipo == "projetil_pokemon" and bool(objeto.AtravessaPokemons):
                posicao = self._somar(posicao, self._mul(direcao, self.EPS * 5.0))
                restante = max(0.0, restante - self.EPS * 5.0)
                ignorar_tick.add(str(colisao.get("alvo_id") or ""))
                continue
            if tipo == "projetil_objeto" and bool(objeto.AtravessaObjetos):
                posicao = self._somar(posicao, self._mul(direcao, self.EPS * 5.0))
                restante = max(0.0, restante - self.EPS * 5.0)
                continue

            if bool(colisao.get("bloqueante", True)):
                ativo = False
                restante = 0.0

        objeto.Posicao = (float(posicao[0]), float(posicao[1]))
        objeto.Direcao = (float(direcao[0]), float(direcao[1]))
        objeto.RicochetesRestantes = int(ricochetes)
        objeto.Ativo = bool(ativo)

        return {
            "origem": origem_inicial,
            "destino": objeto.Posicao,
            "direcao": objeto.Direcao,
            "ativo": objeto.Ativo,
            "ricochetes_restantes": objeto.RicochetesRestantes,
            "eventos": eventos,
        }
