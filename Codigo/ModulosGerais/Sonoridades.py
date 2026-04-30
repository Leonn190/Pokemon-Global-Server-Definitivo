import json
import random
from pathlib import Path

import pygame

from Codigo.ModulosGerais.Auxiliares import bioma_por_tile

silencio = False
Volume = 0.0

_RAIZ_PROJETO = Path(__file__).resolve().parents[2]
_CAMINHO_CATALOGO = _RAIZ_PROJETO / "Dados" / "Catalogo"


def _carregar_catalogo(nome):
    caminho = _CAMINHO_CATALOGO / f"{nome}.json"
    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except Exception as exc:
        print(f"[ERRO] Falha ao carregar catalogo de sonoridades '{nome}': {exc}")
        return {}
    return dados if isinstance(dados, dict) else {}


def _carregar_sons():
    sons = _carregar_catalogo("Sons")
    for dados in sons.values():
        if isinstance(dados, dict):
            dados.setdefault("Som", None)
    return sons


Sons = _carregar_sons()
Musicas = _carregar_catalogo("Musicas")

MUSICAS_MUNDO = {"Vale", "Neve", "Deserto", "Praia", "Vulcão"}

# Estado da música atual
_musica_atual = None
_loop_point = 0.0
_fimloop_point = 0.0
_posicao_manual = 0.0
_vol_mult_atual = 1.0

# Estado do fade
_fade_tipo = None          # None | "out" | "in"
_fade_inicio = 0
_fade_duracao = 900
_fade_volume_inicial = 0.0
_fade_alvo = None

# Estado geral do sistema
_cena_anterior = None
_menu_faixa_atual = None

# Anti-ruído na troca de bioma
_tile_confirmado = None
_tile_candidato = None
_tile_candidato_inicio = 0
_confirmacao_bioma_ms = 700
_ultima_troca_bioma = 0
_cooldown_bioma_ms = 1200


def _garantir_mixer():
    if not pygame.mixer.get_init():
        pygame.mixer.init()


def _obter_som(nome):
    dados = Sons.get(nome)
    if not isinstance(dados, dict):
        return None
    som = dados.get("Som")
    if som is not None:
        return som
    _garantir_mixer()
    try:
        som = pygame.mixer.Sound(dados["Arquivo"])
    except Exception:
        return None
    dados["Som"] = som
    return som


def _volume_musica():
    if silencio:
        return 0.0
    return max(0.0, min(1.0, Volume * _vol_mult_atual))


def VerificaSonoridade(config):
    global silencio, Volume

    silencio = bool(config.get("Mudo", False))
    Volume = max(0.0, min(1.0, float(config.get("Volume", 0.0))))

    _garantir_mixer()
    if _fade_tipo is None:
        pygame.mixer.music.set_volume(_volume_musica())


def tocar(som):
    if som not in Sons:
        return

    audio = _obter_som(som)
    if audio is None:
        return
    volume = Sons[som]["Volume"] * Volume

    if silencio:
        volume = 0.0

    audio.set_volume(min(volume, 1.0))
    audio.play()

    # Mantido como você pediu
    if volume > 1.0:
        audio2 = _obter_som(som)
        if audio2 is None:
            return
        audio2.set_volume(min(volume - 1.0, 1.0))
        audio2.play()


def _iniciar_musica(nome, volume_inicial=None):
    global _musica_atual, _loop_point, _fimloop_point, _posicao_manual, _vol_mult_atual

    if nome not in Musicas:
        print(f"[ERRO] Música '{nome}' não encontrada.")
        return

    dados = Musicas[nome]
    _musica_atual = nome
    _loop_point = float(dados["loop"])
    _fimloop_point = float(dados["fimloop"])
    _vol_mult_atual = float(dados.get("volume", 1.0))
    _posicao_manual = 0.0

    _garantir_mixer()
    pygame.mixer.music.load(dados["arquivo"])

    if volume_inicial is None:
        volume_inicial = _volume_musica()

    pygame.mixer.music.set_volume(max(0.0, min(1.0, volume_inicial)))
    pygame.mixer.music.play()


def TransicaoMusica(nome):
    global _fade_tipo, _fade_inicio, _fade_volume_inicial, _fade_alvo

    nome = str(nome or "").strip()
    if not nome or nome not in Musicas:
        return

    if nome == _musica_atual and _fade_tipo is None:
        return

    if not pygame.mixer.music.get_busy() or _musica_atual is None:
        _iniciar_musica(nome)
        _fade_tipo = None
        _fade_alvo = None
        return

    if _fade_tipo == "out" and _fade_alvo == nome:
        return

    _fade_tipo = "out"
    _fade_inicio = pygame.time.get_ticks()
    _fade_volume_inicial = pygame.mixer.music.get_volume()
    _fade_alvo = nome


def musica_resultado_batalha(vencedor):
    vencedor = str(vencedor or "").strip().lower()
    if vencedor == "jogador":
        return "Vitoria"
    if vencedor == "inimigo":
        return "Derrota"
    return None


def tocar_musica_resultado_batalha(vencedor):
    global _fade_tipo, _fade_alvo

    nome = musica_resultado_batalha(vencedor)
    if nome:
        _fade_tipo = None
        _fade_alvo = None
        _iniciar_musica(nome)


def _atualizar_fade():
    global _fade_tipo, _fade_inicio, _fade_volume_inicial, _fade_alvo

    if _fade_tipo is None:
        return

    agora = pygame.time.get_ticks()
    t = min(1.0, (agora - _fade_inicio) / float(_fade_duracao))

    if _fade_tipo == "out":
        vol = _fade_volume_inicial * (1.0 - t)
        pygame.mixer.music.set_volume(max(0.0, min(1.0, vol)))

        if t >= 1.0:
            alvo = _fade_alvo
            _fade_alvo = None
            _iniciar_musica(alvo, volume_inicial=0.0)
            _fade_tipo = "in"
            _fade_inicio = pygame.time.get_ticks()
            _fade_volume_inicial = 0.0

    elif _fade_tipo == "in":
        vol = _volume_musica() * t
        pygame.mixer.music.set_volume(max(0.0, min(1.0, vol)))

        if t >= 1.0:
            pygame.mixer.music.set_volume(_volume_musica())
            _fade_tipo = None


def _atualizar_loop_manual():
    global _posicao_manual

    if not _musica_atual or not pygame.mixer.music.get_busy():
        return

    pos = pygame.mixer.music.get_pos()
    if pos < 0:
        return

    pos_segundos = (pos / 1000.0) + _posicao_manual

    if pos_segundos >= _fimloop_point:
        pygame.mixer.music.play(-1, start=_loop_point)
        _posicao_manual = _loop_point


def _tem_subtela_carregamento_menu():
    try:
        from Codigo.Telas.Telas.TelaOperador import possui_subtela_carregamento_ativa
        return bool(possui_subtela_carregamento_ativa())
    except Exception:
        return False


class _DummyLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _tile_mundo_atual(cena_mundo):
    controlador = getattr(cena_mundo, "ControladorMundo", None)
    if controlador is None:
        return None

    player = getattr(controlador, "player_local", None)
    leitor = getattr(controlador, "Leitor", None)
    if player is None or leitor is None:
        return None

    pos = getattr(player, "Posicao", None)
    if not isinstance(pos, (list, tuple)) or len(pos) != 2:
        return None

    try:
        px = float(pos[0])
        py = float(pos[1])
    except (TypeError, ValueError):
        return None

    with getattr(leitor, "_lock", None) or _DummyLock():
        chunks = dict(getattr(leitor, "Chunks", {}) or {})
        tamanho_chunk = int(getattr(leitor, "TamanhoChunkBlocos", 10) or 10)

    if not chunks:
        return None

    bloco_x = int(px)
    bloco_y = int(py)
    chunk_x = bloco_x // tamanho_chunk
    chunk_y = bloco_y // tamanho_chunk

    grid = chunks.get((chunk_x, chunk_y))
    if not grid:
        return None

    local_x = bloco_x - chunk_x * tamanho_chunk
    local_y = bloco_y - chunk_y * tamanho_chunk

    if local_y < 0 or local_y >= len(grid):
        return None

    linha = grid[local_y]
    if local_x < 0 or local_x >= len(linha):
        return None

    try:
        return int(linha[local_x])
    except (TypeError, ValueError):
        return None


def tile_mundo_atual(cena_mundo):
    return _tile_mundo_atual(cena_mundo)


def _musica_por_tile(tile):
    bioma = bioma_por_tile(tile)
    return {
        "Vale": "Vale",
        "Floresta": "Vale",
        "Neve": "Neve",
        "Deserto": "Deserto",
        "Praia": "Praia",
        "Vulcão": "Vulcão",
    }.get(bioma)


def musica_confronto_por_tile(tile):
    bioma = bioma_por_tile(tile)
    return {
        "Vale": "ConfrontoDoVale",
        "Floresta": "ConfrontoDoVale",
        "Neve": "ConfrontoDaNeve",
        "Deserto": "ConfrontoDoDeserto",
        "Praia": "ConfrontoDoMar",
        "Vulcão": "ConfrontoDoVulcao",
        "Magico": "ConfrontoDoMagia",
        "Pantano": "ConfrontoDoPantano",
        "AguaFunda": "ConfrontoDoMar",
        "AguaRasa": "ConfrontoDoMar",
    }.get(bioma, "ConfrontoDoVale")


def _musica_mundo_estavel(cena_mundo):
    global _tile_confirmado, _tile_candidato, _tile_candidato_inicio, _ultima_troca_bioma

    tile = _tile_mundo_atual(cena_mundo)
    if tile is None:
        return _musica_atual

    musica = _musica_por_tile(tile)
    if musica is None:
        return _musica_atual

    agora = pygame.time.get_ticks()

    if _tile_confirmado is None:
        _tile_confirmado = tile
        _tile_candidato = None
        return musica

    if tile == _tile_confirmado:
        _tile_candidato = None
        return _musica_por_tile(_tile_confirmado)

    if agora - _ultima_troca_bioma < _cooldown_bioma_ms:
        return _musica_por_tile(_tile_confirmado)

    if tile != _tile_candidato:
        _tile_candidato = tile
        _tile_candidato_inicio = agora
        return _musica_por_tile(_tile_confirmado)

    if agora - _tile_candidato_inicio >= _confirmacao_bioma_ms:
        _tile_confirmado = tile
        _tile_candidato = None
        _ultima_troca_bioma = agora
        return musica

    return _musica_por_tile(_tile_confirmado)


def _resolver_musica_alvo(jogo):
    global _cena_anterior, _menu_faixa_atual, _tile_confirmado, _tile_candidato

    cena = getattr(jogo, "Cena", None)
    cena_id = str(getattr(cena, "ID", "") or "")

    if cena_id != "Mundo":
        _tile_confirmado = None
        _tile_candidato = None

    if cena_id != _cena_anterior and cena_id == "Menu":
        _menu_faixa_atual = random.choice(["Menu1", "Menu2", "Menu3"])

    _cena_anterior = cena_id

    if cena_id == "Login":
        return "Login"

    if cena_id == "Carregamento":
        return "Carregamento"

    if cena_id == "Menu":
        if _tem_subtela_carregamento_menu():
            return "Carregamento"
        if _menu_faixa_atual is None:
            _menu_faixa_atual = random.choice(["Menu1", "Menu2", "Menu3"])
        return _menu_faixa_atual

    if cena_id == "Mundo":
        return _musica_mundo_estavel(cena)

    if cena_id == "Combate":
        finalizador = getattr(getattr(cena, "ControladorBatalha", None), "finalizador", None)
        if finalizador is not None and bool(getattr(finalizador, "_finalizacao_aberta", False)):
            vencedor = getattr(finalizador, "_vencedor_visual", lambda _r: "")(getattr(finalizador, "_ultimo_resultado", {}) or {})
            musica_fechamento = musica_resultado_batalha(vencedor)
            if musica_fechamento:
                return musica_fechamento
        contexto = getattr(jogo, "INFO", {}).get("CombateContexto") if isinstance(getattr(jogo, "INFO", None), dict) else {}
        tile_bioma = contexto.get("tile_bioma") if isinstance(contexto, dict) else None
        return musica_confronto_por_tile(tile_bioma)

    return None


def _atualizar_motor_musica():
    _atualizar_fade()
    _atualizar_loop_manual()


class SistemaMusicas:
    def atualizar_musica(self, jogo=None):
        if jogo is not None:
            config = getattr(jogo, "CONFIG", None)
            if isinstance(config, dict):
                VerificaSonoridade(config)

            alvo = _resolver_musica_alvo(jogo)

            if alvo and alvo != _musica_atual:
                if alvo in MUSICAS_MUNDO and _musica_atual in MUSICAS_MUNDO:
                    TransicaoMusica(alvo)
                else:
                    _iniciar_musica(alvo)

        _atualizar_motor_musica()


SISTEMA_MUSICAS = SistemaMusicas()
