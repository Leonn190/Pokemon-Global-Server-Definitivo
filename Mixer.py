import pygame

pygame.init()
pygame.mixer.init()

# Configuração da tela
tela = pygame.display.set_mode((500, 250))
pygame.display.set_caption("Player com Loop e Avanço")

Volume = 0.8

Musicas = {
}

# Variáveis de controle
_musica_atual = None
_loop_point = 0.0
_fimloop_point = 0.0
_posicao_manual = 0.0
_lista_musicas = list(Musicas.keys())
_indice_musica = 0

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
    _posicao_manual = 0.0
    print(f"Tocando: {nome}")

def AtualizarMusica():
    """Mantém o loop perfeito."""
    global _posicao_manual
    if _musica_atual and pygame.mixer.music.get_busy():
        pos = pygame.mixer.music.get_pos() / 1000.0 + _posicao_manual
        if pos >= _fimloop_point:
            pygame.mixer.music.play(-1, start=_loop_point)
            _posicao_manual = _loop_point

def Avancar(tempo):
    """Avança a música em X segundos respeitando o loop."""
    global _posicao_manual
    nova_pos = _posicao_manual + (pygame.mixer.music.get_pos() / 1000.0) + tempo

    # Se passar do fimloop, reinicia no loop
    if nova_pos >= _fimloop_point:
        nova_pos = _loop_point + (nova_pos - _fimloop_point)

    pygame.mixer.music.play(-1, start=nova_pos)
    _posicao_manual = nova_pos

def PegarPosicaoAtual():
    """Retorna a posição atual em segundos (respeitando loop)."""
    if not _musica_atual:
        return 0.0
    return _posicao_manual + (pygame.mixer.music.get_pos() / 1000.0)

def DesenharBarra(tela):
    """Desenha a barra de progresso da música."""
    largura = 400
    altura = 20
    x = 50
    y = 100

    # Fundo da barra
    pygame.draw.rect(tela, (80, 80, 80), (x, y, largura, altura), border_radius=5)

    # Posição atual
    pos = PegarPosicaoAtual()
    progresso = min(max((pos / _fimloop_point), 0.0), 1.0)  # 0.0 a 1.0

    # Barra preenchida
    preenchido = int(largura * progresso)
    pygame.draw.rect(tela, (0, 200, 100), (x, y, preenchido, altura), border_radius=5)

    # Marcador do loop
    loop_x = x + int((_loop_point / _fimloop_point) * largura)
    pygame.draw.line(tela, (200, 200, 0), (loop_x, y), (loop_x, y + altura), 2)

    # Bordas
    pygame.draw.rect(tela, (255, 255, 255), (x, y, largura, altura), 2, border_radius=5)

def DesenharBotao(tela, rect, texto, ativo=False):
    """Desenha um botão simples."""
    cor = (100, 100, 100) if not ativo else (150, 150, 150)
    pygame.draw.rect(tela, cor, rect, border_radius=8)
    pygame.draw.rect(tela, (255, 255, 255), rect, 2, border_radius=8)

    fonte = pygame.font.SysFont(None, 24)
    txt = fonte.render(texto, True, (255, 255, 255))
    txt_rect = txt.get_rect(center=rect.center)
    tela.blit(txt, txt_rect)

# ---------------- LOOP PRINCIPAL ----------------
clock = pygame.time.Clock()
Musica(_lista_musicas[_indice_musica])  # inicia a primeira música

rodando = True
while rodando:
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            rodando = False

        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_RIGHT:  # seta → avança 10s
                Avancar(10)

        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            mx, my = evento.pos
            if btn_prev.collidepoint(mx, my):
                _indice_musica = (_indice_musica - 1) % len(_lista_musicas)
                Musica(_lista_musicas[_indice_musica])
            elif btn_next.collidepoint(mx, my):
                _indice_musica = (_indice_musica + 1) % len(_lista_musicas)
                Musica(_lista_musicas[_indice_musica])

    AtualizarMusica()

    tela.fill((30, 30, 30))
    DesenharBarra(tela)

    # Botões
    btn_prev = pygame.Rect(120, 160, 100, 40)
    btn_next = pygame.Rect(280, 160, 100, 40)
    DesenharBotao(tela, btn_prev, "Anterior")
    DesenharBotao(tela, btn_next, "Próxima")

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
