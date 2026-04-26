from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from Codigo.ModulosGerais.Auxiliares import carregar_frames

Vector2 = Tuple[float, float]

EFEITOS_ATAQUE_FPS: Dict[str, float] = {
    'LabaredaMultipla': 31.25,
    'Corte': 10.2,
    'BolhasVerdes': 20,
    'CorteDourado': 10.87,
    'ChuvaVermelha': 31.25,
    'ChuvaBrilhante': 33.33,
    'Agua': 23.81,
    'AtemporalRosa': 40,
    'BarreiraCelular': 12.5,
    'ChicoteMultiplo': 13.89,
    'CorteDuploRoxo': 33.33,
    'CorteMagico': 25,
    'CorteRicocheteadoRoxo': 8.93,
    'CorteRosa': 25,
    'DomoVerde': 11.76,
    'EnergiaAzul': 15.38,
    'Engrenagem': 8.7,
    'EspiralAzul': 22.22,
    'Estouro': 10.31,
    'EstouroMagico': 20,
    'EstouroVermelho': 21.74,
    'Explosao': 22.22,
    'ExplosaoPedra': 10.87,
    'ExplosaoVerde': 8.93,
    'ExplosaoVermelha': 33.33,
    'ExplosaoRoxa': 9.52,
    'FacasAzuis': 35.71,
    'FacasBrancas': 26.32,
    'FacasColoridas': 31.25,
    'FacasRosas': 40,
    'FeixeMagenta': 23.81,
    'FeixeRoxo': 10.42,
    'FluxoAzul': 15.38,
    'Fogo': 10.53,
    'Fumaça': 28.57,
    'GasRoxo': 12.82,
    'Garra': 12.5,
    'HexagonoLaminas': 27.78,
    'ImpactoRochoso': 8.7,
    'Karate': 11.11,
    'LuaAmarela': 55.56,
    'MagiaAzul': 38.46,
    'MagiaMagenta': 20.83,
    'MarcaBrilhosa': 26.32,
    'MarcaAmarela': 19.23,
    'MarcaAzul': 26.32,
    'Mordida': 8.7,
    'MultiplasFacas': 27.78,
    'OrbesRoxos': 35.71,
    'PedaçoColorido': 26.32,
    'RaioAzul': 83.33,
    'RajadaAmarela': 28.57,
    'RasgoMagenta': 38.46,
    'RasgosRosa': 35.71,
    'RedemoinhoAzul': 26.32,
    'RedemoinhoCosmico': 10.53,
    'SuperDescarga': 12.2,
    'SuperNova': 31.25,
    'TirosAmarelos': 40,
    'TornadoAgua': 25.64
}


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def _interp(a: float, b: float, t: float) -> float:
    return float(a) + (float(b) - float(a)) * float(t)


class PokemonAnimator:
    _cache_frames_efeitos: dict[str, list[pygame.Surface]] = {}
    _cache_projeteis: dict[str, pygame.Surface | None] = {}

    def __init__(self, controlador=None):
        self.controlador = controlador
        self.animacoes: list[dict[str, object]] = []
        self._avisos: list[str] = []

    def animar_morrer(self, pokemon):
        if pokemon is None:
            return None
        return self._adicionar({"tipo": "morte", "pokemon": pokemon, "tempo": 0.0, "duracao": 0.85, "bloqueante": True})

    def animar_tomar_dano(self, pokemon, valor=None):
        if pokemon is None:
            return None
        return self._adicionar({"tipo": "flash", "pokemon": pokemon, "tempo": 0.0, "duracao": 0.38, "cor": (255, 56, 56), "bloqueante": False})

    def animar_receber_cura(self, pokemon, valor=None):
        if pokemon is None:
            return None
        return self._adicionar({"tipo": "flash", "pokemon": pokemon, "tempo": 0.0, "duracao": 0.48, "cor": (82, 242, 126), "bloqueante": False})

    def exibir_cartucho(self, pokemon, texto, tipo, valor=None, critico=False):
        if pokemon is None:
            return None
        escala = 1.0
        try:
            v = abs(float(valor if valor is not None else str(texto).replace("+", "").replace("CRIT", "").strip() or 0))
        except (TypeError, ValueError):
            v = 0.0
        max_ref = 80.0 if str(tipo) == "cura" else 100.0
        escala += _clamp(v / max_ref, 0.0, 1.0) * 0.55
        if critico:
            escala += 0.22
        return self._adicionar(
            {
                "tipo": "cartucho",
                "pokemon": pokemon,
                "texto": str(texto or ""),
                "categoria": str(tipo or "dano"),
                "valor": valor,
                "critico": bool(critico),
                "escala_alvo": escala,
                "tempo": 0.0,
                "duracao": 0.95,
                "bloqueante": False,
            }
        )

    def animar_lancar_projetil(self, origem, destino, sprite=None, duracao=None):
        p0 = self._posicao(origem)
        p1 = self._posicao(destino)
        if p0 is None or p1 is None:
            return None
        return self._adicionar(
            {
                "tipo": "projetil",
                "origem": p0,
                "destino": p1,
                "sprite": self._carregar_projetil(sprite),
                "tempo": 0.0,
                "duracao": float(duracao or 0.46),
                "bloqueante": True,
            }
        )

    def animar_avanco(self, pokemon, destino, duracao=None):
        if pokemon is None:
            return None
        origem = self._posicao(pokemon)
        alvo = self._posicao(destino)
        if origem is None or alvo is None:
            return None
        dx, dy = alvo[0] - origem[0], alvo[1] - origem[1]
        dist = max(1.0, math.hypot(dx, dy))
        alcance = min(dist * 0.58, 120.0)
        pico = (origem[0] + dx / dist * alcance, origem[1] + dy / dist * alcance)
        return self._adicionar({"tipo": "deslocamento_temporario", "pokemon": pokemon, "origem": origem, "pico": pico, "tempo": 0.0, "duracao": float(duracao or 0.44), "modo": "avanco", "bloqueante": True})

    def animar_salto(self, pokemon, destino, duracao=None):
        if pokemon is None:
            return None
        origem = self._posicao(pokemon)
        alvo = self._posicao(destino)
        if origem is None or alvo is None:
            return None
        dx, dy = alvo[0] - origem[0], alvo[1] - origem[1]
        dist = max(1.0, math.hypot(dx, dy))
        alcance = min(dist * 0.54, 120.0)
        pico = (origem[0] + dx / dist * alcance, origem[1] + dy / dist * alcance)
        return self._adicionar({"tipo": "deslocamento_temporario", "pokemon": pokemon, "origem": origem, "pico": pico, "tempo": 0.0, "duracao": float(duracao or 0.58), "modo": "salto", "bloqueante": True})

    def animar_movimento(self, pokemon, destino_area_id, duracao=None):
        if pokemon is None:
            return None
        origem = self._posicao(pokemon)
        destino = self._posicao_area(destino_area_id)
        if origem is None or destino is None:
            if destino_area_id:
                pokemon.AreaId = destino_area_id
            return None
        return self._adicionar(
            {
                "tipo": "movimento_area",
                "pokemon": pokemon,
                "origem": origem,
                "destino": destino,
                "area_destino": destino_area_id,
                "tempo": 0.0,
                "duracao": float(duracao or 0.62),
                "bloqueante": True,
            }
        )

    def animar_troca(self, pokemon_saida, pokemon_entrada, origem_saida=None, destino_entrada=None):
        saida = self._posicao(pokemon_saida) or self._posicao_area(origem_saida)
        entrada = self._posicao_area(destino_entrada) or self._posicao(pokemon_saida) or self._posicao(pokemon_entrada)
        return self._adicionar(
            {
                "tipo": "troca",
                "pokemon_saida": pokemon_saida,
                "pokemon_entrada": pokemon_entrada,
                "pos_saida": saida,
                "pos_entrada": entrada,
                "area_entrada": destino_entrada,
                "tempo": 0.0,
                "duracao": 1.05,
                "bloqueante": True,
            }
        )

    def animar_troca_posicao(self, pokemon_a, pokemon_b, area_a_depois=None, area_b_depois=None):
        if pokemon_a is None or pokemon_b is None:
            return None
        pos_a = self._posicao(pokemon_a)
        pos_b = self._posicao(pokemon_b)
        if pos_a is None or pos_b is None:
            return None
        return self._adicionar(
            {
                "tipo": "troca_posicao",
                "pokemon_a": pokemon_a,
                "pokemon_b": pokemon_b,
                "origem_a": pos_a,
                "origem_b": pos_b,
                "area_a_depois": area_a_depois,
                "area_b_depois": area_b_depois,
                "tempo": 0.0,
                "duracao": 0.64,
                "bloqueante": True,
            }
        )

    def animar_efeito(self, pokemon, nome_efeito_gif, posicao="alvo"):
        frames = self._carregar_frames_efeito(nome_efeito_gif)
        if pokemon is None or not frames:
            return None
        fps = float(EFEITOS_ATAQUE_FPS.get(str(nome_efeito_gif), 20.0) or 20.0)
        duracao = max(0.15, len(frames) / max(1.0, fps))
        return self._adicionar({"tipo": "gif", "pokemon": pokemon, "frames": frames, "fps": fps, "tempo": 0.0, "duracao": duracao, "bloqueante": False})

    def atualizar(self, dt):
        dt = max(0.0, float(dt or 0.0))
        restantes = []
        for anim in list(self.animacoes):
            anim["tempo"] = float(anim.get("tempo", 0.0)) + dt
            self._aplicar_animacao(anim)
            if float(anim.get("tempo", 0.0)) < float(anim.get("duracao", 0.0)):
                restantes.append(anim)
            else:
                self._finalizar_animacao(anim)
        self.animacoes = restantes

    def desenhar(self, surface):
        for anim in list(self.animacoes):
            tipo = str(anim.get("tipo") or "")
            if tipo == "projetil":
                self._desenhar_projetil(surface, anim)
            elif tipo == "cartucho":
                self._desenhar_cartucho(surface, anim)
            elif tipo == "gif":
                self._desenhar_gif(surface, anim)
            elif tipo in {"troca"}:
                self._desenhar_circulos_troca(surface, anim)

    def esta_ocupado(self):
        return any(bool(anim.get("bloqueante", True)) for anim in self.animacoes)

    def _adicionar(self, animacao):
        if not isinstance(animacao, dict):
            return None
        self.animacoes.append(animacao)
        return animacao

    def _progresso(self, anim):
        duracao = max(0.001, float(anim.get("duracao", 0.0)))
        return _clamp(float(anim.get("tempo", 0.0)) / duracao, 0.0, 1.0)

    def _aplicar_animacao(self, anim):
        tipo = str(anim.get("tipo") or "")
        t = self._progresso(anim)
        if tipo == "flash":
            pokemon = anim.get("pokemon")
            if pokemon is not None:
                pokemon.FlashVisualCor = tuple(anim.get("cor") or (255, 255, 255))
                pokemon.FlashVisualAlpha = int(170 * (1.0 - t) * (0.35 + 0.65 * abs(math.sin(t * math.pi * 4))))
        elif tipo == "deslocamento_temporario":
            pokemon = anim.get("pokemon")
            origem = anim.get("origem")
            pico = anim.get("pico")
            if pokemon is not None and origem and pico:
                vai = math.sin(t * math.pi)
                x = _interp(origem[0], pico[0], vai)
                y = _interp(origem[1], pico[1], vai)
                if str(anim.get("modo")) == "salto":
                    y -= math.sin(t * math.pi) * 55.0
                pokemon.CentroTelaOverride = (x, y)
        elif tipo == "movimento_area":
            pokemon = anim.get("pokemon")
            origem = anim.get("origem")
            destino = anim.get("destino")
            if pokemon is not None and origem and destino:
                suave = t * t * (3 - 2 * t)
                pokemon.CentroTelaOverride = (_interp(origem[0], destino[0], suave), _interp(origem[1], destino[1], suave))
        elif tipo == "morte":
            pokemon = anim.get("pokemon")
            if pokemon is not None:
                pokemon.RotacaoVisual = 360.0 * t
                pokemon.AlphaVisual = int(255 * (1.0 - t))
        elif tipo == "troca_posicao":
            a = anim.get("pokemon_a")
            b = anim.get("pokemon_b")
            oa = anim.get("origem_a")
            ob = anim.get("origem_b")
            suave = t * t * (3 - 2 * t)
            if a is not None and oa and ob:
                a.CentroTelaOverride = (_interp(oa[0], ob[0], suave), _interp(oa[1], ob[1], suave))
            if b is not None and oa and ob:
                b.CentroTelaOverride = (_interp(ob[0], oa[0], suave), _interp(ob[1], oa[1], suave))
        elif tipo == "troca":
            saida = anim.get("pokemon_saida")
            entrada = anim.get("pokemon_entrada")
            if saida is not None:
                saida.AlphaVisual = int(255 * _clamp(1.0 - t * 1.7, 0.0, 1.0))
            if entrada is not None:
                if t < 0.45:
                    entrada.AlphaVisual = 0
                else:
                    entrada.AlphaVisual = int(255 * _clamp((t - 0.45) / 0.55, 0.0, 1.0))

    def _finalizar_animacao(self, anim):
        tipo = str(anim.get("tipo") or "")
        for chave in ("pokemon", "pokemon_a", "pokemon_b", "pokemon_saida", "pokemon_entrada"):
            poke = anim.get(chave)
            if poke is not None:
                poke.CentroTelaOverride = None
                poke.OffsetVisual = (0.0, 0.0)
                poke.AlphaVisual = 255
                poke.RotacaoVisual = 0.0
                poke.FlashVisualAlpha = 0
        if tipo == "movimento_area":
            pokemon = anim.get("pokemon")
            if pokemon is not None and anim.get("area_destino"):
                pokemon.AreaId = anim.get("area_destino")
        elif tipo == "troca_posicao":
            a = anim.get("pokemon_a")
            b = anim.get("pokemon_b")
            if a is not None and anim.get("area_a_depois"):
                a.AreaId = anim.get("area_a_depois")
            if b is not None and anim.get("area_b_depois"):
                b.AreaId = anim.get("area_b_depois")
        elif tipo == "troca":
            saida = anim.get("pokemon_saida")
            entrada = anim.get("pokemon_entrada")
            if saida is not None:
                saida.Ativo = False
                saida.EmReserva = True
                saida.AreaId = None
            if entrada is not None:
                entrada.Ativo = True
                entrada.EmReserva = False
                if anim.get("area_entrada"):
                    entrada.AreaId = anim.get("area_entrada")
        elif tipo == "morte":
            pokemon = anim.get("pokemon")
            if pokemon is not None:
                pokemon.Vivo = False
                pokemon.VidaAtual = 0.0

    def _posicao(self, alvo):
        if alvo is None:
            return None
        if isinstance(alvo, (list, tuple)) and len(alvo) >= 2:
            return (float(alvo[0]), float(alvo[1]))
        rect = getattr(alvo, "RectAtual", None)
        if isinstance(rect, pygame.Rect) and rect.width > 0 and rect.height > 0:
            return rect.center
        area_id = getattr(alvo, "AreaId", None)
        return self._posicao_area(area_id)

    def _posicao_area(self, area_id):
        ctrl = self.controlador
        if ctrl is None or getattr(ctrl, "arena", None) is None or getattr(ctrl, "camera", None) is None:
            return None
        try:
            return ctrl.arena.centro_area_tela(area_id, ctrl.camera)
        except Exception:
            return None

    def _carregar_projetil(self, sprite):
        caminho = None
        if isinstance(sprite, dict):
            caminho = sprite.get("caminho") or sprite.get("arquivo")
        elif sprite:
            caminho = str(sprite)
        if caminho:
            path = Path(str(caminho))
            if not path.is_absolute():
                path = Path.cwd() / path
            chave = str(path)
            if chave not in self._cache_projeteis:
                try:
                    self._cache_projeteis[chave] = pygame.image.load(str(path)).convert_alpha()
                except Exception:
                    self._cache_projeteis[chave] = None
            return self._cache_projeteis.get(chave)
        return None

    def _carregar_frames_efeito(self, nome):
        nome = str(nome or "").strip()
        if not nome:
            return []
        if nome in self._cache_frames_efeitos:
            return self._cache_frames_efeitos[nome]
        base = Path.cwd() / "Recursos" / "Visual" / "AtaquesGifs"
        candidatos = [base / nome, base / f"{nome}_frames"]
        frames = []
        for pasta in candidatos:
            if not pasta.exists() or not pasta.is_dir():
                continue
            try:
                frames = carregar_frames(pasta)
            except Exception:
                frames = []
            if frames:
                break
        self._cache_frames_efeitos[nome] = [f for f in frames if isinstance(f, pygame.Surface)]
        return self._cache_frames_efeitos[nome]

    def _desenhar_projetil(self, surface, anim):
        t = self._progresso(anim)
        origem = anim.get("origem")
        destino = anim.get("destino")
        if not origem or not destino:
            return
        x = _interp(origem[0], destino[0], t)
        y = _interp(origem[1], destino[1], t)
        sprite = anim.get("sprite")
        if isinstance(sprite, pygame.Surface):
            lado = max(20, min(46, int(sprite.get_width())))
            img = pygame.transform.smoothscale(sprite, (lado, lado))
            surface.blit(img, img.get_rect(center=(int(x), int(y))))
        else:
            raio = max(7, int(13 + 4 * math.sin(t * math.pi)))
            pygame.draw.circle(surface, (96, 210, 255), (int(x), int(y)), raio)
            pygame.draw.circle(surface, (242, 252, 255), (int(x), int(y)), max(3, raio // 2))

    def _desenhar_cartucho(self, surface, anim):
        pokemon = anim.get("pokemon")
        pos = self._posicao(pokemon)
        if pos is None:
            return
        t = self._progresso(anim)
        texto = str(anim.get("texto") or "")
        escala = _interp(0.72, float(anim.get("escala_alvo", 1.0)), min(1.0, t * 2.4))
        alpha = int(255 * _clamp(1.0 - max(0.0, t - 0.55) / 0.45, 0.0, 1.0))
        y = pos[1] - 42 - 58 * t
        fonte = pygame.font.SysFont("arial", max(16, int(22 * escala)), bold=True)
        txt = fonte.render(texto, True, (255, 255, 255))
        pad_x, pad_y = int(12 * escala), int(5 * escala)
        rect = pygame.Rect(0, 0, txt.get_width() + pad_x * 2, txt.get_height() + pad_y * 2)
        rect.center = (int(pos[0]), int(y))
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        categoria = str(anim.get("categoria") or "dano")
        if bool(anim.get("critico")):
            cor = (216, 44, 54, alpha)
        elif categoria == "cura":
            cor = (42, 176, 92, alpha)
        elif categoria == "barreira":
            cor = (72, 164, 226, alpha)
        else:
            cor = (226, 114, 44, alpha)
        pygame.draw.rect(surf, cor, surf.get_rect(), border_radius=8)
        pygame.draw.rect(surf, (255, 255, 255, alpha), surf.get_rect(), 2, border_radius=8)
        txt.set_alpha(alpha)
        surf.blit(txt, (pad_x, pad_y))
        surface.blit(surf, rect.topleft)

    def _desenhar_gif(self, surface, anim):
        frames = anim.get("frames") if isinstance(anim.get("frames"), list) else []
        pokemon = anim.get("pokemon")
        pos = self._posicao(pokemon)
        if not frames or pos is None:
            return
        fps = max(1.0, float(anim.get("fps", 20.0) or 20.0))
        idx = min(len(frames) - 1, int(float(anim.get("tempo", 0.0)) * fps) % len(frames))
        frame = frames[idx]
        if not isinstance(frame, pygame.Surface):
            return
        tamanho = max(72, int(max(getattr(pokemon, "RectAtual", pygame.Rect(0, 0, 72, 72)).size or (72, 72)) * 1.35))
        img = pygame.transform.smoothscale(frame, (tamanho, tamanho)).convert_alpha()
        surface.blit(img, img.get_rect(center=(int(pos[0]), int(pos[1]))))

    def _desenhar_circulos_troca(self, surface, anim):
        t = self._progresso(anim)
        for pos, fase in ((anim.get("pos_saida"), 0.0), (anim.get("pos_entrada"), 0.42)):
            if not pos:
                continue
            local_t = _clamp((t - fase) / 0.45, 0.0, 1.0)
            if local_t <= 0 or local_t >= 1.0:
                continue
            raio = int(16 + math.sin(local_t * math.pi) * 76)
            alpha = int(180 * math.sin(local_t * math.pi))
            pygame.draw.circle(surface, (120, 218, 255, alpha), (int(pos[0]), int(pos[1])), raio, max(4, raio // 8))


