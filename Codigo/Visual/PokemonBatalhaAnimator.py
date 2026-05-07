from __future__ import annotations

import math
import unicodedata
from pathlib import Path
from typing import Tuple

import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Visual.ArenaAnimator import ArenaAnimator
from Codigo.Visual.AuxiliaresVisuais import EFEITOS_ATAQUE_FPS
from Codigo.Visual.ContatoIrregularAnimator import ContatoIrregularAnimator
from Codigo.Visual.ProjetilBatalha import GerenciadorProjeteisBatalha

Vector2 = Tuple[float, float]


def _normalizar_nome(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def _interp(a: float, b: float, t: float) -> float:
    return float(a) + (float(b) - float(a)) * float(t)


class PokemonAnimator:
    _cache_icones_atributos: dict[str, pygame.Surface | None] = {}

    def __init__(self, controlador=None):
        self.controlador = controlador
        self.animacoes: list[dict[str, object]] = []
        self.projeteis = GerenciadorProjeteisBatalha(self._posicao_tela)
        self.contatos_irregulares = ContatoIrregularAnimator(self._posicao_mundo, self._posicao_tela)
        self.arena_animator = ArenaAnimator(self._posicao_mundo, self._posicao_tela)
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

    def exibir_cartucho(self, pokemon, texto, tipo, valor=None, critico=False, atributo=None, cor_fundo=None):
        if pokemon is None:
            return None
        escala = 1.0
        try:
            bruto = str(texto).replace("+", "").replace("-", "").replace("CRIT", "").strip()
            v = abs(float(valor if valor is not None else bruto or 0))
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
                "atributo": atributo,
                "cor_fundo": cor_fundo,
                "escala_alvo": escala,
                "tempo": 0.0,
                "duracao": 0.95,
                "bloqueante": False,
            }
        )

    def exibir_cartucho_atributo(self, pokemon, atributo, valor, positivo=None):
        if pokemon is None or not atributo:
            return None
        if positivo is None:
            try:
                positivo = float(valor) >= 0
            except (TypeError, ValueError):
                positivo = True
        texto = self._formatar_variacao(valor, positivo=bool(positivo))
        cor = (55, 136, 232) if bool(positivo) else (126, 68, 190)
        return self.exibir_cartucho(pokemon, texto, "atributo", valor=valor, atributo=atributo, cor_fundo=cor)

    def animar_lancar_projetil(self, origem, destino, sprite=None, duracao=None, tipo_ataque=None, velocidade=None, tamanho=None, cor=None):
        p0 = self._posicao_mundo(origem)
        p1 = self._posicao_mundo(destino)
        if p0 is None or p1 is None:
            return None
        return self.projeteis.animar_lancar(p0, p1, sprite=sprite, duracao=duracao, tipo_ataque=tipo_ataque, velocidade=velocidade, tamanho=tamanho, cor=cor)


    def animar_laser(self, origem, destino, tipo_ataque=None, duracao=None, largura=None, cor=None):
        return self.contatos_irregulares.animar_laser(origem, destino, tipo_ataque=tipo_ataque, duracao=duracao, largura=largura, cor=cor)

    def animar_laser_por_linha(self, pokemon, linha_inicio, linha_fim=None, frente_linha=None, tipo_ataque=None, duracao=None, largura=None, cor=None):
        return self.contatos_irregulares.animar_laser_por_linha(
            pokemon,
            linha_inicio,
            linha_fim,
            frente_linha=frente_linha,
            tipo_ataque=tipo_ataque,
            duracao=duracao,
            largura=largura,
            cor=cor,
        )

    def animar_raio(self, origem, destino, tipo_ataque=None, duracao=None, largura=None, cor=None):
        return self.contatos_irregulares.animar_raio(origem, destino, tipo_ataque=tipo_ataque, duracao=duracao, largura=largura, cor=cor)

    def animar_jato(self, origem, destino, tipo_ataque=None, duracao=None, largura=None, cor=None):
        return self.contatos_irregulares.animar_jato(origem, destino, tipo_ataque=tipo_ataque, duracao=duracao, largura=largura, cor=cor)

    def animar_explosao_onda(self, centro, alvos=None, tipo_ataque=None, raio=None, duracao=None, largura=None, cor=None):
        return self.contatos_irregulares.animar_explosao_onda(centro, alvos=alvos, tipo_ataque=tipo_ataque, raio=raio, duracao=duracao, largura=largura, cor=cor)

    def animar_desvio(self, pokemon, duracao=None, intensidade_tiles=None):
        if pokemon is None:
            return None
        origem = self._posicao_mundo(pokemon)
        if origem is None:
            return None
        lado = str(getattr(pokemon, "Lado", "") or "").strip().lower()
        lado_id = getattr(pokemon, "lado_id", None)
        inimigo = lado == "inimigo" or (lado_id is not None and str(lado_id) != "50")
        intensidade = float(intensidade_tiles or 0.42)
        dx = intensidade if inimigo else -intensidade
        dy = -intensidade * 0.72
        pico = (origem[0] + dx, origem[1] + dy)
        return self._adicionar(
            {
                "tipo": "deslocamento_temporario",
                "pokemon": pokemon,
                "origem": origem,
                "pico": pico,
                "tempo": 0.0,
                "duracao": float(duracao or 0.34),
                "modo": "desvio",
                "bloqueante": False,
            }
        )

    def animar_avanco(self, pokemon, destino, duracao=None):
        if pokemon is None:
            return None
        origem = self._posicao_mundo(pokemon)
        alvo = self._posicao_mundo(destino)
        if origem is None or alvo is None:
            return None
        dx, dy = alvo[0] - origem[0], alvo[1] - origem[1]
        dist = max(1.0, math.hypot(dx, dy))
        raio_origem = self._raio_mundo(pokemon, 0.45)
        raio_alvo = self._raio_mundo(destino, 0.45)
        alcance = max(0.0, dist - raio_origem - raio_alvo)
        pico = (origem[0] + dx / dist * alcance, origem[1] + dy / dist * alcance)
        return self._adicionar({"tipo": "deslocamento_temporario", "pokemon": pokemon, "origem": origem, "pico": pico, "tempo": 0.0, "duracao": float(duracao or 0.78), "modo": "avanco", "bloqueante": True})

    def animar_salto(self, pokemon, destino, duracao=None):
        if pokemon is None:
            return None
        origem = self._posicao_mundo(pokemon)
        alvo = self._posicao_mundo(destino)
        if origem is None or alvo is None:
            return None
        dx, dy = alvo[0] - origem[0], alvo[1] - origem[1]
        dist = max(1.0, math.hypot(dx, dy))
        raio_origem = self._raio_mundo(pokemon, 0.45)
        raio_alvo = self._raio_mundo(destino, 0.45)
        alcance = max(0.0, dist - raio_origem - raio_alvo)
        pico = (origem[0] + dx / dist * alcance, origem[1] + dy / dist * alcance)
        return self._adicionar({"tipo": "deslocamento_temporario", "pokemon": pokemon, "origem": origem, "pico": pico, "tempo": 0.0, "duracao": float(duracao or 0.86), "modo": "salto", "bloqueante": True})

    def animar_deslocamento_ataque(self, pokemon, destinos, modo="avanco", velocidade=None, altura=None, distancia_parada="contato", retornar=True):
        if pokemon is None:
            return None
        origem = self._posicao_mundo(pokemon)
        if origem is None:
            return None
        pontos = [origem]
        impactos = []
        duracoes = []
        atual = origem
        vel = max(0.1, float(velocidade or (7.0 if str(modo) == "salto" else 8.0)))
        for destino in list(destinos or []):
            alvo = self._posicao_mundo(destino)
            if alvo is None:
                continue
            ponto = self._ponto_parada_contato(pokemon, destino, atual, alvo, distancia_parada)
            dist = max(0.05, math.hypot(ponto[0] - atual[0], ponto[1] - atual[1]))
            dur = _clamp(dist / vel, 0.16, 0.72)
            duracoes.append(dur)
            pontos.append(ponto)
            impactos.append(sum(duracoes))
            atual = ponto
        if len(pontos) <= 1:
            return None
        if bool(retornar):
            dist = max(0.05, math.hypot(atual[0] - origem[0], atual[1] - origem[1]))
            duracoes.append(_clamp(dist / vel, 0.16, 0.72))
            pontos.append(origem)
        duracao_total = max(0.16, sum(duracoes))
        return self._adicionar(
            {
                "tipo": "deslocamento_ataque",
                "pokemon": pokemon,
                "pontos": pontos,
                "duracoes": duracoes,
                "impactos": impactos,
                "tempo": 0.0,
                "duracao": duracao_total,
                "modo": str(modo or "avanco"),
                "altura": float(altura or 1.25),
                "bloqueante": True,
            }
        )

    def animar_movimento(self, pokemon, destino_area_id, duracao=None):
        if pokemon is None:
            return None
        origem = self._posicao_mundo(pokemon)
        destino = self._posicao_area_mundo(destino_area_id)
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
        saida = self._posicao_mundo(pokemon_saida) or self._posicao_area_mundo(origem_saida)
        entrada = self._posicao_area_mundo(destino_entrada) or self._posicao_mundo(pokemon_saida) or self._posicao_mundo(pokemon_entrada)
        reserva = self._posicao_reserva_mundo(pokemon_entrada)
        if pokemon_saida is not None:
            pokemon_saida.AlphaVisual = 255
        if pokemon_entrada is not None:
            pokemon_entrada.AlphaVisual = 255
        return self._adicionar(
            {
                "tipo": "troca",
                "pokemon_saida": pokemon_saida,
                "pokemon_entrada": pokemon_entrada,
                "pos_saida": saida,
                "pos_entrada": entrada,
                "pos_reserva": reserva,
                "area_entrada": destino_entrada,
                "tempo": 0.0,
                "duracao": 1.05,
                "bloqueante": True,
            }
        )

    def animar_troca_posicao(self, pokemon_a, pokemon_b, area_a_depois=None, area_b_depois=None):
        if pokemon_a is None or pokemon_b is None:
            return None
        pos_a = self._posicao_mundo(pokemon_a)
        pos_b = self._posicao_mundo(pokemon_b)
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
        return self.arena_animator.animar_efeito(pokemon, nome_efeito_gif, posicao=posicao)

    def animar_captura_batalha(self, usuario, alvo, dados):
        if alvo is None:
            return None
        origem = self._posicao_mundo(usuario) or self._posicao_mundo(alvo)
        destino = self._posicao_mundo(alvo)
        if origem is None or destino is None:
            return None
        return self._adicionar(
            {
                "tipo": "captura_batalha",
                "usuario": usuario,
                "alvo": alvo,
                "origem": origem,
                "destino": destino,
                "bola_nome": str((dados or {}).get("bola_nome") or "Pokeball"),
                "item_base_id": str((dados or {}).get("item_base_id") or ""),
                "checagens": list((dados or {}).get("checagens") or []),
                "capturado": bool((dados or {}).get("capturado", False)),
                "tempo": 0.0,
                "duracao": 2.35,
                "bloqueante": True,
            }
        )

    def atualizar(self, dt):
        dt = max(0.0, float(dt or 0.0))
        self.projeteis.atualizar(dt)
        self.contatos_irregulares.atualizar(dt)
        self.arena_animator.atualizar(dt)
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
        self.projeteis.desenhar(surface)
        self.contatos_irregulares.desenhar(surface)
        self.arena_animator.desenhar(surface)
        for anim in list(self.animacoes):
            tipo = str(anim.get("tipo") or "")
            if tipo == "cartucho":
                self._desenhar_cartucho(surface, anim)
            elif tipo in {"troca"}:
                self._desenhar_fantasmas_troca(surface, anim)
                self._desenhar_circulos_troca(surface, anim)
            elif tipo == "captura_batalha":
                self._desenhar_captura_batalha(surface, anim)

    def esta_ocupado(self):
        return self.projeteis.esta_ocupado() or self.contatos_irregulares.esta_ocupado() or self.arena_animator.esta_ocupado() or any(bool(anim.get("bloqueante", True)) for anim in self.animacoes)

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
                modo = str(anim.get("modo") or "")
                if modo == "desvio":
                    vai = math.sin(t * math.pi) ** 0.78
                x = _interp(origem[0], pico[0], vai)
                y = _interp(origem[1], pico[1], vai)
                if modo == "salto":
                    y -= math.sin(t * math.pi) * 1.25
                pokemon.CentroMundoOverride = (x, y)
        elif tipo == "deslocamento_ataque":
            pokemon = anim.get("pokemon")
            pontos = list(anim.get("pontos") or [])
            duracoes = list(anim.get("duracoes") or [])
            if pokemon is not None and len(pontos) >= 2 and duracoes:
                tempo = float(anim.get("tempo", 0.0))
                acumulado = 0.0
                idx = 0
                for i, dur in enumerate(duracoes):
                    dur = max(0.001, float(dur or 0.0))
                    if tempo <= acumulado + dur or i == len(duracoes) - 1:
                        idx = i
                        break
                    acumulado += dur
                dur = max(0.001, float(duracoes[idx] or 0.0))
                local = _clamp((tempo - acumulado) / dur, 0.0, 1.0)
                suave = local * local * (3 - 2 * local)
                a = pontos[idx]
                b = pontos[min(idx + 1, len(pontos) - 1)]
                x = _interp(a[0], b[0], suave)
                y = _interp(a[1], b[1], suave)
                if str(anim.get("modo") or "") == "salto":
                    y -= math.sin(local * math.pi) * float(anim.get("altura") or 1.25)
                pokemon.CentroMundoOverride = (x, y)
        elif tipo == "movimento_area":
            pokemon = anim.get("pokemon")
            origem = anim.get("origem")
            destino = anim.get("destino")
            if pokemon is not None and origem and destino:
                suave = t * t * (3 - 2 * t)
                pokemon.CentroMundoOverride = (_interp(origem[0], destino[0], suave), _interp(origem[1], destino[1], suave))
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
                a.CentroMundoOverride = (_interp(oa[0], ob[0], suave), _interp(oa[1], ob[1], suave))
            if b is not None and oa and ob:
                b.CentroMundoOverride = (_interp(ob[0], oa[0], suave), _interp(ob[1], oa[1], suave))
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
        elif tipo == "captura_batalha":
            alvo = anim.get("alvo")
            if alvo is not None:
                if t < 0.28:
                    alvo.AlphaVisual = 255
                elif t < 0.46:
                    alvo.AlphaVisual = int(255 * _clamp(1.0 - ((t - 0.28) / 0.18), 0.0, 1.0))
                    alvo.RotacaoVisual = 360.0 * _clamp((t - 0.28) / 0.18, 0.0, 1.0)
                elif not bool(anim.get("capturado")) and t > 0.78:
                    alvo.AlphaVisual = int(255 * _clamp((t - 0.78) / 0.18, 0.0, 1.0))
                    alvo.RotacaoVisual = 0.0
                elif bool(anim.get("capturado")):
                    alvo.AlphaVisual = 0

    def _finalizar_animacao(self, anim):
        tipo = str(anim.get("tipo") or "")
        for chave in ("pokemon", "pokemon_a", "pokemon_b", "pokemon_saida", "pokemon_entrada"):
            poke = anim.get(chave)
            if poke is not None:
                poke.CentroMundoOverride = None
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
        elif tipo == "captura_batalha":
            alvo = anim.get("alvo")
            if alvo is not None:
                if bool(anim.get("capturado")):
                    alvo.Vivo = False
                    alvo.Ativo = False
                    alvo.EmReserva = False
                    alvo.AreaId = None
                    alvo.AlphaVisual = 0
                else:
                    alvo.AlphaVisual = 255
                alvo.RotacaoVisual = 0.0

    def _posicao_mundo(self, alvo):
        if alvo is None:
            return None
        if isinstance(alvo, (list, tuple)) and len(alvo) >= 2:
            return (float(alvo[0]), float(alvo[1]))
        override = getattr(alvo, "CentroMundoOverride", None)
        if isinstance(override, (list, tuple)) and len(override) >= 2:
            return (float(override[0]), float(override[1]))
        area_id = getattr(alvo, "AreaId", None)
        if area_id and not bool(getattr(alvo, "EmReserva", False)):
            pos = self._posicao_area_mundo(area_id)
            if pos is not None:
                return pos
        reserva = self._posicao_reserva_mundo(alvo)
        if reserva is not None:
            return reserva
        rect = getattr(alvo, "RectAtual", None)
        ctrl = self.controlador
        camera = getattr(ctrl, "camera", None) if ctrl is not None else None
        if isinstance(rect, pygame.Rect) and rect.width > 0 and rect.height > 0 and camera is not None:
            try:
                return camera.tela_para_mundo_tiles(rect.center)
            except Exception:
                return None
        return None

    def _posicao_area_mundo(self, area_id):
        ctrl = self.controlador
        if ctrl is None or getattr(ctrl, "arena", None) is None:
            return None
        try:
            return ctrl.arena.centro_area(area_id)
        except Exception:
            return None

    def _posicao_reserva_mundo(self, pokemon):
        ctrl = self.controlador
        if pokemon is None or ctrl is None or getattr(ctrl, "arena", None) is None:
            return None
        try:
            return ctrl.arena.centro_slot_reserva_mundo(getattr(pokemon, "id_batalha", None))
        except Exception:
            return None

    def _posicao_tela(self, pos_mundo):
        if not (isinstance(pos_mundo, (list, tuple)) and len(pos_mundo) >= 2):
            return None
        ctrl = self.controlador
        camera = getattr(ctrl, "camera", None) if ctrl is not None else None
        if camera is None:
            return (float(pos_mundo[0]), float(pos_mundo[1]))
        try:
            return camera.mundo_para_tela_px((float(pos_mundo[0]), float(pos_mundo[1])))
        except Exception:
            return None

    def _raio_mundo(self, alvo, default=0.45):
        ctrl = self.controlador
        camera = getattr(ctrl, "camera", None) if ctrl is not None else None
        tile = max(1.0, float(getattr(camera, "TilePx", 40) or 40)) if camera is not None else 40.0
        rect = getattr(alvo, "RectAtual", None)
        if isinstance(rect, pygame.Rect) and rect.width > 0:
            return max(default, (float(rect.width) * 0.35) / tile)
        return default

    def _ponto_parada_contato(self, pokemon, destino, origem, alvo, distancia_parada="contato"):
        dx, dy = alvo[0] - origem[0], alvo[1] - origem[1]
        dist = max(0.001, math.hypot(dx, dy))
        if _normalizar_nome(distancia_parada) == "contato":
            parada = self._raio_mundo(pokemon, 0.45) + self._raio_mundo(destino, 0.45)
        else:
            try:
                parada = max(0.0, float(distancia_parada))
            except (TypeError, ValueError):
                parada = self._raio_mundo(pokemon, 0.45) + self._raio_mundo(destino, 0.45)
        alcance = max(0.0, dist - parada)
        return (origem[0] + dx / dist * alcance, origem[1] + dy / dist * alcance)

    def _desenhar_cartucho(self, surface, anim):
        pokemon = anim.get("pokemon")
        pos_mundo = self._posicao_mundo(pokemon)
        pos = self._posicao_tela(pos_mundo)
        if pos is None:
            return
        t = self._progresso(anim)
        texto = str(anim.get("texto") or "")
        escala = _interp(0.72, float(anim.get("escala_alvo", 1.0)), min(1.0, t * 2.4))
        alpha = int(255 * _clamp(1.0 - max(0.0, t - 0.55) / 0.45, 0.0, 1.0))
        y = pos[1] - 42 - 58 * t
        fonte = pygame.font.SysFont("arial", max(16, int(22 * escala)), bold=True)
        txt = fonte.render(texto, True, (255, 255, 255))
        icone = self._carregar_icone_atributo(anim.get("atributo"))
        icon_lado = max(0, int(24 * escala)) if icone is not None else 0
        pad_x, pad_y = int(12 * escala), int(5 * escala)
        gap = int(6 * escala) if icone is not None else 0
        rect = pygame.Rect(0, 0, txt.get_width() + icon_lado + gap + pad_x * 2, max(txt.get_height(), icon_lado) + pad_y * 2)
        rect.center = (int(pos[0]), int(y))
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        categoria = str(anim.get("categoria") or "dano")
        cor_cfg = anim.get("cor_fundo")
        if isinstance(cor_cfg, (list, tuple)) and len(cor_cfg) >= 3:
            cor = (int(cor_cfg[0]), int(cor_cfg[1]), int(cor_cfg[2]), alpha)
        elif bool(anim.get("critico")) and categoria == "dano":
            cor = (216, 44, 54, alpha)
        elif categoria == "cura":
            cor = (42, 176, 92, alpha)
        elif categoria == "barreira":
            cor = (72, 164, 226, alpha)
        elif categoria == "desvio":
            cor = (75, 110, 210, alpha)
        else:
            cor = (226, 114, 44, alpha)
        pygame.draw.rect(surf, cor, surf.get_rect(), border_radius=8)
        pygame.draw.rect(surf, (255, 255, 255, alpha), surf.get_rect(), 2, border_radius=8)
        x = pad_x
        if icone is not None:
            icon = pygame.transform.smoothscale(icone, (icon_lado, icon_lado)).convert_alpha()
            icon.set_alpha(alpha)
            surf.blit(icon, icon.get_rect(midleft=(x, surf.get_height() // 2)))
            x += icon_lado + gap
        txt.set_alpha(alpha)
        surf.blit(txt, (x, (surf.get_height() - txt.get_height()) // 2))
        surface.blit(surf, rect.topleft)

    @staticmethod
    def _formatar_variacao(valor, positivo=True):
        try:
            num = float(valor)
        except (TypeError, ValueError):
            bruto = str(valor or "")
            return bruto if bruto.startswith(("+", "-")) else (("+" if positivo else "-") + bruto)
        sinal = "+" if num >= 0 else "-"
        if positivo and num == 0:
            sinal = "+"
        valor_abs = abs(num)
        corpo = str(int(round(valor_abs))) if abs(valor_abs - round(valor_abs)) < 0.001 else f"{valor_abs:.1f}".rstrip("0").rstrip(".")
        return f"{sinal}{corpo}"

    @classmethod
    def _carregar_icone_atributo(cls, atributo):
        chave = _normalizar_nome(atributo)
        if not chave:
            return None
        aliases = {
            "amp": "amplificacao",
            "amplificacao": "amplificacao",
            "dur": "durabilidade",
            "durabilidade": "durabilidade",
        }
        busca = aliases.get(chave, chave)
        if busca in cls._cache_icones_atributos:
            return cls._cache_icones_atributos[busca]
        base = Path.cwd() / "Recursos" / "Visual" / "Icones" / "Atributos"
        escolhido = None
        try:
            for caminho in base.iterdir():
                if caminho.is_file() and _normalizar_nome(caminho.stem) == busca:
                    escolhido = caminho
                    break
        except Exception:
            escolhido = None
        if escolhido is not None:
            try:
                cls._cache_icones_atributos[busca] = pygame.image.load(str(escolhido)).convert_alpha()
            except Exception:
                cls._cache_icones_atributos[busca] = None
        else:
            cls._cache_icones_atributos[busca] = None
        return cls._cache_icones_atributos[busca]

    def _desenhar_fantasmas_troca(self, surface, anim):
        t = self._progresso(anim)
        entrada_alpha = int(255 * _clamp((t - 0.45) / 0.55, 0.0, 1.0))
        saida_alpha = int(255 * _clamp((t - 0.20) / 0.60, 0.0, 1.0))
        if entrada_alpha > 0:
            self._desenhar_pokemon_em_mundo(surface, anim.get("pokemon_entrada"), anim.get("pos_entrada"), entrada_alpha)
        if saida_alpha > 0:
            self._desenhar_pokemon_em_mundo(surface, anim.get("pokemon_saida"), anim.get("pos_reserva"), saida_alpha)

    def _desenhar_pokemon_em_mundo(self, surface, pokemon, pos_mundo, alpha):
        pos = self._posicao_tela(pos_mundo)
        if pokemon is None or pos is None or alpha <= 0:
            return
        ctrl = self.controlador
        camera = getattr(ctrl, "camera", None) if ctrl is not None else None
        img = None
        if hasattr(pokemon, "_frame_atual_escalado"):
            try:
                img = pokemon._frame_atual_escalado(camera)
            except Exception:
                img = None
        if isinstance(img, pygame.Surface):
            copia = img.copy()
            copia.set_alpha(max(0, min(255, int(alpha))))
            surface.blit(copia, copia.get_rect(center=(int(pos[0]), int(pos[1]))))
            return
        tile = max(1, int(getattr(camera, "TilePx", 40) or 40)) if camera is not None else 40
        lado = max(34, int(tile * 1.7))
        cor = (110, 196, 126, int(alpha)) if getattr(pokemon, "Lado", "") == "jogador" else (204, 108, 108, int(alpha))
        sprite = pygame.Surface((lado, lado), pygame.SRCALPHA)
        pygame.draw.circle(sprite, cor, (lado // 2, lado // 2), lado // 2)
        surface.blit(sprite, sprite.get_rect(center=(int(pos[0]), int(pos[1]))))

    def _desenhar_captura_batalha(self, surface, anim):
        t = self._progresso(anim)
        origem = anim.get("origem")
        destino = anim.get("destino")
        if not origem or not destino:
            return
        if t < 0.26:
            p = t / 0.26
            p = p * p * (3 - 2 * p)
            pos_mundo = (_interp(origem[0], destino[0], p), _interp(origem[1], destino[1], p) - math.sin(p * math.pi) * 1.2)
        else:
            pos_mundo = destino
        pos = self._posicao_tela(pos_mundo)
        if pos is None:
            return
        checks = list(anim.get("checagens") or [])
        fase_checks = _clamp((t - 0.48) / 0.30, 0.0, 1.0)
        tremor = 0.0
        if 0.48 <= t <= 0.82 and checks:
            tremor = math.sin(fase_checks * math.pi * max(1, len(checks)) * 2.0) * 8.0
        if not bool(anim.get("capturado")) and t > 0.82:
            pos = (pos[0], pos[1] - math.sin(_clamp((t - 0.82) / 0.18, 0.0, 1.0) * math.pi) * 26.0)
        size = max(26, int(max(1, getattr(getattr(self.controlador, "camera", None), "TilePx", 40) or 40) * 0.72))
        item = {"Nome": anim.get("bola_nome") or "Pokeball", "Code": anim.get("item_base_id") or ""}
        sprite = ItemInventario.surface_item(item, size)
        if sprite is None:
            sprite = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(sprite, (245, 248, 255), (size // 2, size // 2), size // 2)
            pygame.draw.circle(sprite, (218, 52, 68), (size // 2, size // 2), size // 2, max(2, size // 10))
            pygame.draw.line(sprite, (34, 40, 54), (2, size // 2), (size - 2, size // 2), max(2, size // 12))
        rect = sprite.get_rect(center=(int(pos[0] + tremor), int(pos[1])))
        surface.blit(sprite, rect)
        if 0.28 <= t <= 0.45:
            alvo = anim.get("alvo")
            alvo_pos = self._posicao_tela(self._posicao_mundo(alvo))
            if alvo_pos is not None:
                local = _clamp((t - 0.28) / 0.17, 0.0, 1.0)
                alpha = int(180 * (1.0 - local))
                raio = int(18 + 70 * local)
                pygame.draw.circle(surface, (128, 218, 255, alpha), (int(alvo_pos[0]), int(alvo_pos[1])), raio, max(3, raio // 8))

    def _desenhar_circulos_troca(self, surface, anim):
        t = self._progresso(anim)
        for pos_mundo, fase in ((anim.get("pos_saida"), 0.0), (anim.get("pos_entrada"), 0.42), (anim.get("pos_reserva"), 0.28)):
            if not pos_mundo:
                continue
            pos = self._posicao_tela(pos_mundo)
            if pos is None:
                continue
            local_t = _clamp((t - fase) / 0.45, 0.0, 1.0)
            if local_t <= 0 or local_t >= 1.0:
                continue
            raio = int(16 + math.sin(local_t * math.pi) * 76)
            alpha = int(180 * math.sin(local_t * math.pi))
            pygame.draw.circle(surface, (120, 218, 255, alpha), (int(pos[0]), int(pos[1])), raio, max(4, raio // 8))
