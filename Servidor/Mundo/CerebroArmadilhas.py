from __future__ import annotations

import math
import random
from typing import Callable

from Servidor.Mundo.DungeonGeometria import sala_atual_por_posicao


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

    @staticmethod
    def _ponto_em_passagem_sala(layout: dict, sala: dict, x: float, y: float, raio: float) -> bool:
        pos_sala = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else None
        if pos_sala is None:
            return False
        bloco_w = int(layout.get("largura_bloco_sala_tiles", layout.get("tamanho_bloco_sala_tiles", 32)) or 32)
        bloco_h = int(layout.get("altura_bloco_sala_tiles", layout.get("tamanho_bloco_sala_tiles", 24)) or 24)
        parede = max(1, int(layout.get("parede_largura_tiles", 2) or 2))
        porta_w = max(1, int(layout.get("porta_largura_tiles", 4) or 4))
        bx, by = int(pos_sala[0]), int(pos_sala[1])
        x0, y0 = bx * bloco_w, by * bloco_h
        x1, y1 = (bx + 1) * bloco_w, (by + 1) * bloco_h
        folga = max(0.0, float(raio))
        for info in list(sala.get("portas_info") or []):
            if not isinstance(info, dict):
                continue
            direcao = str(info.get("direcao") or "")
            if direcao in {"N", "S"}:
                centro = x0 + bloco_w * 0.5
                if abs(float(x) - centro) > porta_w * 0.5 + folga:
                    continue
                if direcao == "N" and float(y) <= y0 + parede + folga:
                    return True
                if direcao == "S" and float(y) >= y1 - parede - folga:
                    return True
            elif direcao in {"L", "O"}:
                centro = y0 + bloco_h * 0.5
                if abs(float(y) - centro) > porta_w * 0.5 + folga:
                    continue
                if direcao == "O" and float(x) <= x0 + parede + folga:
                    return True
                if direcao == "L" and float(x) >= x1 - parede - folga:
                    return True
        return False

    def _espeto_ricochete_bloqueado(self, layout: dict, sala: dict, x: float, y: float, raio: float, ignorar_trap_id: str) -> bool:
        pos_sala = sala.get("posicao_sala") if isinstance(sala.get("posicao_sala"), (list, tuple)) else None
        if pos_sala is not None and tuple(sala_atual_por_posicao([x, y])) != (int(pos_sala[0]), int(pos_sala[1])):
            return True
        if self._ponto_em_passagem_sala(layout, sala, x, y, raio):
            return True
        tile_vazio = int(layout.get("tile_vazio_dungeon", 9) or 9)
        amostras = [(0.0, 0.0), (raio, 0.0), (-raio, 0.0), (0.0, raio), (0.0, -raio)]
        for ox, oy in amostras:
            tile = self._grid_tile(layout, float(x) + float(ox), float(y) + float(oy))
            if tile is None or int(tile) == tile_vazio:
                return True
        cfg_sala = sala.get("config") if isinstance(sala.get("config"), dict) else {}
        for trap in list(cfg_sala.get("armadilhas") or []):
            if not isinstance(trap, dict) or str(trap.get("id") or "") == str(ignorar_trap_id or ""):
                continue
            tcfg = trap.get("config") if isinstance(trap.get("config"), dict) else {}
            if not bool(tcfg.get("solido", False) or tcfg.get("solido_centro", False)):
                continue
            pos = trap.get("posicao") if isinstance(trap.get("posicao"), (list, tuple)) else None
            if pos is None:
                continue
            limite = float(raio) + float(tcfg.get("raio_colisao", 0.58) or 0.58)
            if self._dist2([x, y], pos) <= limite * limite:
                return True
        return False

    def _atualizar_espeto_ricochete(self, layout: dict, sala: dict, trap: dict, estado: dict) -> None:
        cfg = trap.get("config") if isinstance(trap.get("config"), dict) else {}
        pos0 = trap.get("posicao") if isinstance(trap.get("posicao"), (list, tuple)) else [0.0, 0.0]
        pos = estado.get("posicao") if isinstance(estado.get("posicao"), (list, tuple)) else [float(pos0[0]), float(pos0[1])]
        direcao = estado.get("direcao") if isinstance(estado.get("direcao"), (list, tuple)) else cfg.get("direcao")
        if not isinstance(direcao, (list, tuple)) or len(direcao) != 2:
            rng = random.Random(int(cfg.get("seed", 1) or 1))
            ang = rng.random() * math.tau
            direcao = [math.cos(ang), math.sin(ang)]
        dx, dy = float(direcao[0]), float(direcao[1])
        n = math.hypot(dx, dy) or 1.0
        dx, dy = dx / n, dy / n
        vel = float(cfg.get("velocidade", 2.6) or 2.6)
        raio = float(cfg.get("raio_colisao", cfg.get("raio_dano", 0.45)) or 0.45)
        passo = vel / self.tick_rate
        x, y = float(pos[0]), float(pos[1])
        nx, ny = x + dx * passo, y + dy * passo
        tid = str(trap.get("id") or "")
        if self._espeto_ricochete_bloqueado(layout, sala, nx, ny, raio, tid):
            x_livre = not self._espeto_ricochete_bloqueado(layout, sala, nx, y, raio, tid)
            y_livre = not self._espeto_ricochete_bloqueado(layout, sala, x, ny, raio, tid)
            if x_livre and not y_livre:
                x = nx
                dy *= -1.0
            elif y_livre and not x_livre:
                y = ny
                dx *= -1.0
            else:
                dx *= -1.0
                dy *= -1.0
        else:
            x, y = nx, ny
        estado["posicao"] = [float(x), float(y)]
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

    def _resetar_quebradinhos_sala_vazia(self, layout: dict, sala: dict) -> bool:
        cfg_sala = sala.get("config") if isinstance(sala.get("config"), dict) else {}
        alterou_tiles = False
        for trap in list(cfg_sala.get("armadilhas") or []):
            if not isinstance(trap, dict) or str(trap.get("tipo") or "") != "quebradinho":
                continue
            estado = self._estado_trap(layout, trap)
            estado["fase"] = "inteiro"
            estado.pop("rachando_desde_tick", None)
            pos = trap.get("posicao") if isinstance(trap.get("posicao"), (list, tuple)) else None
            if pos is None:
                continue
            cfg = trap.get("config") if isinstance(trap.get("config"), dict) else {}
            tile_original = int(cfg.get("tile_original", layout.get("tile_chao_dungeon", 8)) or layout.get("tile_chao_dungeon", 8) or 8)
            alterou_tiles = self._grid_set(layout, int(float(pos[0])), int(float(pos[1])), tile_original) or alterou_tiles
        return alterou_tiles

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

    def _projetil_bloqueado(self, layout: dict, x: float, y: float, ignorar_trap_id: str = "", sala: dict | None = None) -> bool:
        pos_sala = sala.get("posicao_sala") if isinstance(sala, dict) and isinstance(sala.get("posicao_sala"), (list, tuple)) else None
        if pos_sala is not None and tuple(sala_atual_por_posicao([x, y])) != (int(pos_sala[0]), int(pos_sala[1])):
            return True
        tile = self._grid_tile(layout, x, y)
        if tile is None:
            return True
        tile_vazio = int(layout.get("tile_vazio_dungeon", 9) or 9)
        if int(tile) == tile_vazio:
            return True
        for sala in layout.get("salas", []) if isinstance(layout.get("salas"), list) else []:
            if not isinstance(sala, dict):
                continue
            cfg_sala = sala.get("config") if isinstance(sala.get("config"), dict) else {}
            for trap in list(cfg_sala.get("armadilhas") or []):
                if not isinstance(trap, dict):
                    continue
                if str(trap.get("id") or "") == str(ignorar_trap_id or ""):
                    continue
                tipo = str(trap.get("tipo") or "")
                if tipo == "espeto_movel":
                    continue
                tcfg = trap.get("config") if isinstance(trap.get("config"), dict) else {}
                if not bool(tcfg.get("solido", False) or tcfg.get("solido_centro", False)):
                    continue
                pos = trap.get("posicao") if isinstance(trap.get("posicao"), (list, tuple)) else None
                if pos is None:
                    continue
                raio = float(tcfg.get("raio_colisao", 0.58) or 0.58)
                if self._dist2([x, y], pos) <= raio * raio:
                    return True
        return False

    def _atualizar_torreta(self, layout: dict, sala: dict, trap: dict, estado: dict, players: list, tick: int, aplicar_dano: Callable[[object, str], bool] | None = None) -> None:
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
            if self._projetil_bloqueado(layout, nx, ny, ignorar_trap_id=str(trap.get("id") or ""), sala=sala):
                continue
            proj["posicao"] = [nx, ny]
            proj["distancia"] = float(proj.get("distancia", 0.0) or 0.0) + vel / self.tick_rate
            raio_proj = float(proj.get("raio", cfg.get("raio_tiro", 0.18)) or 0.18)
            atingiu_player = False
            for player in players:
                raio_player = max(0.1, float(getattr(player, "raio_colisao", 0.55) or 0.55))
                if self._dist2(player.posicao, [nx, ny]) <= (raio_player + raio_proj) ** 2:
                    if callable(aplicar_dano):
                        aplicar_dano(player, "tiro_torreta")
                    atingiu_player = True
                    break
            if not atingiu_player:
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
        iniciar_queda: Callable[[object, str], bool],
        registrar_diff: Callable | None = None,
    ) -> bool:
        if not isinstance(layout, dict):
            return False
        players = list(players or [])
        players = [p for p in players if not bool(getattr(p, "estado_extra", {}).get("morto", False) or getattr(p, "estado_extra", {}).get("game_over", False))]
        alterou_tiles = False
        salas_por_pos = {
            tuple(s.get("posicao_sala", [0, 0])): s
            for s in layout.get("salas", [])
            if isinstance(s, dict)
        }
        players_por_sala: dict[str, list] = {}
        for player in players:
            if self._player_no_buraco(layout, player):
                iniciar_queda(player, "queda_buraco")
                continue
            sala = salas_por_pos.get(tuple(sala_atual_por_posicao(player.posicao)))
            if isinstance(sala, dict):
                players_por_sala.setdefault(str(sala.get("id") or ""), []).append(player)

        for sala in layout.get("salas", []) if isinstance(layout.get("salas"), list) else []:
            if not isinstance(sala, dict):
                continue
            players_sala = players_por_sala.get(str(sala.get("id") or ""), [])
            if not players_sala:
                alterou_tiles = self._resetar_quebradinhos_sala_vazia(layout, sala) or alterou_tiles
                if not players:
                    continue
            cfg_sala = sala.get("config") if isinstance(sala.get("config"), dict) else {}
            for trap in list(cfg_sala.get("armadilhas") or []):
                if not isinstance(trap, dict):
                    continue
                tipo = str(trap.get("tipo") or "")
                estado = self._estado_trap(layout, trap)
                if tipo == "espeto_movel":
                    self._atualizar_espeto_movel(trap, estado)
                elif tipo == "espeto_ricochete":
                    self._atualizar_espeto_ricochete(layout, sala, trap, estado)
                elif tipo == "quebradinho":
                    alterou_tiles = self._atualizar_quebradinho(layout, trap, estado, players_sala, int(tick)) or alterou_tiles
                elif tipo == "torreta":
                    self._atualizar_torreta(layout, sala, trap, estado, players_sala, int(tick), aplicar_dano)
                elif tipo == "barra_fogo":
                    estado["bolas_posicoes"] = self._bolas_barra_fogo(trap, int(tick))

                pontos_dano = []
                if tipo in {"espeto", "espeto_movel", "espeto_ricochete"}:
                    pos = estado.get("posicao") if isinstance(estado.get("posicao"), (list, tuple)) else trap.get("posicao", [0.0, 0.0])
                    raio = float((trap.get("config") or {}).get("raio_dano", 0.44) if isinstance(trap.get("config"), dict) else 0.44)
                    pontos_dano.append((pos, raio, tipo))
                elif tipo == "barra_fogo":
                    raio = float((trap.get("config") or {}).get("raio_bola", 0.23) if isinstance(trap.get("config"), dict) else 0.23)
                    pontos_dano.extend((p, raio, "barra_fogo") for p in list(estado.get("bolas_posicoes") or []))
                for player in players_sala:
                    raio_player = max(0.1, float(getattr(player, "raio_colisao", 0.55) or 0.55))
                    for pos, raio, motivo in pontos_dano:
                        if self._dist2(player.posicao, pos) <= (raio_player + float(raio)) ** 2:
                            aplicar_dano(player, str(motivo))
                            break

        if callable(registrar_diff) and (players or alterou_tiles):
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
