from __future__ import annotations

import csv
import os
import random
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Codigo.ModulosGerais.Camera import CameraBatalha
from Codigo.ModulosBatalha.ControladorBatalha import ControladorBatalha
from Codigo.ModulosBatalha.ElementosHudBatalha import ElementosHudBatalha
from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import criar_pokemon_inicial_materializado


def carregar_especies_validas() -> list[str]:
    arquivo = ROOT / "Dados" / "Pokemon Global Server - Pokemons.csv"
    if not arquivo.exists():
        return []
    with arquivo.open("r", encoding="utf-8-sig") as f:
        return [str(row.get("Nome") or "").strip() for row in csv.DictReader(f) if str(row.get("Nome") or "").strip()]


def sortear_especies(especies: list[str], total: int = 12) -> list[str]:
    unicas = list(dict.fromkeys(nome for nome in especies if str(nome).strip()))
    seed = os.environ.get("BATALHA_TESTE_SEED")
    rng = random.Random(seed) if seed else random.Random()
    if len(unicas) >= total:
        return rng.sample(unicas, total)
    if not unicas:
        raise RuntimeError("Nenhuma especie valida encontrada no CSV de Pokemons.")
    sorteadas = list(unicas)
    while len(sorteadas) < total:
        sorteadas.append(rng.choice(unicas))
    rng.shuffle(sorteadas)
    return sorteadas[:total]


def montar_time(especies: list[str]) -> dict:
    if len(especies) != 6:
        raise RuntimeError(f"Era esperado montar exatamente 6 espécies, mas vieram {len(especies)}.")
    slots = [criar_pokemon_inicial_materializado(especie) for especie in especies[:6]]
    if len(slots) != 6:
        raise RuntimeError(f"Falha ao materializar 6 Pokémon. Total materializado: {len(slots)}.")
    return {"Nome": "TimeTeste", "Slots": slots}


def main() -> int:
    pygame.init()
    try:
        tela = pygame.display.set_mode((1920, 1080))
    except pygame.error:
        tela = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Pokemon Global Server - BatalhaTeste")
    clock = pygame.time.Clock()
    fonte = pygame.font.SysFont("consolas", 24)

    nomes_validos = carregar_especies_validas()
    sorteio = sortear_especies(nomes_validos, total=12)
    jogador = sorteio[:6]
    inimigo = sorteio[6:12]

    time_jogador = montar_time(jogador)
    time_inimigo = montar_time(inimigo)
    contexto = {
        "tipo": "treinador",
        "time_jogador": time_jogador,
        "npc_contexto": {"times_pokemon": [time_inimigo], "batalha_numero": 1},
        "arena_largura": 40,
        "arena_altura": 20,
        "largura": 80,
        "altura": 40,
        "centro": [40.0, 20.0],
        "modo_teste": False,
        "energia_infinita_teste": False,
        "batalha_teste_local": True,
        "client_id": "batalha_teste_local",
    }

    camera = CameraBatalha(tela.get_size(), posicao_inicial_tiles=(20.0, 8.0), tile_px=40)
    camera.definir_limites_mundo(80, 40)
    camera.definir_referencia_arena((20.0, 10.0), (40.0, 20.0))
    controlador = ControladorBatalha(contexto)
    hud = ElementosHudBatalha(controlador_batalha=controlador, camera=camera)

    botao = pygame.Rect(20, 72, 280, 46)
    rodando = True
    def alternar_modo_teste() -> None:
        ativo = not controlador.modo_teste_ativo()
        controlador.definir_modo_teste(ativo)
        contexto["modo_teste"] = ativo
        contexto["energia_infinita_teste"] = ativo
        controlador.Contexto["modo_teste"] = ativo
        controlador.Contexto["energia_infinita_teste"] = ativo

    while rodando:
        dt = clock.tick(180) / 1000.0
        eventos = pygame.event.get()
        for ev in eventos:
            if ev.type == pygame.QUIT:
                rodando = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_F2:
                alternar_modo_teste()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and botao.collidepoint(ev.pos):
                alternar_modo_teste()

        camera.TamanhoTelaPx = tela.get_size()
        camera.processar_eventos(eventos)
        camera.atualizar(dt)
        controlador.atualizar(eventos, dt)

        tela.fill((22, 24, 30))
        controlador.renderizar_arena(tela, camera)
        hud.desenhar_indicadores_campo(tela)
        controlador.renderizar_pokemons(tela, camera)
        hud.desenhar(tela, eventos, dt)

        pygame.draw.rect(tela, (28, 44, 62), botao, border_radius=8)
        pygame.draw.rect(tela, (170, 200, 232), botao, 2, border_radius=8)
        texto_botao = fonte.render(f"Modo teste: {'ON' if controlador.modo_teste_ativo() else 'OFF'} (F2)", True, (240, 247, 255))
        tela.blit(texto_botao, (botao.x + 10, botao.y + 10))
        energia_txt = fonte.render(f"Energia infinita (teste): {'ON' if contexto.get('energia_infinita_teste') else 'OFF'}", True, (228, 236, 245))
        tela.blit(energia_txt, (20, 124))

        topo = fonte.render("BatalhaTeste.py | ambiente 6v6 local", True, (250, 250, 210))
        tela.blit(topo, (20, 20))
        fps_txt = fonte.render(f"{clock.get_fps():.0f} FPS", True, (240, 247, 255))
        tela.blit(fps_txt, fps_txt.get_rect(topright=(tela.get_width() - 20, 18)))
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
