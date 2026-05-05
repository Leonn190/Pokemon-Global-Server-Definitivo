from __future__ import annotations

import math
from typing import Callable

from SimuladorServerJogo.Mundo.DungeonGeometria import sala_atual_por_posicao


class CerebroArmadilhas:
    """Estado autoritativo das armadilhas de dungeon.

    O layout contem a configuracao estatica. Este coordenador mantem apenas
    estado runtime deterministico em `layout["estado_armadilhas"]`.
    """

    def __init__(self, tick_rate: int = 30) -> None:
        self.tick_rate = max(1, int(tick_rate or 30))

    @staticmethod
    def _dist2(a, b) -> float:
        return (float(a[0]) - float(b[0])) ** 2 + (float(a[1]) - float(b[1])) ** 2

    @staticmethod
    def _grid_set(layout: dict, x: int, y: int, tile: int) -> bool:
        grid = layout.get("grid_tiles") if isinstance(layout.get("grid_tiles"), list) else []
        if 0 <= int(y) < len(grid) and isinstance(grid[int(y)], list) and 0 <= int(x) < len(grid[int(y)]):
            if int(grid[int(y)][int(x)]) != int(tile):
                grid[int(y)][int(x)] = int(tile)
                return True
        return False

    @staticmethod
    def _grid_tile(layout: dict, x: float, y: float) -> int | None:
        grid = layout.get("grid_tiles") if isinstance(layout.get("grid_tiles"), list) else []
        tx, ty = int(math.floor(float(x))), int(math.floor(float(y)))
        if 0 <= ty < len(grid) and isinstance(grid[ty], list) and 0 <= tx < len(grid[ty]):
            try:
                return int(grid[ty][tx])
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _feet_box_centro_no_tile(player) -> tuple[int, int]:
        return (int(math.floor(float(player.posicao[0]))), int(math.floor(float(player.posicao[1]))))

    def _player_no_buraco(self, layout: dict, player) -> bool:
        tile_buraco = int(layout.get("tile_buraco", 10) or 10)
        tx, ty = self._feet_box_centro_no_tile(player)
        if self._grid_tile(layout, tx, ty) != tile_buraco:
            return False
        # Feet-box reduzida: so cai quando o centro dos pes esta bem dentro do tile.
        fx = abs(float(player.posicao[0]) - (tx + 0.5))
        fy = abs(float(player.posicao[1]) - (ty + 0.5))
        return fx <= 0.36 and fy <= 0.36

    def _estado_trap(self, layout: dict, trap: dict) -> dict:
        estado = layout.setdefault("estado_armadilhas", {})
        traps = estado.setdefault("traps", {})
        tid = str(trap.get("id") or "")
        atual = traps.setdefault(tid, {})
        atual.setdefault("id", tid)
        atual.setdefault("tipo", str(trap.get("tipo") or ""))
        return atual

    def _atualizar_espeto_movel(self, trap: dict, estado: dict) -> None:
        cfg = trap.get("config") if isinstance(trap.get("config"), dict) else {}
        pos0 = trap.get("posicao") if isinstance(trap.get("posicao"), (list, tuple)) else [0.0, 0.0]
        pos = estado.get("posicao") if isinstance(estado.get("posicao"), (list, tuple)) else [float(pos0[0]), float(pos0[1])]
        direcao = estado.get("direcao") if isinstance(estado.get("direcao"), (list, tuple)) else cfg.get("direcao", [1, 0])
        dx, dy = float(direcao[0]), float(direcao[1])
        n = math.hypot(dx, dy) or 1.0
        dx, dy = dx / n, dy / n
        vel = float(cfg.get("velocidade", 1.5) or 1.5)
        nx = float(pos[0]) + dx * vel / self.tick_rate
        ny = float(pos[1]) + dy * vel / self.tick_rate
        lim = cfg.get("limites_sala") if isinstance(cfg.get("limites_sala"), (list, tuple)) and len(cfg.get("limites_sala")) == 4 else None
        if lim is not None:
            x0, y0, x1, y1 = [float(v) for v in lim]
            bateu = False
            if nx < x0 or nx > x1:
                dx *= -1.0
                nx = max(x0, min(x1, nx))
                bateu = True
            if ny < y0 or ny > y1:
                dy *= -1.0
                ny = max(y0, min(y1, ny))
                bateu = True
            if bateu and abs(dx) + abs(dy) <= 0.001:
                dx = 1.0
        estado["posicao"] = [float(nx), float(ny)]
        estado["direcao"] = [float(dx), float(dy)]

    def _atualizar_quebradinho(self, layout: dict, trap: dict, estado: dict, players: list, tick: int) -> bool:
        cfg = trap.get("config") if isinstance(trap.get("config"), dict) else {}
        pos = trap.get("posicao") if isinstance(trap.get("posicao"), (list, tuple)) else None
        if pos is None:
            return False
        tx, ty = int(float(pos[0])), int(float(pos[1]))
        fase = str(estado.get("fase") or "inteiro")
        if fase == "buraco":
            return False
        for player in players:
            if self._dist2(player.posicao, [tx + 0.5, ty + 0.5]) <= 0.52 * 0.52:
                if fase == "inteiro":
                    estado["fase"] = "rachando"
                    estado["rachando_desde_tick"] = int(tick)
                break
        if str(estado.get("fase") or "") == "rachando":
            atraso = int(cfg.get("tempo_rachando_ticks", 45) or 45)
            if tick - int(estado.get("rachando_desde_tick", tick) or tick) >= atraso:
                estado["fase"] = "buraco"
                return self._grid_set(layout, tx, ty, int(layout.get("tile_buraco", 10) or 10))
        return False

    def _bolas_barra_fogo(self, trap: dict, tick: int) -> list[list[float]]:
        cfg = trap.get("config") if isinstance(trap.get("config"), dict) else {}
        centro = trap.get("posicao") if isinstance(trap.get("posicao"), (list, tuple)) else [0.0, 0.0]
        bolas = max(1, int(cfg.get("bolas", 4) or 4))
        barras = max(1, int(cfg.get("barras", 1) or 1))
        vel = float(cfg.get("velocidade_giro", 1.1) or 1.1)
        comp = float(cfg.get("comprimento", 2.0) or 2.0)
        ang_base = (tick / self.tick_rate) * vel
        out = []
        for barra in range(barras):
            offset = (math.tau / barras) * barra
            for i in range(1, bolas + 1):
                r = comp * (i / bolas)
                ang = ang_base + offset
                out.append([float(centro[0]) + math.cos(ang) * r, float(centro[1]) + math.sin(ang) * r])
        return out

    def _atualizar_torreta(self, trap: dict, estado: dict, players: list, tick: int) -> None:
        cfg = trap.get("config") if isinstance(trap.get("config"), dict) else {}
        pos = trap.get("posicao") if isinstance(trap.get("posicao"), (list, tuple)) else [0.0, 0.0]
        projeteis = estado.setdefault("projeteis", [])
        vivos = []
        for proj in list(projeteis):
            if not isinstance(proj, dict):
                continue
            direcao = proj.get("direcao") if isinstance(proj.get("direcao"), (list, tuple)) else [1.0, 0.0]
            vel = float(proj.get("velocidade", cfg.get("velocidade_tiro", 5.0)) or 5.0)
            p = proj.get("posicao") if isinstance(proj.get("posicao"), (list, tuple)) else list(pos)
            nx = float(p[0]) + float(direcao[0]) * vel / self.tick_rate
            ny = float(p[1]) + float(direcao[1]) * vel / self.tick_rate
            proj["posicao"] = [nx, ny]
            proj["distancia"] = float(proj.get("distancia", 0.0) or 0.0) + vel / self.tick_rate
            if float(proj["distancia"]) < float(cfg.get("alcance", 8.0) or 8.0):
                vivos.append(proj)
        estado["projeteis"] = vivos
        cooldown = int(cfg.get("cooldown_ticks", 60) or 60)
        if tick < int(estado.get("proximo_tiro_tick", 0) or 0) or not players:
            return
        alvo = min(players, key=lambda p: self._dist2(pos, p.posicao))
        dx = float(alvo.posicao[0]) - float(pos[0])
        dy = float(alvo.posicao[1]) - float(pos[1])
        n = math.hypot(dx, dy) or 1.0
        vivos.append(
            {
                "id": f"{trap.get('id')}_shot_{tick}",
                "posicao": [float(pos[0]), float(pos[1])],
                "direcao": [dx / n, dy / n],
                "velocidade": float(cfg.get("velocidade_tiro", 5.0) or 5.0),
                "distancia": 0.0,
                "raio": float(cfg.get("raio_tiro", 0.18) or 0.18),
            }
        )
        estado["proximo_tiro_tick"] = tick + cooldown

    def executar_tick(
        self,
        layout: dict,
        players: list,
        tick: int,
        aplicar_dano: Callable[[object, str], bool],
        matar_queda: Callable[[object, str], bool],
        registrar_diff: Callable | None = None,
    ) -> bool:
        if not isinstance(layout, dict) or not players:
            return False
        alterou_tiles = False
        salas_por_pos = {
            tuple(s.get("posicao_sala", [0, 0])): s
            for s in layout.get("salas", [])
            if isinstance(s, dict)
        }
        players_por_sala: dict[str, list] = {}
        for player in players:
            if self._player_no_buraco(layout, player):
                matar_queda(player, "queda_buraco")
            sala = salas_por_pos.get(tuple(sala_atual_por_posicao(player.posicao)))
            if isinstance(sala, dict):
                players_por_sala.setdefault(str(sala.get("id") or ""), []).append(player)

        for sala in layout.get("salas", []) if isinstance(layout.get("salas"), list) else []:
            if not isinstance(sala, dict):
                continue
            players_sala = players_por_sala.get(str(sala.get("id") or ""), [])
            cfg_sala = sala.get("config") if isinstance(sala.get("config"), dict) else {}
            for trap in list(cfg_sala.get("armadilhas") or []):
                if not isinstance(trap, dict):
                    continue
                tipo = str(trap.get("tipo") or "")
                estado = self._estado_trap(layout, trap)
                if tipo == "espeto_movel":
                    self._atualizar_espeto_movel(trap, estado)
                elif tipo == "quebradinho":
                    alterou_tiles = self._atualizar_quebradinho(layout, trap, estado, players_sala, int(tick)) or alterou_tiles
                elif tipo == "torreta":
                    self._atualizar_torreta(trap, estado, players_sala, int(tick))
                elif tipo == "barra_fogo":
                    estado["bolas_posicoes"] = self._bolas_barra_fogo(trap, int(tick))

                pontos_dano = []
                if tipo in {"espeto", "espeto_movel"}:
                    pos = estado.get("posicao") if isinstance(estado.get("posicao"), (list, tuple)) else trap.get("posicao", [0.0, 0.0])
                    raio = float((trap.get("config") or {}).get("raio_dano", 0.44) if isinstance(trap.get("config"), dict) else 0.44)
                    pontos_dano.append((pos, raio, tipo))
                elif tipo == "barra_fogo":
                    raio = float((trap.get("config") or {}).get("raio_bola", 0.23) if isinstance(trap.get("config"), dict) else 0.23)
                    pontos_dano.extend((p, raio, "barra_fogo") for p in list(estado.get("bolas_posicoes") or []))
                elif tipo == "torreta":
                    for proj in list(estado.get("projeteis") or []):
                        pontos_dano.append((proj.get("posicao", [0.0, 0.0]), float(proj.get("raio", 0.18) or 0.18), "tiro_torreta"))
                for player in players_sala:
                    raio_player = max(0.1, float(getattr(player, "raio_colisao", 0.55) or 0.55))
                    for pos, raio, motivo in pontos_dano:
                        if self._dist2(player.posicao, pos) <= (raio_player + float(raio)) ** 2:
                            aplicar_dano(player, str(motivo))
                            break

        if callable(registrar_diff):
            estado = layout.get("estado_armadilhas") if isinstance(layout.get("estado_armadilhas"), dict) else {}
            registrar_diff(
                "evento",
                payload={"dimensao": str(layout.get("dimensao") or ""), "estado_armadilhas": estado, "tiles_alterados": bool(alterou_tiles)},
                escopo={"centro": [0.0, 0.0], "raio": 999999.0},
                objeto_id=None,
                autor="server",
                categoria="dungeon_armadilhas",
            )
        return bool(alterou_tiles)
