from Codigo.Modulos.EfeitosTela import FecharIris, AbrirIris
from Codigo.Modulos.Camera import CameraBatalha
from Codigo.Modulos.ControladorBatalha import ControladorBatalha
from Codigo.Modulos.ElementosHudCombate import ElementosHudCombate
from Codigo.Telas.SubtelaOpcoes import SubtelaOpcoes
import pygame


class CenaCombate:
    def Inicializar(self, JOGO):
        self.Abertura = AbrirIris
        self.Fechamento = FecharIris
        self.ID = "Combate"
        self.SubtelaOpcoes = SubtelaOpcoes()

        contexto = JOGO.INFO.get("CombateContexto") if isinstance(JOGO.INFO.get("CombateContexto"), dict) else {}
        tile_px = 40
        largura = float(contexto.get("largura", 100) or 100)
        altura = float(contexto.get("altura", 60) or 60)
        centro = contexto.get("centro") if isinstance(contexto.get("centro"), (list, tuple)) and len(contexto.get("centro")) == 2 else [largura * 0.5, altura * 0.5]
        half_w = (float(JOGO.TELA.get_size()[0]) / float(tile_px)) * 0.5
        half_h = (float(JOGO.TELA.get_size()[1]) / float(tile_px)) * 0.5
        pos_inicial = (float(centro[0]) - half_w, float(centro[1]) - half_h)

        self.Camera = CameraBatalha(JOGO.TELA.get_size(), posicao_inicial_tiles=pos_inicial, tile_px=tile_px)
        self.Camera.definir_limites_mundo(largura, altura)
        self.Camera.atualizar(0.0)
        self.ControladorBatalha = ControladorBatalha(contexto)
        self.ElementosHudCombate = ElementosHudCombate(ao_fugir=lambda: self._fugir_combate(JOGO))

    def _fugir_combate(self, jogo) -> None:
        jogo.INFO["ImuneCombateAteMs"] = int(pygame.time.get_ticks()) + 3000
        jogo.CenaAlvo = "Mundo"

    def Tela(self, JOGO, EVENTOS, dt):
        self.Camera.TamanhoTelaPx = JOGO.TELA.get_size()
        self.SubtelaOpcoes.processar_eventos(JOGO, EVENTOS)
        bloqueado = self.SubtelaOpcoes.Ativa
        if not bloqueado:
            self.Camera.processar_eventos(EVENTOS)
        self.Camera.atualizar(dt)

        JOGO.TELA.fill((20, 20, 28))
        self.ControladorBatalha.atualizar(EVENTOS, dt)
        self.ControladorBatalha.renderizar(JOGO.TELA, self.Camera)
        self.ElementosHudCombate.desenhar(JOGO.TELA, EVENTOS, dt)
        self.SubtelaOpcoes.desenhar(JOGO)

    def Finalizar(self, JOGO):
        pass
