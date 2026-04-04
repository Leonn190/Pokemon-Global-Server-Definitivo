from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Paineis.FichaItem import FichaItem
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto, TextoAnimado


class TelaDialogo:
    def __init__(
        self,
        player_nome: str,
        player_skin: str,
        npc_payload: Dict[str, object],
        ao_encerrar: Optional[Callable[[], None]] = None,
        ator_local=None,
    ):
        self.Ativa = True
        self._ao_encerrar = ao_encerrar
        self._ator_local = ator_local
        self._npc = dict(npc_payload or {})
        estado = self._npc.get("estado") if isinstance(self._npc.get("estado"), dict) else {}
        self._npc_nome = str(self._npc.get("nome") or estado.get("nome") or "NPC")
        self._npc_skin = str(self._npc.get("skin") or estado.get("skin") or "1.png")
        self._npc_id = int(self._npc.get("id", 0) or 0)
        self._npc_code = str(estado.get("npc_code") or "")
        self._player_nome = str(player_nome or "Você")
        self._player_skin = str(player_skin or "1.png")

        self._ator_player = Ator(nome_skin=self._player_skin, posicao=(0.0, 0.0), escala_skin_tiles=1.15, tile_px=64)
        self._ator_npc = Ator(nome_skin=self._npc_skin, posicao=(0.0, 0.0), escala_skin_tiles=1.15, tile_px=64)
        self._ator_player.Nome = self._player_nome
        self._ator_npc.Nome = self._npc_nome

        self._dialogo = self._carregar_dialogo()
        self._catalogo = self._carregar_catalogo_vendedor()
        self._mapa_icones = self._mapear_icones_itens()

        self._no_atual = str(self._dialogo.get("inicio", ""))
        self._texto_animado = TextoAnimado("", cps=48.0)
        self._opcoes: List[Dict[str, object]] = []
        self._botoes_loja: list[dict] = []
        self._tamanho_loja_montado: tuple[int, int] | None = None
        self._status_compra = ""
        self._ficha_item_tooltip = FichaItem()
        self._hover_idx = -1
        self._tempo_respiracao = 0.0
        self._cache_tamanho: tuple[int, int] | None = None
        self._overlay: pygame.Surface | None = None
        self._fade_top: pygame.Surface | None = None
        self._fade_bottom: pygame.Surface | None = None
        self._ator_player.definir_angulo_olhar(45.0)
        self._ator_npc.definir_angulo_olhar(135.0)
        self._reconstruir_no_atual()

    @staticmethod
    def _mapear_icones_itens() -> dict[str, Path]:
        base = Path("Recursos") / "Visual" / "Itens"
        mapa: dict[str, Path] = {}
        if not base.exists():
            return mapa
        for arquivo in base.rglob("*.png"):
            mapa[arquivo.stem.strip().lower()] = arquivo
        return mapa

    def _icone_item(self, nome_item: str) -> pygame.Surface | None:
        caminho = self._mapa_icones.get(str(nome_item or "").strip().lower())
        if caminho is None or not caminho.exists():
            return None
        try:
            return pygame.transform.smoothscale(pygame.image.load(str(caminho)).convert_alpha(), (36, 36))
        except pygame.error:
            return None

    def _carregar_catalogo_vendedor(self) -> Dict[str, object]:
        arquivo = Path("Dados") / "Pokemon Global Server - NPC Vendedor.csv"
        if not arquivo.exists():
            return {"padrao": [], "secreta": None}
        with arquivo.open("r", encoding="utf-8") as f:
            for idx, row in enumerate(csv.DictReader(f), start=1):
                code = str(row.get("Code") or idx).strip() or str(idx)
                nome = str(row.get("Nome") or "").strip().lower()
                if code != self._npc_code and nome != self._npc_nome.lower():
                    continue
                padrao = []
                for i in range(1, 6):
                    item_nome = str(row.get(f"Item {i}") or "").strip()
                    preco_raw = str(row.get(f"Preço {i}") or "0").strip()
                    if not item_nome:
                        continue
                    try:
                        preco = int(float(preco_raw or 0))
                    except Exception:
                        preco = 0
                    padrao.append({"item_nome": item_nome, "preco": max(0, preco)})
                item_s = str(row.get("Item S") or "").strip()
                preco_s = str(row.get("Preço S") or "0").strip()
                secreta = None
                if item_s:
                    try:
                        preco_item_s = int(float(preco_s or 0))
                    except Exception:
                        preco_item_s = 0
                    secreta = {"item_nome": item_s, "preco": max(0, preco_item_s)}
                return {"padrao": padrao, "secreta": secreta}
        return {"padrao": [], "secreta": None}

    @staticmethod
    def _item_por_nome(nome_item: str) -> Dict[str, object]:
        arquivo = Path("Dados") / "Pokemon Global Server - Itens.csv"
        if not arquivo.exists():
            return {"Code": "", "Nome": str(nome_item), "quantidade": 1}
        with arquivo.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                nome = str(row.get("Nome") or "").strip()
                if nome.lower() != str(nome_item or "").strip().lower():
                    continue
                item = dict(row)
                item["Nome"] = nome
                item["Code"] = str(row.get("Code") or "").strip()
                item["quantidade"] = 1
                return item
        return {"Code": "", "Nome": str(nome_item), "quantidade": 1}

    def _carregar_dialogo(self) -> Dict[str, object]:
        caminho = Path("Codigo") / "InteracaoNPC" / f"{self._npc_nome}.json"
        if not caminho.exists():
            return {
                "inicio": "fallback",
                "nos": {
                    "fallback": {
                        "fala": f"Olá, eu sou {self._npc_nome}. Ainda estou sem falas configuradas.",
                        "opcoes": [{"texto": "Tudo bem, até depois.", "fim": True}],
                    }
                },
            }
        try:
            with caminho.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {"inicio": "fallback", "nos": {"fallback": {"fala": "Tive um problema para abrir meu diálogo.", "opcoes": [{"texto": "Fechar", "fim": True}]}}}

    def _no_atual_obj(self) -> Dict[str, object]:
        nos = self._dialogo.get("nos") if isinstance(self._dialogo.get("nos"), dict) else {}
        return nos.get(self._no_atual, {}) if isinstance(nos.get(self._no_atual, {}), dict) else {}

    def _tipo_loja_atual(self) -> str:
        no = self._no_atual_obj()
        loja = str(no.get("loja") or "").strip().lower()
        if loja in {"padrao", "secreta"}:
            return loja
        if self._no_atual == "loja_secreta":
            return "secreta"
        if self._no_atual == "loja_padrao":
            return "padrao"
        return ""

    def _montar_botoes_loja(self, tela_size: tuple[int, int]) -> None:
        tipo = self._tipo_loja_atual()
        self._botoes_loja = []
        self._tamanho_loja_montado = tela_size
        if tipo not in {"padrao", "secreta"}:
            return

        ofertas = []
        if tipo == "padrao":
                ofertas = [o for o in list(self._catalogo.get("padrao") or []) if isinstance(o, dict)]
        else:
            secreta = self._catalogo.get("secreta") if isinstance(self._catalogo.get("secreta"), dict) else None
            if secreta:
                ofertas = [dict(secreta)]

        w, h = tela_size
        cols = 5
        gap = 16
        lado = max(72, min(110, int(w * 0.07)))
        total_w = (cols * lado) + ((cols - 1) * gap)
        base_x = int((w - total_w) * 0.5)
        base_y = int(h * 0.74)

        for i, oferta in enumerate(ofertas):
            c = i % cols
            rect = pygame.Rect(base_x + c * (lado + gap), base_y, lado, lado)
            nome_item = str(oferta.get("item_nome") or "")
            item = self._item_por_nome(nome_item)

            def _comprar(_jogo, _botao, item_payload=dict(item), preco=int(oferta.get("preco", 0) or 0)):
                self._acao_compra_local(item_payload, preco)

            botao = Botao(
                rect,
                "",
                execute=_comprar,
                style={
                    "radius": 12,
                    "border_width": 2,
                    "bg": (35, 52, 82),
                    "bg_hover": (51, 74, 112),
                    "bg_pressed": (25, 39, 62),
                    "border": (112, 138, 182),
                    "border_hover": (201, 224, 255),
                    "text_style": {"size": 1, "outline_thickness": 0, "shadow": False, "align": "center"},
                },
            )
            botao.set_tooltip(str(item.get("Nome") or "Item"), style={"size": 16})
            self._botoes_loja.append(
                {
                    "botao": botao,
                    "item": item,
                    "preco": int(oferta.get("preco", 0) or 0),
                    "icone": self._icone_item(item.get("Nome", "")),
                }
            )

        fechar = Botao(
            pygame.Rect(int((w - 220) * 0.5), base_y + lado + 52, 220, 48),
            "Fechar conversa",
            execute=lambda _jogo, _botao: self._encerrar(),
            style={"radius": 12, "text_style": {"size": 18, "outline_thickness": 1, "shadow": False}},
        )
        self._botoes_loja.append({"botao": fechar, "item": None, "preco": None, "icone": None})

    def _acao_compra_local(self, item_payload: Dict[str, object], preco: int) -> None:
        ator = self._ator_local
        perfil = getattr(ator, "Perfil", None)
        inventario = getattr(ator, "Inventario", None)
        if perfil is None or inventario is None:
            self._status_compra = "Falha: perfil ou inventário indisponível"
            return
        saldo = int(getattr(perfil, "Dinheiro", 0) or 0)
        if saldo < int(preco):
            self._status_compra = "Dinheiro insuficiente"
            return
        item = dict(item_payload or {})
        item["quantidade"] = 1
        if not inventario.adicionar_item(item):
            self._status_compra = "Inventário sem espaço"
            return
        perfil.Dinheiro = max(0, saldo - int(preco))
        self._status_compra = f"Comprou {item.get('Nome', 'item')} por {int(preco)} dinheiro"

    def _reconstruir_no_atual(self) -> None:
        no = self._no_atual_obj()
        fala = str(no.get("fala") or "...")
        opcoes = list(no.get("opcoes", [])) if isinstance(no.get("opcoes"), list) else []
        self._texto_animado.set_texto(fala)
        self._opcoes = [o for o in opcoes if isinstance(o, dict)]
        self._hover_idx = -1
        self._status_compra = ""
        if self._tipo_loja_atual() in {"padrao", "secreta"}:
            tela = pygame.display.get_surface()
            self._montar_botoes_loja(tela.get_size() if tela is not None else (1280, 720))
        else:
            self._botoes_loja = []
            self._tamanho_loja_montado = None

    def _encerrar(self) -> None:
        self.Ativa = False
        if callable(self._ao_encerrar):
            self._ao_encerrar()

    def _selecionar_opcao(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._opcoes):
            return
        op = self._opcoes[idx]
        if bool(op.get("fim", False)):
            self._encerrar()
            return
        prox = str(op.get("proximo") or "")
        if not prox:
            self._encerrar()
            return
        self._no_atual = prox
        self._reconstruir_no_atual()

    def processar_eventos(self, eventos: List[pygame.event.Event]) -> bool:
        if not self.Ativa:
            return False
        for ev in eventos:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self._encerrar()
                return True
            if self._tipo_loja_atual() in {"padrao", "secreta"}:
                continue
            if ev.type == pygame.MOUSEMOTION:
                self._hover_idx = self._opcao_no_mouse(ev.pos)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if not self._texto_animado.concluido:
                    self._texto_animado.pular_animacao()
                else:
                    idx = self._opcao_no_mouse(ev.pos)
                    if idx >= 0:
                        self._selecionar_opcao(idx)
                return True
        return True

    def _opcao_rects(self, tela_size) -> List[pygame.Rect]:
        w, h = tela_size
        base_x = int(w * 0.20)
        base_y = int(h * 0.75)
        bw = int(w * 0.60)
        bh = 44
        gap = 8
        return [pygame.Rect(base_x, base_y + i * (bh + gap), bw, bh) for i in range(len(self._opcoes))]

    def _garantir_cache_fundos(self, tela_size: tuple[int, int]) -> None:
        if self._cache_tamanho == tela_size:
            return
        w, h = tela_size
        self._cache_tamanho = tela_size
        self._overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 130))

        self._fade_top = pygame.Surface((w, int(h * 0.42)), pygame.SRCALPHA)
        for y in range(self._fade_top.get_height()):
            t = y / max(1, self._fade_top.get_height() - 1)
            alpha = int(255 * (1.0 - t) ** 1.95)
            pygame.draw.line(self._fade_top, (0, 0, 0, alpha), (0, y), (w, y))

        self._fade_bottom = pygame.Surface((w, int(h * 0.58)), pygame.SRCALPHA)
        for y in range(self._fade_bottom.get_height()):
            t = y / max(1, self._fade_bottom.get_height() - 1)
            alpha = int(248 * (t ** 1.75))
            pygame.draw.line(self._fade_bottom, (0, 0, 0, alpha), (0, y), (w, y))

    def _opcao_no_mouse(self, mouse_pos) -> int:
        for i, r in enumerate(self._opcao_rects(pygame.display.get_surface().get_size() if pygame.display.get_surface() else (1280, 720))):
            if r.collidepoint(mouse_pos):
                return i
        return -1

    def atualizar(self, dt: float) -> None:
        if self.Ativa:
            self._texto_animado.atualizar(dt)
            self._tempo_respiracao += max(0.0, float(dt))

    def desenhar(self, tela: pygame.Surface, eventos: Optional[List[pygame.event.Event]] = None, dt: float = 0.0) -> None:
        if not self.Ativa:
            return
        eventos = eventos or []
        w, h = tela.get_size()
        self._garantir_cache_fundos((w, h))
        tela.blit(self._overlay, (0, 0))
        tela.blit(self._fade_top, (0, 0))
        tela.blit(self._fade_bottom, (0, h - self._fade_bottom.get_height()))

        self._ator_player.set_tile_px(64)
        self._ator_npc.set_tile_px(64)
        self._ator_player.desenhar(tela, posicao_tela=(int(w * 0.12), int(h * 0.87)), respiracao_tempo=self._tempo_respiracao)
        self._ator_npc.desenhar(tela, posicao_tela=(int(w * 0.88), int(h * 0.87)), respiracao_tempo=self._tempo_respiracao)
        Texto(self._player_nome, pos=(int(w * 0.12), int(h * 0.92)), style={"size": 22, "align": "midbottom", "outline": True}).draw(tela)
        Texto(self._npc_nome, pos=(int(w * 0.88), int(h * 0.92)), style={"size": 22, "align": "midbottom", "outline": True}).draw(tela)

        Texto(self._texto_animado.texto_visivel, pos=(int(w * 0.10), int(h * 0.61)), style={"size": 24, "align": "topleft", "outline": True}).draw(tela)

        if self._texto_animado.concluido and self._tipo_loja_atual() in {"padrao", "secreta"}:
            if self._tamanho_loja_montado != (w, h):
                self._montar_botoes_loja((w, h))
            hover_entrada = None
            for entrada in self._botoes_loja:
                botao = entrada.get("botao")
                if not isinstance(botao, Botao):
                    continue
                botao.render(tela, eventos, dt, None)
                icone = entrada.get("icone")
                if icone is not None:
                    rect = icone.get_rect(center=botao.rect.center)
                    tela.blit(icone, rect)
                preco = entrada.get("preco")
                if isinstance(preco, int):
                    Texto(f"{preco} dinheiro", pos=(botao.rect.centerx, botao.rect.bottom + 8), style={"size": 18, "align": "midtop", "outline": True, "color": (255, 223, 120)}).draw(tela)
                if bool(getattr(botao, "hover", False)) and isinstance(entrada.get("item"), dict):
                    hover_entrada = entrada
            if hover_entrada is not None:
                botao = hover_entrada.get("botao")
                if isinstance(botao, Botao):
                    largura_ficha = max(280, int(w * 0.24))
                    ficha_rect = pygame.Rect(0, 0, largura_ficha, 72)
                    ficha_rect.midbottom = (botao.rect.centerx, botao.rect.top - 8)
                    ficha_rect.clamp_ip(pygame.Rect(8, 8, w - 16, h - 16))
                    pygame.draw.rect(tela, (11, 17, 28), ficha_rect, border_radius=12)
                    pygame.draw.rect(tela, (103, 138, 198), ficha_rect, 2, border_radius=12)
                    self._ficha_item_tooltip.renderizar(tela, ficha_rect.inflate(-8, -8), hover_entrada.get("item"))
            if self._status_compra:
                Texto(self._status_compra, pos=(int(w * 0.5), int(h * 0.90)), style={"size": 18, "align": "midbottom", "outline": True, "color": (220, 235, 255)}).draw(tela)
            return

        if self._texto_animado.concluido:
            self._hover_idx = self._opcao_no_mouse(pygame.mouse.get_pos())
            for i, (op, rect) in enumerate(zip(self._opcoes, self._opcao_rects((w, h)))):
                hover = i == self._hover_idx
                tamanho = 24 if hover else 22
                cor = (255, 241, 156) if hover else (228, 235, 248)
                desloc_x = 4 if hover else 0
                Texto(str(op.get("texto") or "..."), pos=(rect.x + 6 + desloc_x, rect.centery), style={"size": tamanho, "align": "midleft", "outline": True, "color": cor}).draw(tela)
        else:
            Texto("(clique para concluir o texto)", pos=(int(w * 0.5), int(h * 0.88)), style={"size": 18, "align": "midbottom", "outline": True, "color": (220, 220, 230)}).draw(tela)
