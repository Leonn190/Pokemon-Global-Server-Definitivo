from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from Codigo.ModulosGerais.Auxiliares import carregar_frames

Vector2 = Tuple[float, float]


def _normalizar_nome(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


PALETA_TIPOS_ATAQUE: Dict[str, tuple[int, int, int]] = {
    "normal": (187, 176, 151),
    "fogo": (219, 106, 72),
    "agua": (80, 130, 219),
    "planta": (86, 171, 90),
    "eletrico": (224, 199, 61),
    "gelo": (152, 208, 225),
    "lutador": (168, 89, 71),
    "venenoso": (147, 92, 180),
    "veneno": (147, 92, 180),
    "terra": (164, 132, 73),
    "voador": (133, 168, 205),
    "psiquico": (217, 104, 146),
    "inseto": (140, 164, 63),
    "pedra": (128, 121, 107),
    "fantasma": (96, 90, 143),
    "dragao": (87, 97, 191),
    "sombrio": (86, 77, 76),
    "metal": (132, 145, 157),
    "fada": (220, 154, 196),
    "cosmico": (102, 105, 176),
    "sonoro": (198, 123, 219),
}


PROJETEIS_ESPECIAIS: Dict[str, dict[str, object]] = {
    "biscoito": {
        "nome": "Biscoito",
        "caminho": "Recursos/Visual/Projeteis/biscoito.png",
        "velocidade": 8.0,
        "gira": True,
        "rotacao_base": 0.0,
    }
}

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
    _cache_icones_atributos: dict[str, pygame.Surface | None] = {}

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

    def animar_lancar_projetil(self, origem, destino, sprite=None, duracao=None, tipo_ataque=None, velocidade=None):
        p0 = self._posicao_mundo(origem)
        p1 = self._posicao_mundo(destino)
        if p0 is None or p1 is None:
            return None
        config = self._config_projetil(sprite, tipo_ataque=tipo_ataque, velocidade=velocidade)
        dist = max(0.001, math.hypot(p1[0] - p0[0], p1[1] - p0[1]))
        duracao_real = float(duracao or 0.0)
        if duracao_real <= 0:
            vel = float(config.get("velocidade") or 0.0)
            duracao_real = _clamp(dist / vel if vel > 0 else 0.46, 0.18, 1.20)
        return self._adicionar(
            {
                "tipo": "projetil",
                "origem": p0,
                "destino": p1,
                "sprite": config.get("sprite"),
                "config": config,
                "tempo": 0.0,
                "duracao": duracao_real,
                "bloqueante": True,
            }
        )

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
                self._desenhar_fantasmas_troca(surface, anim)
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
                modo = str(anim.get("modo") or "")
                if modo == "desvio":
                    vai = math.sin(t * math.pi) ** 0.78
                x = _interp(origem[0], pico[0], vai)
                y = _interp(origem[1], pico[1], vai)
                if modo == "salto":
                    y -= math.sin(t * math.pi) * 1.25
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

    def _config_projetil(self, sprite=None, tipo_ataque=None, velocidade=None):
        dados = dict(sprite or {}) if isinstance(sprite, dict) else {}
        nome = dados.get("nome") or dados.get("projetil") or dados.get("codigo") or dados.get("code") or (sprite if isinstance(sprite, str) else None)
        chave = _normalizar_nome(nome)
        base = dict(PROJETEIS_ESPECIAIS.get(chave) or {})
        caminho = dados.get("caminho") or dados.get("arquivo") or base.get("caminho") or base.get("arquivo")
        if caminho is None and chave in PROJETEIS_ESPECIAIS:
            caminho = self._buscar_arquivo_projetil(base.get("nome") or nome)
        elif caminho is not None and not Path(str(caminho)).is_absolute() and Path(str(caminho)).parent == Path("."):
            caminho = self._buscar_arquivo_projetil(caminho) or caminho
        config = {
            "nome": str(base.get("nome") or nome or "padrao"),
            "velocidade": float(velocidade or dados.get("velocidade") or base.get("velocidade") or 7.0),
            "gira": bool(dados.get("gira", base.get("gira", False))),
            "rotacao_base": float(dados.get("rotacao_base", base.get("rotacao_base", 0.0)) or 0.0),
            "tipo_ataque": str(tipo_ataque or dados.get("tipo") or dados.get("tipo_ataque") or "normal").strip().lower(),
            "sprite": self._carregar_projetil(caminho),
        }
        config["cor"] = PALETA_TIPOS_ATAQUE.get(config["tipo_ataque"], PALETA_TIPOS_ATAQUE["normal"])
        return config

    def _buscar_arquivo_projetil(self, nome):
        chave = _normalizar_nome(nome)
        if not chave:
            return None
        cache_key = f"_busca:{chave}"
        if cache_key in self._cache_projeteis:
            return None
        base = Path.cwd() / "Recursos" / "Visual" / "Projeteis"
        try:
            for caminho in base.rglob("*"):
                if caminho.is_file() and caminho.suffix.lower() in {".png", ".webp", ".jpg", ".jpeg"} and _normalizar_nome(caminho.stem) == chave:
                    return caminho
        except Exception:
            pass
        self._cache_projeteis[cache_key] = None
        return None

    def _carregar_projetil(self, sprite):
        if not sprite:
            return None
        path = Path(str(sprite))
        if not path.is_absolute():
            path = Path.cwd() / path
        chave = str(path)
        if chave not in self._cache_projeteis:
            try:
                self._cache_projeteis[chave] = pygame.image.load(str(path)).convert_alpha()
            except Exception:
                self._cache_projeteis[chave] = None
        return self._cache_projeteis.get(chave)

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
        pos = self._posicao_tela((_interp(origem[0], destino[0], t), _interp(origem[1], destino[1], t)))
        if pos is None:
            return
        x, y = pos
        config = anim.get("config") if isinstance(anim.get("config"), dict) else {}
        sprite = anim.get("sprite")
        if isinstance(sprite, pygame.Surface):
            lado = max(20, min(50, int(max(sprite.get_width(), sprite.get_height()))))
            img = pygame.transform.smoothscale(sprite, (lado, lado)).convert_alpha()
            ang = float(config.get("rotacao_base", 0.0) or 0.0)
            if bool(config.get("gira", False)):
                ang += float(anim.get("tempo", 0.0)) * 720.0
            if abs(ang) > 0.001:
                img = pygame.transform.rotozoom(img, -ang, 1.0)
            surface.blit(img, img.get_rect(center=(int(x), int(y))))
        else:
            cor = tuple(config.get("cor") or PALETA_TIPOS_ATAQUE["normal"])
            raio = max(7, int(13 + 4 * math.sin(t * math.pi)))
            brilho = tuple(min(255, int(c * 1.25 + 32)) for c in cor)
            pygame.draw.circle(surface, (*cor, 230), (int(x), int(y)), raio)
            pygame.draw.circle(surface, (*brilho, 235), (int(x - raio * 0.25), int(y - raio * 0.25)), max(3, raio // 2))

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
        elif bool(anim.get("critico")):
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

    def _desenhar_gif(self, surface, anim):
        frames = anim.get("frames") if isinstance(anim.get("frames"), list) else []
        pokemon = anim.get("pokemon")
        pos_mundo = self._posicao_mundo(pokemon)
        pos = self._posicao_tela(pos_mundo)
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
