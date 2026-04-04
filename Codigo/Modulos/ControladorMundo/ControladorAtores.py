"""Controlador de atores remotos (players e NPCs do servidor)."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from Codigo.Geradores.Ator import Ator
from Codigo.Geradores.Player.Inventario import Inventario
from Codigo.Geradores.Player.Perfil import Perfil


class ControladorAtores:
    def __init__(self) -> None:
        self.AtoresRemotosPorId: Dict[int, Ator] = {}

    def upsert(self, oid: int, payload: Dict[str, object], id_player_local: int = -1) -> Optional[Ator]:
        if int(oid) == int(id_player_local):
            self.AtoresRemotosPorId.pop(int(oid), None)
            return None
        tipo = str(payload.get("tipo", "")).strip().lower()
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        subtipo = str(estado.get("subtipo", "")).strip().lower()
        if tipo != "entidade_player" and subtipo not in {"npc_vendedor"}:
            self.AtoresRemotosPorId.pop(int(oid), None)
            return None

        dados = dict(payload)
        dados["id"] = int(oid)
        pos = dados.get("posicao", (0.0, 0.0))
        if not isinstance(pos, (list, tuple)) or len(pos) != 2:
            pos = (0.0, 0.0)

        remoto = self.AtoresRemotosPorId.get(int(oid))
        if remoto is None:
            remoto = Ator(nome_skin=str(dados.get("skin", "S1")), posicao=(float(pos[0]), float(pos[1])), escala_skin_tiles=1.0, tile_px=50)
            remoto.Id = int(oid)
            self.AtoresRemotosPorId[int(oid)] = remoto

        remoto.definir_posicao(float(pos[0]), float(pos[1]))
        nome = dados.get("nome") or dados.get("usuario")
        if nome:
            remoto.Nome = str(nome)
        skin = dados.get("skin")
        if skin and str(skin) != str(getattr(remoto, "NomeSkin", "")):
            remoto.set_nome_skin(str(skin))

        if "angulo" in estado:
            remoto.definir_angulo_olhar(float(estado.get("angulo", 0.0)))
        if bool(estado.get("tapa")):
            remoto.iniciar_tapa()

        if remoto.Perfil is None:
            remoto.Perfil = Perfil()
        if remoto.Inventario is None:
            remoto.Inventario = Inventario()
        if isinstance(dados.get("perfil"), dict):
            remoto.Perfil.aplicar_serializado(dados.get("perfil"))
        if isinstance(dados.get("inventario"), dict):
            remoto.Inventario.aplicar_serializado(dados.get("inventario"))

        remoto.update(dados)
        return remoto

    def remover(self, oid: int) -> None:
        self.AtoresRemotosPorId.pop(int(oid), None)

    def renderizar(self, oid: int, tela, camera, dt: float) -> bool:
        ator = self.AtoresRemotosPorId.get(int(oid))
        if ator is None:
            return False
        ator.atualizar(dt)
        ator.set_tile_px(getattr(camera, "TilePx", 50))
        pos_tela = camera.mundo_para_tela_px(ator.Posicao)
        ator.desenhar(tela, posicao_tela=pos_tela, respiracao_tempo=0.0)
        if getattr(ator, "Nome", ""):
            Ator.desenhar_nome(tela, pos_tela, ator.Nome)
        return True

    def npc_proximo(self, objetos: Dict[int, Dict[str, object]], posicao: Tuple[float, float], raio: float = 2.2) -> Optional[Dict[str, object]]:
        px, py = float(posicao[0]), float(posicao[1])
        melhor = None
        melhor_d2 = None
        for oid, obj in objetos.items():
            if not isinstance(obj, dict):
                continue
            estado = obj.get("estado") if isinstance(obj.get("estado"), dict) else {}
            subtipo = str(estado.get("subtipo", "")).strip().lower()
            if subtipo != "npc_vendedor":
                continue
            inter = estado.get("interacao") if isinstance(estado.get("interacao"), dict) else {}
            if bool(inter.get("ativa", False)):
                continue
            pos = obj.get("posicao")
            if not isinstance(pos, (list, tuple)) or len(pos) != 2:
                continue
            dx = float(pos[0]) - px
            dy = float(pos[1]) - py
            d2 = (dx * dx) + (dy * dy)
            if d2 > (raio * raio):
                continue
            if melhor_d2 is None or d2 < melhor_d2:
                melhor_d2 = d2
                melhor = {"id": int(oid), "obj": obj}
        return melhor
