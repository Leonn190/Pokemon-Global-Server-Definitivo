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
        valor = pokemon.get('total')
        if valor in (None, ''):
            return 0.0
        try:
            return float(valor)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def tipo_principal(cls, pokemon: object) -> str:
        if not isinstance(pokemon, dict):
            return ''

        tipos = pokemon.get('Tipos')
        if isinstance(tipos, (list, tuple)) and tipos:
            return str(tipos[0] or '')

        tipo = pokemon.get('Tipo')
        if tipo not in (None, ''):
            return str(tipo)

        return ''

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

        nome = cls.nome_pokemon(pokemon)
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
    def _desenhar_nivel(cls, tela, pokemon, rect: pygame.Rect):
        nivel = cls.nivel_pokemon(pokemon)
        if nivel in (None, ""):
            return

        txt_nivel = Texto(
            f"Lv {nivel}",
            style={
                'size': 11,
                'color': (255, 255, 255),
                'align': 'midright',
                'outline': True,
                'outline_color': (8, 12, 20),
                'outline_thickness': 2,
            },
        )
        txt_nivel.set_pos((rect.right - 3, rect.bottom - 7))
        txt_nivel.draw(tela)

    @classmethod
    def desenhar_item_no_rect(cls, tela, pokemon, rect: pygame.Rect):
        if pokemon is None:
            return

        sprite = cls.surface_pokemon(pokemon, lado_px=max(20, rect.width - 10))
        if sprite is not None:
            tela.blit(sprite, sprite.get_rect(center=rect.center))
        else:
            cls._desenhar_sigla_fallback(tela, pokemon, rect)

        cls._desenhar_nivel(tela, pokemon, rect)
