import random

import pygame
pygame.mixer.init()

silencio = False
Volume = 0.0

def VerificaSonoridade(config):
    global silencio
    global Volume

    silencio = bool(config["Mudo"])
    Volume = max(0.0, min(1.0, float(config["Volume"])))

    volume_musica = 0.0 if silencio else Volume
    pygame.mixer.music.set_volume(volume_musica)

Sons = {
    "Clique": {"Som": lambda: pygame.mixer.Sound("Recursos/Sonoridades/Sons/Clique.wav"), "Volume": 0.75},
    "Bloq": {"Som": lambda: pygame.mixer.Sound("Recursos/Sonoridades/Sons/Bloq.wav"), "Volume": 0.85}
}

def tocar(som):
    audio = Sons[som]["Som"]()
    volume = Sons[som]["Volume"] * Volume

    if silencio:
        volume = 0

    audio.set_volume(min(volume, 1))  # Garante que não passa de 1
    audio.play()
    if volume > 1:
        audio2 = Sons[som]["Som"]()
        audio2.set_volume(min(volume - 1, 1))
        audio2.play()

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
        "fimloop": 134.19,
    },
    "Login": {
        "arquivo": "Recursos/Sonoridades/Musicas/Menu/Login.ogg",
        "loop": 7.03,
        "fimloop": 60.26,
    },
    "Carregamento": {
        "arquivo": "Recursos/Sonoridades/Musicas/Menu/Carregamento.ogg",
        "loop": 1.28,
        "fimloop": 109.43,
    },
    "ConfrontoDoVale": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDoVale.ogg",
        "loop": 2.34,
        "fimloop": 83.6
    },
    "ConfrontoDaNeve": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDaNeve.ogg",
        "loop": 2.32,
        "fimloop": 83.65
    },
    "ConfrontoDoMar": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDoMar.ogg",
        "loop": 2.27,
        "fimloop": 83.64
    },
    "ConfrontoDoDeserto": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDoDeserto.ogg",
        "loop": 2.33,
        "fimloop": 83.655
    },
    "ConfrontoDoVulcao": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDoVulcao.ogg",
        "loop": 2.34,
        "fimloop": 83.62
    },
    "ConfrontoDoMagia": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDaMagia.ogg",
        "loop": 2.34,
        "fimloop": 83.62
    },
    "ConfrontoDoPantano": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDoPantano.ogg",
        "loop": 2.34,
        "fimloop": 83.62
    },
    "Vale": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Vale.ogg",
        "loop": 3.2,
        "fimloop": 111.9
    },
    "Neve": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Neve.ogg",
        "loop": 4.2,
        "fimloop": 68.35
    },
    "Deserto": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Deserto.ogg",
        "loop": 0.2,
        "fimloop": 87.45
    },
    "Vulcão": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Vulcão.ogg",
        "loop": 10.19,
        "fimloop": 62.23,
    },
    "Praia": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Praia.ogg",
        "loop": 10.24,
        "fimloop": 154.99,
    }
}

# Variáveis de controle
_musica_atual = None
_loop_point = 0.0
_fimloop_point = 0.0
_posicao_manual = 0.0   # NOVO: corrige o loop perfeito
_vol_mult_atual = 1.0   # NOVO: multiplicador de volume da música atual

# ======= ESTADOS P/ TRANSIÇÃO =======
_fade_state = "idle"         # "idle" | "out" | "in"
_fade_start_ms = 0
_fade_ms = 5000              # 5 segundos
_fade_from_vol = 1.0
_fade_to_vol = 0.0
_fade_target_music = None    # nome da música a tocar após o fade-out
_fade_prev_music = None      # música que estava tocando quando o fade começou


def _volume_musica_alvo():
    if silencio:
        return 0.0
    return max(0.0, min(1.0, Volume * _vol_mult_atual))


def TransicaoMusica(nome):

    global _fade_state, _fade_start_ms, _fade_from_vol, _fade_to_vol
    global _fade_target_music, _fade_prev_music, _musica_atual

    nome = str(nome or "").strip()
    if not nome:
        return

    # Nada tocando? Toca direto, sem transição.
    if not pygame.mixer.music.get_busy() or _musica_atual is None:
        _iniciar_musica(nome)
        pygame.mixer.music.set_volume(_volume_musica_alvo())
        _fade_state = "idle"
        _fade_target_music = None
        _fade_prev_music = None
        return

    # Se a faixa pedida já é a atual e não há transição, não faz nada.
    if _fade_state == "idle" and nome == _musica_atual:
        return

    # Se já está no meio de uma transição...
    if _fade_state != "idle":
        # Pedido igual ao alvo já programado: mantém a transição em curso.
        if nome == _fade_target_music:
            return

        # Voltou para a música original no meio do fade-out: reverte o fade
        # a partir do volume atual, sem reiniciar a faixa.
        if nome == _fade_prev_music:
            _fade_state = "in"
            _fade_start_ms = pygame.time.get_ticks()
            _fade_from_vol = pygame.mixer.music.get_volume()
            _fade_to_vol = _volume_musica_alvo()
            _fade_target_music = None
            return

        # Trocar o alvo no meio da transição: reaproveita o volume atual.
        _fade_state = "out"
        _fade_start_ms = pygame.time.get_ticks()
        _fade_from_vol = pygame.mixer.music.get_volume()
        _fade_to_vol = 0.0
        _fade_target_music = nome
        if not _fade_prev_music:
            _fade_prev_music = _musica_atual
        return

    # Inicia um novo fade-out para trocar de faixa.
    _fade_prev_music = _musica_atual
    _fade_state = "out"
    _fade_start_ms = pygame.time.get_ticks()
    _fade_from_vol = pygame.mixer.music.get_volume()
    _fade_to_vol = 0.0
    _fade_target_music = nome


def _iniciar_musica(nome):
    """Inicia a música e define os pontos de loop."""
    global _musica_atual, _loop_point, _fimloop_point, _posicao_manual, _vol_mult_atual
    if nome not in Musicas:
        print(f"[ERRO] Música '{nome}' não encontrada.")
        return

    dados = Musicas[nome]
    _musica_atual = nome
    _loop_point = dados["loop"]
    _fimloop_point = dados["fimloop"]
    _vol_mult_atual = float(dados.get("vol_mult", 1.0))

    pygame.mixer.music.load(dados["arquivo"])
    pygame.mixer.music.set_volume(_volume_musica_alvo())
    pygame.mixer.music.play()  # toca do início
    _posicao_manual = 0.0  # zera a posição manual


def _atualizar_motor_musica():
    """Mantém loop perfeito e aplica transições de volume."""
    global _fade_state, _fade_start_ms, _fade_from_vol, _fade_to_vol
    global _fade_target_music, _musica_atual, _loop_point, _fimloop_point, _posicao_manual

    # ===== Fade (se ativo) =====
    if _fade_state != "idle":
        now = pygame.time.get_ticks()
        t = min(1.0, (now - _fade_start_ms) / float(_fade_ms))

        # Fade é aplicado sobre o volume-alvo atual (já com multiplicador)
        alvo = _volume_musica_alvo()
        # Mantém compatibilidade com o seu estado: "out" vai pra 0, "in" vai pro alvo
        if _fade_state == "out":
            v0 = _fade_from_vol
            v1 = 0.0
        else:  # "in"
            v0 = _fade_from_vol
            v1 = alvo

        vol = v0 + (v1 - v0) * t
        vol = max(0.0, min(1.0, vol))
        pygame.mixer.music.set_volume(vol)

        if t >= 1.0:
            if _fade_state == "out":
                if _fade_target_music is not None:
                    _iniciar_musica(_fade_target_music)  # já seta volume com vol_mult
                    pygame.mixer.music.set_volume(_volume_musica_alvo())
                _fade_state = "idle"
                _fade_target_music = None
            else:  # "in"
                _fade_state = "idle"

    # ===== Loop perfeito =====
    if _musica_atual and pygame.mixer.music.get_busy():
        pos = pygame.mixer.music.get_pos() / 1000.0 + _posicao_manual
        if pos >= _fimloop_point:
            pygame.mixer.music.play(-1, start=_loop_point)
            _posicao_manual = _loop_point


class _DummyLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class SistemaMusicas:
    def __init__(self):
        self._cena_anterior = None
        self._menu_faixa_atual = None
        self._ultimo_tile_mundo = None

    def atualizar_musica(self, jogo=None):
        if jogo is not None:
            config = getattr(jogo, "CONFIG", None)
            if isinstance(config, dict):
                VerificaSonoridade(config)
            cena = getattr(jogo, "Cena", None)
            cena_id = str(getattr(cena, "ID", "") or "")

            if cena_id != "Mundo":
                self._ultimo_tile_mundo = None

            alvo = self._resolver_musica_alvo(jogo)
            if alvo:
                if cena_id == "Mundo":
                    tile_atual = self._tile_mundo_atual(cena)
                    if tile_atual is not None:
                        self._ultimo_tile_mundo = tile_atual

                atual = self._musica_corrente_ou_em_transicao()
                if alvo != atual:
                    if self._eh_musica_mundo(alvo) and self._eh_musica_mundo(_musica_atual):
                        TransicaoMusica(alvo)
                    else:
                        _iniciar_musica(alvo)
        _atualizar_motor_musica()

    @staticmethod
    def _musica_corrente_ou_em_transicao():
        if _fade_state == "out" and _fade_target_music is not None:
            return _fade_target_music
        if _fade_state == "in" and _musica_atual is not None:
            return _musica_atual
        return _musica_atual

    def _resolver_musica_alvo(self, jogo):
        cena = getattr(jogo, "Cena", None)
        cena_id = str(getattr(cena, "ID", "") or "")

        if cena_id != self._cena_anterior and cena_id == "Menu":
            self._menu_faixa_atual = random.choice(["Menu1", "Menu2", "Menu3"])
        self._cena_anterior = cena_id

        if cena_id == "Login":
            return "Login"

        if cena_id == "Carregamento":
            return "Carregamento"

        if cena_id == "Menu":
            if self._menu_faixa_atual is None:
                self._menu_faixa_atual = random.choice(["Menu1", "Menu2", "Menu3"])
            if self._tem_subtela_carregamento_menu():
                return "Carregamento"
            return self._menu_faixa_atual

        if cena_id == "Mundo":
            return self._musica_mundo_por_bloco(cena)

        return None

    def _tem_subtela_carregamento_menu(self):
        try:
            from Codigo.Telas.TelaOperador import possui_subtela_carregamento_ativa
            return bool(possui_subtela_carregamento_ativa())
        except Exception:
            return False

    def _musica_mundo_por_bloco(self, cena_mundo):
        tile = self._tile_mundo_atual(cena_mundo)
        if tile is None:
            return self._musica_corrente_ou_em_transicao()

        if self._ultimo_tile_mundo is not None and tile == self._ultimo_tile_mundo:
            return self._musica_corrente_ou_em_transicao()

        musica = self._mapa_musica_mundo_por_tile(tile)
        if musica is None:
            return self._musica_corrente_ou_em_transicao()
        return musica

    def _tile_mundo_atual(self, cena_mundo):
        controlador_mundo = getattr(cena_mundo, "ControladorMundo", None)
        if controlador_mundo is None:
            return None

        player = getattr(controlador_mundo, "player_local", None)
        leitor = getattr(controlador_mundo, "Leitor", None)
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

        tamanho_chunk = max(1, int(tamanho_chunk))
        bloco_x = int(px // 1)
        bloco_y = int(py // 1)
        chunk_x = int(bloco_x // tamanho_chunk)
        chunk_y = int(bloco_y // tamanho_chunk)
        grid = chunks.get((chunk_x, chunk_y))
        if not grid:
            return None

        local_x = int(bloco_x - (chunk_x * tamanho_chunk))
        local_y = int(bloco_y - (chunk_y * tamanho_chunk))
        if local_y < 0 or local_y >= len(grid):
            return None
        linha = grid[local_y]
        if local_x < 0 or local_x >= len(linha):
            return None

        try:
            return int(linha[local_x])
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _mapa_musica_mundo_por_tile(tile):
        mapa = {
            2: "Vale",
            3: "Vale",
            6: "Neve",
            5: "Deserto",
            4: "Praia",
            8: "Vulcão",
        }
        return mapa.get(tile)

    @staticmethod
    def _eh_musica_mundo(nome):
        return nome in {"Vale", "Neve", "Deserto", "Praia", "Vulcão"}


SISTEMA_MUSICAS = SistemaMusicas()
