from __future__ import annotations

import math
from typing import Dict, Iterable, List, Tuple

from SimuladorServerJogo.Batalha.ObjetoBatalha import ObjetoBatalha
from SimuladorServerJogo.Batalha.VerificadorColisao import EPSILON, primeiro_impacto_segmento, refletir_vetor

Vec2 = Tuple[float, float]


class RastreadorFluxos:
    def __init__(self, limites: Tuple[float, float, float, float]) -> None:
        self._limites = tuple(float(v) for v in limites)

    @staticmethod
    def _mul(v: Vec2, s: float) -> Vec2:
        return (float(v[0]) * float(s), float(v[1]) * float(s))

    @staticmethod
    def _sum(a: Vec2, b: Vec2) -> Vec2:
        return (float(a[0]) + float(b[0]), float(a[1]) + float(b[1]))

    @staticmethod
    def _norm(v: Vec2) -> Vec2:
        m = math.hypot(float(v[0]), float(v[1]))
        if m <= EPSILON:
            return (1.0, 0.0)
        return (float(v[0]) / m, float(v[1]) / m)

    @staticmethod
    def _clamp(valor: float, minimo: float, maximo: float) -> float:
        return max(float(minimo), min(float(maximo), float(valor)))

    @staticmethod
    def _dist(a: Vec2, b: Vec2) -> float:
        return math.hypot(float(a[0] - b[0]), float(a[1] - b[1]))

    @staticmethod
    def _dot(a: Vec2, b: Vec2) -> float:
        return float(a[0] * b[0] + a[1] * b[1])

    @staticmethod
    def _sub(a: Vec2, b: Vec2) -> Vec2:
        return (float(a[0] - b[0]), float(a[1] - b[1]))

    def _dist_segmento_ponto(self, a: Vec2, b: Vec2, p: Vec2) -> float:
        ab = self._sub(b, a)
        ap = self._sub(p, a)
        tamanho2 = self._dot(ab, ab)
        if tamanho2 <= EPSILON:
            return self._dist(a, p)
        t = self._clamp(self._dot(ap, ab) / tamanho2, 0.0, 1.0)
        proj = (a[0] + (ab[0] * t), a[1] + (ab[1] * t))
        return self._dist(proj, p)

    def _alcance_area_no_tick(self, objeto: ObjetoBatalha, elapsed: int) -> float:
        alcance_max = max(0.0, float(objeto.DadosExtras.get("alcance") or objeto.Fluxo.get("alcance") or 0.0))
        v0 = max(0.01, float(objeto.VelocidadeTilesTick or 0.01))
        a = float(objeto.AceleracaoTilesTick2 or 0.0)
        n = max(1, int(elapsed))
        alcance_tick = (v0 * n) + (0.5 * a * n * n)
        alcance_tick = max(0.0, alcance_tick)
        if bool(objeto.Fluxo.get("ajustavel", False)):
            minimo = float(objeto.Fluxo.get("alcance_min") or 0.1)
            maximo = float(objeto.Fluxo.get("alcance_max") or alcance_max or minimo)
            alcance_max = self._clamp(alcance_max, minimo, maximo)
        return min(alcance_max, alcance_tick if alcance_tick > 0.0 else alcance_max)

    @staticmethod
    def _lerp(a: Vec2, b: Vec2, t: float) -> Vec2:
        return (a[0] + ((b[0] - a[0]) * t), a[1] + ((b[1] - a[1]) * t))

    def _point_in_polygon(self, point: Vec2, polygon: List[Vec2]) -> bool:
        if len(polygon) < 3:
            return False
        inside = False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if (yi > point[1]) != (yj > point[1]):
                x_cross = (xj - xi) * (point[1] - yi) / ((yj - yi) or 1e-8) + xi
                if point[0] < x_cross:
                    inside = not inside
            j = i
        return inside

    def _circle_samples(self, center: Vec2, radius: float) -> List[Vec2]:
        pts = [center]
        for ang in range(0, 360, 24):
            rad = math.radians(ang)
            c = math.cos(rad)
            s = math.sin(rad)
            for mul in (0.48, 0.82, 1.0):
                pts.append((center[0] + (c * radius * mul), center[1] + (s * radius * mul)))
        return pts

    def _scaled_factor(self, fluxo: Dict[str, object], source_radius_tiles: float) -> float:
        return 1.0 + (source_radius_tiles * 2.0 - 1.5) * 0.08 if bool(fluxo.get("escalonavel", False)) else 1.0

    def _exit_direction(self, aim_dir: Vec2, fluxo: Dict[str, object]) -> Vec2:
        offset_value = float(fluxo.get("offset", 0.0) or 0.0)
        if abs(offset_value) <= 1e-9:
            return aim_dir
        if bool(fluxo.get("grudado", False)):
            base_ang = math.atan2(aim_dir[1], aim_dir[0])
            ang = math.radians(offset_value)
            return (math.cos(base_ang + ang), math.sin(base_ang + ang))
        return aim_dir

    def _base_start(self, center: Vec2, aim_dir: Vec2, fluxo: Dict[str, object], source_radius_tiles: float) -> tuple[Vec2, Vec2, Vec2]:
        exit_dir = self._norm(self._exit_direction(aim_dir, fluxo))
        perp = (-exit_dir[1], exit_dir[0])
        spacing = float(fluxo.get("espacamento", 0.0) or 0.0)
        offset = float(fluxo.get("offset", 0.0) or 0.0)
        if bool(fluxo.get("grudado", False)):
            start = self._sum(center, self._mul(exit_dir, source_radius_tiles))
        else:
            start = self._sum(center, self._mul(exit_dir, source_radius_tiles + spacing))
            start = self._sum(start, self._mul(perp, offset))
        return start, exit_dir, perp

    def _width_profile_tiles(self, fluxo: Dict[str, object], total_len_tiles: float) -> tuple[List[float], List[float]]:
        total_len_tiles = max(0.10, total_len_tiles)
        base = max(0.0, float(fluxo.get("largura_base", 0.0) or 0.0))
        teto = max(0.0, float(fluxo.get("largura_teto", 0.0) or 0.0))
        widths = [base, teto]
        dists = [0.0, total_len_tiles]
        faixas = max(0, int(fluxo.get("faixas", 0) or 0))
        if faixas <= 0:
            return dists, widths
        largura_faixa = max(0.0, float(fluxo.get("largura_faixa", teto) or teto))
        repeticao = bool(fluxo.get("repeticao_faixas", True))
        ciclico = bool(fluxo.get("faixas_ciclicas", False))
        if ciclico:
            step = max(0.10, float(fluxo.get("distancia_faixa", 1.0) or 1.0))
            pos = step
            toggle = True
            dists = [0.0]
            widths = [base]
            while pos < total_len_tiles - 1e-6:
                dists.append(pos)
                widths.append(teto if toggle else largura_faixa)
                toggle = not toggle
                pos += step
            dists.append(total_len_tiles)
            widths.append(teto if len(widths) % 2 == 1 else largura_faixa)
            return dists, widths
        segments = faixas + 2
        step = total_len_tiles / max(1, segments - 1)
        dists = [i * step for i in range(segments)]
        widths = [base, teto]
        if repeticao:
            use_teto = False
            for _ in range(faixas):
                widths.append(teto if use_teto else largura_faixa)
                use_teto = not use_teto
        else:
            widths.extend([largura_faixa for _ in range(faixas)])
        return dists, widths[: len(dists)]

    def _curvature_anchors(self, fluxo: Dict[str, object], total_len_tiles: float) -> tuple[List[float], List[float]]:
        total_len_tiles = max(0.10, total_len_tiles)
        points_n = max(0, int(fluxo.get("pontos_curvatura", 0) or 0))
        cyclic = bool(fluxo.get("curvaturas_ciclicas", False))
        invertido = bool(fluxo.get("invertido", True))
        vals = [float(fluxo.get(f"curvatura_{i}", 0.0) or 0.0) for i in range(1, 7)]
        positions: List[float] = []
        offsets: List[float] = []
        if cyclic:
            step = max(0.10, float(fluxo.get("distancia_entre_curvaturas", 1.0) or 1.0))
            pos = step
            idx = 0
            while pos < total_len_tiles + 1e-6 and len(positions) < 24:
                base = vals[idx % max(1, points_n if points_n > 0 else 1)] if points_n > 0 else vals[0]
                if invertido and idx % 2 == 1:
                    base = -base
                positions.append(pos)
                offsets.append(base)
                pos += step
                idx += 1
        else:
            if points_n <= 0:
                return positions, offsets
            step = total_len_tiles / max(1, points_n + 1)
            for i in range(points_n):
                positions.append(step * (i + 1))
                offsets.append(vals[i])
        return positions, offsets

    def _catmull_rom(self, points: List[Vec2], segments_per_edge: int = 10) -> List[Vec2]:
        if len(points) < 2:
            return points[:]
        out = [points[0]]
        ext = [points[0]] + points + [points[-1]]
        for i in range(1, len(ext) - 2):
            p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
            for j in range(1, segments_per_edge + 1):
                t = j / float(segments_per_edge)
                t2 = t * t
                t3 = t2 * t
                point = (
                    0.5
                    * (
                        (2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
                    ),
                    0.5
                    * (
                        (2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
                    ),
                )
                out.append(point)
        return out

    def _polygon_from_centerline(self, points: List[Vec2], widths: List[float], source_center: Vec2, source_radius_tiles: float, fluxo: Dict[str, object], axis_dir: Vec2) -> List[Vec2]:
        if len(points) < 2:
            return []
        if bool(fluxo.get("grudado", False)):
            src_r = source_radius_tiles
            outer_r = max(src_r, max(self._dist(p, source_center) for p in points))
            center_ang = math.atan2(axis_dir[1], axis_dir[0])
            base_half_ang = min((math.tau * 0.5) - 1e-6, math.radians(max(0.0, float(fluxo.get("largura_base", 0.0) or 0.0)) * 0.5))
            teto_half_ang = min((math.tau * 0.5) - 1e-6, math.radians(max(0.0, float(fluxo.get("largura_teto", 0.0) or 0.0)) * 0.5))
            outer_samples = max(1, int(max(1e-6, teto_half_ang) * 18))
            inner_samples = max(1, int(max(1e-6, base_half_ang) * 18))
            outer = []
            for i in range(outer_samples + 1):
                t = i / float(outer_samples)
                ang = center_ang + teto_half_ang - (2.0 * teto_half_ang * t)
                outer.append((source_center[0] + math.cos(ang) * outer_r, source_center[1] + math.sin(ang) * outer_r))
            inner = []
            for i in range(inner_samples + 1):
                t = i / float(inner_samples)
                ang = center_ang - base_half_ang + (2.0 * base_half_ang * t)
                inner.append((source_center[0] + math.cos(ang) * src_r, source_center[1] + math.sin(ang) * src_r))
            return outer + inner
        left: List[Vec2] = []
        right: List[Vec2] = []
        for i, point in enumerate(points):
            if i == 0:
                tangent = self._sub(points[i + 1], points[i])
            elif i == len(points) - 1:
                tangent = self._sub(points[i], points[i - 1])
            else:
                tangent = self._sub(points[i + 1], points[i - 1])
            tangent = self._norm(tangent)
            normal = (-tangent[1], tangent[0])
            half = widths[i] * 0.5
            left.append(self._sum(point, self._mul(normal, half)))
            right.append(self._sum(point, self._mul(normal, -half)))
        return left + list(reversed(right))

    def alvo_atingido_area(self, objeto: ObjetoBatalha, alvo_pos: Vec2, alvo_raio: float, origem_execucao: Vec2, elapsed: int) -> bool:
        fluxo = dict(objeto.Fluxo or {})
        alcance = max(0.05, self._alcance_area_no_tick(objeto, elapsed))
        source_radius_tiles = float(objeto.DadosExtras.get("source_radius_tiles", 0.75) or 0.75)
        scale = self._scaled_factor(fluxo, source_radius_tiles)
        alcance *= scale
        aim_dir = self._norm(objeto.Direcao)
        start_center, axis_dir, perp = self._base_start(origem_execucao, aim_dir, fluxo, source_radius_tiles)
        dists_nodes, widths_nodes = self._width_profile_tiles(fluxo, alcance)
        curvature_pos, curvature_vals = self._curvature_anchors(fluxo, alcance)
        anchor_map = {0.0: 0.0, alcance: 0.0}
        for d, v in zip(curvature_pos, curvature_vals):
            anchor_map[self._clamp(d, 0.0, alcance)] = v * scale
        anchor_keys = sorted(anchor_map.keys())
        anchor_points = [self._sum(start_center, self._sum(self._mul(axis_dir, d), self._mul(perp, anchor_map[d]))) for d in anchor_keys]
        if bool(fluxo.get("curvatura_circular", True)) and len(anchor_points) >= 3:
            smooth = self._catmull_rom(anchor_points, 10)
        else:
            smooth = []
            for i in range(len(anchor_points) - 1):
                a = anchor_points[i]
                b = anchor_points[i + 1]
                steps = max(2, int(self._dist(a, b) / max(0.25, 0.25)))
                for j in range(steps):
                    t = j / float(steps)
                    smooth.append(self._lerp(a, b, t))
            smooth.append(anchor_points[-1])
        if len(smooth) < 2:
            smooth = [start_center, self._sum(start_center, self._mul(axis_dir, alcance))]
        widths: List[float] = []
        cumulative = [0.0]
        total_len = 0.0
        for i in range(1, len(smooth)):
            total_len += self._dist(smooth[i], smooth[i - 1])
            cumulative.append(total_len)
        for d in cumulative:
            idx = 0
            while idx < len(dists_nodes) - 1 and d > dists_nodes[idx + 1]:
                idx += 1
            if idx >= len(dists_nodes) - 1:
                w = widths_nodes[-1]
            else:
                a_d, b_d = dists_nodes[idx], dists_nodes[idx + 1]
                a_w, b_w = widths_nodes[idx], widths_nodes[idx + 1]
                t = 0.0 if abs(b_d - a_d) < 1e-8 else (d - a_d) / (b_d - a_d)
                if str(fluxo.get("hastes", "")).casefold() == "concavo":
                    t = 1 - (1 - t) * (1 - t)
                elif str(fluxo.get("hastes", "")).casefold() == "convexo":
                    t = t * t
                w = a_w + (b_w - a_w) * t
            widths.append(max(0.0, w * scale))

        polygon = self._polygon_from_centerline(smooth, widths, origem_execucao, source_radius_tiles, fluxo, axis_dir)
        for ponto in self._circle_samples(alvo_pos, float(alvo_raio)):
            if self._point_in_polygon(ponto, polygon):
                return True
        return False

    def alvo_atingido_zona(self, objeto: ObjetoBatalha, alvo_pos: Vec2, alvo_raio: float, elapsed: int) -> bool:
        raio_max = float(objeto.DadosExtras.get("raio_max", objeto.Fluxo.get("raio", 1.0)) or 1.0)
        v0 = max(0.01, float(objeto.VelocidadeTilesTick or 0.01))
        a = float(objeto.AceleracaoTilesTick2 or 0.0)
        n = max(1, int(elapsed))
        raio_atual = min(raio_max, max(0.0, (v0 * n) + (0.5 * a * n * n)))
        return self._dist(tuple(objeto.Posicao), alvo_pos) <= float(raio_atual) + float(alvo_raio)

    def avancar_projetil_um_tick(
        self,
        objeto: ObjetoBatalha,
        pokemons: Iterable[Dict[str, object]],
        objetos: Iterable[Dict[str, object]] | None = None,
        *,
        ignorar_ids: Iterable[str] | None = None,
    ) -> Dict[str, object]:
        objeto.avancar_tick()
        eventos: List[Dict[str, object]] = []
        segmentos: List[Dict[str, object]] = []
        origem = (float(objeto.PosicaoAnterior[0]), float(objeto.PosicaoAnterior[1]))
        ignorar_temporario = {
            str(k): float(v)
            for k, v in dict(objeto.DadosExtras.get("ignorar_impactos_ids") or {}).items()
            if str(k)
        }
        pokemons_por_id = {str(p.get("id") or ""): dict(p) for p in list(pokemons or []) if str(p.get("id") or "")}

        objeto.VelocidadeAtualTilesTick = max(0.01, float(objeto.VelocidadeAtualTilesTick or objeto.VelocidadeTilesTick) + float(objeto.AceleracaoTilesTick2 or 0.0))
        deslocamento_tick = min(float(objeto.VelocidadeAtualTilesTick), max(0.0, float(objeto.AlcanceRestante)))
        restante_tick = deslocamento_tick
        atual = origem

        while restante_tick > EPSILON and objeto.Ativo:
            for alvo_id in list(ignorar_temporario.keys()):
                poke = pokemons_por_id.get(alvo_id)
                if poke is None:
                    ignorar_temporario.pop(alvo_id, None)
                    continue
                pos = poke.get("pos") or poke.get("posicao") or (0.0, 0.0)
                if self._dist(atual, (float(pos[0]), float(pos[1]))) > float(ignorar_temporario[alvo_id]) + 1e-4:
                    ignorar_temporario.pop(alvo_id, None)
            seg_origem = atual
            alvo = self._sum(atual, self._mul(self._norm(objeto.Direcao), restante_tick))
            ignorar_ids_loop = set(str(v) for v in list(ignorar_ids or []) if str(v))
            ignorar_ids_loop.update(ignorar_temporario.keys())
            impacto = primeiro_impacto_segmento(
                atual,
                alvo,
                float(objeto.Raio),
                self._limites,
                pokemons,
                objetos=objetos,
                ignorar_ids=list(ignorar_ids_loop),
            )
            if impacto is None:
                atual = alvo
                objeto.DistanciaPercorrida += restante_tick
                objeto.AlcanceRestante = max(0.0, float(objeto.AlcanceRestante) - restante_tick)
                segmentos.append({"origem": [round(seg_origem[0], 4), round(seg_origem[1], 4)], "destino": [round(atual[0], 4), round(atual[1], 4)]})
                restante_tick = 0.0
                break

            deslocamento = max(0.0, float(restante_tick) * float(impacto.t))
            objeto.DistanciaPercorrida += deslocamento
            objeto.AlcanceRestante = max(0.0, float(objeto.AlcanceRestante) - deslocamento)
            atual = (float(impacto.ponto[0]), float(impacto.ponto[1]))
            restante_tick -= deslocamento

            direcao_antes = [round(float(objeto.Direcao[0]), 6), round(float(objeto.Direcao[1]), 6)]
            mult_antes = round(float(objeto.MultiplicadorDanoAtual), 6)
            evento = {
                "tipo": "parede" if impacto.tipo == "parede" else ("objeto" if impacto.tipo == "objeto" else "pokemon"),
                "normal": [round(float(impacto.normal[0]), 4), round(float(impacto.normal[1]), 4)],
                "ponto": [round(float(atual[0]), 4), round(float(atual[1]), 4)],
                "alvo_id": str(impacto.alvo_id or ""),
                "multiplicador_dano_no_impacto": round(float(objeto.MultiplicadorDanoAtual), 6),
                "distancia_percorrida_no_impacto": round(float(objeto.DistanciaPercorrida), 6),
                "alcance_restante_no_impacto": round(float(objeto.AlcanceRestante), 6),
                "ricochete": False,
                "atravessou": False,
            }

            if impacto.tipo == "parede":
                if objeto.RicocheteiaObjetos and objeto.RicochetesRestantes > 0:
                    objeto.Direcao = refletir_vetor(objeto.Direcao, impacto.normal)
                    objeto.RicochetesRestantes -= 1
                    objeto.MultiplicadorDanoAtual *= float(objeto.MultiplicadorDanoPorRicochet)
                    objeto.AlcanceRestante += float(objeto.AumentoAlcancePorRicochet)
                    evento["ricochete"] = True
                else:
                    objeto.Ativo = False
            elif impacto.tipo == "objeto":
                if objeto.RicocheteiaObjetos and objeto.RicochetesRestantes > 0:
                    objeto.Direcao = refletir_vetor(objeto.Direcao, impacto.normal)
                    objeto.RicochetesRestantes -= 1
                    objeto.MultiplicadorDanoAtual *= float(objeto.MultiplicadorDanoPorRicochet)
                    objeto.AlcanceRestante += float(objeto.AumentoAlcancePorRicochet)
                    evento["ricochete"] = True
                elif objeto.AtravessaObjetos and objeto.AtravessadasRestantes > 0:
                    objeto.AtravessadasRestantes -= 1
                    objeto.MultiplicadorDanoAtual *= float(objeto.MultiplicadorDanoPorAtravessada)
                    objeto.AlcanceRestante += float(objeto.AumentoAlcancePorAtravessada)
                    evento["atravessou"] = True
                else:
                    objeto.Ativo = False
            else:
                if objeto.RicocheteiaPokemons and objeto.RicochetesRestantes > 0:
                    objeto.Direcao = refletir_vetor(objeto.Direcao, impacto.normal)
                    objeto.RicochetesRestantes -= 1
                    objeto.MultiplicadorDanoAtual *= float(objeto.MultiplicadorDanoPorRicochet)
                    objeto.AlcanceRestante += float(objeto.AumentoAlcancePorRicochet)
                    evento["ricochete"] = True
                elif objeto.AtravessaPokemons and objeto.AtravessadasRestantes > 0:
                    objeto.AtravessadasRestantes -= 1
                    objeto.MultiplicadorDanoAtual *= float(objeto.MultiplicadorDanoPorAtravessada)
                    objeto.AlcanceRestante += float(objeto.AumentoAlcancePorAtravessada)
                    evento["atravessou"] = True
                    poke = pokemons_por_id.get(str(impacto.alvo_id or ""))
                    if poke is not None:
                        alvo_pos = poke.get("pos") or poke.get("posicao") or (0.0, 0.0)
                        alvo_raio = float(poke.get("raio_tiles") or 0.0) + float(objeto.Raio)
                        ignorar_temporario[str(impacto.alvo_id or "")] = max(0.0, alvo_raio)
                else:
                    objeto.Ativo = False

            evento["direcao_no_impacto"] = direcao_antes
            evento["direcao_apos_impacto"] = [round(float(objeto.Direcao[0]), 6), round(float(objeto.Direcao[1]), 6)]
            evento["multiplicador_dano_no_impacto"] = mult_antes
            evento["multiplicador_dano_apos_impacto"] = round(float(objeto.MultiplicadorDanoAtual), 6)

            eventos.append(evento)
            seg = {"origem": [round(seg_origem[0], 4), round(seg_origem[1], 4)], "destino": [round(atual[0], 4), round(atual[1], 4)], "impacto": dict(evento)}
            segmentos.append(seg)
            atual = self._sum(atual, self._mul(self._norm(objeto.Direcao), 0.002))
            restante_tick = max(0.0, restante_tick - 0.002)
            if objeto.AlcanceRestante <= EPSILON:
                objeto.Ativo = False

        objeto.Posicao = atual
        objeto.DadosExtras["ignorar_impactos_ids"] = dict(ignorar_temporario)
        if objeto.AlcanceRestante <= EPSILON:
            objeto.Ativo = False

        return {
            "origem": origem,
            "destino": atual,
            "eventos": eventos,
            "segmentos": segmentos,
            "distancia_tick": round(float(deslocamento_tick) - float(restante_tick), 4),
        }
