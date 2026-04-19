from __future__ import annotations

from typing import Dict

from Codigo.Geradores.PokemonMundo import Pokemon
from Codigo.ModulosGerais.Camera import CameraBatalha
from Codigo.ModulosGerais.FiltroCamera import FiltroCamera
from Codigo.Paineis.FichaPokemon import FichaPokemon
from Codigo.Server.ServerMundo import coletar_regras_mundo


class ModuladorRegras:
    def __init__(self) -> None:
        self._regras: Dict[str, object] = {}

    def coletar_regras(self, ip_server: str) -> Dict[str, object]:
        if not str(ip_server or "").strip():
            return {}
        resposta = coletar_regras_mundo(ip_server)
        if not isinstance(resposta, dict) or str(resposta.get("status")) != "ok":
            return {}
        regras = resposta.get("regras") if isinstance(resposta.get("regras"), dict) else {}
        self._regras = dict(regras)
        return dict(self._regras)

    def obter(self) -> Dict[str, object]:
        return dict(self._regras)

    def definir_regras(self, regras: Dict[str, object]) -> None:
        self._regras = dict(regras or {})

    def aplicar_em_cena_mundo(self, cena, jogo) -> None:
        if cena is None or jogo is None:
            return
        regras = self.obter()
        if not regras:
            return

        jogo.INFO["RegrasMundo"] = dict(regras)

        mundo = regras.get("mundo") if isinstance(regras.get("mundo"), dict) else {}
        chunk_tiles = mundo.get("chunk_tiles")
        if chunk_tiles is not None and getattr(cena, "ControladorMundo", None) is not None:
            try:
                cena.ControladorMundo.Objetos._chunk_tamanho_tiles = int(chunk_tiles)
            except (TypeError, ValueError, AttributeError):
                pass

        pokemons = regras.get("pokemons") if isinstance(regras.get("pokemons"), dict) else {}
        intervalo_anim = pokemons.get("animacao_intervalo_frame_ms")
        incremento_tamanho = pokemons.get("tamanho_incremento_por_escala", pokemons.get("tamanho_incremento_por_tamanho"))
        diametro_base_tamanho = pokemons.get("tamanho_diametro_base_tiles")
        if intervalo_anim is not None:
            Pokemon._INTERVALO_FRAME_ANIM_MS = int(intervalo_anim)
            FichaPokemon._INTERVALO_FRAME_ANIM_MS = int(intervalo_anim)
        if incremento_tamanho is not None:
            Pokemon._INCREMENTO_DIAMETRO_POR_ESCALA = float(incremento_tamanho)
        if diametro_base_tamanho is not None:
            Pokemon._DIAMETRO_BASE_TILES = float(diametro_base_tamanho)

        gerais = regras.get("gerais") if isinstance(regras.get("gerais"), dict) else {}
        zoom_min = gerais.get("combate_camera_zoom_min")
        zoom_max = gerais.get("combate_camera_zoom_max")
        if zoom_min is not None and zoom_max is not None:
            CameraBatalha.TILE_MIN = int(zoom_min)
            CameraBatalha.TILE_MAX = int(zoom_max)

        ciclo = regras.get("ciclo") if isinstance(regras.get("ciclo"), dict) else {}
        iluminacao = ciclo.get("iluminacao") if isinstance(ciclo.get("iluminacao"), dict) else {}
        if iluminacao:
            FiltroCamera.reconfigurar_iluminacao(iluminacao)
