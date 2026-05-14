import math
import os
from dataclasses import dataclass

import pygame


SKINS_DIR = r"C:\Users\euleo\OneDrive\Documentos\GitHub\Pokemon-Global-Server-Definitivo\Recursos\Visual\Skins"
OUTPUT_DIR = os.path.join(SKINS_DIR, "redimensionadas")
SKIN_MIN = 1
SKIN_MAX = 97
SCREEN_W = 1280
SCREEN_H = 820
FPS = 60
BG_COLOR = (18, 22, 30)
PANEL_COLOR = (28, 35, 46)
PANEL_BORDER = (70, 88, 110)
TEXT_COLOR = (232, 238, 246)
MUTED_TEXT = (174, 188, 205)
ACCENT = (88, 170, 255)
ACCENT_2 = (112, 205, 138)
BUTTON_COLOR = (66, 123, 214)
BUTTON_HOVER = (88, 145, 236)
ERROR_COLOR = (230, 100, 100)
SUCCESS_COLOR = (95, 208, 126)
PREVIEW_CENTER = (SCREEN_W // 2, 360)


pygame.init()
pygame.font.init()


FONT = pygame.font.SysFont("consolas", 20)
FONT_SMALL = pygame.font.SysFont("consolas", 17)
FONT_BIG = pygame.font.SysFont("consolas", 28, bold=True)


def _cor_predominante(surface: pygame.Surface) -> tuple[int, int, int]:
    amostra = pygame.transform.smoothscale(surface, (16, 16))
    soma_r = soma_g = soma_b = total = 0
    for y in range(amostra.get_height()):
        for x in range(amostra.get_width()):
            r, g, b, a = amostra.get_at((x, y))
            if a < 25:
                continue
            soma_r += r
            soma_g += g
            soma_b += b
            total += 1

    if total == 0:
        return (198, 236, 247)

    return (soma_r // total, soma_g // total, soma_b // total)


def _clarear_cor(cor: tuple[int, int, int], fator: float = 0.35) -> tuple[int, int, int]:
    r, g, b = cor
    r = int(r + (255 - r) * fator)
    g = int(g + (255 - g) * fator)
    b = int(b + (255 - b) * fator)
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def redimensionar_surface_proporcional(surface: pygame.Surface, escala: float) -> pygame.Surface:
    largura_original = max(1, surface.get_width())
    altura_original = max(1, surface.get_height())
    escala = max(0.01, float(escala))
    nova_largura = max(1, int(round(largura_original * escala)))
    nova_altura = max(1, int(round(altura_original * escala)))
    return pygame.transform.smoothscale(surface, (nova_largura, nova_altura)).convert_alpha()


class DesenhaAtor:
    def __init__(self, skin_surface: pygame.Surface, escala: float = 1.0, tile_px: int = 50):
        self._escala_tiles = float(escala)
        self._tile_px = max(1, int(tile_px))
        self._tile_px_referencia = 50
        self.sprite_offset_graus = -90

        self._skin_original = skin_surface.convert_alpha()
        self._skin = self._redimensionar_skin(self._skin_original)

        base = _cor_predominante(self._skin_original)
        self._cor_maos = _clarear_cor(base, fator=0.40)
        self._cache_corpo_rotacionado: dict[int, pygame.Surface] = {}
        self._cache_ordem_angulos: list[int] = []
        self._cache_limite_angulos = 120

    def _redimensionar_skin(self, surf: pygame.Surface) -> pygame.Surface:
        largura_original = max(1, surf.get_width())
        altura_original = max(1, surf.get_height())

        fator_tile = self._tile_px / float(self._tile_px_referencia)
        fator_escala = max(0.01, fator_tile * self._escala_tiles)

        nova_largura = max(1, int(round(largura_original * fator_escala)))
        nova_altura = max(1, int(round(altura_original * fator_escala)))

        return pygame.transform.smoothscale(surf, (nova_largura, nova_altura)).convert_alpha()

    def set_skin(self, skin_surface: pygame.Surface) -> None:
        self._skin_original = skin_surface.convert_alpha()
        self._skin = self._redimensionar_skin(self._skin_original)

        base = _cor_predominante(self._skin_original)
        self._cor_maos = _clarear_cor(base, fator=0.40)
        self._cache_corpo_rotacionado.clear()
        self._cache_ordem_angulos.clear()

    def set_escala(self, escala: float) -> None:
        self._escala_tiles = max(0.01, float(escala))
        self._skin = self._redimensionar_skin(self._skin_original)
        self._cache_corpo_rotacionado.clear()
        self._cache_ordem_angulos.clear()

    def _obter_corpo_rotacionado(self, angulo: float) -> pygame.Surface:
        chave = int(round(float(angulo) * 0.5) * 2) % 360
        corpo = self._cache_corpo_rotacionado.get(chave)
        if corpo is not None:
            return corpo

        corpo = pygame.transform.rotate(self._skin, chave)
        self._cache_corpo_rotacionado[chave] = corpo
        self._cache_ordem_angulos.append(chave)
        if len(self._cache_ordem_angulos) > self._cache_limite_angulos:
            antigo = self._cache_ordem_angulos.pop(0)
            self._cache_corpo_rotacionado.pop(antigo, None)
        return corpo

    def desenhar(
        self,
        tela: pygame.Surface,
        centro: tuple[int, int],
        mouse_pos: tuple[int, int] | None = None,
        angulo_graus: float | None = None,
        respiracao_tempo: float = 0.0,
        recuo_mao: float = 0.0,
    ) -> dict[str, tuple[int, int] | int]:
        cx, cy = centro

        if angulo_graus is None:
            mx, my = mouse_pos if mouse_pos is not None else (cx + 1, cy)
            dx = mx - cx
            dy = my - cy
            if dx == 0 and dy == 0:
                dx = 1
            angulo_base = math.degrees(math.atan2(-dy, dx))
        else:
            angulo_base = float(angulo_graus)

        rad = math.radians(angulo_base)
        vx = math.cos(rad)
        vy = -math.sin(rad)

        angulo = angulo_base + self.sprite_offset_graus + 180
        corpo = self._obter_corpo_rotacionado(angulo)
        corpo_rect = corpo.get_rect(center=(int(cx), int(cy)))

        px = -vy
        py = vx

        # As maos seguem um padrao fixo. A escala afeta apenas o corpo/skin.
        base = float(self._tile_px)
        raio_mao = max(5, int(base * 0.20))
        dist_lateral = int(base * 1.15)
        dist_vertical = int(base * 0.03)

        respiracao = math.sin(max(0.0, float(respiracao_tempo)) * 3.4) * 3.0
        recuo = max(0.0, float(recuo_mao))

        mao_dir_x = cx + px * dist_lateral + vx * (respiracao - recuo)
        mao_dir_y = cy + py * dist_lateral - dist_vertical + vy * (respiracao - recuo)
        mao_esq_x = cx - px * dist_lateral + vx * respiracao
        mao_esq_y = cy - py * dist_lateral - dist_vertical + vy * respiracao

        mao_dir = (int(mao_dir_x), int(mao_dir_y))
        mao_esq = (int(mao_esq_x), int(mao_esq_y))

        tela.blit(corpo, corpo_rect)

        contorno = (12, 20, 38)
        pygame.draw.circle(tela, contorno, mao_esq, raio_mao + 2)
        pygame.draw.circle(tela, contorno, mao_dir, raio_mao + 2)
        pygame.draw.circle(tela, self._cor_maos, mao_esq, raio_mao)
        pygame.draw.circle(tela, self._cor_maos, mao_dir, raio_mao)

        return {
            "mao_tapa": mao_dir,
            "mao_apoio": mao_esq,
            "raio_mao": raio_mao,
        }


@dataclass
class Slider:
    rect: pygame.Rect
    titulo: str
    minimo: float
    maximo: float
    valor: float
    decimal_places: int = 2
    inteiro: bool = False
    centro_visual: float | None = None

    def __post_init__(self) -> None:
        self.arrastando = False

    def normalizado_para_valor(self, t: float) -> float:
        t = _clamp(t, 0.0, 1.0)
        if self.centro_visual is None:
            return self.minimo + (self.maximo - self.minimo) * t

        meio = 0.5
        centro = float(self.centro_visual)
        if t <= meio:
            frac = t / meio if meio > 0 else 0.0
            return self.minimo + (centro - self.minimo) * frac
        frac = (t - meio) / (1.0 - meio) if meio < 1.0 else 1.0
        return centro + (self.maximo - centro) * frac

    def valor_para_normalizado(self, valor: float) -> float:
        valor = _clamp(valor, self.minimo, self.maximo)
        if self.centro_visual is None:
            total = self.maximo - self.minimo
            return 0.0 if total == 0 else (valor - self.minimo) / total

        meio = 0.5
        centro = float(self.centro_visual)
        if valor <= centro:
            trecho = centro - self.minimo
            return 0.0 if trecho == 0 else meio * ((valor - self.minimo) / trecho)
        trecho = self.maximo - centro
        return meio if trecho == 0 else meio + meio * ((valor - centro) / trecho)

    def knob_x(self) -> int:
        t = self.valor_para_normalizado(self.valor)
        return int(round(self.rect.left + t * self.rect.width))

    def set_from_mouse_x(self, mouse_x: int) -> None:
        t = (mouse_x - self.rect.left) / max(1, self.rect.width)
        valor = self.normalizado_para_valor(t)
        if self.inteiro:
            valor = int(round(valor))
        self.valor = _clamp(valor, self.minimo, self.maximo)

    def handle_event(self, event: pygame.event.Event) -> bool:
        mudou = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            area_expandida = self.rect.inflate(0, 18)
            if area_expandida.collidepoint(event.pos):
                self.arrastando = True
                self.set_from_mouse_x(event.pos[0])
                mudou = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.arrastando = False
        elif event.type == pygame.MOUSEMOTION and self.arrastando:
            self.set_from_mouse_x(event.pos[0])
            mudou = True
        return mudou

    def draw(self, tela: pygame.Surface, mouse_pos: tuple[int, int]) -> None:
        titulo = self.titulo
        valor_str = f"{int(round(self.valor))}" if self.inteiro else f"{self.valor:.{self.decimal_places}f}x"
        texto = FONT.render(f"{titulo}: {valor_str}", True, TEXT_COLOR)
        tela.blit(texto, (self.rect.x, self.rect.y - 32))

        pygame.draw.line(tela, PANEL_BORDER, self.rect.midleft, self.rect.midright, 6)
        if self.centro_visual is not None:
            x_centro = int(round(self.rect.left + 0.5 * self.rect.width))
            pygame.draw.line(tela, ACCENT_2, (x_centro, self.rect.y - 6), (x_centro, self.rect.bottom + 6), 2)

        knob_x = self.knob_x()
        hovered = self.rect.inflate(0, 18).collidepoint(mouse_pos)
        pygame.draw.circle(tela, ACCENT if hovered or self.arrastando else TEXT_COLOR, (knob_x, self.rect.centery), 12)
        pygame.draw.circle(tela, BG_COLOR, (knob_x, self.rect.centery), 5)


@dataclass
class Button:
    rect: pygame.Rect
    texto: str

    def foi_clicado(self, event: pygame.event.Event) -> bool:
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

    def draw(self, tela: pygame.Surface, mouse_pos: tuple[int, int]) -> None:
        hovered = self.rect.collidepoint(mouse_pos)
        cor = BUTTON_HOVER if hovered else BUTTON_COLOR
        pygame.draw.rect(tela, cor, self.rect, border_radius=10)
        pygame.draw.rect(tela, PANEL_BORDER, self.rect, 2, border_radius=10)
        texto = FONT.render(self.texto, True, (255, 255, 255))
        texto_rect = texto.get_rect(center=self.rect.center)
        tela.blit(texto, texto_rect)


class EditorSkinsApp:
    def __init__(self) -> None:
        self.tela = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("EditorSkins")
        self.clock = pygame.time.Clock()
        self.rodando = True

        self.mensagem = ""
        self.cor_mensagem = MUTED_TEXT
        self.tempo_mensagem = 0.0

        self.slider_skin = Slider(
            rect=pygame.Rect(120, 650, 460, 18),
            titulo="Skin",
            minimo=SKIN_MIN,
            maximo=SKIN_MAX,
            valor=SKIN_MIN,
            decimal_places=0,
            inteiro=True,
        )
        self.slider_escala = Slider(
            rect=pygame.Rect(700, 650, 460, 18),
            titulo="Escala proporcional",
            minimo=0.10,
            maximo=5.00,
            valor=1.00,
            decimal_places=2,
            inteiro=False,
            centro_visual=1.00,
        )
        self.botao_salvar = Button(pygame.Rect(540, 720, 200, 52), "Salvar redimensionada")
        self.botao_reset = Button(pygame.Rect(770, 720, 140, 52), "Resetar")

        self.cache_skins: dict[int, pygame.Surface] = {}
        self.skin_atual_idx = int(self.slider_skin.valor)
        self.skin_surface = self.carregar_skin(self.skin_atual_idx)
        self.ator = DesenhaAtor(self.skin_surface, escala=float(self.slider_escala.valor), tile_px=50)

    def definir_mensagem(self, texto: str, cor: tuple[int, int, int] = MUTED_TEXT) -> None:
        self.mensagem = texto
        self.cor_mensagem = cor
        self.tempo_mensagem = pygame.time.get_ticks() / 1000.0

    def caminho_skin(self, idx: int) -> str:
        return os.path.join(SKINS_DIR, f"{idx}.png")

    def carregar_skin(self, idx: int) -> pygame.Surface:
        idx = int(idx)
        if idx in self.cache_skins:
            return self.cache_skins[idx].copy()

        caminho = self.caminho_skin(idx)
        if not os.path.isfile(caminho):
            raise FileNotFoundError(f"Skin nao encontrada: {caminho}")

        surface = pygame.image.load(caminho).convert_alpha()
        self.cache_skins[idx] = surface
        return surface.copy()

    def atualizar_skin_se_necessario(self) -> None:
        idx = int(round(self.slider_skin.valor))
        if idx == self.skin_atual_idx:
            return
        self.skin_atual_idx = idx
        self.skin_surface = self.carregar_skin(idx)
        self.ator.set_skin(self.skin_surface)
        self.definir_mensagem(f"Skin {idx}.png carregada.")

    def salvar_skin_redimensionada(self) -> None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        nome_arquivo = f"{self.skin_atual_idx}.png"
        destino = os.path.join(OUTPUT_DIR, nome_arquivo)
        redimensionada = redimensionar_surface_proporcional(self.skin_surface, float(self.slider_escala.valor))
        pygame.image.save(redimensionada, destino)
        self.definir_mensagem(f"Salvo em: {destino}", SUCCESS_COLOR)

    def resetar_escala(self) -> None:
        self.slider_escala.valor = 1.0
        self.ator.set_escala(1.0)
        self.definir_mensagem("Escala resetada para 1.00x.", SUCCESS_COLOR)

    def processar_eventos(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.rodando = False
                return

            mudou_skin = self.slider_skin.handle_event(event)
            mudou_escala = self.slider_escala.handle_event(event)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.rodando = False
                    return
                if event.key == pygame.K_LEFT:
                    self.slider_skin.valor = max(SKIN_MIN, int(round(self.slider_skin.valor)) - 1)
                    mudou_skin = True
                elif event.key == pygame.K_RIGHT:
                    self.slider_skin.valor = min(SKIN_MAX, int(round(self.slider_skin.valor)) + 1)
                    mudou_skin = True
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self.slider_escala.valor = max(self.slider_escala.minimo, float(self.slider_escala.valor) - 0.05)
                    mudou_escala = True
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    self.slider_escala.valor = min(self.slider_escala.maximo, float(self.slider_escala.valor) + 0.05)
                    mudou_escala = True
                elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    self.salvar_skin_redimensionada()
                elif event.key == pygame.K_r:
                    self.resetar_escala()

            if mudou_skin:
                self.atualizar_skin_se_necessario()
            if mudou_escala:
                self.ator.set_escala(float(self.slider_escala.valor))

            if self.botao_salvar.foi_clicado(event):
                self.salvar_skin_redimensionada()
            if self.botao_reset.foi_clicado(event):
                self.resetar_escala()

    def desenhar_fundo_preview(self) -> None:
        preview_rect = pygame.Rect(90, 80, SCREEN_W - 180, 500)
        pygame.draw.rect(self.tela, PANEL_COLOR, preview_rect, border_radius=18)
        pygame.draw.rect(self.tela, PANEL_BORDER, preview_rect, 2, border_radius=18)

        centro_x, centro_y = PREVIEW_CENTER
        pygame.draw.line(self.tela, (48, 58, 74), (preview_rect.left + 30, centro_y), (preview_rect.right - 30, centro_y), 1)
        pygame.draw.line(self.tela, (48, 58, 74), (centro_x, preview_rect.top + 30), (centro_x, preview_rect.bottom - 30), 1)

        base_rect = pygame.Rect(0, 0, 260, 260)
        base_rect.center = PREVIEW_CENTER
        pygame.draw.rect(self.tela, (22, 28, 36), base_rect, border_radius=14)
        pygame.draw.rect(self.tela, (44, 54, 70), base_rect, 1, border_radius=14)

    def desenhar_ui(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        titulo = FONT_BIG.render("EditorSkins", True, TEXT_COLOR)
        self.tela.blit(titulo, (90, 26))

        subtitulo = FONT_SMALL.render(
            "Mouse gira a skin | seta esquerda/direita troca skin | - / + ajusta escala | Ctrl+S salva",
            True,
            MUTED_TEXT,
        )
        self.tela.blit(subtitulo, (320, 34))

        self.desenhar_fundo_preview()

        self.slider_skin.draw(self.tela, mouse_pos)
        self.slider_escala.draw(self.tela, mouse_pos)
        self.botao_salvar.draw(self.tela, mouse_pos)
        self.botao_reset.draw(self.tela, mouse_pos)

        caminho = self.caminho_skin(self.skin_atual_idx)
        escala = float(self.slider_escala.valor)
        largura_nova = max(1, int(round(self.skin_surface.get_width() * escala)))
        altura_nova = max(1, int(round(self.skin_surface.get_height() * escala)))

        info1 = FONT.render(f"Arquivo atual: {os.path.basename(caminho)}", True, TEXT_COLOR)
        info2 = FONT.render(
            f"Original: {self.skin_surface.get_width()}x{self.skin_surface.get_height()} px", True, MUTED_TEXT
        )
        info3 = FONT.render(f"Resultado: {largura_nova}x{altura_nova} px", True, MUTED_TEXT)
        info4 = FONT.render(f"Pasta de saida: {OUTPUT_DIR}", True, MUTED_TEXT)
        info5 = FONT_SMALL.render(
            "A escala altera apenas a PNG da skin. Os braços continuam no tamanho padrao do preview.",
            True,
            ACCENT_2,
        )

        self.tela.blit(info1, (110, 700))
        self.tela.blit(info2, (110, 730))
        self.tela.blit(info3, (110, 758))
        self.tela.blit(info4, (110, 786))
        self.tela.blit(info5, (440, 590))

        if self.mensagem:
            texto_msg = FONT_SMALL.render(self.mensagem, True, self.cor_mensagem)
            self.tela.blit(texto_msg, (430, 780))

    def desenhar(self) -> None:
        self.tela.fill(BG_COLOR)
        self.desenhar_ui()
        self.ator.desenhar(
            self.tela,
            PREVIEW_CENTER,
            mouse_pos=pygame.mouse.get_pos(),
            respiracao_tempo=pygame.time.get_ticks() / 1000.0,
        )
        pygame.display.flip()

    def run(self) -> None:
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            if not os.path.isdir(SKINS_DIR):
                raise FileNotFoundError(f"Pasta de skins nao encontrada: {SKINS_DIR}")
        except Exception as exc:
            self.definir_mensagem(str(exc), ERROR_COLOR)

        while self.rodando:
            self.clock.tick(FPS)
            try:
                self.processar_eventos()
                self.desenhar()
            except Exception as exc:
                self.definir_mensagem(str(exc), ERROR_COLOR)
                self.desenhar()

        pygame.quit()


if __name__ == "__main__":
    EditorSkinsApp().run()