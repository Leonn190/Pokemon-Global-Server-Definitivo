from __future__ import annotations

from typing import Dict, List

from Codigo.Geradores.PokemonBatalha import PokemonBatalha
from Codigo.ModulosBatalha.Arena import Arena
from Codigo.ModulosBatalha.InicializadorBatalha import InicializadorBatalha, pontos_lados_arena
from Codigo.ModulosBatalha.SistemaBatalha import SistemaBatalha
from Codigo.ModulosBatalha.PlayerBatalha import PlayerBatalha


class ControladorBatalha:
    _MAX_ATIVOS = 3

    def __init__(self, contexto: Dict[str, object]):
        self.Contexto = dict(contexto or {})
        self.Arena = Arena(self.Contexto)
        self.SistemaBatalha = SistemaBatalha(self.Contexto)
        self.PokemonsAliados: List[PokemonBatalha] = []
        self.PokemonsInimigos: List[PokemonBatalha] = []
        self.PokemonsReservaAliados: List[Dict[str, object]] = []
        self.PokemonsReservaInimigos: List[Dict[str, object]] = []
        self.Jogador = PlayerBatalha("jogador", max_ativos=self._MAX_ATIVOS)
        self.Inimigo = PlayerBatalha("inimigo", max_ativos=self._MAX_ATIVOS)
        self.PokemonSelecionado: PokemonBatalha | None = None
        self._inicializar_times()

    def _inicializar_times(self) -> None:
        init = InicializadorBatalha(self.Contexto)
        batalha = init.inicializar()
        self.Contexto["batalha_inicializada"] = batalha

        centro = self.Contexto.get("centro") if isinstance(self.Contexto.get("centro"), (list, tuple)) and len(self.Contexto.get("centro")) == 2 else [40.0, 20.0]
        arena_w = float(self.Contexto.get("arena_largura", 40) or 40)
        arena_h = float(self.Contexto.get("arena_altura", 20) or 20)
        self.Jogador.TimeCompleto = [poke for poke in batalha.get("jogador", []) if isinstance(poke, dict)]
        self.Inimigo.TimeCompleto = [poke for poke in batalha.get("inimigo", []) if isinstance(poke, dict)]
        aliados_ativos = self.Jogador.preparar_slots()
        inimigos_ativos = self.Inimigo.preparar_slots()
        self.PokemonsReservaAliados = list(self.Jogador.PokemonsReserva)
        self.PokemonsReservaInimigos = list(self.Inimigo.PokemonsReserva)
        pos_aliados, pos_inimigos = pontos_lados_arena(
            centro=(float(centro[0]), float(centro[1])),
            largura=arena_w,
            altura=arena_h,
            total_aliados=len(aliados_ativos),
            total_inimigos=len(inimigos_ativos),
        )

        self.PokemonsAliados = [PokemonBatalha(poke, posicao=pos_aliados[i], lado="jogador", regras=self.Contexto) for i, poke in enumerate(aliados_ativos) if i < len(pos_aliados)]
        self.PokemonsInimigos = [PokemonBatalha(poke, posicao=pos_inimigos[i], lado="inimigo", regras=self.Contexto) for i, poke in enumerate(inimigos_ativos) if i < len(pos_inimigos)]
        self.Jogador.definir_ativos(self.PokemonsAliados)
        self.Inimigo.definir_ativos(self.PokemonsInimigos)
        self.SistemaBatalha.definir_lados(self.PokemonsAliados, self.PokemonsInimigos)

    def selecionar_por_mouse(self, mouse_tela_px, camera) -> PokemonBatalha | None:
        alvo = None
        if not isinstance(mouse_tela_px, (tuple, list)) or len(mouse_tela_px) != 2:
            self.PokemonSelecionado = None
            return None
        mx, my = int(mouse_tela_px[0]), int(mouse_tela_px[1])
        for poke in (self.PokemonsAliados + self.PokemonsInimigos):
            cx, cy = poke.centro_tela(camera)
            r = poke.raio_px(camera)
            if (mx - cx) * (mx - cx) + (my - cy) * (my - cy) <= r * r:
                alvo = poke
                break
        if alvo is self.PokemonSelecionado:
            self.PokemonSelecionado = None
        else:
            self.PokemonSelecionado = alvo
        return self.PokemonSelecionado

    def atualizar(self, eventos, dt: float) -> None:
        self.SistemaBatalha.atualizar(eventos, dt)

    def renderizar(self, tela, camera) -> None:
        self.Arena.renderizar(tela, camera)
        for poke in self.PokemonsAliados:
            poke.renderizar(tela, camera, selecionado=(poke is self.PokemonSelecionado))
        for poke in self.PokemonsInimigos:
            poke.renderizar(tela, camera, selecionado=(poke is self.PokemonSelecionado))
