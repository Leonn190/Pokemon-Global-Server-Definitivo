import random
import pygame

from Codigo.ModulosGerais.Auxiliares import bioma_por_tile

silencio = False
Volume = 0.0

Sons = {
    "Clique": {
        "Arquivo": "Recursos/Sonoridades/Sons/Clique.wav",
        "Som": None,
        "Volume": 0.75
    },
    "Bloq": {
        "Arquivo": "Recursos/Sonoridades/Sons/Bloq.wav",
        "Som": None,
        "Volume": 0.85
    },
    "Abre": {
        "Arquivo": "Recursos/Sonoridades/Sons/Abre.wav",
        "Som": None,
        "Volume": 0.80
    },
    "AbrirBau": {
        "Arquivo": "Recursos/Sonoridades/Sons/AbrirBau.mp3",
        "Som": None,
        "Volume": 0.85
    },
    "Apagou": {
        "Arquivo": "Recursos/Sonoridades/Sons/Apagou.wav",
        "Som": None,
        "Volume": 0.80
    },
    "BaterFerramenta": {
        "Arquivo": "Recursos/Sonoridades/Sons/BaterFerramenta.mp3",
        "Som": None,
        "Volume": 0.85
    },
    "CliqueOpções": {
        "Arquivo": "Recursos/Sonoridades/Sons/CliqueOpções.mp3",
        "Som": None,
        "Volume": 0.80
    },
    "Conseguiu": {
        "Arquivo": "Recursos/Sonoridades/Sons/Conseguiu.wav",
        "Som": None,
        "Volume": 0.85
    },
    "Dropar": {
        "Arquivo": "Recursos/Sonoridades/Sons/Dropar.wav",
        "Som": None,
        "Volume": 0.85
    },
    "Falhou": {
        "Arquivo": "Recursos/Sonoridades/Sons/Falhou.wav",
        "Som": None,
        "Volume": 0.85
    },
    "Fecha": {
        "Arquivo": "Recursos/Sonoridades/Sons/Fecha.wav",
        "Som": None,
        "Volume": 0.80
    },
    "Salvou": {
        "Arquivo": "Recursos/Sonoridades/Sons/Salvou.wav",
        "Som": None,
        "Volume": 0.85
    }
}

Musicas = {
    "Menu1": {
        "arquivo": "Recursos/Sonoridades/Musicas/Menu/Menu1.ogg",
        "loop": 12.7,
        "fimloop": 110.55
    },
    "Menu2": {
        "arquivo": "Recursos/Sonoridades/Musicas/Menu/Menu2.ogg",
        "loop": 1.34,
        "fimloop": 146.92
    },
    "Menu3": {
        "arquivo": "Recursos/Sonoridades/Musicas/Menu/Menu3.ogg",
        "loop": 1.67,
        "fimloop": 134.19
    },
    "Login": {
        "arquivo": "Recursos/Sonoridades/Musicas/Menu/Login.ogg",
        "loop": 7.03,
        "fimloop": 60.26
    },
    "Carregamento": {
        "arquivo": "Recursos/Sonoridades/Musicas/Menu/Carregamento.ogg",
        "loop": 1.28,
        "fimloop": 109.43
    },
    "ConfrontoDoVale": {
        "arquivo": "Recursos/Sonoridades/Musicas/Batalha/Confrontos/ConfrontoDoVale.ogg",
        "loop": 2.34,
        "fimloop": 83.6
    },
    "ConfrontoDaNeve": {
        "arquivo": "Recursos/Sonoridades/Musicas/Batalha/Confrontos/ConfrontoDaNeve.ogg",
        "loop": 2.32,
        "fimloop": 83.65
    },
    "ConfrontoDoMar": {
        "arquivo": "Recursos/Sonoridades/Musicas/Batalha/Confrontos/ConfrontoDoMar.ogg",
        "loop": 2.27,
        "fimloop": 83.64
    },
    "ConfrontoDoDeserto": {
        "arquivo": "Recursos/Sonoridades/Musicas/Batalha/Confrontos/ConfrontoDoDeserto.ogg",
        "loop": 2.33,
        "fimloop": 83.655
    },
    "ConfrontoDoVulcao": {
        "arquivo": "Recursos/Sonoridades/Musicas/Batalha/Confrontos/ConfrontoDoVulcao.ogg",
        "loop": 2.34,
        "fimloop": 83.62
    },
    "ConfrontoDoMagia": {
        "arquivo": "Recursos/Sonoridades/Musicas/Batalha/Confrontos/ConfrontoDaMagia.ogg",
        "loop": 2.34,
        "fimloop": 83.62
    },
    "ConfrontoDoPantano": {
        "arquivo": "Recursos/Sonoridades/Musicas/Batalha/Confrontos/ConfrontoDoPantano.ogg",
        "loop": 2.34,
        "fimloop": 83.62
    },
    "Vale": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Vale.ogg",
        "loop": 3.2,
        "fimloop": 111.9,
        "volume": 0.55
    },
    "Neve": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Neve.ogg",
        "loop": 4.2,
        "fimloop": 68.35,
        "volume": 0.55
    },
    "Deserto": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Deserto.ogg",
        "loop": 0.2,
        "fimloop": 87.45,
        "volume": 0.55
    },
    "Vulcão": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Vulcão.ogg",
        "loop": 10.19,
        "fimloop": 62.23,
        "volume": 0.55
    },
    "Praia": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Praia.ogg",
        "loop": 10.24,
        "fimloop": 154.99,
        "volume": 0.55
    }
}

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
