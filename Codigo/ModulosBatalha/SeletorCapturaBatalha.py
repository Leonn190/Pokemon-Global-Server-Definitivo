from __future__ import annotations

import unicodedata

import pygame

from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Prefabs.Texto import Texto


BOLAS_CONHECIDAS = {
    "pokeball",
    "greatball",
    "ultraball",
    "masterball",
    "levelball",
    "furyball",
    "heavyball",
    "aquaball",
    "attemptball",
    "premierball",
    "candyball",
    "loveball",
    "secretball",
    "fastball",
    "fruitball",
    "tallball",
    "sniperball",
    "beastball",
}


def _normalizar(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _qtd(item: dict) -> int:
    try:
        return max(0, int(float((item or {}).get("quantidade", 1) or 1)))
    except (TypeError, ValueError):
        return 1


class SeletorCapturaBatalha:
    def __init__(self, controlador) -> None:
        self.controlador = controlador
        self.slots: list[dict[str, object]] = []
        self.rects: list[pygame.Rect] = []
        self.arraste: dict[str, object] | None = None
        self.retorno: dict[str, object] | None = None
        self._txt_qtd = Texto("", style={"size": 13, "align": "bottomright", "outline": True, "outline_thickness": 2, "shadow": False, "color": (255, 255, 255)})
        self._txt_nome = Texto("", style={"size": 11, "align": "center", "outline": True, "outline_thickness": 2, "shadow": False, "color": (240, 244, 255)})

    def ativo(self) -> bool:
        tipo = str(getattr(self.controlador, "tipo_batalha", "") or "").strip().lower()
        return tipo == "confronto" and not bool(getattr(self.controlador, "modo_teste", False))

    def atualizar_slots(self) -> None:
        self.slots = self._coletar_slots() if self.ativo() else []

    def _coletar_slots(self) -> list[dict[str, object]]:
        ator = self.controlador.ator_local() if hasattr(self.controlador, "ator_local") else None
        inventario = getattr(ator, "Inventario", None)
        itens = list(getattr(inventario, "Itens", []) or [])
        agrupados: dict[str, dict[str, object]] = {}
        for indice, item in enumerate(itens):
            if not isinstance(item, dict):
                continue
            nome = str(item.get("Nome") or item.get("nome") or item.get("item_nome") or "").strip()
            code = str(item.get("Code") or item.get("code") or item.get("item_base_id") or "").strip()
            estilo = str(item.get("Estilo") or item.get("estilo") or "").strip().lower()
            nome_norm = _normalizar(nome)
            code_norm = _normalizar(code)
            if estilo != "bola" and nome_norm not in BOLAS_CONHECIDAS and code_norm not in BOLAS_CONHECIDAS:
                continue
            chave = code_norm or nome_norm
            if not chave:
                continue
            atual = agrupados.get(chave)
            if atual is None:
                base = dict(item)
                base["quantidade"] = 0
                atual = {
                    "chave": chave,
                    "nome_norm": nome_norm,
                    "item": base,
                    "quantidade": 0,
                    "primeiro_indice": int(indice),
                    "item_base_id": code,
                    "item_nome": nome,
                }
                agrupados[chave] = atual
            atual["quantidade"] = int(atual.get("quantidade", 0) or 0) + _qtd(item)
            if int(indice) < int(atual.get("primeiro_indice", indice) or indice):
                atual["primeiro_indice"] = int(indice)
        saida = []
        for slot in agrupados.values():
            if int(slot.get("quantidade", 0) or 0) <= 0:
                continue
            item = dict(slot.get("item") or {})
            item["quantidade"] = int(slot.get("quantidade", 0) or 0)
            slot["item"] = item
            saida.append(slot)
        saida.sort(key=lambda s: (0 if _normalizar(s.get("item_nome") or (s.get("item") or {}).get("Nome")) == "premierball" else 1, -int(s.get("quantidade", 0) or 0), int(s.get("primeiro_indice", 9999) or 9999)))
        return saida[:3]

    def layout(self, botao_pronto: pygame.Rect, tela: pygame.Surface) -> list[pygame.Rect]:
        self.atualizar_slots()
        if not self.slots:
            self.rects = []
            return []
        lado = int(botao_pronto.height)
        gap = max(12, int(lado * 0.14))
        margem = 12
        total = len(self.slots) * lado + max(0, len(self.slots) - 1) * gap
        x0 = botao_pronto.left - gap - total
        if x0 < margem:
            lado = max(34, min(lado, int((botao_pronto.left - gap - margem - (len(self.slots) - 1) * gap) / max(1, len(self.slots)))))
            total = len(self.slots) * lado + max(0, len(self.slots) - 1) * gap
            x0 = max(margem, botao_pronto.left - gap - total)
        y = botao_pronto.y + (botao_pronto.height - lado) // 2
        self.rects = [pygame.Rect(x0 + i * (lado + gap), y, lado, lado) for i in range(len(self.slots))]
        return [pygame.Rect(r) for r in self.rects]

    def iniciar_arraste(self, pos_mouse) -> bool:
        if not self.ativo():
            return False
        self.atualizar_slots()
        for indice, rect in enumerate(self.rects):
            if rect.collidepoint(pos_mouse) and indice < len(self.slots):
                self.arraste = {"slot": dict(self.slots[indice]), "origem_rect": pygame.Rect(rect), "pos": tuple(pos_mouse)}
                self.retorno = None
                return True
        return False

    def atualizar_arraste(self, pos_mouse) -> None:
        if self.arraste is not None:
            self.arraste["pos"] = tuple(pos_mouse)
        if self.retorno is not None:
            self.retorno["t"] = min(1.0, float(self.retorno.get("t", 0.0)) + 0.18)
            if float(self.retorno.get("t", 0.0)) >= 1.0:
                self.retorno = None

    def finalizar_arraste(self, pos_mouse) -> bool:
        if self.arraste is None:
            return False
        slot = dict(self.arraste.get("slot") or {})
        origem = pygame.Rect(self.arraste.get("origem_rect") or pygame.Rect(0, 0, 0, 0))
        self.arraste = None
        alvo = self._pokemon_alvo_valido(pos_mouse)
        montador = getattr(self.controlador, "montador_jogadas", None)
        if alvo is not None and montador is not None and montador.preparar_captura(alvo, slot):
            return True
        self.retorno = {"slot": slot, "origem_rect": origem, "pos": tuple(pos_mouse), "t": 0.0}
        return False

    def consumiu_ponto(self, pos_mouse) -> bool:
        if self.arraste is not None:
            return True
        return any(rect.collidepoint(pos_mouse) for rect in self.rects)

    def _pokemon_alvo_valido(self, pos_mouse):
        area_id = self.controlador.arena.area_em_posicao_mouse(pos_mouse, self.controlador.camera) if getattr(self.controlador, "arena", None) is not None else None
        if area_id:
            pokemon = self.controlador.arena.pokemon_na_area(area_id)
            if self._pokemon_valido(pokemon, exigir_rect=False):
                return pokemon
        for pokemon in reversed(list(getattr(self.controlador, "pokemons", []) or [])):
            if not self._pokemon_valido(pokemon):
                continue
            try:
                if pokemon.contem_ponto(pos_mouse):
                    return pokemon
            except Exception:
                continue
        return None

    def _pokemon_valido(self, pokemon, exigir_rect: bool = True) -> bool:
        if pokemon is None:
            return False
        if int(getattr(pokemon, "lado_id", -1)) == int(getattr(self.controlador, "lado_jogador", -2)):
            return False
        if not self.controlador.pokemon_visivel(pokemon):
            return False
        if not pokemon.esta_vivo() or not pokemon.esta_ativo() or pokemon.esta_na_reserva():
            return False
        if not bool(exigir_rect):
            return True
        rect = getattr(pokemon, "RectAtual", None)
        return isinstance(rect, pygame.Rect) and rect.width > 0 and rect.height > 0

    def desenhar(self, tela: pygame.Surface) -> None:
        if not self.ativo():
            return
        self.atualizar_slots()
        for indice, slot in enumerate(self.slots):
            if indice >= len(self.rects):
                continue
            rect = self.rects[indice]
            alpha = 115 if self.arraste is not None and (self.arraste.get("slot") or {}).get("chave") == slot.get("chave") else 230
            self._desenhar_slot(tela, rect, slot, alpha=alpha)
        if self.retorno is not None:
            self._desenhar_icone_flutuante(tela, self.retorno.get("slot"), self._pos_retorno())
        if self.arraste is not None:
            self._desenhar_icone_flutuante(tela, self.arraste.get("slot"), self.arraste.get("pos"))

    def _desenhar_slot(self, tela, rect, slot, alpha=230) -> None:
        camada = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(camada, (18, 24, 38, alpha), camada.get_rect(), border_radius=10)
        pygame.draw.rect(camada, (236, 242, 255, min(255, alpha + 15)), camada.get_rect(), 2, border_radius=10)
        tela.blit(camada, rect.topleft)
        item = dict(slot.get("item") or {})
        sprite = ItemInventario.surface_item(item, max(20, rect.width - 14))
        if sprite is not None:
            tela.blit(sprite, sprite.get_rect(center=rect.center))
        else:
            self._txt_nome.set_text(str(item.get("Nome") or item.get("nome") or "Ball")[:8])
            self._txt_nome.set_pos(rect.center)
            self._txt_nome.draw(tela)
        self._txt_qtd.set_text(str(int(slot.get("quantidade", 0) or 0)))
        self._txt_qtd.set_pos((rect.right - 4, rect.bottom - 3))
        self._txt_qtd.draw(tela)

    def _desenhar_icone_flutuante(self, tela, slot, pos) -> None:
        if not pos:
            return
        item = dict((slot or {}).get("item") or {})
        lado = max(34, self.rects[0].width if self.rects else 48)
        sprite = ItemInventario.surface_item(item, lado)
        if sprite is not None:
            tela.blit(sprite, sprite.get_rect(center=(int(pos[0]), int(pos[1]))))
            return
        pygame.draw.circle(tela, (236, 244, 255), (int(pos[0]), int(pos[1])), lado // 2)
        pygame.draw.circle(tela, (48, 58, 82), (int(pos[0]), int(pos[1])), lado // 2, 2)

    def _pos_retorno(self):
        if self.retorno is None:
            return None
        t = max(0.0, min(1.0, float(self.retorno.get("t", 0.0))))
        pos = self.retorno.get("pos") or (0, 0)
        rect = pygame.Rect(self.retorno.get("origem_rect") or pygame.Rect(0, 0, 0, 0))
        suave = t * t * (3 - 2 * t)
        return (float(pos[0]) + (rect.centerx - float(pos[0])) * suave, float(pos[1]) + (rect.centery - float(pos[1])) * suave)
