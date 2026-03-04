import os
import threading

import pygame

from Codigo.Modulos.DesenhaAtor import DesenhaAtor
from Codigo.Prefabs.Barra import Barra
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto
from Codigo.Server.ServerMenu import criar_personagem

_SKINS_LIBERADAS = [f"S{i}.png" for i in range(1, 13)]

_INICIAIS_FOGO = ["Charmander", "Torchic", "Fennekin", "Litten"]
_INICIAIS_PLANTA = ["Bulbasaur", "Treecko", "Chespin", "Rowlet"]
_INICIAIS_AGUA = ["Squirtle", "Mudkip", "Froakie", "Popplio"]

_GRUPOS_INICIAIS = [
    ("Fogo", _INICIAIS_FOGO),
    ("Planta", _INICIAIS_PLANTA),
    ("Água", _INICIAIS_AGUA),
]

_LISTA_INICIAIS = _INICIAIS_FOGO + _INICIAIS_PLANTA + _INICIAIS_AGUA

_COR_GRUPO = {
    "Fogo": {"bg": (74, 35, 35), "hover": (94, 43, 43), "select": (130, 58, 50), "border": (220, 125, 110)},
    "Água": {"bg": (33, 52, 82), "hover": (40, 65, 102), "select": (55, 90, 135), "border": (125, 188, 245)},
    "Planta": {"bg": (37, 69, 45), "hover": (44, 82, 55), "select": (60, 120, 80), "border": (140, 220, 155)},
}

_TIPO_POR_POKEMON = {nome: "Fogo" for nome in _INICIAIS_FOGO}
_TIPO_POR_POKEMON.update({nome: "Planta" for nome in _INICIAIS_PLANTA})
_TIPO_POR_POKEMON.update({nome: "Água" for nome in _INICIAIS_AGUA})

_ESTILO_BOTAO = {
    "radius": 16,
    "border_width": 2,
    "border": (26, 34, 62),
    "border_hover": (255, 220, 120),
    "bg": (25, 34, 60),
    "bg_hover": (40, 53, 90),
    "bg_pressed": (18, 25, 45),
    "hover_scale": 1.03,
    "press_scale": 0.97,
    "text_style": {
        "size": 28,
        "color": (245, 246, 255),
        "hover_color": (255, 226, 120),
        "outline": True,
        "outline_color": (0, 0, 0),
        "outline_thickness": 1,
        "shadow": True,
        "shadow_color": (0, 0, 0, 160),
        "shadow_offset": (2, 2),
    },
}


def _scale_to_fit_keep_ratio(img: pygame.Surface, max_w: int, max_h: int) -> pygame.Surface:
    if max_w <= 0 or max_h <= 0:
        return img
    w, h = img.get_size()
    if w <= 0 or h <= 0:
        return img
    scale = min(max_w / w, max_h / h, 1.0)
    if abs(scale - 1.0) < 1e-6:
        return img
    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))
    return pygame.transform.smoothscale(img, (nw, nh)).convert_alpha()


class SubtelaCriarPersonagem:
    def __init__(self, tela_size, ip_server, usuario, concluir_callback=None, voltar_callback=None):
        self.ip_server = ip_server
        self.usuario = usuario
        self.concluir_callback = concluir_callback
        self.voltar_callback = voltar_callback
        self.encerrada = False

        self._overlay = None
        self._overlay_size = (0, 0)
        self._painel = pygame.Rect(0, 0, 0, 0)

        self._skin_index = 0
        self._pokemon_index = 0

        self._skins = self._carregar_skins()
        self._desenhador = DesenhaAtor(self._skins[self._skin_index], escala=1.35)

        self._icones_pokemon = self._carregar_icones_pokemon()
        self._animacoes_pokemon = self._carregar_animacoes_pokemon()

        self._frame_anim = 0
        self._tempo_anim = 0.0
        self._fps_anim = 18.0

        self._thread = None
        self._resultado = None

        self._titulo = None
        self._mensagem = Texto("Escolha sua skin e seu inicial", (0, 0), style={"size": 24, "align": "center"})

        self.barra_skin = None

        self._botoes_grupos = []
        self._botoes_flat = []

        self.botao_voltar = None
        self.botao_criar = None

        self._quadro_skin = pygame.Rect(0, 0, 0, 0)
        self._quadro_anim = pygame.Rect(0, 0, 0, 0)

        self._rebuild_layout(tela_size)

    def _carregar_skins(self):
        skins = []
        for nome in _SKINS_LIBERADAS:
            caminho = os.path.join("Recursos", "Visual", "Skins", "Liberadas", nome)
            try:
                skins.append(pygame.image.load(caminho).convert_alpha())
            except pygame.error:
                fallback = pygame.Surface((32, 32), pygame.SRCALPHA)
                fallback.fill((190, 220, 255))
                skins.append(fallback)
        return skins

    def _carregar_icones_pokemon(self):
        icones = {}
        for nome in _LISTA_INICIAIS:
            caminho = os.path.join("Recursos", "Visual", "Pokemons", "Imagens", f"{nome.lower()}.png")
            try:
                img = pygame.image.load(caminho).convert_alpha()
            except pygame.error:
                img = pygame.Surface((64, 64), pygame.SRCALPHA)
                img.fill((35, 38, 50))
                pygame.draw.circle(img, (230, 230, 230), (32, 32), 24)

            icones[nome] = pygame.transform.smoothscale(img, (62, 62)).convert_alpha()
        return icones

    def _carregar_animacoes_pokemon(self):
        animacoes = {}
        for nome in _LISTA_INICIAIS:
            pasta = os.path.join("Recursos", "Visual", "Pokemons", "Animação", nome.lower())
            frames = []

            if os.path.isdir(pasta):
                arquivos = [arq for arq in os.listdir(pasta) if arq.lower().endswith(".png")]

                def _key(n):
                    base = n.rsplit(".", 1)[0]
                    if "_" in base:
                        tail = base.rsplit("_", 1)[-1]
                        if tail.isdigit():
                            return int(tail)
                    return 0

                arquivos.sort(key=_key)

                for arq in arquivos:
                    caminho = os.path.join(pasta, arq)
                    try:
                        frames.append(pygame.image.load(caminho).convert_alpha())
                    except pygame.error:
                        pass

            if not frames:
                frames = [self._icones_pokemon[nome]]

            animacoes[nome] = frames
        return animacoes

    def _rebuild_layout(self, tela_size):
        largura, altura = tela_size

        self._overlay_size = tela_size
        self._overlay = pygame.Surface(tela_size, pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 170))

        painel_w = min(940, int(largura * 0.84))
        painel_h = min(620, int(altura * 0.76))
        self._painel = pygame.Rect(0, 0, painel_w, painel_h)
        self._painel.center = (largura // 2, altura // 2)

        pad = 30
        y0 = self._painel.top + pad

        self._titulo = Texto("Criar Personagem", (self._painel.centerx, y0), style={"size": 40, "align": "center"})
        self._mensagem.set_pos((self._painel.centerx, y0 + 42))

        btn = 74
        gap_in = 12
        gap_blocos = 22
        bloco_w = (btn * 2) + gap_in
        bloco_h = (btn * 2) + gap_in
        grid_w = (bloco_w * 3) + (gap_blocos * 2)

        col_gap = 42
        quadro_w = 188
        quadro_h = 156

        # Centraliza o bloco inteiro (grid + gap + coluna da direita) dentro do painel
        inner_w = self._painel.width - (pad * 2)
        total_content_w = grid_w + col_gap + quadro_w
        offset_x = max(0, int((inner_w - total_content_w) / 2))

        x0 = self._painel.left + pad + offset_x
        col_dir_x = x0 + grid_w + col_gap

        max_right = self._painel.right - pad
        if col_dir_x + quadro_w > max_right:
            col_dir_x = max_right - quadro_w
            grid_w = max(320, col_dir_x - col_gap - x0)

        secao_skin_top = y0 + 86
        self._quadro_skin = pygame.Rect(col_dir_x, secao_skin_top, quadro_w, quadro_h)

        barra_h = 32
        barra_y = self._quadro_skin.centery - (barra_h // 2)
        self.barra_skin = Barra(
            pygame.Rect(x0, barra_y, grid_w, barra_h),
            "Skin",
            self._skin_index + 1,
            1,
            len(self._skins),
            casas_decimais=0,
        )

        blocos_y = self._quadro_skin.bottom + 52
        self._botoes_grupos = []
        self._botoes_flat = []

        for gi, (nome_grupo, lista_pokes) in enumerate(_GRUPOS_INICIAIS):
            bloco_x = x0 + gi * (bloco_w + gap_blocos)
            container = pygame.Rect(bloco_x, blocos_y, bloco_w, bloco_h)

            rects = []
            for i in range(4):
                col = i % 2
                row = i // 2
                rx = bloco_x + col * (btn + gap_in)
                ry = blocos_y + row * (btn + gap_in)
                rects.append(pygame.Rect(rx, ry, btn, btn))

            for poke_nome, rect in zip(lista_pokes, rects):
                self._botoes_flat.append((poke_nome, nome_grupo, rect))

            titulo_pos = (container.centerx, container.top - 24)
            self._botoes_grupos.append(
                {
                    "nome_grupo": nome_grupo,
                    "pokemon": lista_pokes,
                    "rects": rects,
                    "container": container,
                    "titulo_pos": titulo_pos,
                }
            )

        anim_top = blocos_y + 4  # 2px para baixo
        self._quadro_anim = pygame.Rect(col_dir_x, anim_top, quadro_w, quadro_h)

        y_rodape = self._painel.bottom - 74
        self.botao_voltar = Botao(
            pygame.Rect(self._painel.left + pad, y_rodape, 210, 56),
            "Voltar",
            execute=self._voltar,
            style=_ESTILO_BOTAO,
        )
        self.botao_criar = Botao(
            pygame.Rect(self._painel.right - pad - 210, y_rodape, 210, 56),
            "Criar",
            execute=self._criar,
            style=_ESTILO_BOTAO,
        )

        bottom_safe = y_rodape - 18
        if self._quadro_anim.bottom > bottom_safe:
            dy = self._quadro_anim.bottom - bottom_safe
            self._quadro_anim.move_ip(0, -dy)
            for grp in self._botoes_grupos:
                grp["container"].move_ip(0, -dy)
                grp["titulo_pos"] = (grp["titulo_pos"][0], grp["titulo_pos"][1] - dy)
                grp["rects"] = [r.move(0, -dy) for r in grp["rects"]]
            self._botoes_flat = [(n, g, r.move(0, -dy)) for n, g, r in self._botoes_flat]

    def _voltar(self, jogo, botao):
        if callable(self.voltar_callback):
            self.voltar_callback()
        self.encerrada = True

    def _worker_criar(self, skin_nome, pokemon_nome):
        self._resultado = criar_personagem(self.ip_server, self.usuario, skin_nome, pokemon_nome)

    def _criar(self, jogo, botao):
        if self._thread and self._thread.is_alive():
            return

        skin_nome = _SKINS_LIBERADAS[self._skin_index].replace(".png", "")
        pokemon = _LISTA_INICIAIS[self._pokemon_index]

        self._mensagem.set_text("Registrando personagem no servidor...")
        self._thread = threading.Thread(target=self._worker_criar, args=(skin_nome, pokemon), daemon=True)
        self._resultado = None
        self._thread.start()

    def _processar_resultado(self):
        if not self._resultado:
            return

        resposta = self._resultado
        self._resultado = None
        self._thread = None

        if resposta.get("status") == "ok":
            self._mensagem.set_text(resposta.get("mensagem", "Personagem criado!"))
            if callable(self.concluir_callback):
                self.concluir_callback()
            self.encerrada = True
            return

        self._mensagem.set_text(resposta.get("mensagem", "Falha ao criar personagem"))

    def _render_grupos_pokemon(self, tela, eventos):
        mouse = pygame.mouse.get_pos()

        for grp in self._botoes_grupos:
            cx, cy = grp["titulo_pos"]
            placa = pygame.Rect(0, 0, grp["container"].width, 22)
            placa.center = (cx, cy + 2)
            pygame.draw.rect(tela, (18, 26, 48), placa, border_radius=10)
            pygame.draw.rect(tela, (95, 110, 150), placa, 2, border_radius=10)

            t = Texto(grp["nome_grupo"], grp["titulo_pos"], style={"size": 22, "align": "center"})
            t.draw(tela)

        selecionado_nome = _LISTA_INICIAIS[self._pokemon_index]

        for poke_nome, grupo_nome, rect in self._botoes_flat:
            hover = rect.collidepoint(mouse)
            selecionado = poke_nome == selecionado_nome
            cor_set = _COR_GRUPO.get(grupo_nome, _COR_GRUPO["Água"])

            cor_bg = cor_set["bg"]
            cor_borda = cor_set["border"]

            if hover:
                cor_bg = cor_set["hover"]
            if selecionado:
                cor_bg = cor_set["select"]
                cor_borda = (255, 235, 165)

            pygame.draw.rect(tela, cor_bg, rect, border_radius=12)
            pygame.draw.rect(tela, cor_borda, rect, 2, border_radius=12)

            icone = self._icones_pokemon[poke_nome]
            icon_rect = icone.get_rect(center=rect.center)
            tela.blit(icone, icon_rect)

        for ev in eventos:
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                for poke_nome, _, rect in self._botoes_flat:
                    if rect.collidepoint(ev.pos):
                        self._pokemon_index = _LISTA_INICIAIS.index(poke_nome)
                        self._frame_anim = 0
                        self._tempo_anim = 0.0
                        break

    def render(self, tela, eventos, dt, JOGO=None):
        size = tela.get_size()
        if size != self._overlay_size:
            self._rebuild_layout(size)

        self._processar_resultado()

        tela.blit(self._overlay, (0, 0))

        pygame.draw.rect(tela, (15, 22, 42), self._painel, border_radius=20)
        pygame.draw.rect(tela, (255, 220, 120), self._painel, 2, border_radius=20)

        self._titulo.draw(tela)
        self._mensagem.draw(tela)

        if self.barra_skin.render(tela, eventos):
            novo_indice = int(round(self.barra_skin.valor)) - 1
            novo_indice = max(0, min(novo_indice, len(self._skins) - 1))
            if novo_indice != self._skin_index:
                self._skin_index = novo_indice
                self._desenhador.set_skin(self._skins[self._skin_index])
        else:
            self.barra_skin.set_valor(self._skin_index + 1)

        pygame.draw.rect(tela, (20, 29, 52), self._quadro_skin, border_radius=14)
        pygame.draw.rect(tela, (95, 110, 150), self._quadro_skin, 2, border_radius=14)
        self._desenhador.desenhar(tela, self._quadro_skin.center, pygame.mouse.get_pos())

        self._render_grupos_pokemon(tela, eventos)

        nome_poke = _LISTA_INICIAIS[self._pokemon_index]
        texto_poke = Texto(
            nome_poke,
            (self._quadro_anim.centerx, self._quadro_anim.top - 28),
            style={"size": 24, "align": "center"},
        )
        texto_poke.draw(tela)

        pygame.draw.rect(tela, (20, 29, 52), self._quadro_anim, border_radius=14)
        pygame.draw.rect(tela, (95, 110, 150), self._quadro_anim, 2, border_radius=14)

        frames = self._animacoes_pokemon[nome_poke]
        self._tempo_anim += dt
        if self._tempo_anim >= 1.0 / self._fps_anim:
            self._tempo_anim = 0.0
            self._frame_anim = (self._frame_anim + 1) % len(frames)

        frame = frames[self._frame_anim]

        margem = 16
        max_w = self._quadro_anim.width - (margem * 2)
        max_h = self._quadro_anim.height - (margem * 2)
        frame_fit = _scale_to_fit_keep_ratio(frame, max_w, max_h)

        rect_frame = frame_fit.get_rect(center=self._quadro_anim.center)
        tela.blit(frame_fit, rect_frame)

        bloqueado = self._thread is not None and self._thread.is_alive()
        self.botao_criar.set_habilitado(not bloqueado)
        self.botao_voltar.set_habilitado(not bloqueado)

        self.botao_voltar.render(tela, eventos, dt, JOGO=JOGO)
        self.botao_criar.render(tela, eventos, dt, JOGO=JOGO)