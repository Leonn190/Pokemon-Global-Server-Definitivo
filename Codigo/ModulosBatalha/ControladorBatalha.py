from __future__ import annotations

from typing import Dict, List

from Codigo.Geradores.PokemonBatalha import PokemonBatalha
from Codigo.ModulosBatalha.Arena import Arena
from Codigo.ModulosBatalha.InicializadorBatalha import InicializadorBatalha, pontos_lados_arena
from Codigo.ModulosBatalha.SistemaBatalha import SistemaBatalha


class ControladorBatalha:
    def __init__(self, contexto: Dict[str, object]):
        self.Contexto = dict(contexto or {})
        self.Arena = Arena(self.Contexto)
        self.SistemaBatalha = SistemaBatalha(self.Contexto)
        self.PokemonsAliados: List[PokemonBatalha] = []
        self.PokemonsInimigos: List[PokemonBatalha] = []
        self._inicializar_times()

    def _inicializar_times(self) -> None:
        init = InicializadorBatalha(self.Contexto)
        batalha = init.inicializar()
        self.Contexto["batalha_inicializada"] = batalha

        centro = self.Contexto.get("centro") if isinstance(self.Contexto.get("centro"), (list, tuple)) and len(self.Contexto.get("centro")) == 2 else [50.0, 30.0]
        arena_w = float(self.Contexto.get("arena_largura", 50) or 50)
        arena_h = float(self.Contexto.get("arena_altura", 30) or 30)
        pos_aliados, pos_inimigos = pontos_lados_arena(
            centro=(float(centro[0]), float(centro[1])),
            largura=arena_w,
            altura=arena_h,
            total_aliados=len(batalha.get("jogador", [])),
            total_inimigos=len(batalha.get("inimigo", [])),
        )

        self.PokemonsAliados = [PokemonBatalha(poke, posicao=pos_aliados[i], lado="jogador") for i, poke in enumerate(batalha.get("jogador", [])) if i < len(pos_aliados)]
        self.PokemonsInimigos = [PokemonBatalha(poke, posicao=pos_inimigos[i], lado="inimigo") for i, poke in enumerate(batalha.get("inimigo", [])) if i < len(pos_inimigos)]
        self.SistemaBatalha.definir_lados(self.PokemonsAliados, self.PokemonsInimigos)

    def atualizar(self, eventos, dt: float) -> None:
        self.SistemaBatalha.atualizar(eventos, dt)

    def renderizar(self, tela, camera) -> None:
        self.Arena.renderizar(tela, camera)
        for poke in self.PokemonsAliados:
            poke.renderizar(tela, camera)
        for poke in self.PokemonsInimigos:
            poke.renderizar(tela, camera)
