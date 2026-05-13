from __future__ import annotations

import csv
import random
import sys
import unicodedata
from pathlib import Path

import pygame
try:
    import moderngl  # noqa: F401
except ImportError:
    moderngl = None

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from Codigo.ModulosBatalha.ControladorBatalha import ControladorBatalha
from Codigo.ModulosGerais.Camera import CameraBatalha
from Codigo.ModulosGerais.PipelineGrafica import PipelineGrafica
from SimuladorServerJogo.Gerais.LoaderTabelas import carregar_csv_dict
from SimuladorServerJogo.Gerais.LoaderRegras import carregar_regras_cliente_mundo


PERMITIR_ATAQUES_FORA_DA_LISTA_OBRIGATORIA = False
ATAQUES_OBRIGATORIOS_SIMULADOR: list[str] = [

    "Selar Arcano",
    "Desorientar",
    "Atravessar",
    "Lambida",
    "Toque do Medo",
    "Susto",
    "Maldade",
    "Golpe Espelhado",
    "Mão Espectral",
    "Pulso de Plasma",
    "Devorador de Pecados",
    "Maldição",
    "Jogada de Sorte",
    "Ataque Fantasmagórico",
    "Sede de Sangue",
    "Explosão Fantasma",
    "Golpe Cruel",
    "Fantasma",
    "Azar",
    "Escama Mistica",
    "Barragem Draconica",
    "Rugido",
    "Garra do Dragao",
    "Ultraje",
    "Sopro do Dragao",
    "Tiro de Escamas",
    "Sem Fraquezas",
    "Juramento do Dracomante",
    "Golpe Destrutivo",
    "Investida Draconica",
    "Territorio Sagrado",
    "Lanca Eterea",
]


def _chave_ataque(nome: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(nome or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _valor_coluna(linha: dict, *nomes, default=""):
    if not isinstance(linha, dict):
        return default
    alvos = {_chave_ataque(nome) for nome in nomes if str(nome or "").strip()}
    for chave, valor in linha.items():
        if _chave_ataque(chave) in alvos and valor not in (None, ""):
            return valor
    return default


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
    ataque = str(_valor_coluna(bruto, "Ataque", "Nome", "nome")).strip()
    tipo = str(_valor_coluna(bruto, "Tipo", "tipo", default="Normal")).strip() or "Normal"
    estilo = str(_valor_coluna(bruto, "Estilo", "estilo", default="Ativa")).strip()
    code = str(_valor_coluna(bruto, "Code", "code")).strip()
    try:
        custo = int(float(_valor_coluna(bruto, "Custo", "custo", default=0) or 0))
    except (TypeError, ValueError):
        custo = 0
    descricao = str(_valor_coluna(bruto, "Descrição", "Descricao", "Descrição Nivel 1", "Descricao Nivel 1")).strip()
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
        "Descrição": descricao,
        "Descricao": descricao,
        "Descrição Nivel 1": descricao,
        "Descrição Nivel 2": str(_valor_coluna(bruto, "Descrição Nivel 2", "Descricao Nivel 2")).strip(),
        "Descrição Nivel 3": str(_valor_coluna(bruto, "Descrição Nivel 3", "Descricao Nivel 3")).strip(),
        "Code": code,
        "code": code,
    }


def carregar_ataques(caminho_csv: Path) -> list[dict]:
    ataques = []
    if not caminho_csv.exists():
        return ataques
    for row in carregar_csv_dict(caminho_csv.name):
        if not any(str(v).strip() for v in row.values()):
            continue
        atk = normalizar_ataque(row)
        if not atk["Ataque"]:
            continue
        ataques.append(atk)
    return ataques


def resolver_ataques_obrigatorios(ataques: list[dict]) -> list[dict]:
    if not ATAQUES_OBRIGATORIOS_SIMULADOR:
        return []
    por_nome = {_chave_ataque(atk.get("Ataque") or atk.get("Nome")): atk for atk in ataques}
    obrigatorios: list[dict] = []
    vistos: set[str] = set()
    for nome in ATAQUES_OBRIGATORIOS_SIMULADOR:
        chave = _chave_ataque(nome)
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        ataque = por_nome.get(chave)
        if ataque is None:
            print(f"[SimuladorBatalha] Ataque obrigatorio nao encontrado no CSV: {nome!r}")
            continue
        obrigatorios.append(ataque)
    return obrigatorios


def distribuir_ataques_obrigatorios(ataques_obrigatorios: list[dict], total_pokemons: int, slots_por_pokemon: int = 5) -> list[list[dict]]:
    grupos: list[list[dict]] = [[] for _ in range(max(0, total_pokemons))]
    if not grupos:
        return grupos
    limite = len(grupos) * max(1, int(slots_por_pokemon or 1))
    for i, ataque in enumerate(ataques_obrigatorios[:limite]):
        grupos[i % len(grupos)].append(ataque)
    if len(ataques_obrigatorios) > limite:
        excedente = len(ataques_obrigatorios) - limite
        print(f"[SimuladorBatalha] {excedente} ataque(s) obrigatorio(s) sem slot disponivel.")
    return grupos


def sortear_ataques_simulador(ataques: list[dict], obrigatorios: list[dict] | None = None, total: int = 5) -> list[dict]:
    total = max(0, int(total or 0))
    escolhidos: list[dict] = []
    usados: set[str] = set()

    for ataque in list(obrigatorios or []):
        chave = _chave_ataque(ataque.get("Ataque") or ataque.get("Nome"))
        if not chave or chave in usados or len(escolhidos) >= total:
            continue
        escolhidos.append(ataque)
        usados.add(chave)

    if len(escolhidos) >= total or not ataques:
        return escolhidos[:total]
    if not PERMITIR_ATAQUES_FORA_DA_LISTA_OBRIGATORIA:
        return escolhidos[:total]

    pool = [atk for atk in ataques if _chave_ataque(atk.get("Ataque") or atk.get("Nome")) not in usados]
    random.shuffle(pool)
    escolhidos.extend(pool[: max(0, total - len(escolhidos))])
    return escolhidos[:total]


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
    especies = carregar_especies_validas(RAIZ / "Dados" / "Tabelas" / "Pokemon Global Server - Pokemons.csv")
    ataques = carregar_ataques(RAIZ / "Dados" / "Tabelas" / "Pokemon Global Server - Ataques.csv")
    ataques_obrigatorios = distribuir_ataques_obrigatorios(resolver_ataques_obrigatorios(ataques), total_pokemons=12)
    random.shuffle(especies)

    precisa = 12
    if not especies:
        print("[SimuladorBatalha] Nenhuma espécie válida encontrada no CSV. Usando fallback seguro.")
        especies = ["Pikachu", "Bulbasaur", "Charmander", "Squirtle"]
    escolhidas = especies[:precisa] if len(especies) >= precisa else [random.choice(especies) for _ in range(precisa)]

    pokemons_serializados = []
    areas_j = [f"A{i}" for i in range(1, 10)]
    areas_i = [f"I{i}" for i in range(1, 10)]
    random.shuffle(areas_j)
    random.shuffle(areas_i)

    for lado_id, lado_visual, offset in ((50, "jogador", 1), (51, "inimigo", 101)):
        for i in range(6):
            indice_pokemon = len(pokemons_serializados)
            especie = escolhidas[(0 if lado_id == 50 else 6) + i]
            dados = criar_materializado(especie)
            ativo = i < 3
            area_id = (areas_j if lado_id == 50 else areas_i)[i] if ativo else None
            atk_sample = sortear_ataques_simulador(
                ataques,
                obrigatorios=ataques_obrigatorios[indice_pokemon] if indice_pokemon < len(ataques_obrigatorios) else [],
                total=5,
            )
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


def criar_janela(tamanho=(1920, 1080), flags=pygame.RESIZABLE):
    if moderngl is not None:
        try:
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
            try:
                return pygame.display.set_mode(tamanho, flags | pygame.OPENGL | pygame.DOUBLEBUF, vsync=0), True
            except TypeError:
                return pygame.display.set_mode(tamanho, flags | pygame.OPENGL | pygame.DOUBLEBUF), True
        except pygame.error:
            pass
    return pygame.display.set_mode(tamanho, flags), False


class JogoSimulador:
    def __init__(self):
        self.CONFIG = {"Shader": True}
        self.INFO = {}


class CenaSimuladorBatalha:
    def __init__(self, controlador, fonte_overlay, btn_teste, clock):
        self.controlador = controlador
        self.fonte_overlay = fonte_overlay
        self.btn_teste = btn_teste
        self.clock = clock

    def tela_atual_eh_complexa(self):
        return True

    def render_base(self, surface, JOGO, EVENTOS, dt):
        _ = (JOGO, EVENTOS, dt)
        surface.fill((8, 12, 18))
        self.controlador.desenhar(surface)

    def render_hud(self, surface, JOGO, EVENTOS, dt):
        _ = (JOGO, EVENTOS, dt)
        pygame.draw.rect(surface, (28, 36, 54), self.btn_teste, border_radius=10)
        pygame.draw.rect(surface, (120, 144, 190), self.btn_teste, 2, border_radius=10)
        txt_teste = self.fonte_overlay.render(f"Modo teste: {'ON' if self.controlador.modo_teste else 'OFF'}", True, (236, 242, 255))
        surface.blit(txt_teste, txt_teste.get_rect(center=self.btn_teste.center))

        fps = self.clock.get_fps()
        txt_fps = self.fonte_overlay.render(f"FPS: {fps:5.1f}", True, (240, 245, 255))
        surface.blit(txt_fps, txt_fps.get_rect(topright=(surface.get_width() - 16, 12)))


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Simulador Batalha - Fase 1")
    janela, janela_opengl = criar_janela()
    tela = pygame.Surface(janela.get_size()).convert()
    pipeline = PipelineGrafica(tela, tela_display=janela)
    if janela_opengl and not pipeline.shader_disponivel():
        janela = pygame.display.set_mode(tela.get_size(), pygame.RESIZABLE)
        tela = pygame.Surface(janela.get_size()).convert()
        pipeline = PipelineGrafica(tela, tela_display=janela)
    clock = pygame.time.Clock()

    estado_inicial = montar_estado_inicial()
    camera = CameraBatalha(tela.get_size(), posicao_inicial_tiles=(0, 0), tile_px=40)
    controlador = ControladorBatalha(camera=camera)
    controlador.iniciar(estado_inicial)
    fonte_overlay = pygame.font.SysFont("consolas", 20, bold=True)
    btn_teste = pygame.Rect(20, 130, 170, 40)
    jogo = JogoSimulador()
    cena = CenaSimuladorBatalha(controlador, fonte_overlay, btn_teste, clock)

    rodando = True
    while rodando:
        dt = clock.tick(180) / 1000.0
        eventos = pygame.event.get()
        for evento in eventos:
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.VIDEORESIZE:
                pipeline.liberar()
                janela, janela_opengl = criar_janela((max(960, evento.w), max(540, evento.h)))
                tela = pygame.Surface(janela.get_size()).convert()
                pipeline = PipelineGrafica(tela, tela_display=janela)
                if janela_opengl and not pipeline.shader_disponivel():
                    janela = pygame.display.set_mode(tela.get_size(), pygame.RESIZABLE)
                    tela = pygame.Surface(janela.get_size()).convert()
                    pipeline = PipelineGrafica(tela, tela_display=janela)
                controlador.camera.TamanhoTelaPx = (float(tela.get_width()), float(tela.get_height()))
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and btn_teste.collidepoint(evento.pos):
                controlador.definir_modo_teste(not controlador.modo_teste)

        controlador.atualizar(dt, eventos)
        if controlador.solicitou_encerrar_batalha:
            rodando = False
            continue
        pipeline.renderizar_frame(jogo=jogo, cena=cena, eventos=eventos, dt=dt)
        pygame.display.flip()

    pipeline.liberar()
    pygame.quit()


if __name__ == "__main__":
    main()
