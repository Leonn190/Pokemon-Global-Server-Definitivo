from __future__ import annotations

import math
from typing import Dict, Iterable, List, Tuple

from SimuladorServerJogo.Batalha.ObjetoBatalha import ObjetoBatalha
from SimuladorServerJogo.Gerais.LoaderRegras import carregar_regras_batalha


Vec2 = Tuple[float, float]


class SimuladorFisica:
    def __init__(self, sistema) -> None:
        self._sistema = sistema
        self._regras_batalha = carregar_regras_batalha()

    @staticmethod
    def _fnum(valor, default: float = 0.0) -> float:
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _vec(a: object, default: Vec2 = (0.0, 0.0)) -> Vec2:
        if isinstance(a, (list, tuple)) and len(a) >= 2:
            return (float(a[0]), float(a[1]))
        return (float(default[0]), float(default[1]))

    @staticmethod
    def _somar(a: Vec2, b: Vec2) -> Vec2:
        return (float(a[0] + b[0]), float(a[1] + b[1]))

    @staticmethod
    def _sub(a: Vec2, b: Vec2) -> Vec2:
        return (float(a[0] - b[0]), float(a[1] - b[1]))

    @staticmethod
    def _mul(a: Vec2, escalar: float) -> Vec2:
        return (float(a[0] * escalar), float(a[1] * escalar))

    @staticmethod
    def _dist(a: Vec2, b: Vec2) -> float:
        return math.hypot(float(a[0] - b[0]), float(a[1] - b[1]))

    @staticmethod
    def _normalizar(v: Vec2) -> Vec2:
        mag = math.hypot(float(v[0]), float(v[1]))
        if mag <= 1e-9:
            return (1.0, 0.0)
        return (float(v[0] / mag), float(v[1] / mag))

    @staticmethod
    def _dot(a: Vec2, b: Vec2) -> float:
        return float(a[0] * b[0] + a[1] * b[1])

    @staticmethod
    def _perp(v: Vec2) -> Vec2:
        return (-float(v[1]), float(v[0]))

    @staticmethod
    def _clamp(valor: float, minimo: float, maximo: float) -> float:
        return max(float(minimo), min(float(maximo), float(valor)))

    def _regra(self, chave: str, default: float) -> float:
        try:
            return float(self._regras_batalha.get(chave, default))
        except (TypeError, ValueError, AttributeError):
            return float(default)

    def velocidade_media_referencia(self) -> float:
        vivos = [p for p in self._sistema.listar_pokemons() if not p.ForaDeCombate]
        if not vivos:
            return 1.0
        soma = sum(max(1.0, p.obter_atributo("Vel")) for p in vivos)
        return max(1.0, soma / float(len(vivos)))

    def velocidade_pokemon_tiles_tick(self, pokemon, percentual: float = 100.0) -> float:
        referencia = self.velocidade_media_referencia()
        vel = max(1.0, pokemon.obter_atributo("Vel"))
        base = 0.1 * (vel / referencia)
        return max(0.01, base * max(0.0, float(percentual)) / 100.0)

    def limitar_ao_campo(self, posicao: Vec2, raio: float = 0.0) -> tuple[Vec2, Vec2]:
        largura = max(1.0, self._fnum(self._sistema.Contexto.get("largura"), 80.0))
        altura = max(1.0, self._fnum(self._sistema.Contexto.get("altura"), 40.0))
        x = self._clamp(float(posicao[0]), float(raio), largura - float(raio))
        y = self._clamp(float(posicao[1]), float(raio), altura - float(raio))

        normal_x = 0.0
        normal_y = 0.0
        if x <= float(raio) + 1e-6:
            normal_x = 1.0
        elif x >= largura - float(raio) - 1e-6:
            normal_x = -1.0
        if y <= float(raio) + 1e-6:
            normal_y = 1.0
        elif y >= altura - float(raio) - 1e-6:
            normal_y = -1.0
        return ((x, y), (normal_x, normal_y))

    def objetos_estaticos(self) -> List[Dict[str, object]]:
        objetos: List[Dict[str, object]] = []
        for indice, estrutura in enumerate(list(self._sistema.Contexto.get("estruturas") or [])):
            if not isinstance(estrutura, dict):
                continue
            x = self._fnum(estrutura.get("x"), 0.0)
            y = self._fnum(estrutura.get("y"), 0.0)
            raio = max(0.35, self._fnum(estrutura.get("raio"), 0.6))
            objetos.append(
                {
                    "id": f"estrutura:{indice}",
                    "posicao": (x, y),
                    "raio": raio,
                    "tipo": "estrutura",
                }
            )
        return objetos

    def alinhar_objeto_ao_campo(self, objeto: ObjetoBatalha) -> Vec2:
        posicao, normal = self.limitar_ao_campo(objeto.Posicao, raio=objeto.Raio)
        objeto.Posicao = posicao
        return normal

    def alinhar_pokemon_ao_campo(self, pokemon) -> Vec2:
        posicao, normal = self.limitar_ao_campo(pokemon.Posicao, raio=pokemon.RaioColisao)
        pokemon.Posicao = posicao
        return normal

    def circulos_colidem(self, pos_a: Vec2, raio_a: float, pos_b: Vec2, raio_b: float) -> bool:
        return self._dist(pos_a, pos_b) <= float(raio_a) + float(raio_b)

    def segmento_intersecta_circulo(self, inicio: Vec2, fim: Vec2, centro: Vec2, raio: float) -> bool:
        vx = float(fim[0] - inicio[0])
        vy = float(fim[1] - inicio[1])
        wx = float(centro[0] - inicio[0])
        wy = float(centro[1] - inicio[1])
        tamanho2 = (vx * vx) + (vy * vy)
        if tamanho2 <= 1e-9:
            return self._dist(inicio, centro) <= float(raio)
        t = max(0.0, min(1.0, ((wx * vx) + (wy * vy)) / tamanho2))
        proj = (float(inicio[0] + vx * t), float(inicio[1] + vy * t))
        return self._dist(proj, centro) <= float(raio)

    def pokemons_no_raio(self, centro: Vec2, raio: float, *, ignorar: Iterable[str] | None = None) -> List[object]:
        ignorados = {str(v) for v in list(ignorar or [])}
        encontrados = []
        for pokemon in self._sistema.listar_pokemons():
            if pokemon.ForaDeCombate or pokemon.Uid in ignorados:
                continue
            if self.circulos_colidem(centro, raio, pokemon.Posicao, pokemon.RaioColisao):
                encontrados.append(pokemon)
        return encontrados

    def pokemon_em_cone(
        self,
        pokemon,
        origem: Vec2,
        direcao: Vec2,
        alcance: float,
        largura_graus: float,
    ) -> bool:
        vetor = self._sub(pokemon.Posicao, origem)
        distancia = math.hypot(vetor[0], vetor[1])
        if distancia <= 1e-9:
            return True
        if distancia > float(alcance) + float(pokemon.RaioColisao):
            return False
        direcao_norm = self._normalizar(direcao)
        alvo_norm = self._normalizar(vetor)
        produto = self._clamp(self._dot(direcao_norm, alvo_norm), -1.0, 1.0)
        angulo = math.degrees(math.acos(produto))
        meio_angulo = max(1.0, float(largura_graus) * 0.5)
        return angulo <= meio_angulo

    def refletir_vetor(self, direcao: Vec2, normal: Vec2) -> Vec2:
        direcao_n = self._normalizar(direcao)
        normal_n = self._normalizar(normal)
        produto = self._dot(direcao_n, normal_n)
        refletido = self._sub(direcao_n, self._mul(normal_n, 2.0 * produto))
        return self._normalizar(refletido)

    def _vetor_velocidade_pokemon(self, pokemon) -> Vec2:
        vetor = self._sub(getattr(pokemon, "Posicao", (0.0, 0.0)), getattr(pokemon, "PosicaoAnterior", (0.0, 0.0)))
        magnitude = math.hypot(vetor[0], vetor[1])
        if magnitude <= 1e-9:
            return (0.0, 0.0)
        return self._mul(self._normalizar(vetor), max(0.0, float(getattr(pokemon, "VelocidadeAtualTilesTick", magnitude) or magnitude)))

    def _interseccao_segmento_circulo(self, inicio: Vec2, fim: Vec2, centro: Vec2, raio: float) -> Dict[str, object] | None:
        d = self._sub(fim, inicio)
        f = self._sub(inicio, centro)
        a = self._dot(d, d)
        if a <= 1e-9:
            if self._dist(inicio, centro) <= float(raio):
                normal = self._normalizar(self._sub(inicio, centro))
                return {"t": 0.0, "ponto": inicio, "normal": normal}
            return None

        b = 2.0 * self._dot(f, d)
        c = self._dot(f, f) - (float(raio) * float(raio))
        discriminante = (b * b) - (4.0 * a * c)
        if discriminante < 0.0:
            return None

        raiz = math.sqrt(max(0.0, discriminante))
        candidatos = [(-b - raiz) / (2.0 * a), (-b + raiz) / (2.0 * a)]
        for t in sorted(candidatos):
            if 0.0 <= t <= 1.0:
                ponto = self._somar(inicio, self._mul(d, t))
                normal = self._normalizar(self._sub(ponto, centro))
                return {"t": float(t), "ponto": ponto, "normal": normal}
        return None

    def resolver_colisoes_pokemon(self, pokemon, origem: Vec2, destino: Vec2, velocidade_tiles_tick: float, tick: int) -> List[Dict[str, object]]:
        eventos: List[Dict[str, object]] = []
        melhor_evento: Dict[str, object] | None = None
        for outro in self._sistema.listar_pokemons():
            if outro is pokemon or outro.ForaDeCombate:
                continue
            interseccao = self._interseccao_segmento_circulo(origem, destino, outro.Posicao, float(pokemon.RaioColisao) + float(outro.RaioColisao))
            if interseccao is None:
                continue
            if melhor_evento is None or float(interseccao.get("t", 1.0)) < float(melhor_evento.get("t", 1.0)):
                melhor_evento = {"outro": outro, **interseccao}

        if melhor_evento is None:
            return eventos

        outro = melhor_evento["outro"]
        normal = self._normalizar(tuple(melhor_evento.get("normal") or (1.0, 0.0)))
        ponto = tuple(melhor_evento.get("ponto") or origem)
        pokemon.Posicao = (float(ponto[0]), float(ponto[1]))
        pokemon.PosicaoAnterior = origem

        vetor_a = self._mul(self._normalizar(self._sub(destino, origem)), max(0.0, float(velocidade_tiles_tick)))
        vetor_b = self._vetor_velocidade_pokemon(outro)
        velocidade_relativa = max(0.05, abs(self._dot(self._sub(vetor_a, vetor_b), normal)))

        massa_a = max(0.2, float(getattr(pokemon, "Peso", 1.0) or 1.0))
        massa_b = max(0.2, float(getattr(outro, "Peso", 1.0) or 1.0))
        massa_total = max(0.4, massa_a + massa_b)
        restitui = self._regra("batalha_colisao_restituicao", 0.35)
        deslocamento_base = max(
            self._regra("batalha_colisao_deslocamento_base_min", 0.25),
            velocidade_relativa * self._regra("batalha_colisao_deslocamento_por_velocidade_relativa", 6.0),
        )
        desloca_a = deslocamento_base * (massa_b / massa_total)
        desloca_b = deslocamento_base * (massa_a / massa_total)
        velocidade_reacao_min = self._regra("batalha_colisao_velocidade_reacao_min", 0.03)
        velocidade_a = max(velocidade_reacao_min, velocidade_relativa * (massa_b / massa_total) * (1.0 + restitui))
        velocidade_b = max(velocidade_reacao_min, velocidade_relativa * (massa_a / massa_total) * (1.0 + restitui))

        destino_a, _ = self.limitar_ao_campo(self._somar(pokemon.Posicao, self._mul(normal, desloca_a)), raio=pokemon.RaioColisao)
        destino_b, _ = self.limitar_ao_campo(self._sub(outro.Posicao, self._mul(normal, desloca_b)), raio=outro.RaioColisao)

        dano_base_min = self._regra("batalha_colisao_dano_base_min", 1.0)
        velocidade_ref_min = self._regra("batalha_colisao_velocidade_referencia_min", 0.1)
        dano_por_massa_velocidade = self._regra("batalha_colisao_dano_por_massa_velocidade", 8.0)
        dano_por_ataque = self._regra("batalha_colisao_dano_por_ataque", 0.35)
        dano_em_b = max(
            dano_base_min,
            (massa_a * max(velocidade_ref_min, float(velocidade_tiles_tick)) * dano_por_massa_velocidade) + (pokemon.obter_atributo("Atk") * dano_por_ataque),
        )
        dano_em_a = max(
            dano_base_min,
            (massa_b * max(velocidade_ref_min, float(getattr(outro, "VelocidadeAtualTilesTick", 0.05) or 0.05)) * dano_por_massa_velocidade)
            + (outro.obter_atributo("Atk") * dano_por_ataque),
        )

        eventos.append(
            {
                "tipo": "colisao_pokemon",
                "tick": int(tick),
                "a": pokemon.Uid,
                "b": outro.Uid,
                "t": round(float(melhor_evento.get("t", 0.0)), 4),
                "ponto": [round(pokemon.Posicao[0], 4), round(pokemon.Posicao[1], 4)],
                "normal": [round(normal[0], 4), round(normal[1], 4)],
                "velocidade_relativa": round(velocidade_relativa, 4),
                "dano_em_a": round(dano_em_a, 4),
                "dano_em_b": round(dano_em_b, 4),
                "movimentos": [
                    {
                        "pokemon_id": pokemon.Uid,
                        "origem": [round(pokemon.Posicao[0], 4), round(pokemon.Posicao[1], 4)],
                        "destino": [round(destino_a[0], 4), round(destino_a[1], 4)],
                        "velocidade": round(velocidade_a, 4),
                    },
                    {
                        "pokemon_id": outro.Uid,
                        "origem": [round(outro.Posicao[0], 4), round(outro.Posicao[1], 4)],
                        "destino": [round(destino_b[0], 4), round(destino_b[1], 4)],
                        "velocidade": round(velocidade_b, 4),
                    },
                ],
            }
        )
        return eventos

    def mover_pokemon_um_tick(self, pokemon, destino: Vec2, velocidade_tiles_tick: float, tick: int) -> Dict[str, object]:
        origem = (float(pokemon.Posicao[0]), float(pokemon.Posicao[1]))
        distancia_total = self._dist(origem, destino)
        if distancia_total <= 1e-9:
            return {
                "concluido": True,
                "origem": origem,
                "destino": origem,
                "distancia": 0.0,
                "colisoes": [],
            }

        direcao = self._normalizar(self._sub(destino, origem))
        passo = min(float(velocidade_tiles_tick), distancia_total)
        nova_posicao = self._somar(origem, self._mul(direcao, passo))
        pokemon.PosicaoAnterior = origem
        pokemon.VelocidadeAtualTilesTick = float(velocidade_tiles_tick)

        colisoes = self.resolver_colisoes_pokemon(pokemon, origem, nova_posicao, velocidade_tiles_tick, tick)
        if colisoes:
            return {
                "concluido": True,
                "interrompido_por_colisao": True,
                "origem": origem,
                "destino_planejado": (float(destino[0]), float(destino[1])),
                "destino": (float(pokemon.Posicao[0]), float(pokemon.Posicao[1])),
                "distancia": round(self._dist(origem, pokemon.Posicao), 4),
                "velocidade": round(float(velocidade_tiles_tick), 4),
                "colisoes": colisoes,
            }

        pokemon.Posicao = nova_posicao
        normal_campo = self.alinhar_pokemon_ao_campo(pokemon)
        if abs(normal_campo[0]) > 1e-9 or abs(normal_campo[1]) > 1e-9:
            colisoes.append({"tipo": "parede_campo", "normal": [normal_campo[0], normal_campo[1]]})

        for objeto in self.objetos_estaticos():
            if not self.circulos_colidem(pokemon.Posicao, pokemon.RaioColisao, self._vec(objeto.get("posicao")), self._fnum(objeto.get("raio"), 0.6)):
                continue
            delta = self._sub(pokemon.Posicao, self._vec(objeto.get("posicao")))
            normal = self._normalizar(delta if self._dist(pokemon.Posicao, self._vec(objeto.get("posicao"))) > 1e-9 else (1.0, 0.0))
            sobreposicao = (pokemon.RaioColisao + self._fnum(objeto.get("raio"), 0.6)) - self._dist(pokemon.Posicao, self._vec(objeto.get("posicao")))
            pokemon.Posicao = self._somar(pokemon.Posicao, self._mul(normal, max(0.0, sobreposicao)))
            colisoes.append({"tipo": "objeto_campo", "objeto_id": objeto.get("id"), "normal": [normal[0], normal[1]]})

        restante = self._dist(pokemon.Posicao, destino)
        return {
            "concluido": restante <= max(0.02, float(velocidade_tiles_tick) * 0.35),
            "origem": origem,
            "destino_planejado": (float(destino[0]), float(destino[1])),
            "destino": (float(pokemon.Posicao[0]), float(pokemon.Posicao[1])),
            "distancia": round(passo, 4),
            "velocidade": round(float(velocidade_tiles_tick), 4),
            "colisoes": colisoes,
        }

    def avancar_objeto_um_tick(self, objeto: ObjetoBatalha) -> Dict[str, object]:
        objeto.avancar_tick()
        origem = objeto.PosicaoAnterior
        if objeto.VelocidadeTilesTick > 0.0:
            objeto.Posicao = self._somar(objeto.Posicao, self._mul(self._normalizar(objeto.Direcao), objeto.VelocidadeTilesTick))
        normal_campo = self.alinhar_objeto_ao_campo(objeto)
        return {
            "origem": origem,
            "destino": objeto.Posicao,
            "normal_campo": normal_campo,
        }
