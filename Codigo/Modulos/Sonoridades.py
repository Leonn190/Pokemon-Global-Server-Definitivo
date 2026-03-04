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
        "fimloop": 110.55,
        "vol_mult": 1.0
    },
    "Menu2": {
        "arquivo": "Recursos/Sonoridades/Musicas/Menu/Menu2.ogg",
        "loop": 1.34,
        "fimloop": 146.92,
        "vol_mult": 1.0
    },
    "Menu3": {
        "arquivo": "Recursos/Sonoridades/Musicas/Menu/Menu3.ogg",
        "loop": 1.67,
        "fimloop": 134.19,
        "vol_mult": 1.0
    },
    "Login": {
        "arquivo": "Recursos/Sonoridades/Musicas/Menu/Login.ogg",
        "loop": 7.03,
        "fimloop": 60.26,
        "vol_mult": 0.6
    },
    "ConfrontoDoVale": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDoVale.ogg",
        "loop": 2.34,
        "fimloop": 83.6,
        "vol_mult": 1.0
    },
    "ConfrontoDaNeve": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDaNeve.ogg",
        "loop": 2.32,
        "fimloop": 83.65,
        "vol_mult": 1.0
    },
    "ConfrontoDoMar": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDoMar.ogg",
        "loop": 2.27,
        "fimloop": 83.64,
        "vol_mult": 1.0
    },
    "ConfrontoDoDeserto": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDoDeserto.ogg",
        "loop": 2.33,
        "fimloop": 83.655,
        "vol_mult": 1.0
    },
    "ConfrontoDoVulcao": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDoVulcao.ogg",
        "loop": 2.34,
        "fimloop": 83.62,
        "vol_mult": 1.0
    },
    "ConfrontoDoMagia": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDaMagia.ogg",
        "loop": 2.34,
        "fimloop": 83.62,
        "vol_mult": 1.0
    },
    "ConfrontoDoPantano": {
        "arquivo": "Recursos/Sonoridades/Musicas/Combate/ConfrontoDoPantano.ogg",
        "loop": 2.34,
        "fimloop": 83.62,
        "vol_mult": 1.0
    },
    "Vale": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Vale.ogg",
        "loop": 3.2,
        "fimloop": 111.9,
        "vol_mult": 1.0
    },
    "Neve": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Neve.ogg",
        "loop": 4.2,
        "fimloop": 68.35,
        "vol_mult": 1.0
    },
    "Deserto": {
        "arquivo": "Recursos/Sonoridades/Musicas/Mundo/Deserto.ogg",
        "loop": 0.2,
        "fimloop": 87.45,
        "vol_mult": 1.0
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

    # Nada tocando? Toca direto, sem transição
    if not pygame.mixer.music.get_busy():
        Musica(nome)
        pygame.mixer.music.set_volume(_volume_musica_alvo())
        _fade_state = "idle"
        _fade_target_music = None
        _fade_prev_music = None
        return

    # Se já está no meio de uma transição...
    if _fade_state != "idle":
        # Cancelamento: pediram de volta a música que tocava antes do fade-out
        if nome == _fade_prev_music:
            _fade_state = "in"
            _fade_start_ms = pygame.time.get_ticks()
            _fade_from_vol = pygame.mixer.music.get_volume()
            _fade_to_vol = _volume_musica_alvo()
            _fade_target_music = None
            return
        # Trocar alvo durante o fade-out: atualiza alvo e recomeça fade a partir do volume atual
        _fade_state = "out"
        _fade_start_ms = pygame.time.get_ticks()
        _fade_from_vol = pygame.mixer.music.get_volume()
        _fade_to_vol = 0.0
        _fade_target_music = nome
        # _fade_prev_music mantém a referência da música original
        return

    # Inicia um novo fade-out para trocar de faixa
    _fade_prev_music = _musica_atual
    _fade_state = "out"
    _fade_start_ms = pygame.time.get_ticks()
    _fade_from_vol = pygame.mixer.music.get_volume()
    _fade_to_vol = 0.0
    _fade_target_music = nome


def Musica(nome):
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


def AtualizarMusica():
    """Chamar a cada frame: mantém o loop perfeito e aplica a transição suave."""
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
                    Musica(_fade_target_music)  # já seta volume com vol_mult
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