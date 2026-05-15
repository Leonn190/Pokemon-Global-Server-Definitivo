"""Mixin de movimento fisico e colisao do ControladorPlayer."""

from __future__ import annotations

from typing import Tuple
import time

from Codigo.ModulosGerais.Colisor import Colisor


class MovimentoPlayerMixin:
    def _correcao_servidor_bloqueando(self) -> bool:
        return time.monotonic() < float(self._bloqueio_correcao_servidor_ate)

    def _ativar_bloqueio_correcao(self) -> None:
        self._bloqueio_correcao_servidor_ate = time.monotonic() + float(self._janela_bloqueio_correcao_s)

    def _resolver_colisao_player_local(self, posicao_antes: Tuple[float, float], dt: float) -> None:
        ator = self._player_local
        if ator is None:
            return
        depois = tuple(ator.Posicao)
        player_id = getattr(ator, "Id", None)
        raio_ator = max(0.0, float(getattr(getattr(ator, "Colisor", None), "raio_colisao", 0.35)))
        colisores_brutos = [c for c in self._objetos.iter_colisores_proximos_por_raio(depois, raio_tiles=10.0) if c[0] != player_id]
        if colisores_brutos:
            margem = 0.25
            filtrados = []
            for c in colisores_brutos:
                oid, sx, sy, raio_obj, tipo_obj, *_ = c
                d2 = ((float(sx) - float(depois[0])) ** 2 + (float(sy) - float(depois[1])) ** 2)
                if str(tipo_obj).strip().lower() in {"entidade_pokemon", "pokemon"}:
                    limite_real = float(raio_ator + raio_obj)
                    if d2 <= (limite_real * limite_real):
                        if not self._ator_bloqueia_batalha(ator):
                            payload_pokemon = self._objetos.snapshot_objeto_por_id(int(oid))
                            if isinstance(payload_pokemon, dict) and payload_pokemon:
                                self._colisao_pokemon_pendente = payload_pokemon
                            else:
                                self._colisao_pokemon_pendente = {"id": int(oid), "posicao": [float(sx), float(sy)]}
                    continue
                limite = float(raio_ator + raio_obj + margem)
                if d2 <= (limite * limite):
                    filtrados.append(c)
            if len(filtrados) > 24:
                filtrados.sort(key=lambda c: ((float(c[1]) - float(depois[0])) ** 2 + (float(c[2]) - float(depois[1])) ** 2))
                colisores = filtrados[:24]
            else:
                colisores = filtrados
        else:
            colisores = []
        px, py = Colisor.resolver_movimento_com_colisores(
            posicao_antes=posicao_antes,
            posicao_depois=depois,
            raio_entidade=raio_ator,
            colisores=colisores,
            dt=dt,
        )
        px, py = self._resolver_limites_dungeon(posicao_antes, (px, py), raio_ator)
        ator.definir_posicao(px, py)
        self._normalizar_posicao_player_local()

    def _resolver_limites_dungeon(self, antes, depois, raio):
        dim = str(self._objetos.dimensao_atual_client() or "Mundo")
        layout = self._objetos.LayoutDungeonAtual if isinstance(getattr(self._objetos, "LayoutDungeonAtual", None), dict) else {}
        if not dim.startswith("Dungeon_") or not layout:
            return depois
        bloco_w = int(layout.get("largura_bloco_sala_tiles", layout.get("tamanho_bloco_sala_tiles", 32)) or 32)
        bloco_h = int(layout.get("altura_bloco_sala_tiles", layout.get("tamanho_bloco_sala_tiles", 24)) or 24)
        salas = {
            tuple(s.get("posicao_sala", [])): s
            for s in layout.get("salas", []) if isinstance(s, dict) and isinstance(s.get("posicao_sala"), (list, tuple))
        }
        a = (int(float(antes[0]) // bloco_w), int(float(antes[1]) // bloco_h))
        d = (int(float(depois[0]) // bloco_w), int(float(depois[1]) // bloco_h))
        if d not in salas:
            return self._clamp_sala_pos(antes, a, bloco_w, bloco_h, raio, layout, salas.get(a, {}))
        if a == d:
            return self._clamp_sala_pos(depois, a, bloco_w, bloco_h, raio, layout, salas.get(a, {}))
        if a not in salas or abs(a[0] - d[0]) + abs(a[1] - d[1]) != 1:
            return self._clamp_sala_pos(antes, a, bloco_w, bloco_h, raio, layout, salas.get(a, {}))
        direcao = "L" if d[0] > a[0] else "O" if d[0] < a[0] else "S" if d[1] > a[1] else "N"
        sala = salas.get(a, {})
        info = next((p for p in list(sala.get("portas_info") or []) if str(p.get("direcao") or "") == direcao), None)
        if not isinstance(info, dict) or bool(info.get("trancada", False)):
            return self._clamp_sala_pos(antes, a, bloco_w, bloco_h, raio, layout, sala)
        porta_w = max(1, int(layout.get("porta_largura_tiles", 4) or 4))
        if direcao in {"N", "S"}:
            centro = a[0] * bloco_w + bloco_w * 0.5
            if abs(float(depois[0]) - centro) > (porta_w * 0.5):
                return self._clamp_sala_pos(antes, a, bloco_w, bloco_h, raio, layout, sala)
        else:
            centro = a[1] * bloco_h + bloco_h * 0.5
            if abs(float(depois[1]) - centro) > (porta_w * 0.5):
                return self._clamp_sala_pos(antes, a, bloco_w, bloco_h, raio, layout, sala)
        return depois

    @staticmethod
    def _pos_em_abertura(pos, sala_idx, bloco_w, bloco_h, raio, layout, sala):
        if not isinstance(sala, dict):
            return False
        bx, by = sala_idx
        parede = max(1, int(layout.get("parede_largura_tiles", 2) or 2))
        porta_w = max(1, int(layout.get("porta_largura_tiles", 4) or 4))
        x, y = float(pos[0]), float(pos[1])
        x0, y0 = bx * bloco_w, by * bloco_h
        x1, y1 = (bx + 1) * bloco_w, (by + 1) * bloco_h
        if x < x0 - raio or x > x1 + raio or y < y0 - raio or y > y1 + raio:
            return False
        for info in list(sala.get("portas_info") or []):
            if bool(info.get("trancada", False)):
                continue
            direcao = str(info.get("direcao") or "")
            if direcao in {"N", "S"}:
                centro = x0 + bloco_w * 0.5
                if abs(x - centro) > porta_w * 0.5:
                    continue
                if direcao == "N" and y <= y0 + parede + raio:
                    return True
                if direcao == "S" and y >= y1 - parede - raio:
                    return True
            elif direcao in {"L", "O"}:
                centro = y0 + bloco_h * 0.5
                if abs(y - centro) > porta_w * 0.5:
                    continue
                if direcao == "O" and x <= x0 + parede + raio:
                    return True
                if direcao == "L" and x >= x1 - parede - raio:
                    return True
        return False

    @staticmethod
    def _clamp_sala_pos(pos, sala_idx, bloco_w, bloco_h, raio, layout=None, sala=None):
        bx, by = sala_idx
        layout = layout if isinstance(layout, dict) else {}
        sala = sala or {}
        if MovimentoPlayerMixin._pos_em_abertura(pos, sala_idx, bloco_w, bloco_h, raio, layout, sala):
            return (float(pos[0]), float(pos[1]))
        margem = max(0.08, float(raio)) + max(1, int(layout.get("parede_largura_tiles", 2) or 2))
        if bx < 0 or by < 0:
            return pos
        return (
            max(bx * bloco_w + margem, min((bx + 1) * bloco_w - margem, float(pos[0]))),
            max(by * bloco_h + margem, min((by + 1) * bloco_h - margem, float(pos[1]))),
        )

    @staticmethod
    def _clamp_passagem(pos, sala_idx, bloco_w, bloco_h, raio, layout, sala):
        if not isinstance(sala, dict):
            return None
        bx, by = sala_idx
        parede = max(1, int(layout.get("parede_largura_tiles", 2) or 2))
        porta_w = max(1, int(layout.get("porta_largura_tiles", 4) or 4))
        x, y = float(pos[0]), float(pos[1])
        x0, y0 = bx * bloco_w, by * bloco_h
        x1, y1 = (bx + 1) * bloco_w, (by + 1) * bloco_h
        folga = max(0.1, float(raio))
        for info in list(sala.get("portas_info") or []):
            if bool(info.get("trancada", False)):
                continue
            direcao = str(info.get("direcao") or "")
            if direcao in {"N", "S"}:
                centro = x0 + bloco_w * 0.5
                min_x = centro - porta_w * 0.5 + folga
                max_x = centro + porta_w * 0.5 - folga
                if min_x > max_x:
                    min_x = max_x = centro
                if x < min_x or x > max_x:
                    continue
                if direcao == "N" and y <= y0 + parede + folga:
                    return (max(min_x, min(max_x, x)), max(y0 - folga, min(y0 + parede + folga, y)))
                if direcao == "S" and y >= y1 - parede - folga:
                    return (max(min_x, min(max_x, x)), max(y1 - parede - folga, min(y1 + folga, y)))
            elif direcao in {"L", "O"}:
                centro = y0 + bloco_h * 0.5
                min_y = centro - porta_w * 0.5 + folga
                max_y = centro + porta_w * 0.5 - folga
                if min_y > max_y:
                    min_y = max_y = centro
                if y < min_y or y > max_y:
                    continue
                if direcao == "O" and x <= x0 + parede + folga:
                    return (max(x0 - folga, min(x0 + parede + folga, x)), max(min_y, min(max_y, y)))
                if direcao == "L" and x >= x1 - parede - folga:
                    return (max(x1 - parede - folga, min(x1 + folga, x)), max(min_y, min(max_y, y)))
        return None

    def _normalizar_posicao_player_local(self) -> None:
        ator = self._player_local
        controle = getattr(ator, "Controle", None) if ator is not None else None
        if controle is None:
            return
        normalizar = getattr(controle, "normalizar_posicao_mundo", None)
        if callable(normalizar):
            normalizar()
