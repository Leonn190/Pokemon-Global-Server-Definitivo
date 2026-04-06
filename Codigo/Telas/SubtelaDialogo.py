from __future__ import annotations

import csv
import json
import unicodedata
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pygame

from Codigo.Geradores.Ator import Ator
from Codigo.Modulos.Loja import Loja
from Codigo.Prefabs.Texto import Texto, TextoAnimado


from Codigo.Telas.Subtela import Subtela


class SubtelaDialogo(Subtela):
    usar_overlay_gerenciador = False

    @staticmethod
    def _valor_coluna(row: Dict[str, object], *nomes: str) -> str:
        if not isinstance(row, dict):
            return ""
        for nome in nomes:
            if nome in row:
                return str(row.get(nome) or "").strip()
        alvo = {str(nome or "").strip().lower(): str(nome or "") for nome in nomes}
        for chave, valor in row.items():
            if str(chave or "").strip().lower() in alvo:
                return str(valor or "").strip()
        return ""

    def __init__(
        self,
        player_nome: str,
        player_skin: str,
        npc_payload: Dict[str, object],
        ao_encerrar: Optional[Callable[[], None]] = None,
        ao_iniciar_batalha: Optional[Callable[[Dict[str, object]], None]] = None,
        ao_registrar_ganho: Optional[Callable[[Dict[str, object]], None]] = None,
        ator_local=None,
    ):
        super().__init__()
        self.Ativa = True
        self._ao_encerrar = ao_encerrar
        self._ator_local = ator_local
        self._npc = dict(npc_payload or {})
        estado = self._npc.get("estado") if isinstance(self._npc.get("estado"), dict) else {}
        self._npc_nome = str(self._npc.get("nome") or estado.get("nome") or "NPC")
        self._npc_skin = str(self._npc.get("skin") or estado.get("skin") or "1.png")
        self._npc_id = int(self._npc.get("id", 0) or 0)
        self._npc_code = str(estado.get("npc_code") or "")
        self._npc_estilo = str(estado.get("estilo") or "vendedor").strip().lower()
        self._player_nome = str(player_nome or "Você")
        self._player_skin = str(player_skin or "1.png")
        self._ao_iniciar_batalha = ao_iniciar_batalha
        self._ao_registrar_ganho = ao_registrar_ganho

        self._ator_player = Ator(nome_skin=self._player_skin, posicao=(0.0, 0.0), escala_skin_tiles=1.15, tile_px=64)
        self._ator_npc = Ator(nome_skin=self._npc_skin, posicao=(0.0, 0.0), escala_skin_tiles=1.15, tile_px=64)
        self._ator_player.Desenhador._escala_tiles *= 1.10
        self._ator_npc.Desenhador._escala_tiles *= 1.10
        self._ator_player.Nome = self._player_nome
        self._ator_npc.Nome = self._npc_nome

        self._dialogo = self._carregar_dialogo()
        self._mapa_icones = self._mapear_icones_itens()
        self._npc_tipo_estadio = str(estado.get("estadio_tipo") or "").strip()
        self._loja = Loja(
            npc_nome=self._npc_nome,
            npc_code=self._npc_code,
            npc_estilo=self._npc_estilo,
            ator_local=self._ator_local,
            valor_coluna=self._valor_coluna,
            item_por_nome=self._item_por_nome,
            icone_item=self._icone_item,
            nivel_respeito_estadio=self._nivel_respeito_estadio,
            tipo_estadio_npc=self._npc_tipo_estadio,
            callback_ganho=self._ao_registrar_ganho,
        )

        self._no_atual = str(self._dialogo.get("inicio", ""))
        self._texto_animado = TextoAnimado("", cps=48.0)
        self._opcoes: List[Dict[str, object]] = []
        self._hover_idx = -1
        self._tempo_respiracao = 0.0
        self._cache_tamanho: tuple[int, int] | None = None
        self._overlay: pygame.Surface | None = None
        self._fade_top: pygame.Surface | None = None
        self._fade_bottom: pygame.Surface | None = None
        self._ator_player.definir_angulo_olhar(45.0)
        self._ator_npc.definir_angulo_olhar(135.0)
        self._intro_duracao = 0.72
        self._intro_t = 0.0
        self._intro_finalizada = False
        self._zoom_dialogo = 1.5
        self._reconstruir_no_atual()

    @staticmethod
    def _normalizar_tipo_estadio(valor: str) -> str:
        texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode("ascii")
        texto = texto.strip().lower()
        aliases = {"eletrico": "eletrico", "eletricoo": "eletrico", "terra": "terrestre", "dragao": "dragao"}
        return aliases.get(texto, texto)

    def _nivel_respeito_estadio(self, tipo_estadio: str) -> int:
        ator = self._ator_local
        perfil = getattr(ator, "Perfil", None) if ator is not None else None
        if perfil is None:
            return 0
        tipo = self._normalizar_tipo_estadio(tipo_estadio)
        mapa = {
            "normal": "RespeitoEstadioNormal",
            "fogo": "RespeitoEstadioFogo",
            "agua": "RespeitoEstadioAgua",
            "planta": "RespeitoEstadioPlanta",
            "eletrico": "RespeitoEstadioEletrico",
            "gelo": "RespeitoEstadioGelo",
            "lutador": "RespeitoEstadioLutador",
            "venenoso": "RespeitoEstadioVenenoso",
            "terrestre": "RespeitoEstadioTerrestre",
            "voador": "RespeitoEstadioVoador",
            "psiquico": "RespeitoEstadioPsiquico",
            "inseto": "RespeitoEstadioInseto",
            "pedra": "RespeitoEstadioPedra",
            "fantasma": "RespeitoEstadioFantasma",
            "dragao": "RespeitoEstadioDragao",
            "sombrio": "RespeitoEstadioSombrio",
            "metal": "RespeitoEstadioMetal",
            "fada": "RespeitoEstadioFada",
            "cosmico": "RespeitoEstadioCosmico",
            "sonoro": "RespeitoEstadioSonoro",
        }
        chave = mapa.get(tipo, "")
        valor = int(getattr(perfil, chave, 0) if chave else 0)
        return max(0, min(4, valor))

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
        pasta = "Combatentes" if self._npc_estilo == "combatente" else "Vendedores"
        caminho = Path("Dados") / "InteracoesNPC" / pasta / f"{self._npc_nome}.json"
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
        return self._loja.tipo_loja_no(self._no_atual, no)

    def _reconstruir_no_atual(self) -> None:
        if self._no_atual in {"", "saudacao"}:
            cfg = self._dialogo.get("inicio_por_respeito") if isinstance(self._dialogo.get("inicio_por_respeito"), dict) else {}
            if cfg:
                tipo_estadio = str(cfg.get("tipo_estadio") or "")
                mapa_nos = cfg.get("mapa") if isinstance(cfg.get("mapa"), dict) else {}
                nivel = self._nivel_respeito_estadio(tipo_estadio)
                no_cfg = mapa_nos.get(str(nivel))
                if isinstance(no_cfg, str) and no_cfg:
                    self._no_atual = no_cfg
        no = self._no_atual_obj()
        fala = str(no.get("fala") or "...")
        opcoes = list(no.get("opcoes", [])) if isinstance(no.get("opcoes"), list) else []
        self._texto_animado.set_texto(fala)
        self._opcoes = [o for o in opcoes if isinstance(o, dict)]
        self._hover_idx = -1
        self._loja.limpar_status()
        if self._tipo_loja_atual() in {"padrao", "secreta", "presente"}:
            tela = pygame.display.get_surface()
            self._loja.montar_botoes(self._tipo_loja_atual(), tela.get_size() if tela is not None else (1280, 720))

    def _encerrar(self) -> None:
        self.Ativa = False
        if callable(self._ao_encerrar):
            self._ao_encerrar()

    def _selecionar_opcao(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._opcoes):
            return
        op = self._opcoes[idx]
        prox_presente = op.get("proximo_presente")
        if prox_presente is not None:
            try:
                presente_idx = int(prox_presente)
            except Exception:
                presente_idx = 0
            if presente_idx > 0:
                status = self._loja.status_presente(presente_idx)
                if status == "ja_coletado":
                    prox = str(op.get("proximo_ja_coletado") or "")
                elif status == "sem_respeito":
                    prox = str(op.get("proximo_sem_respeito") or "")
                else:
                    prox = ""
                if prox:
                    self._no_atual = prox
                    self._reconstruir_no_atual()
                    return
                if status in {"ja_coletado", "sem_respeito"}:
                    self._encerrar()
                return
        acao = str(op.get("acao") or "").strip().lower()
        if acao == "batalhar":
            if callable(self._ao_iniciar_batalha):
                self._ao_iniciar_batalha(
                    {
                        "npc_id": int(self._npc_id or 0),
                        "npc_nome": str(self._npc_nome or "NPC"),
                        "npc_code": str(self._npc_code or ""),
                        "npc_estilo": str(self._npc_estilo or "combatente"),
                    }
                )
            self._encerrar()
            return
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
            if not self._intro_finalizada:
                continue
            if self._tipo_loja_atual() in {"padrao", "secreta", "presente"}:
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
        self._overlay.fill((0, 0, 0, 78))

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
            self._intro_t += max(0.0, float(dt))
            if self._intro_t >= self._intro_duracao:
                self._intro_finalizada = True
            if self._intro_finalizada:
                self._texto_animado.atualizar(dt)
            self._tempo_respiracao += max(0.0, float(dt))

    def desenhar(self, tela: pygame.Surface, eventos: Optional[List[pygame.event.Event]] = None, dt: float = 0.0) -> None:
        if not self.Ativa:
            return
        eventos = eventos or []
        w, h = tela.get_size()
        self._garantir_cache_fundos((w, h))
        progresso_intro = max(0.0, min(1.0, self._intro_t / max(0.001, float(self._intro_duracao))))
        zoom = 1.0 + ((self._zoom_dialogo - 1.0) * progresso_intro)
        if zoom > 1.001:
            quadro = tela.copy()
            zw = max(1, int(w * zoom))
            zh = max(1, int(h * zoom))
            # scale padrão reduz custo em diálogo/intro comparado ao smoothscale.
            quadro_zoom = pygame.transform.scale(quadro, (zw, zh))
            tela.blit(quadro_zoom, ((w - zw) // 2, (h - zh) // 2))
        self._overlay.set_alpha(int(78 + (92 * progresso_intro)))
        self._fade_top.set_alpha(int(255 * progresso_intro))
        self._fade_bottom.set_alpha(int(255 * progresso_intro))
        tela.blit(self._overlay, (0, 0))
        tela.blit(self._fade_top, (0, 0))
        tela.blit(self._fade_bottom, (0, h - self._fade_bottom.get_height()))

        self._ator_player.set_tile_px(64)
        self._ator_npc.set_tile_px(64)
        pos_player_x = int((w * 0.12) + ((1.0 - progresso_intro) * (-w * 0.14)))
        pos_npc_x = int((w * 0.88) + ((1.0 - progresso_intro) * (w * 0.14)))
        self._ator_player.desenhar(tela, posicao_tela=(pos_player_x, int(h * 0.87)), respiracao_tempo=self._tempo_respiracao)
        self._ator_npc.desenhar(tela, posicao_tela=(pos_npc_x, int(h * 0.87)), respiracao_tempo=self._tempo_respiracao)
        Texto(self._player_nome, pos=(pos_player_x, int(h * 0.92)), style={"size": 22, "align": "midbottom", "outline": True}).draw(tela)
        Texto(self._npc_nome, pos=(pos_npc_x, int(h * 0.92)), style={"size": 22, "align": "midbottom", "outline": True}).draw(tela)

        Texto(self._texto_animado.texto_visivel, pos=(int(w * 0.10), int(h * 0.61)), style={"size": 24, "align": "topleft", "outline": True}).draw(tela)

        if self._texto_animado.concluido and self._tipo_loja_atual() in {"padrao", "secreta", "presente"}:
            self._loja.renderizar(tela, eventos, dt, self._tipo_loja_atual(), fechar_callback=self._encerrar)
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
