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
    "Clique": {"Som": lambda: pygame.mixer.Sound("Recursos/Audio/Sons/Clique.wav"), "Volume": 0.75},
    "Bloq": {"Som": lambda: pygame.mixer.Sound("Recursos/Audio/Sons/Bloq.wav"), "Volume": 0.85}
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
    "Menu": {
        "arquivo": "Recursos/Sonoridades/Musicas/TelaMenu.ogg",
        "loop": 12.7,
        "fimloop": 110.55
    },
    "ConfrontoDoVale": {
        "arquivo": "Recursos/Audio/Musicas/ConfrontoDoVale.ogg",
        "loop": 2.34,
        "fimloop": 83.6
    },
    "ConfrontoDaNeve": {
        "arquivo": "Recursos/Audio/Musicas/ConfrontoDaNeve.ogg",
        "loop": 2.32,
        "fimloop": 83.6
    },
    "ConfrontoDoMar": {
        "arquivo": "Recursos/Audio/Musicas/ConfrontoDoMar.ogg",
        "loop": 2.27,
        "fimloop": 83.64
    },
    "ConfrontoDoDeserto": {
        "arquivo": "Recursos/Audio/Musicas/ConfrontoDoDeserto.ogg",
        "loop": 2.33,
        "fimloop": 83.655
    },
    "ConfrontoDoVulcao": {
        "arquivo": "Recursos/Audio/Musicas/ConfrontoDoVulcao.ogg",
        "loop": 2.34,
        "fimloop": 83.62
    },
    "ConfrontoDoMagia": {
        "arquivo": "Recursos/Audio/Musicas/ConfrontoDaMagia.ogg",
        "loop": 2.34,
        "fimloop": 83.62
    },
    "ConfrontoDoPantano": {
        "arquivo": "Recursos/Audio/Musicas/ConfrontoDoPantano.ogg",
        "loop": 2.34,
        "fimloop": 83.62
    },
    "Vale": {
        "arquivo": "Recursos/Audio/Musicas/Vale.ogg",
        "loop": 3.2,
        "fimloop": 111.9
    },
    "Neve": {
        "arquivo": "Recursos/Audio/Musicas/Neve.ogg",
        "loop": 4.2,
        "fimloop": 68.35
    },
    "Deserto": {
        "arquivo": "Recursos/Audio/Musicas/Deserto.ogg",
        "loop": 0.2,
        "fimloop": 87.45
    }
}

# Variáveis de controle
_musica_atual = None
_loop_point = 0.0
_fimloop_point = 0.0
_posicao_manual = 0.0   # NOVO: corrige o loop perfeito

# ======= ESTADOS P/ TRANSIÇÃO =======
_fade_state = "idle"         # "idle" | "out" | "in"
_fade_start_ms = 0
_fade_ms = 5000              # 5 segundos
_fade_from_vol = 1.0
_fade_to_vol = 0.0
_fade_target_music = None    # nome da música a tocar após o fade-out
_fade_prev_music = None      # música que estava tocando quando o fade começou

def TransicaoMusica(nome):

    global _fade_state, _fade_start_ms, _fade_from_vol, _fade_to_vol
    global _fade_target_music, _fade_prev_music, _musica_atual

    # Nada tocando? Toca direto, sem transição
    if not pygame.mixer.music.get_busy():
        Musica(nome)
        pygame.mixer.music.set_volume(Volume)
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
            _fade_to_vol = Volume
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
    global _musica_atual, _loop_point, _fimloop_point, _posicao_manual
    if nome not in Musicas:
        print(f"[ERRO] Música '{nome}' não encontrada.")
        return

    dados = Musicas[nome]
    _musica_atual = nome
    _loop_point = dados["loop"]
    _fimloop_point = dados["fimloop"]

    pygame.mixer.music.load(dados["arquivo"])
    pygame.mixer.music.set_volume(Volume)
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
        vol = _fade_from_vol + (_fade_to_vol - _fade_from_vol) * t
        vol = max(0.0, min(1.0, vol))
        pygame.mixer.music.set_volume(vol)

        if t >= 1.0:
            if _fade_state == "out":
                # troca de faixa sem fade-in: volta direto ao volume padrão
                if _fade_target_music is not None:
                    Musica(_fade_target_music)          # toca do início
                    pygame.mixer.music.set_volume(Volume)
                # encerra transição
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
