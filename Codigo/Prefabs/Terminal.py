from __future__ import annotations

import threading
import time

import pygame

from Codigo.Prefabs.CaixaTexto import CaixaTexto
from Codigo.Prefabs.Texto import Texto


class Terminal:
    def __init__(self, rect, callback_enviar=None, callback_buscar=None, autor_local="anon"):
        self.rect = pygame.Rect(rect)
        self.caixa = CaixaTexto(
            pygame.Rect(self.rect.x + 8, self.rect.bottom - 34, self.rect.w - 16, 26),
            placeholder="ENTER para digitar...",
            max_chars=120,
            ativo=False,
        )
        self.caixa._estilo_texto["size"] = 18
        self.callback_enviar = callback_enviar
        self.callback_buscar = callback_buscar
        self.autor_local = str(autor_local or "anon")
        self.digitando = False
        self._mensagens = []
        self._ultimo_id = 0
        self._ultimo_novo_ts = 0.0
        self._ligado = False
        self._thread = None
        self._scroll_linhas = 0
        self._linhas_visiveis = 25
        self._fonte_linhas = pygame.font.Font(None, 17)
        self._cache_linhas_historico = []
        self._cache_largura_historico = -1
        self._historico_sujo = True

    @property
    def esta_digitando(self):
        return self.digitando

    def iniciar(self):
        if self._ligado:
            return
        self._ligado = True
        self._thread = threading.Thread(target=self._loop_poll, daemon=True)
        self._thread.start()

    def parar(self):
        self._ligado = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.6)

    def _loop_poll(self):
        while self._ligado:
            if self.callback_buscar:
                try:
                    resposta = self.callback_buscar(self._ultimo_id)
                except Exception:
                    resposta = None
                self._aplicar_busca(resposta)
            time.sleep(0.5)

    def _aplicar_busca(self, resposta):
        if not isinstance(resposta, dict) or resposta.get("status") != "ok":
            return
        mensagens = resposta.get("mensagens", [])
        novo = False
        for m in mensagens:
            if not isinstance(m, dict):
                continue
            msg_id = int(m.get("id", 0))
            if msg_id <= self._ultimo_id:
                continue
            self._ultimo_id = msg_id
            self._mensagens.append(m)
            novo = True
        if novo:
            self._mensagens = self._mensagens[-180:]
            self._ultimo_novo_ts = time.time()
            self._scroll_linhas = 0
            self._historico_sujo = True

    def processar_eventos(self, eventos):
        eventos_restantes = []
        for evento in eventos:
            if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if not self.digitando:
                    self.digitando = True
                    self.caixa.set_ativo(True)
                    self.caixa.selecionada = True
                    continue
                self._enviar_local()
                continue

            if self.digitando and evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                self._fechar_digitacao()
                continue

            if self.digitando and evento.type == pygame.MOUSEWHEEL:
                self._scroll_linhas = max(0, self._scroll_linhas - int(evento.y))
                continue

            if self.digitando and evento.type in (pygame.KEYDOWN, pygame.KEYUP, pygame.TEXTINPUT):
                eventos_restantes.append(evento)
                continue

            eventos_restantes.append(evento)
        return eventos_restantes

    def _fechar_digitacao(self):
        self.digitando = False
        self.caixa.set_ativo(False)

    def _enviar_local(self):
        texto = self.caixa.texto.strip()
        if not texto:
            self._fechar_digitacao()
            return
        self.caixa.set_texto("")
        self._fechar_digitacao()
        if not self.callback_enviar:
            return
        try:
            resposta = self.callback_enviar(texto)
        except Exception:
            resposta = None
        if not isinstance(resposta, dict) or resposta.get("status") != "ok":
            return
        msg = resposta.get("mensagem_terminal")
        if not isinstance(msg, dict):
            return
        msg_id = int(msg.get("id", 0))
        if msg_id > self._ultimo_id:
            self._ultimo_id = msg_id
            self._mensagens.append(msg)
            self._mensagens = self._mensagens[-180:]
            self._ultimo_novo_ts = time.time()
            self._scroll_linhas = 0
            self._historico_sujo = True

    def _quebrar_linhas(self, texto, largura_px):
        texto = str(texto or "")
        if not texto:
            return [""]
        palavras = texto.split(" ")
        linhas = []
        atual = ""
        for p in palavras:
            teste = p if not atual else f"{atual} {p}"
            if self._fonte_linhas.size(teste)[0] <= largura_px:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = p
        if atual:
            linhas.append(atual)
        return linhas or [texto]

    def _linhas_historico(self):
        largura = max(80, self.rect.w - 22)
        if (not self._historico_sujo) and self._cache_largura_historico == largura:
            return list(self._cache_linhas_historico)

        linhas = []
        for m in self._mensagens:
            prefixo = f"{m.get('autor', 'anon')}: "
            texto = str(m.get("texto", ""))
            quebradas = self._quebrar_linhas(prefixo + texto, largura)
            linhas.extend(quebradas)

        self._cache_linhas_historico = linhas
        self._cache_largura_historico = largura
        self._historico_sujo = False
        return list(linhas)

    def desenhar(self, tela, eventos, dt):
        agora = time.time()
        if not self.digitando and agora > self._ultimo_novo_ts + 3.5:
            return

        alpha = 230
        if not self.digitando and agora > self._ultimo_novo_ts + 3.0:
            alpha = int(230 * max(0.0, 1.0 - (agora - (self._ultimo_novo_ts + 3.0)) / 0.5))

        fundo = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        fundo.fill((0, 0, 0, alpha))
        tela.blit(fundo, self.rect.topleft)

        linhas = self._linhas_historico()
        total = len(linhas)
        inicio = max(0, total - self._linhas_visiveis - self._scroll_linhas)
        fim = max(0, total - self._scroll_linhas)
        visiveis = linhas[inicio:fim]

        y = self.rect.y + 6
        for linha in visiveis:
            Texto(linha, (self.rect.x + 10, y), style={"size": 15, "outline": False, "shadow": False, "color": (235, 235, 235)}).draw(tela)
            y += 14

        if self.digitando:
            self.caixa.render(tela, eventos, dt)
