import os
import json
import pygame

pygame.init()
pygame.mixer.init()

# ===================== CONFIG =====================
TELA_W, TELA_H = 740, 320
tela = pygame.display.set_mode((TELA_W, TELA_H))
pygame.display.set_caption("Editor de Loop (Pygame)")

FPS = 60
VOLUME = 0.4
SAVE_PATH = "loop_points.json"   # onde salva/carrega os pontos

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
    }
}

# ===================== UTIL =====================
def clamp(v, a, b):
    return max(a, min(b, v))

def fmt_time(t):
    if t < 0:
        t = 0
    m = int(t // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 100)
    return f"{m:02d}:{s:02d}.{ms:02d}"

def file_exists(path):
    try:
        return os.path.isfile(path)
    except OSError:
        return False

# ===================== UI (Botão) =====================
class Botao:
    def __init__(self, rect, texto):
        self.rect = pygame.Rect(rect)
        self.texto = texto

    def draw(self, surf, fonte, hover=False):
        bg = (60, 60, 60) if not hover else (90, 90, 90)
        pygame.draw.rect(surf, bg, self.rect, border_radius=10)
        pygame.draw.rect(surf, (255, 255, 255), self.rect, 2, border_radius=10)
        txt = fonte.render(self.texto, True, (255, 255, 255))
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def hit(self, pos):
        return self.rect.collidepoint(pos)

# ===================== PLAYER/EDITOR =====================
class LoopEditor:
    def __init__(self, musicas: dict):
        self.musicas = musicas
        self.lista = list(musicas.keys())
        self.idx = 0

        self.nome = None
        self.arquivo = None

        # pontos de loop (segundos)
        self.loop_ini = 0.0
        self.loop_fim = 0.0

        # duração (segundos)
        self.dur = 1.0

        # relógio manual de posição
        self.playing = False
        self._base_pos = 0.0          # "onde começou" (seek)
        self._t0_ms = 0               # tick quando demos play()
        self._paused_pos = 0.0        # posição quando pausou

        # scrubbing
        self.scrubbing = False

        # se True: aplica loop automaticamente; se False: toca livre (pra editar)
        self.loop_preview = True

        self.carregar_musica(self.lista[self.idx], tentar_carregar_pontos=True)

    def _calc_duracao(self, arquivo):
        try:
            snd = pygame.mixer.Sound(arquivo)
            d = snd.get_length()
            if d and d > 0.1:
                return float(d)
        except pygame.error:
            pass
        return 1.0

    def _pos_agora(self):
        if not self.playing:
            return self._paused_pos
        dt = (pygame.time.get_ticks() - self._t0_ms) / 1000.0
        return self._base_pos + dt

    def _reiniciar_no(self, pos):
        pos = clamp(pos, 0.0, max(0.0, self.dur))
        pygame.mixer.music.play(-1, start=pos)
        self._base_pos = pos
        self._t0_ms = pygame.time.get_ticks()
        self._paused_pos = pos
        self.playing = True

    def carregar_musica(self, nome, tentar_carregar_pontos=False):
        if nome not in self.musicas:
            return

        dados = self.musicas[nome]
        arquivo = dados["arquivo"]
        if not file_exists(arquivo):
            print(f"[ERRO] Arquivo não encontrado: {arquivo}")
            return

        self.nome = nome
        self.arquivo = arquivo

        self.dur = self._calc_duracao(arquivo)

        # defaults (do dicionário)
        self.loop_ini = float(dados.get("loop", 0.0))
        self.loop_fim = float(dados.get("fimloop", self.dur))

        # sanitiza
        self.loop_ini = clamp(self.loop_ini, 0.0, self.dur)
        self.loop_fim = clamp(self.loop_fim, 0.0, self.dur)
        if self.loop_fim <= self.loop_ini:
            self.loop_fim = clamp(self.loop_ini + 0.1, 0.0, self.dur)

        pygame.mixer.music.load(arquivo)
        pygame.mixer.music.set_volume(VOLUME)
        self._reiniciar_no(0.0)

        if tentar_carregar_pontos:
            self.carregar_pontos_json()

        print(f"Tocando: {self.nome} | dur={self.dur:.2f}s | loop=({self.loop_ini:.2f}..{self.loop_fim:.2f})")

    def prox(self):
        self.idx = (self.idx + 1) % len(self.lista)
        self.carregar_musica(self.lista[self.idx], tentar_carregar_pontos=True)

    def ant(self):
        self.idx = (self.idx - 1) % len(self.lista)
        self.carregar_musica(self.lista[self.idx], tentar_carregar_pontos=True)

    def play_pause(self):
        if self.playing:
            self._paused_pos = self._pos_agora()
            pygame.mixer.music.pause()
            self.playing = False
        else:
            pygame.mixer.music.unpause()
            self._base_pos = self._paused_pos
            self._t0_ms = pygame.time.get_ticks()
            self.playing = True

    def set_loop_ini(self):
        p = self._pos_agora()
        self.loop_ini = clamp(p, 0.0, self.dur)
        if self.loop_fim <= self.loop_ini:
            self.loop_fim = clamp(self.loop_ini + 0.1, 0.0, self.dur)

    def set_loop_fim(self):
        p = self._pos_agora()
        self.loop_fim = clamp(p, 0.0, self.dur)
        if self.loop_fim <= self.loop_ini:
            self.loop_ini = clamp(self.loop_fim - 0.1, 0.0, self.dur)

    def reset_loop(self):
        self.loop_ini = 0.0
        self.loop_fim = self.dur

    def update(self):
        # NÃO aplica loop se: pausado, scrubbando, ou preview desligado
        if (not self.playing) or self.scrubbing or (not self.loop_preview):
            return

        pos = self._pos_agora()
        if pos >= self.loop_fim:
            excedente = pos - self.loop_fim
            loop_len = max(0.001, self.loop_fim - self.loop_ini)
            novo = self.loop_ini + (excedente % loop_len)
            self._reiniciar_no(novo)

    def seek(self, pos):
        self._reiniciar_no(pos)

    def salvar_pontos_json(self, path=SAVE_PATH):
        data = {}
        if file_exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        data[self.nome] = {
            "arquivo": self.arquivo,
            "loop": float(self.loop_ini),
            "fimloop": float(self.loop_fim),
            "dur": float(self.dur)
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] Salvo em {path}: {self.nome} loop=({self.loop_ini:.2f}..{self.loop_fim:.2f})")

    def carregar_pontos_json(self, path=SAVE_PATH):
        if not file_exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        if self.nome in data:
            item = data[self.nome]
            self.loop_ini = clamp(float(item.get("loop", self.loop_ini)), 0.0, self.dur)
            self.loop_fim = clamp(float(item.get("fimloop", self.loop_fim)), 0.0, self.dur)
            if self.loop_fim <= self.loop_ini:
                self.loop_fim = clamp(self.loop_ini + 0.1, 0.0, self.dur)

            print(f"[OK] Carregado de {path}: {self.nome} loop=({self.loop_ini:.2f}..{self.loop_fim:.2f})")

# ===================== DESENHO =====================
def draw_barra(surf, editor: LoopEditor, rect, fonte):
    x, y, w, h = rect
    pygame.draw.rect(surf, (70, 70, 70), rect, border_radius=10)

    pos = editor._pos_agora()
    dur = max(0.001, editor.dur)
    prog = clamp(pos / dur, 0.0, 1.0)

    fill_w = int(w * prog)
    pygame.draw.rect(surf, (0, 200, 110), (x, y, fill_w, h), border_radius=10)

    # loop markers
    ini_x = x + int((editor.loop_ini / dur) * w)
    fim_x = x + int((editor.loop_fim / dur) * w)
    pygame.draw.line(surf, (255, 220, 0), (ini_x, y - 6), (ini_x, y + h + 6), 3)
    pygame.draw.line(surf, (255, 120, 120), (fim_x, y - 6), (fim_x, y + h + 6), 3)

    pygame.draw.rect(surf, (255, 255, 255), rect, 2, border_radius=10)

    info = f"{editor.nome} | {fmt_time(pos)} / {fmt_time(editor.dur)}"
    surf.blit(fonte.render(info, True, (240, 240, 240)), (x, y - 32))

    loop_info = f"Loop: {fmt_time(editor.loop_ini)}  ->  {fmt_time(editor.loop_fim)} | Preview: {'ON' if editor.loop_preview else 'OFF'}"
    surf.blit(fonte.render(loop_info, True, (240, 240, 240)), (x, y + h + 12))

def barra_pos_to_time(mx, barra_rect, dur):
    x, y, w, h = barra_rect
    t = ((mx - x) / max(1, w)) * max(0.0, dur)
    return clamp(t, 0.0, dur)

# ===================== MAIN =====================
def main():
    fonte = pygame.font.SysFont(None, 24)
    fonte_big = pygame.font.SysFont(None, 28)

    editor = LoopEditor(Musicas)

    # barra centralizada no eixo Y
    barra_h = 22
    barra_y = (TELA_H // 2) - (barra_h // 2)
    barra_rect = pygame.Rect(40, barra_y, 660, barra_h)

    # botões (posição ajustada pra ficar legal com barra no meio)
    btn_prev = Botao((40, 240, 110, 46), "Anterior")
    btn_next = Botao((160, 240, 110, 46), "Próxima")
    btn_play = Botao((280, 240, 120, 46), "Play/Pause")
    btn_ini  = Botao((410, 240, 140, 46), "Set Loop Ini")
    btn_fim  = Botao((560, 240, 140, 46), "Set Loop Fim")

    btn_save = Botao((40, 20, 120, 40), "Salvar (S)")
    btn_load = Botao((170, 20, 140, 40), "Carregar (L)")
    btn_rst  = Botao((320, 20, 140, 40), "Reset (R)")

    clock = pygame.time.Clock()
    rodando = True

    while rodando:
        mouse_pos = pygame.mouse.get_pos()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                rodando = False

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    rodando = False
                elif e.key == pygame.K_SPACE:
                    editor.play_pause()
                elif e.key == pygame.K_i:
                    editor.set_loop_ini()
                elif e.key == pygame.K_o:
                    editor.set_loop_fim()
                elif e.key == pygame.K_r:
                    editor.reset_loop()
                elif e.key == pygame.K_s:
                    editor.salvar_pontos_json()
                elif e.key == pygame.K_l:
                    editor.carregar_pontos_json()
                elif e.key == pygame.K_p:
                    editor.loop_preview = not editor.loop_preview

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if barra_rect.collidepoint(e.pos):
                    editor.scrubbing = True
                    t = barra_pos_to_time(e.pos[0], barra_rect, editor.dur)
                    editor.seek(t)
                else:
                    if btn_prev.hit(e.pos):
                        editor.ant()
                    elif btn_next.hit(e.pos):
                        editor.prox()
                    elif btn_play.hit(e.pos):
                        editor.play_pause()
                    elif btn_ini.hit(e.pos):
                        editor.set_loop_ini()
                    elif btn_fim.hit(e.pos):
                        editor.set_loop_fim()
                    elif btn_save.hit(e.pos):
                        editor.salvar_pontos_json()
                    elif btn_load.hit(e.pos):
                        editor.carregar_pontos_json()
                    elif btn_rst.hit(e.pos):
                        editor.reset_loop()

            if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                editor.scrubbing = False

            if e.type == pygame.MOUSEMOTION:
                if editor.scrubbing:
                    t = barra_pos_to_time(e.pos[0], barra_rect, editor.dur)
                    editor.seek(t)

        editor.update()

        tela.fill((25, 25, 28))

        # topo
        btn_save.draw(tela, fonte, btn_save.hit(mouse_pos))
        btn_load.draw(tela, fonte, btn_load.hit(mouse_pos))
        btn_rst.draw(tela, fonte, btn_rst.hit(mouse_pos))

        # barra
        draw_barra(tela, editor, barra_rect, fonte_big)

        # botoes baixo
        btn_prev.draw(tela, fonte, btn_prev.hit(mouse_pos))
        btn_next.draw(tela, fonte, btn_next.hit(mouse_pos))
        btn_play.draw(tela, fonte, btn_play.hit(mouse_pos))
        btn_ini.draw(tela, fonte, btn_ini.hit(mouse_pos))
        btn_fim.draw(tela, fonte, btn_fim.hit(mouse_pos))

        # dicas
        status_loop = "ON" if editor.loop_preview else "OFF"
        dicas = f"Espaço: Play/Pause | I: Loop Ini | O: Loop Fim | Arraste: Seek | P: Loop Preview {status_loop} | S/L: Salvar/Carregar | R: Reset"
        tela.blit(fonte.render(dicas, True, (190, 190, 190)), (40, 290))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()