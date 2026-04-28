from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

import pygame

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from Codigo.ModulosBatalha.ControladorBatalha import ControladorBatalha
from Codigo.ModulosGerais.Camera import CameraBatalha
from SimuladorServerJogo.Gerais.LoaderRegras import carregar_regras_cliente_mundo


def carregar_especies_validas(caminho_csv: Path) -> list[str]:
    bloqueios = ("Mega", "Gigantamax", "Ultra", "Eternamax", "Radiante")
    especies: list[str] = []
    if not caminho_csv.exists():
        return especies
    with caminho_csv.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            nome = str(row.get("Nome") or "").strip()
            if not nome:
                continue
            estagio = str(row.get("Estagio") or "").strip().upper()
            raridade = str(row.get("Raridade") or "").strip()
            try:
                raridade_num = float(raridade)
            except (TypeError, ValueError):
                continue
            if estagio in {"F", "FF"} or raridade_num < 1.0 or raridade_num > 10.0:
                continue
            if any(b.lower() in nome.lower() for b in bloqueios):
                continue
            especies.append(nome)
    return especies


def normalizar_ataque(bruto: dict) -> dict:
    ataque = str(bruto.get("Ataque") or bruto.get("Nome") or bruto.get("nome") or "").strip()
    tipo = str(bruto.get("Tipo") or bruto.get("tipo") or "Normal").strip() or "Normal"
    estilo = str(bruto.get("Estilo") or bruto.get("estilo") or "Ativa").strip()
    code = str(bruto.get("Code") or bruto.get("code") or "").strip()
    try:
        custo = int(float(bruto.get("Custo") or bruto.get("custo") or 0))
    except (TypeError, ValueError):
        custo = 0
    return {
        "Ataque": ataque,
        "Nome": ataque,
        "nome": ataque,
        "Tipo": tipo,
        "tipo": tipo,
        "Custo": custo,
        "custo": custo,
        "Estilo": estilo,
        "estilo": estilo,
        "Descrição Nivel 1": str(bruto.get("Descrição Nivel 1") or "").strip(),
        "Descrição Nivel 2": str(bruto.get("Descrição Nivel 2") or "").strip(),
        "Descrição Nivel 3": str(bruto.get("Descrição Nivel 3") or "").strip(),
        "Code": code,
        "code": code,
    }


def carregar_ataques(caminho_csv: Path) -> list[dict]:
    ataques = []
    if not caminho_csv.exists():
        return ataques
    with caminho_csv.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if not any(str(v).strip() for v in row.values()):
                continue
            atk = normalizar_ataque(row)
            if not atk["Ataque"]:
                continue
            ataques.append(atk)
    return ataques


def criar_materializado(especie: str) -> dict:
    try:
        from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import gerar_pokemon_server, materializar_pokemon

        pokemon_gerado = gerar_pokemon_server(novo_id=0, posicao=(0.0, 0.0), chunk_xy=(0, 0), especie=especie)
        estado = dict(getattr(pokemon_gerado, "estado_extra", {}) or {})
        bruto = {
            "id": 0,
            "especie": str(getattr(pokemon_gerado, "Especie", especie) or especie),
            "nome": str(getattr(pokemon_gerado, "Especie", especie) or especie),
            "nivel": int(estado.get("nivel", 1) or 1),
            "iv": int(estado.get("iv", 0) or 0),
            "subivs": dict(estado.get("subivs", {}) or {}),
            "stats_base": dict(estado.get("stats_base", {}) or {}),
            "stats": dict(estado.get("stats", {}) or {}),
            "altura": float(estado.get("altura", 1.0) or 1.0),
            "peso": float(estado.get("peso", 1.0) or 1.0),
            "tipos": list(estado.get("tipos", []) or []),
            "grupo": str(estado.get("grupo", "") or ""),
            "raridade": int(estado.get("raridade", 1) or 1),
            "estagio": int(estado.get("estagio", 1) or 1),
            "escala": int(estado.get("escala", 3) or 3),
            "variacao_tamanho": int(estado.get("variacao_tamanho", 0) or 0),
            "tamanho": str(estado.get("tamanho", "M") or "M"),
            "tamanho_tiles": float(estado.get("tamanho_tiles", 0.6) or 0.6),
            "code": str(estado.get("code", "") or ""),
            "linhagem": str(estado.get("linhagem", "") or ""),
            "equipaveis": int(estado.get("equipaveis", 1) or 1),
            "chunk_origem": list(estado.get("chunk_origem", [0, 0]) or [0, 0]),
        }
        return materializar_pokemon(bruto, efeitos_captura=None)
    except Exception as exc:
        print(f"[SimuladorBatalha] Falha ao materializar '{especie}': {exc!r}. Usando fallback visual.")
        return {
            "id": 0,
            "especie": especie,
            "nome": especie,
            "nivel": 1,
            "stats": {"Vida": 50, "Atk": 20, "Def": 20, "SpA": 20, "SpD": 20, "Vel": 20, "Mag": 20, "Per": 20, "Ene": 20, "Int": 20, "CrD": 20, "CrC": 10},
            "stats_base": {"Vida": 50, "Atk": 20, "Def": 20, "SpA": 20, "SpD": 20, "Vel": 20, "Mag": 20, "Per": 20, "Ene": 20, "Int": 20, "CrD": 20, "CrC": 10},
            "tipos": ["Normal"],
            "peso": 1.0,
            "escala": 3,
        }


def montar_estado_inicial() -> dict:
    especies = carregar_especies_validas(RAIZ / "Dados" / "Pokemon Global Server - Pokemons.csv")
    ataques = carregar_ataques(RAIZ / "Dados" / "Pokemon Global Server - Ataques.csv")
    random.shuffle(especies)

    precisa = 12
    if not especies:
        print("[SimuladorBatalha] Nenhuma espécie válida encontrada no CSV. Usando fallback seguro.")
        especies = ["Pikachu", "Bulbasaur", "Charmander", "Squirtle"]
    escolhidas = especies[:precisa] if len(especies) >= precisa else [random.choice(especies) for _ in range(precisa)]

    pokemons_serializados = []
    areas_j = ["A1", "A2", "A3"]
    areas_i = ["I1", "I2", "I3"]

    for lado_id, lado_visual, offset in ((50, "jogador", 1), (51, "inimigo", 101)):
        for i in range(6):
            especie = escolhidas[(0 if lado_id == 50 else 6) + i]
            dados = criar_materializado(especie)
            ativo = i < 3
            area_id = (areas_j if lado_id == 50 else areas_i)[i] if ativo else None
            atk_sample = random.sample(ataques, k=min(5, len(ataques))) if ataques else []
            stats_base = dict((dados.get("stats_base") if isinstance(dados.get("stats_base"), dict) else dados.get("stats")) or {})
            stats_normalizado = dict(stats_base)
            variacoes = {chave: 0 for chave in stats_normalizado.keys()}
            dados["stats_base"] = dict(stats_base)
            dados["stats"] = dict(stats_normalizado)
            dados["Variacoes"] = variacoes
            pokemons_serializados.append(
                {
                    "id_batalha": f"{lado_id:03d}{offset + i:02d}",
                    "id_original": dados.get("id"),
                    "lado_id": lado_id,
                    "lado_visual": lado_visual,
                    "ativo": ativo,
                    "em_reserva": not ativo,
                    "vivo": True,
                    "area_id": area_id,
                    "dados": dados,
                    "ataques": [normalizar_ataque(a) for a in atk_sample],
                }
            )

    largura, altura = 120, 72

    regras_cliente = carregar_regras_cliente_mundo()
    animacao = regras_cliente.get("animacao") if isinstance(regras_cliente.get("animacao"), dict) else {}
    intervalo_frame_ms = int(animacao.get("intervalo_frame_ms", 85) or 85)

    return {
        "id_partida": "simulador_local_fase1",
        "tipo_batalha": "Confronto",
        "rodada_atual": 1,
        "lado_jogador": 50,
        "lados": [
            {"lado_id": 50, "lado_visual": "jogador", "nome": "Jogador"},
            {"lado_id": 51, "lado_visual": "inimigo", "nome": "Oponente"},
        ],
        "arena": {
            "centro": (60, 36),
            "largura": largura,
            "altura": altura,
            "arena_largura": 40,
            "arena_altura": 20,
            "origem": (0, 0),
            "tiles": [],
            "estruturas": [],
        },
        "regras": {"animacao": {"intervalo_frame_ms": intervalo_frame_ms}},
        "pokemons": pokemons_serializados,
    }


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Simulador Batalha - Fase 1")
    tela = pygame.display.set_mode((1920, 1080), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    estado_inicial = montar_estado_inicial()
    camera = CameraBatalha(tela.get_size(), posicao_inicial_tiles=(0, 0), tile_px=40)
    controlador = ControladorBatalha(camera=camera)
    controlador.iniciar(estado_inicial)
    fonte_overlay = pygame.font.SysFont("consolas", 20, bold=True)
    btn_teste = pygame.Rect(20, 130, 170, 40)

    rodando = True
    while rodando:
        dt = clock.tick(180) / 1000.0
        eventos = pygame.event.get()
        for evento in eventos:
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.VIDEORESIZE:
                tela = pygame.display.set_mode((max(960, evento.w), max(540, evento.h)), pygame.RESIZABLE)
                controlador.camera.TamanhoTelaPx = (float(tela.get_width()), float(tela.get_height()))
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and btn_teste.collidepoint(evento.pos):
                controlador.definir_modo_teste(not controlador.modo_teste)

        controlador.atualizar(dt, eventos)
        if controlador.solicitou_encerrar_batalha:
            rodando = False
            continue
        tela.fill((8, 12, 18))
        controlador.desenhar(tela)
        pygame.draw.rect(tela, (28, 36, 54), btn_teste, border_radius=10)
        pygame.draw.rect(tela, (120, 144, 190), btn_teste, 2, border_radius=10)
        txt_teste = fonte_overlay.render(f"Modo teste: {'ON' if controlador.modo_teste else 'OFF'}", True, (236, 242, 255))
        tela.blit(txt_teste, txt_teste.get_rect(center=btn_teste.center))

        fps = clock.get_fps()
        txt_fps = fonte_overlay.render(f"FPS: {fps:5.1f}", True, (240, 245, 255))
        tela.blit(txt_fps, txt_fps.get_rect(topright=(tela.get_width() - 16, 12)))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
