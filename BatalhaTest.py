from __future__ import annotations

import csv
import sys
import types
import unicodedata
import uuid
from pathlib import Path
from typing import Dict, List

import pygame


def _instalar_stub_server_batalha_offline() -> None:
    """
    Evita dependência acidental do servidor real durante o teste visual.
    Deve rodar antes de qualquer import de módulos de batalha que importam
    Codigo.Server.ServerBatalha.
    """
    nome_modulo = "Codigo.Server.ServerBatalha"
    if nome_modulo in sys.modules:
        return

    stub = types.ModuleType(nome_modulo)

    def iniciar_batalha_server(ip: str, client_id: str, contexto_batalha: Dict[str, object] | None = None) -> Dict[str, object]:
        _ = (ip, client_id, contexto_batalha)
        return {
            "status": "offline_stub",
            "modo_teste": True,
            "mensagem": "BatalhaTest offline: servidor desabilitado.",
        }

    def enviar_jogada_batalha_server(ip: str, client_id: str, jogadas: List[Dict[str, object]] | None = None, batalha_id: str = "") -> Dict[str, object]:
        _ = (ip, client_id, jogadas, batalha_id)
        return {
            "status": "offline_stub",
            "modo_teste": True,
            "mensagem": "BatalhaTest offline: jogadas não enviadas.",
        }

    stub.iniciar_batalha_server = iniciar_batalha_server
    stub.enviar_jogada_batalha_server = enviar_jogada_batalha_server
    sys.modules[nome_modulo] = stub


_instalar_stub_server_batalha_offline()

from Codigo.ModulosBatalha.ControladorBatalha import ControladorBatalha
from Codigo.ModulosBatalha.ElementosHudBatalha import ElementosHudBatalha
from Codigo.ModulosGerais.Camera import CameraBatalha
from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import criar_pokemon_inicial_materializado


LARGURA_TELA = 1920
ALTURA_TELA = 1080
FPS_ALVO = 180

LARGURA_MUNDO = 80
ALTURA_MUNDO = 40
ARENA_LARGURA = 40
ARENA_ALTURA = 20

POKEMONS_CSV = Path("Dados") / "Pokemon Global Server - Pokemons.csv"
ATAQUES_CSV = Path("Dados") / "Pokemon Global Server - Ataques.csv"

ATAQUES_INICIAIS = [
    "Investida",
    "Biscoito",
    "Enraivecer",
    "Provocar",
    "Proteger",
    "Arranhar",
    "Recarga",
    "Energia",
    "Hiper Raio",
    "Guilhotina",
    "Disparo",
    "Chifrada",
    "Resetar",
    "Tankar",
    "Estocada",
    "Bola Climática",
    "Hiper Presa",
    "Investida Selvagem",
]


class ControladorBatalhaTeste(ControladorBatalha):
    _MAX_ATIVOS = 6


# ----------------------------- utilidades de dados -----------------------------
def _normalizar_texto(valor: object) -> str:
    base = unicodedata.normalize("NFKD", str(valor or ""))
    sem_acento = "".join(ch for ch in base if not unicodedata.combining(ch))
    return sem_acento.strip().casefold()


def _float(valor: object, default: float = 0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def carregar_especies_teste(qtd: int = 12) -> List[str]:
    especies: List[str] = []
    if not POKEMONS_CSV.exists():
        return [f"Pokemon-{i + 1}" for i in range(qtd)]

    with POKEMONS_CSV.open("r", encoding="utf-8-sig", newline="") as arquivo:
        for row in csv.DictReader(arquivo):
            nome = str(row.get("Nome") or "").strip()
            if not nome:
                continue
            raridade = _float(row.get("Raridade"), 0.0)
            estagio = _float(row.get("Estagio"), 0.0)
            if 1.0 <= raridade <= 10.0 and estagio > 0:
                especies.append(nome)
            if len(especies) >= qtd:
                break

    if not especies:
        especies = ["MissingNo"]
    while len(especies) < qtd:
        especies.append(especies[len(especies) % len(especies)])
    return especies[:qtd]


def carregar_ataques_base() -> Dict[str, Dict[str, object]]:
    base: Dict[str, Dict[str, object]] = {}
    if not ATAQUES_CSV.exists():
        return base

    with ATAQUES_CSV.open("r", encoding="utf-8-sig", newline="") as arquivo:
        for row in csv.DictReader(arquivo):
            nome = str(row.get("Ataque") or row.get("Nome") or "").strip()
            if not nome:
                continue
            base[_normalizar_texto(nome)] = dict(row)
    return base


def ataque_por_nome(nome: str, ataques_base: Dict[str, Dict[str, object]]) -> Dict[str, object]:
    ataque = dict(ataques_base.get(_normalizar_texto(nome), {}))
    if not ataque:
        ataque = {
            "Ataque": nome,
            "Nome": nome,
            "Tipo": "Normal",
            "Custo": 0,
        }
    ataque["Ataque"] = str(ataque.get("Ataque") or nome)
    ataque["Nome"] = str(ataque.get("Nome") or ataque["Ataque"])
    ataque["Tipo"] = str(ataque.get("Tipo") or "Normal")
    return ataque


def _estado_ref(pokemon: Dict[str, object]) -> Dict[str, object]:
    if not isinstance(pokemon.get("estado"), dict):
        pokemon["estado"] = {}
    return pokemon["estado"]


def materializar_pokemon_teste(especie: str, uid: str) -> Dict[str, object]:
    try:
        pokemon = criar_pokemon_inicial_materializado(especie)
    except Exception:
        pokemon = {}

    if not isinstance(pokemon, dict):
        pokemon = {}

    estado = _estado_ref(pokemon)
    nome = str(pokemon.get("nome") or pokemon.get("especie") or especie)
    especie_real = str(pokemon.get("especie") or especie)

    vida_base = max(80.0, _float(pokemon.get("vida_atual"), _float(estado.get("vida_atual"), 120.0)))
    energia_max = max(300.0, _float(estado.get("stats", {}).get("Ene"), 120.0) * 6.0)

    # Campos robustos no topo
    pokemon["uid"] = uid
    pokemon["id"] = uid
    pokemon["nome"] = nome
    pokemon["Nome"] = nome
    pokemon["especie"] = especie_real
    pokemon["Especie"] = especie_real
    pokemon["nivel"] = int(_float(pokemon.get("nivel"), 50))
    pokemon["Nivel"] = pokemon["nivel"]
    pokemon["vida_atual"] = vida_base
    pokemon["VidaAtual"] = vida_base
    pokemon["vida_max"] = vida_base
    pokemon["Vida"] = vida_base
    pokemon["energia"] = energia_max
    pokemon["Energia"] = energia_max
    pokemon["energia_max"] = energia_max
    pokemon["EnergiaMaxima"] = energia_max

    stats = dict(estado.get("stats") or {})
    for chave, valor_default in {
        "Vida": vida_base,
        "Atk": 45,
        "Def": 45,
        "SpA": 45,
        "SpD": 45,
        "Vel": 45,
        "Mag": 45,
        "Per": 45,
        "Ene": 45,
        "Int": 45,
    }.items():
        stats[chave] = _float(stats.get(chave), valor_default)
        pokemon[chave] = stats[chave]

    # Campos robustos no estado
    estado["uid"] = uid
    estado["id"] = uid
    estado["nome"] = nome
    estado["especie"] = especie_real
    estado["nivel"] = int(_float(estado.get("nivel"), pokemon["nivel"]))
    estado["vida_atual"] = vida_base
    estado["vida_max"] = vida_base
    estado["stats"] = stats

    return pokemon


def distribuir_ataques(pokemons: List[Dict[str, object]], ataques_base: Dict[str, Dict[str, object]]) -> None:
    grupos: List[List[Dict[str, object]]] = [[] for _ in pokemons]
    for i, nome_ataque in enumerate(ATAQUES_INICIAIS):
        idx = i % len(pokemons)
        grupos[idx].append(ataque_por_nome(nome_ataque, ataques_base))

    # garante no mínimo 2 ataques por pokémon para navegação da ficha
    ataque_extra = ataque_por_nome("Investida", ataques_base)
    for i, pokemon in enumerate(pokemons):
        while len(grupos[i]) < 2:
            grupos[i].append(dict(ataque_extra))

        estado = _estado_ref(pokemon)
        pokemon["habilidades"] = [dict(a) for a in grupos[i]]
        pokemon["ataques"] = [dict(a) for a in grupos[i]]
        pokemon["Habilidades"] = [dict(a) for a in grupos[i]]
        estado["habilidades"] = [dict(a) for a in grupos[i]]
        estado["ataques"] = [dict(a) for a in grupos[i]]


def montar_contexto_batalha() -> Dict[str, object]:
    especies = carregar_especies_teste(qtd=12)
    ataques_base = carregar_ataques_base()

    pokemons = [
        materializar_pokemon_teste(especie, uid=f"TEST-{i + 1:02d}-{uuid.uuid4().hex[:6].upper()}")
        for i, especie in enumerate(especies)
    ]
    distribuir_ataques(pokemons, ataques_base)

    aliados = pokemons[:6]
    inimigos = pokemons[6:12]

    time_jogador = {"Nome": "Teste Aliados", "Slots": aliados}
    time_inimigo = {"Nome": "Teste Inimigos", "Slots": inimigos}

    return {
        "tipo": "treinador",
        "modo_teste": True,
        "server_ip": "",
        "client_id": "batalha-test-local",
        "batalha_id_servidor": "batalha-test-local",
        "largura": LARGURA_MUNDO,
        "altura": ALTURA_MUNDO,
        "centro": [LARGURA_MUNDO / 2.0, ALTURA_MUNDO / 2.0],
        "arena_largura": ARENA_LARGURA,
        "arena_altura": ARENA_ALTURA,
        "batalha": {
            "ticks_por_segundo": 30,
            "duracao_turno_ticks": 50,
            "combate_pokemon_tamanho_diametro_base_tiles": 1.0,
            "combate_pokemon_tamanho_incremento_por_escala": 0.15,
        },
        "time_jogador": time_jogador,
        "times_jogador": [time_jogador],
        "pokemons_jogador": aliados,
        "npc_contexto": {
            "batalha_numero": 1,
            "times_pokemon": [time_inimigo],
        },
    }


# ------------------------------ utilidades de HUD ------------------------------
def obter_controlador_jogadas(hud: ElementosHudBatalha):
    return getattr(hud, "_jogadas", None) or getattr(hud, "_fluxos", None)


def listar_jogadas(hud: ElementosHudBatalha) -> List[Dict[str, object]]:
    jogadas = obter_controlador_jogadas(hud)
    if jogadas is None:
        return []
    try:
        return list(jogadas.listar_jogadas())
    except Exception:
        return []


def limpar_preparacao_e_jogadas(hud: ElementosHudBatalha) -> None:
    jogadas = obter_controlador_jogadas(hud)
    if jogadas is None:
        return
    if hasattr(jogadas, "cancelar_preparacao"):
        jogadas.cancelar_preparacao()
    montador = getattr(jogadas, "_montador", None)
    if montador is not None and hasattr(montador, "limpar"):
        montador.limpar()


def instalar_pronto_fake(hud: ElementosHudBatalha) -> None:
    controlador_jogadas = obter_controlador_jogadas(hud)
    if controlador_jogadas is None:
        print("[BatalhaTest] Aviso: controlador de jogadas não encontrado; pronto() sem patch.")
        return

    def pronto_fake():
        print("\n=== JOGADAS PREPARADAS NO TESTE ===")
        jogadas = listar_jogadas(hud)
        if not jogadas:
            print("(nenhuma jogada preparada)")
        for indice, item in enumerate(jogadas, start=1):
            print(f"{indice:02d}: {item}")
        print("=== FIM (sem envio para servidor) ===\n")
        return "teste"

    controlador_jogadas.pronto = pronto_fake


def _nome_pokemon(pokemon) -> str:
    if pokemon is None:
        return "-"
    return str(getattr(pokemon, "Nome", "") or getattr(pokemon, "Especie", "") or "-")


def _nome_ataque_atual(hud: ElementosHudBatalha) -> str:
    ficha = getattr(hud, "_ficha", None)
    if ficha is None or not hasattr(ficha, "ataque_selecionado"):
        return "-"
    ataque = ficha.ataque_selecionado()
    if not isinstance(ataque, dict):
        return "-"
    return str(ataque.get("Ataque") or ataque.get("Nome") or "-")


def _alternar_selecao_tab(controlador: ControladorBatalhaTeste) -> None:
    lista = list(controlador.PokemonsAliados) + list(controlador.PokemonsInimigos)
    if not lista:
        return
    atual = getattr(controlador, "PokemonSelecionado", None)
    if atual not in lista:
        controlador.selecionar_pokemon(lista[0])
        return
    idx = (lista.index(atual) + 1) % len(lista)
    controlador.selecionar_pokemon(lista[idx])


def imprimir_ajuda_terminal() -> None:
    print("\n=== BatalhaTest.py | Atalhos ===")
    print("ESC  -> sair")
    print("F1   -> ajuda")
    print("F2   -> listar jogadas preparadas")
    print("R    -> limpar preparação/jogadas")
    print("TAB  -> alternar seleção entre os 12 pokémons")
    print("Mouse esquerdo -> selecionar / mirar / preparar")
    print("Mouse direito arrastando -> pan câmera")
    print("Scroll -> zoom câmera")
    print("===============================\n")


def desenhar_overlay_debug(
    tela: pygame.Surface,
    fonte: pygame.font.Font,
    clock: pygame.time.Clock,
    controlador: ControladorBatalhaTeste,
    hud: ElementosHudBatalha,
) -> None:
    linhas = [
        "BatalhaTest.py",
        f"FPS: {clock.get_fps():6.2f} (alvo={FPS_ALVO})",
        f"modo_teste={bool(controlador.Contexto.get('modo_teste', False))}",
        f"Selecionado: {_nome_pokemon(controlador.PokemonSelecionado)}",
        f"Ataque: {_nome_ataque_atual(hud)}",
        f"Jogadas preparadas: {len(listar_jogadas(hud))}",
        "ESC sair | F1 ajuda | F2 listar jogadas | R limpar",
    ]

    padding = 8
    altura_linha = 22
    largura = min(820, max(400, int(max(fonte.size(txt)[0] for txt in linhas) + padding * 2)))
    altura = len(linhas) * altura_linha + padding * 2

    painel = pygame.Surface((largura, altura), pygame.SRCALPHA)
    painel.fill((12, 18, 30, 188))
    tela.blit(painel, (12, 12))

    y = 12 + padding
    for linha in linhas:
        surf = fonte.render(linha, True, (235, 242, 255))
        tela.blit(surf, (12 + padding, y))
        y += altura_linha


def main() -> int:
    pygame.init()
    pygame.display.set_caption("Pokemon Global Server - Batalha Test")
    tela = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA), pygame.DOUBLEBUF)
    clock = pygame.time.Clock()
    fonte_debug = pygame.font.SysFont("consolas", 20)

    contexto = montar_contexto_batalha()

    controlador = ControladorBatalhaTeste(contexto)
    controlador.Contexto["modo_teste"] = True
    controlador.SistemaBatalha.Contexto["modo_teste"] = True

    camera = CameraBatalha(
        tela.get_size(),
        posicao_inicial_tiles=(20.0, 10.0),
        tile_px=40,
    )
    camera.definir_limites_mundo(LARGURA_MUNDO, ALTURA_MUNDO, toroidal=False)
    camera.definir_referencia_arena((20.0, 10.0), (ARENA_LARGURA, ARENA_ALTURA))

    hud = ElementosHudBatalha(controlador_batalha=controlador, camera=camera, ao_fugir=lambda: None)
    instalar_pronto_fake(hud)

    imprimir_ajuda_terminal()

    rodando = True
    while rodando:
        dt = clock.tick(FPS_ALVO) / 1000.0
        eventos = pygame.event.get()

        for evento in eventos:
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    rodando = False
                elif evento.key == pygame.K_F1:
                    imprimir_ajuda_terminal()
                elif evento.key == pygame.K_F2:
                    print("=== JOGADAS PREPARADAS (F2) ===")
                    for i, item in enumerate(listar_jogadas(hud), start=1):
                        print(f"{i:02d}: {item}")
                    print("=== FIM ===")
                elif evento.key == pygame.K_r:
                    limpar_preparacao_e_jogadas(hud)
                    print("[BatalhaTest] Preparação e jogadas limpas.")
                elif evento.key == pygame.K_TAB:
                    _alternar_selecao_tab(controlador)

        eventos_camera = hud.filtrar_eventos_camera(tela, eventos, dt)
        camera.processar_eventos(eventos_camera)
        camera.atualizar(dt)

        controlador.atualizar(eventos, dt)

        tela.fill((6, 10, 18))
        controlador.renderizar(tela, camera)
        hud.desenhar(tela, eventos, dt)
        desenhar_overlay_debug(tela, fonte_debug, clock, controlador, hud)

        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
