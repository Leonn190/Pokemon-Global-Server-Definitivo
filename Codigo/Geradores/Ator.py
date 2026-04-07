"""Ator concreto do mundo, sem herança genérica."""

from __future__ import annotations

import math
import os
from typing import Optional, Tuple

import pygame

from Codigo.Modulos.DesenhaAtor import DesenhaAtor
from Codigo.Modulos.Colisor import Colisor
from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Texto import Texto
from Codigo.Prefabs.Barra import Barra

Vector2 = Tuple[float, float]


class Ator:
    _cache_nome_texto = {}

    @staticmethod
    def normalizar_nome_skin(nome_skin: str) -> str:
        base = str(nome_skin or "1").strip() or "1"
        if base.lower().endswith(".png"):
            base = base[:-4]
        if base.lower().startswith("s") and base[1:].isdigit():
            base = base[1:]
        return f"{base}.png"

    @staticmethod
    def carregar_skin(nome_skin: str):
        nome_base = Ator.normalizar_nome_skin(nome_skin)
        caminho = os.path.join("Recursos", "Visual", "Skins", nome_base)
        try:
            return pygame.image.load(caminho).convert_alpha()
        except pygame.error:
            fallback = pygame.Surface((32, 32), pygame.SRCALPHA)
            fallback.fill((190, 220, 255))
            return fallback

    def __init__(
        self,
        skin_surface=None,
        nome_skin: str = "1",
        posicao: Vector2 = (0.0, 0.0),
        velocidade: Vector2 = (0.0, 0.0),
        raio_colisao: float = 0.55,
        raio_interacao: Optional[float] = None,
        escala_skin_tiles: float = 1.0,
        tile_px: int = 50,
        id_objeto: int = 0,
    ) -> None:
        self.Id = int(id_objeto)
        self.Posicao = (float(posicao[0]), float(posicao[1]))
        self.Velocidade = (float(velocidade[0]), float(velocidade[1]))
        self.Colisor = Colisor(
            x=self.Posicao[0],
            y=self.Posicao[1],
            raio_colisao=float(raio_colisao),
            raio_interacao=raio_interacao,
        )
        if skin_surface is None:
            skin_surface = self.carregar_skin(nome_skin)
        self.NomeSkin = self.normalizar_nome_skin(nome_skin)
        self.Skin = skin_surface
        self.Desenhador = DesenhaAtor(self.Skin, escala=escala_skin_tiles, tile_px=tile_px)

        self.AnguloOlhar = 0.0
        self.Nome = ""
        self._duracao_tapa = 0.5
        self._tempo_tapa = 0.0
        self._raio_mao_colisao = max(0.3, raio_colisao * 0.65)
        self._raio_mao_colisao_base = float(self._raio_mao_colisao)
        self.ColisorMao = Colisor(
            x=self.Posicao[0],
            y=self.Posicao[1],
            raio_colisao=self._raio_mao_colisao,
            raio_interacao=self._raio_mao_colisao,
            ativo=False,
        )
        self.Perfil = None
        self.Inventario = None
        self.Controle = None
        self.EstadoMiraAtiva = False
        self._stamina_alpha = 0.0
        self.BarraStamina = Barra(pygame.Rect(0, 0, 75, 9), valor=100, minimo=0, maximo=100, mostrar_rotulo=False, suavizacao=20.0)
        self.BarraStamina.cor_fundo = (16, 22, 30)
        self.BarraStamina.cor_borda = (180, 210, 255)
        self.BarraStamina.cor_preenchimento = (86, 220, 125)

        self._alvo_posicao = self.Posicao
        self._alvo_angulo = self.AnguloOlhar
        self._velocidade_interp_alvo = 10.0
        self._tempo_respiracao = 0.0

    def update(self, payload: dict) -> None:
        dados = payload if isinstance(payload, dict) else {}
        pos = dados.get("posicao")
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            px, py = float(pos[0]), float(pos[1])
            self._alvo_posicao = (px, py)
            dx = px - float(self.Posicao[0])
            dy = py - float(self.Posicao[1])
            if (dx * dx + dy * dy) > (8.0 * 8.0) or bool(dados.get("hard", False)):
                self.definir_posicao(px, py)

        nome = dados.get("nome") or dados.get("usuario")
        if nome:
            self.Nome = str(nome)
        skin = dados.get("skin")
        if skin and str(skin) != str(self.NomeSkin):
            self.set_nome_skin(str(skin))

        estado = dados.get("estado") if isinstance(dados.get("estado"), dict) else {}
        vel_estado = float(estado.get("velocidade", 0.0) or 0.0)
        if vel_estado > 0.0:
            self._velocidade_interp_alvo = max(4.0, min(18.0, vel_estado * 1.35))
        if "angulo" in estado:
            alvo_ang = float(estado.get("angulo", self.AnguloOlhar))
            self._alvo_angulo = alvo_ang
            if bool(dados.get("hard", False)):
                self.definir_angulo_olhar(alvo_ang)
        if bool(estado.get("tapa")):
            self.iniciar_tapa()
        if self.Perfil is not None and isinstance(dados.get("perfil"), dict):
            self.Perfil.aplicar_serializado(dados.get("perfil"))
        if self.Inventario is not None and isinstance(dados.get("inventario"), dict):
            self.Inventario.aplicar_serializado(dados.get("inventario"))
        if self.Inventario is not None and "slot_selecionado" in dados:
            try:
                self.Inventario.SlotSelecionado = int(dados.get("slot_selecionado"))
            except Exception:
                pass
        if bool(estado.get("mirando", False)):
            self.EstadoMiraAtiva = True
        elif "mirando" in estado:
            self.EstadoMiraAtiva = False

    def definir_posicao(self, x: float, y: float) -> None:
        self.Posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.Posicao)

    def mover(self, dx: float, dy: float) -> None:
        nx = self.Posicao[0] + float(dx)
        ny = self.Posicao[1] + float(dy)
        self._alvo_posicao = (float(nx), float(ny))
        self.definir_posicao(nx, ny)

    @classmethod
    def desenhar_nome(cls, tela, pos_tela, nome, deslocamento_y: int = 54):
        nome_str = str(nome or "").strip()
        if not nome_str:
            return
        texto = cls._cache_nome_texto.get(nome_str)
        if texto is None:
            texto = Texto(nome_str, pos=(0, 0), style={"size": 17, "align": "midbottom", "outline": True, "outline_thickness": 1, "shadow": False, "color": (250, 250, 255)})
            cls._cache_nome_texto[nome_str] = texto
        else:
            texto.set_text(nome_str)
        tempo = pygame.time.get_ticks() * 0.004
        fase = (abs(hash(nome_str)) % 360) * 0.0174533
        oscilacao = math.sin(tempo + fase) * 2.0
        texto.set_pos((int(pos_tela[0]), int(pos_tela[1]) - int(deslocamento_y) + int(round(oscilacao))))
        texto.draw(tela)

    @staticmethod
    def _estilo_item(item) -> str:
        if isinstance(item, dict):
            valor = item.get("Estilo", item.get("estilo", ""))
        else:
            valor = getattr(item, "Estilo", getattr(item, "estilo", ""))
        return str(valor or "").strip().lower()

    def set_tile_px(self, tile_px: int) -> None:
        self.Desenhador.set_tile_px(tile_px)

    def set_skin(self, skin_surface) -> None:
        self.Skin = skin_surface
        self.Desenhador.set_skin(skin_surface)

    def set_nome_skin(self, nome_skin: str) -> None:
        self.NomeSkin = self.normalizar_nome_skin(nome_skin)
        self.set_skin(self.carregar_skin(self.NomeSkin))

    def definir_angulo_olhar(self, angulo_graus: float) -> None:
        self.AnguloOlhar = float(angulo_graus)

    def iniciar_tapa(self) -> None:
        perfil = getattr(self, "Perfil", None)
        tapa_por_segundo = float(getattr(perfil, "TapaPorSegundo", 2.0) or 2.0)
        self._duracao_tapa = 1.0 / max(0.1, tapa_por_segundo)
        self._tempo_tapa = self._duracao_tapa

    def Tapar(self) -> None:
        self.iniciar_tapa()

    def GanharXP(self, quantidade_xp) -> dict:
        perfil = getattr(self, "Perfil", None)
        if perfil is None:
            return {"xp_ganho": 0, "niveis_ganhos": 0, "nivel_atual": 0, "xp_atual": 0, "xp_alvo": 0}
        ganho = max(0, int(quantidade_xp or 0))
        if ganho <= 0 or int(getattr(perfil, "Nivel", 0)) >= int(getattr(perfil, "NIVEL_MAXIMO", 50)):
            perfil.normalizar_progresso_xp()
            return {"xp_ganho": 0, "niveis_ganhos": 0, "nivel_atual": int(perfil.Nivel), "xp_atual": int(perfil.XP), "xp_alvo": int(perfil.XPAlvo)}
        nivel_antes = int(perfil.Nivel)
        perfil.XP = int(perfil.XP) + ganho
        perfil.normalizar_progresso_xp()
        return {
            "xp_ganho": ganho,
            "niveis_ganhos": max(0, int(perfil.Nivel) - nivel_antes),
            "nivel_atual": int(perfil.Nivel),
            "xp_atual": int(perfil.XP),
            "xp_alvo": int(perfil.XPAlvo),
        }

    def esta_tapando(self) -> bool:
        return self._tempo_tapa > 0.0

    def atualizar(self, dt: float) -> None:
        dt = max(0.0, float(dt))
        self._tempo_respiracao += dt

        # Player local não deve ser puxado por alvo antigo de interpolação.
        if self.Controle is not None:
            self._alvo_posicao = (float(self.Posicao[0]), float(self.Posicao[1]))
            self._alvo_angulo = float(self.AnguloOlhar)
            self._velocidade_interp_alvo = 10.0

        if self._tempo_tapa > 0.0:
            self._tempo_tapa = max(0.0, self._tempo_tapa - dt)

        px, py = float(self.Posicao[0]), float(self.Posicao[1])
        ax, ay = float(self._alvo_posicao[0]), float(self._alvo_posicao[1])
        dx, dy = (ax - px), (ay - py)
        dist = math.hypot(dx, dy)
        if dist > 1e-4:
            passo = min(dist, max(4.0, float(self._velocidade_interp_alvo)) * dt)
            k = passo / dist
            self.definir_posicao(px + dx * k, py + dy * k)

        diff_ang = (float(self._alvo_angulo) - float(self.AnguloOlhar) + 540.0) % 360.0 - 180.0
        if abs(diff_ang) > 0.05:
            vel_ang = 540.0 * dt
            inc = max(-vel_ang, min(vel_ang, diff_ang))
            self.definir_angulo_olhar(float(self.AnguloOlhar) + inc)

    def _progresso_tapa(self) -> float:
        if self._tempo_tapa <= 0.0:
            return 0.0
        return 1.0 - (self._tempo_tapa / self._duracao_tapa)

    def _alcance_tapa_px(self) -> float:
        if self._tempo_tapa <= 0.0:
            return 0.0
        progresso = self._progresso_tapa()
        fase = 1.0 - abs(1.0 - (progresso * 2.0))
        return max(0.0, fase) * 0.55

    def desenhar(self, tela, mouse_pos=None, posicao_tela=None, respiracao_tempo=0.0) -> None:
        centro = self.Posicao if posicao_tela is None else posicao_tela
        cx, cy = centro
        inventario = getattr(self, "Inventario", None)
        item_mao = inventario.item_na_mao() if inventario is not None else None

        estilo = nome = ""
        if item_mao is not None:
            if isinstance(item_mao, dict):
                estilo = str(item_mao.get("Estilo", item_mao.get("estilo", "")) or "").strip().lower()
                nome = str(item_mao.get("Nome", item_mao.get("nome", "")) or "").strip().lower()
            else:
                estilo = str(getattr(item_mao, "Estilo", getattr(item_mao, "estilo", "")) or "").strip().lower()
                nome = str(getattr(item_mao, "Nome", getattr(item_mao, "nome", "")) or "").strip().lower()

        if item_mao is not None and estilo == "ferramenta":
            angulo_base = float(self.AnguloOlhar)
            rad = math.radians(angulo_base)
            vx, vy = math.cos(rad), -math.sin(rad)
            px, py = -vy, vx

            base = float(self.Desenhador._tile_px)
            escala = max(1.0, float(self.Desenhador._escala_tiles))
            dist_lateral = int(base * 1.15 * escala)
            dist_vertical = int(base * 0.03 * escala)

            progresso = max(0.0, min(1.0, float(self._progresso_tapa())))
            empurrao_tapa = max(0.0, float(self._alcance_tapa_px()))
            respiracao = math.sin(max(0.0, float(respiracao_tempo)) * 3.4) * 3.0

            mao_x = cx + px * dist_lateral
            mao_y = cy + py * dist_lateral - dist_vertical

            if empurrao_tapa > 0.0:
                arco = math.sin(progresso * math.pi)
                mao_x += vx * (60.0 * arco) - px * (16.0 * arco)
                mao_y += vy * (60.0 * arco) - py * (16.0 * arco)
            else:
                recuo = 16.0 if bool(getattr(self, "EstadoMiraAtiva", False)) else 0.0
                mao_x += vx * (respiracao - recuo)
                mao_y += vy * (respiracao - recuo)

            ang_mao = math.degrees(math.atan2(-(mao_y - cy), mao_x - cx))
            eh_picareta = nome.startswith("picareta")

            lado = max(62, int(base * (1.65 if eh_picareta else 1.95) * escala))
            sprite = ItemInventario.surface_item(item_mao, lado_px=lado)

            if sprite is not None:
                if eh_picareta:
                    sprite = pygame.transform.flip(sprite, True, False)
                    ang_item = ang_mao - 24.0
                    grip = (0.50, 0.52)
                else:
                    ang_item = ang_mao - 78.0
                    grip = (0.46, 0.58)

                w, h = sprite.get_size()
                gx, gy = w * grip[0], h * grip[1]

                sprite = pygame.transform.rotozoom(sprite, ang_item, 1.0)
                offset = pygame.math.Vector2(gx - w / 2, gy - h / 2).rotate(ang_item)
                rect = sprite.get_rect(center=(int(mao_x - offset.x), int(mao_y - offset.y)))
                tela.blit(sprite, rect)

        dados_mao = self.Desenhador.desenhar(
            tela,
            centro,
            mouse_pos=mouse_pos,
            angulo_graus=self.AnguloOlhar,
            alcance_tapa=self._alcance_tapa_px(),
            progresso_tapa=self._progresso_tapa(),
            respiracao_tempo=respiracao_tempo,
            recuo_mao=(16.0 if bool(getattr(self, "EstadoMiraAtiva", False)) else 0.0),
        )

        if item_mao is not None and estilo != "ferramenta":
            sprite_item = ItemInventario.surface_item(item_mao, lado_px=max(19, int(dados_mao["raio_mao"] * 2.8)))
            if sprite_item is not None:
                tela.blit(sprite_item, sprite_item.get_rect(center=dados_mao["mao_tapa"]))


    def atualizar_visual(self, dt: float) -> None:
        dt = max(0.0, float(dt))
        self.atualizar_colisor_mao_mundo()
        perfil = getattr(self, "Perfil", None)
        if perfil is None:
            self._stamina_alpha = 0.0
            return
        self.BarraStamina.maximo = max(1.0, float(perfil.StaminaMax))
        self.BarraStamina.set_valor(float(perfil.Stamina))
        self.BarraStamina.atualizar(dt)
        cheio = perfil.Stamina >= (perfil.StaminaMax - 0.001)
        controle = getattr(self, "Controle", None)
        tentando_correr = bool(getattr(controle, "_tentando_correr", False))
        consumindo = bool(getattr(controle, "_consumindo_stamina", False))
        alvo_alpha = 255.0 if (consumindo or not cheio or tentando_correr) else 0.0
        velocidade = 10.0 if alvo_alpha > self._stamina_alpha else 6.0
        self._stamina_alpha += (alvo_alpha - self._stamina_alpha) * min(1.0, dt * velocidade)

    def renderizar_stamina(self, tela, camera, dt):
        _ = dt
        if self._stamina_alpha <= 1.0:
            return
        px, py = camera.mundo_para_tela_px(self.Posicao)
        self.BarraStamina.rect.midbottom = (int(px), int(py - 44))
        bar_surf = pygame.Surface(self.BarraStamina.rect.size, pygame.SRCALPHA)
        rect_original = self.BarraStamina.rect.copy()
        self.BarraStamina.rect.topleft = (0, 0)
        self.BarraStamina._desenhar_barra(bar_surf)
        self.BarraStamina.rect = rect_original
        bar_surf.set_alpha(int(self._stamina_alpha))
        tela.blit(bar_surf, self.BarraStamina.rect.topleft)

    def atualizar_colisor_mao_mundo(self) -> None:
        item_mao = self.Inventario.item_na_mao() if self.Inventario is not None else None
        estilo = ""
        aplica_multiplicador = False
        if isinstance(item_mao, dict):
            estilo = str(item_mao.get("Estilo", item_mao.get("estilo", "")) or "").strip().lower()
            aplica_multiplicador = bool(item_mao.get("usa_multiplicador_tapa_ferramenta", item_mao.get("UsaMultiplicadorTapaFerramenta", estilo == "ferramenta")))
        elif item_mao is not None:
            estilo = str(getattr(item_mao, "Estilo", getattr(item_mao, "estilo", "")) or "").strip().lower()
            aplica_multiplicador = bool(getattr(item_mao, "usa_multiplicador_tapa_ferramenta", getattr(item_mao, "UsaMultiplicadorTapaFerramenta", estilo == "ferramenta")))
        perfil = getattr(self, "Perfil", None)
        raio_base = max(0.05, float(getattr(perfil, "RaioTapa", self._raio_mao_colisao_base) if perfil is not None else self._raio_mao_colisao_base))
        multiplicador = max(1.0, float(getattr(perfil, "MultiplicadorFerramentaTapa", 1.5) if perfil is not None else 1.5))
        raio_mao = raio_base * (multiplicador if aplica_multiplicador else 1.0)
        self.ColisorMao.raio_colisao = float(raio_mao)
        self.ColisorMao.raio_interacao = float(raio_mao)

        rad = math.radians(self.AnguloOlhar)
        frente_x = math.cos(rad)
        frente_y = -math.sin(rad)
        alcance = self._alcance_tapa_px()
        self.ColisorMao.mover_para(self.Posicao[0] + frente_x * alcance, self.Posicao[1] + frente_y * alcance)
        self.ColisorMao.ativo = self._tempo_tapa > 0.0

    def ponto_mao_direita_mundo(self, usar_alcance_tapa: bool = False) -> Vector2:
        rad = math.radians(float(self.AnguloOlhar))
        frente_x = math.cos(rad)
        frente_y = -math.sin(rad)
        lateral_x = -frente_y
        lateral_y = frente_x
        alcance_tapa = self._alcance_tapa_px() if bool(usar_alcance_tapa) else 0.0
        px = float(self.Posicao[0]) + (lateral_x * 0.28) + (frente_x * (0.22 + alcance_tapa))
        py = float(self.Posicao[1]) + (lateral_y * 0.28) + (frente_y * (0.22 + alcance_tapa))
        return (px, py)
    
