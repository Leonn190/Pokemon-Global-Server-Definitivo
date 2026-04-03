from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame

from Codigo.Prefabs.Texto import Texto


class PokemonInventario:
    PASTA_IMAGENS = Path("Recursos") / "Visual" / "Pokemons" / "Imagens"

    _mapa_por_nome: Dict[str, str] | None = None
    _mapa_por_numero: Dict[str, str] | None = None
    _cache_surface: Dict[Tuple[str, int], Optional[pygame.Surface]] = {}
    _cache_icone_coracao: Dict[int, Optional[pygame.Surface]] = {}
    _cache_icone_tipo: Dict[Tuple[str, int], Optional[pygame.Surface]] = {}
    _mostrar_poder_slots: bool = False

    @classmethod
    def definir_mostrar_poder_slots(cls, ativo: bool):
        cls._mostrar_poder_slots = bool(ativo)

    @staticmethod
    def _norm(texto: str) -> str:
        base = "".join(
            c
            for c in unicodedata.normalize("NFKD", str(texto or "").lower())
            if not unicodedata.combining(c)
        )
        for ch in ("_", "-", "'", "."):
            base = base.replace(ch, " ")
        return " ".join(base.split())

    @classmethod
    def _construir_mapas(cls):
        if cls._mapa_por_nome is not None and cls._mapa_por_numero is not None:
            return

        mapa_nome: Dict[str, str] = {}
        mapa_numero: Dict[str, str] = {}
        if cls.PASTA_IMAGENS.exists():
            for arq in cls.PASTA_IMAGENS.rglob("*"):
                if not arq.is_file() or arq.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                    continue
                chaves = {cls._norm(arq.stem), cls._norm(arq.name)}
                for chave in chaves:
                    if chave and chave not in mapa_nome:
                        mapa_nome[chave] = str(arq)

                for numero in re.findall(r"\d+", arq.stem):
                    numero_limpo = str(int(numero))
                    mapa_numero.setdefault(numero_limpo, str(arq))
                    mapa_numero.setdefault(numero.zfill(3), str(arq))

        cls._mapa_por_nome = mapa_nome
        cls._mapa_por_numero = mapa_numero

    @staticmethod
    def nome_pokemon(pokemon: object) -> str:
        if isinstance(pokemon, dict):
            for chave in ("Apelido", "apelido", "Nome", "nome", "Especie", "especie", "Pokemon", "pokemon", "Species", "species"):
                valor = pokemon.get(chave)
                if valor:
                    return str(valor)
        return str(pokemon or "Pokémon")

    @staticmethod
    def especie_pokemon(pokemon: object) -> str:
        if isinstance(pokemon, dict):
            for chave in ("Especie", "especie", "Species", "species", "Pokemon", "pokemon", "Nome", "nome"):
                valor = pokemon.get(chave)
                if valor:
                    return str(valor)
        return PokemonInventario.nome_pokemon(pokemon)

    @staticmethod
    def nivel_pokemon(pokemon: object):
        if not isinstance(pokemon, dict):
            return None
        for chave in ("Nivel", "nivel", "Nível", "Level", "level"):
            valor = pokemon.get(chave)
            if valor in (None, ""):
                continue
            try:
                return int(valor)
            except (TypeError, ValueError):
                return valor
        return None

    @staticmethod
    def poder_total(pokemon: object) -> float:
        if not isinstance(pokemon, dict):
            return 0.0
        fonte = pokemon.get('estado') if isinstance(pokemon.get('estado'), dict) else pokemon
        valor = fonte.get('poder')
        if valor in (None, ''):
            valor = fonte.get('Poder')
        if valor in (None, ''):
            valor = fonte.get('poder_relativo')
        if valor in (None, ''):
            valor = fonte.get('PoderRelativo')
        if valor in (None, ''):
            return 0.0
        try:
            return float(valor)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def favorito(pokemon: object) -> bool:
        if not isinstance(pokemon, dict):
            return False
        return bool(pokemon.get('favorito', False))

    @staticmethod
    def pode_subir_nivel(pokemon: object) -> bool:
        if not isinstance(pokemon, dict):
            return False
        fonte = pokemon.get('estado') if isinstance(pokemon.get('estado'), dict) else pokemon
        try:
            xp_atual = int(float(fonte.get('XP', fonte.get('xp', 0)) or 0))
            xp_alvo = int(float(fonte.get('XPAlvo', fonte.get('xp_alvo', 0)) or 0))
            return xp_alvo > 0 and xp_atual >= xp_alvo
        except (TypeError, ValueError):
            return False

    @classmethod
    def normalizar_tipo(cls, tipo: str) -> str:
        return cls._norm(tipo)

    @classmethod
    def tipos_pokemon(cls, pokemon: object) -> list[str]:
        if not isinstance(pokemon, dict):
            return []
        tipos = pokemon.get('tipos')
        if isinstance(tipos, (list, tuple)):
            lista = [cls.normalizar_tipo(str(t)) for t in tipos if str(t).strip()]
        else:
            tipo = pokemon.get('tipo')
            lista = [cls.normalizar_tipo(str(tipo))] if str(tipo or '').strip() else []

        unicos = []
        for tipo in lista:
            if tipo and tipo not in unicos:
                unicos.append(tipo)
        return unicos

    @classmethod
    def icone_tipo(cls, tipo: str, lado_px: int) -> Optional[pygame.Surface]:
        lado_px = int(max(10, lado_px))
        nome = cls.normalizar_tipo(tipo)
        chave = (nome, lado_px)
        if chave in cls._cache_icone_tipo:
            return cls._cache_icone_tipo[chave]
        caminho = Path('Recursos') / 'Visual' / 'Icones' / 'Tipos' / f'{nome}.png'
        surf = None
        if caminho.exists():
            try:
                surf = pygame.image.load(str(caminho)).convert_alpha()
                surf = pygame.transform.smoothscale(surf, (lado_px, lado_px))
            except Exception:
                surf = None
        cls._cache_icone_tipo[chave] = surf
        return surf

    @classmethod
    def _icone_coracao(cls, lado_px: int) -> Optional[pygame.Surface]:
        lado_px = int(max(8, lado_px))
        if lado_px in cls._cache_icone_coracao:
            return cls._cache_icone_coracao[lado_px]
        caminho = Path("Recursos") / "Visual" / "Icones" / "Diversos" / "Coração.png"
        try:
            surf = pygame.image.load(str(caminho)).convert_alpha()
            surf = pygame.transform.smoothscale(surf, (lado_px, lado_px))
        except Exception:
            surf = None
        cls._cache_icone_coracao[lado_px] = surf
        return surf

    @classmethod
    def tipo_principal(cls, pokemon: object) -> str:
        if not isinstance(pokemon, dict):
            return ''
        tipos = cls.tipos_pokemon(pokemon)
        return tipos[0] if tipos else ''

    @classmethod
    def chave_pokemon(cls, pokemon: object) -> str:
        if isinstance(pokemon, dict):
            for chave in ("UID", "uid", "Uuid", "uuid", "IdUnico", "id_unico", "ID", "Id", "id"):
                valor = pokemon.get(chave)
                if valor not in (None, ""):
                    return f"id:{valor}"
            nome = cls.nome_pokemon(pokemon)
            nivel = cls.nivel_pokemon(pokemon)
            numero = pokemon.get("Numero") or pokemon.get("numero") or pokemon.get("Dex") or pokemon.get("dex")
            partes = [cls._norm(nome)]
            if numero not in (None, ""):
                partes.append(str(numero))
            if nivel not in (None, ""):
                partes.append(str(nivel))
            return "nome:" + "|".join(partes)
        return f"obj:{id(pokemon)}"

    @classmethod
    def _path_pokemon(cls, pokemon: object) -> Optional[str]:
        cls._construir_mapas()
        if isinstance(pokemon, dict):
            for chave in ("Icone", "icone", "Sprite", "sprite", "Imagem", "imagem", "Frente", "frente", "CaminhoSprite", "caminho_sprite", "CaminhoIcone", "caminho_icone"):
                valor = pokemon.get(chave)
                if not valor:
                    continue
                caminho = Path(str(valor))
                if caminho.exists():
                    return str(caminho)
                caminho_rel = cls.PASTA_IMAGENS / str(valor)
                if caminho_rel.exists():
                    return str(caminho_rel)

            for chave in ("Numero", "numero", "Dex", "dex"):
                valor = pokemon.get(chave)
                if valor in (None, ""):
                    continue
                numero = str(valor).strip()
                achado = cls._mapa_por_numero.get(numero)
                if achado is None and numero.isdigit():
                    achado = cls._mapa_por_numero.get(str(int(numero)))
                    if achado is None:
                        achado = cls._mapa_por_numero.get(numero.zfill(3))
                if achado:
                    return achado

        nome = cls.especie_pokemon(pokemon)
        if nome:
            return cls._mapa_por_nome.get(cls._norm(nome))
        return None

    @classmethod
    def surface_pokemon(cls, pokemon: object, lado_px: int) -> Optional[pygame.Surface]:
        path = cls._path_pokemon(pokemon)
        if not path:
            return None

        lado_px = int(max(8, lado_px))
        chave = (path, lado_px)
        if chave in cls._cache_surface:
            return cls._cache_surface[chave]

        try:
            surf = pygame.image.load(path).convert_alpha()
            surf = pygame.transform.smoothscale(surf, (lado_px, lado_px))
        except Exception:
            surf = None

        cls._cache_surface[chave] = surf
        return surf

    @classmethod
    def _desenhar_sigla_fallback(cls, tela, pokemon, rect: pygame.Rect):
        fundo = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(fundo, (42, 58, 96, 235), fundo.get_rect(), border_radius=10)
        pygame.draw.rect(fundo, (164, 186, 236), fundo.get_rect(), 2, border_radius=10)
        tela.blit(fundo, rect.topleft)

        nome = cls.nome_pokemon(pokemon)
        sigla = "".join(parte[:1].upper() for parte in nome.split()[:2]) or nome[:2].upper() or "PK"
        txt = Texto(
            sigla[:3],
            style={
                'size': 15,
                'color': (242, 246, 255),
                'align': 'center',
                'outline': True,
                'outline_color': (8, 12, 20),
                'outline_thickness': 2,
            },
        )
        txt.set_pos(rect.center)
        txt.draw(tela)

    @classmethod
    def desenhar_item_no_rect(cls, tela, pokemon, rect: pygame.Rect, escala_sprite: float = 1.0):
        if pokemon is None:
            return

        escala = max(0.1, float(escala_sprite))
        lado_base = min(rect.width, rect.height)
        lado_sprite = max(20, int(lado_base * escala))
        sprite = cls.surface_pokemon(pokemon, lado_px=lado_sprite)
        if sprite is not None:
            tela.blit(sprite, sprite.get_rect(center=rect.center))
        else:
            cls._desenhar_sigla_fallback(tela, pokemon, rect)

        if cls.favorito(pokemon):
            lado_icone = max(12, int(rect.height * 0.22))
            coracao = cls._icone_coracao(lado_icone)
            if coracao is not None:
                tela.blit(coracao, coracao.get_rect(topright=(rect.right - 3, rect.y + 3)))

        if cls.pode_subir_nivel(pokemon):
            marcador = pygame.Rect(rect.x + 4, rect.y + 6, 12, 12)
            pygame.draw.rect(tela, (176, 250, 170), marcador, border_radius=3)
            pygame.draw.rect(tela, (236, 255, 234), marcador, 1, border_radius=3)
            texto_p = Texto(
                "P",
                style={
                    "size": 10,
                    "color": (10, 22, 10),
                    "align": "center",
                    "outline": False,
                    "shadow": False,
                },
            )
            texto_p.set_pos(marcador.center)
            texto_p.draw(tela)

        if cls._mostrar_poder_slots and rect.height >= 54:
            poder = int(round(cls.poder_total(pokemon)))
            fonte_size = max(10, int(rect.height * 0.20))
            txt_poder = Texto(
                str(poder),
                style={
                    "size": fonte_size,
                    "color": (244, 248, 255),
                    "align": "center",
                    "outline": True,
                    "outline_color": (8, 12, 20),
                    "outline_thickness": 2,
                    "shadow": False,
                },
            )
            txt_poder.set_pos((rect.centerx, rect.bottom - max(7, int(rect.height * 0.12))))
            txt_poder.draw(tela)
