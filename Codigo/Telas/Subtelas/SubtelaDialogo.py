from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pygame

from Codigo.ModulosGerais.LoaderTabelas import carregar_csv_dict

from Codigo.Geradores.Ator import Ator
from Codigo.ModulosMundo.LeitorDialogo import LeitorDialogo
from Codigo.ModulosMundo.Loja import Loja
from Codigo.Prefabs.Texto import Texto, TextoAnimado
from Codigo.Telas.Subtelas.Subtela import Subtela


class SubtelaDialogo(Subtela):
    usar_overlay_gerenciador = False
    camada_render = "scene"

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
        self._ao_iniciar_batalha = ao_iniciar_batalha
        self._ao_registrar_ganho = ao_registrar_ganho
        self._ator_local = ator_local

        if self._ator_local is not None and not isinstance(getattr(self._ator_local, "SetorDialogo", None), dict):
            self._ator_local.SetorDialogo = {}

        self._npc = dict(npc_payload or {})
        estado = self._npc.get("estado") if isinstance(self._npc.get("estado"), dict) else {}
        self._npc_nome = str(self._npc.get("nome") or estado.get("nome") or "NPC")
        self._npc_skin = str(self._npc.get("skin") or estado.get("skin") or "1.png")
        self._npc_id = int(self._npc.get("id", 0) or 0)
        self._npc_code = str(estado.get("npc_code") or self._npc.get("code") or self._npc_id or self._npc_nome)
        self._npc_tipo_estadio = str(estado.get("estadio_tipo") or estado.get("estadio") or self._npc.get("estadio_tipo") or self._npc.get("estadio") or "").strip()
        self._npc_cargo = self._inferir_cargo_npc(estado)

        self._player_nome = str(player_nome or "Você")
        self._player_skin = str(player_skin or "1.png")

        self._ator_player = Ator(nome_skin=self._player_skin, posicao=(0.0, 0.0), escala_skin_tiles=1.15, tile_px=64)
        self._ator_npc = Ator(nome_skin=self._npc_skin, posicao=(0.0, 0.0), escala_skin_tiles=1.15, tile_px=64)
        self._ator_player.Desenhador._escala_tiles *= 1.10
        self._ator_npc.Desenhador._escala_tiles *= 1.10
        self._ator_player.Nome = self._player_nome
        self._ator_npc.Nome = self._npc_nome

        self._mapa_icones = self._mapear_icones_itens()
        self._loja = Loja(
            npc_nome=self._npc_nome,
            npc_code=self._npc_code,
            npc_estilo="vendedor" if self._npc_cargo == "vendedor" else "combatente",
            ator_local=self._ator_local,
            valor_coluna=self._valor_coluna,
            item_por_nome=self._item_por_nome,
            icone_item=self._icone_item,
            nivel_respeito_estadio=self._nivel_respeito_estadio,
            tipo_estadio_npc=self._npc_tipo_estadio,
            callback_ganho=self._ao_registrar_ganho,
            catalogo_estado=estado.get("loja") if isinstance(estado.get("loja"), dict) else None,
        )

        self._leitor = LeitorDialogo(
            self._carregar_dialogo(),
            ator_local=self._ator_local,
            npc_payload={
                **self._npc,
                "estado": {
                    **estado,
                    "cargo": self._npc_cargo,
                    "npc_code": self._npc_code,
                    "estadio_tipo": self._npc_tipo_estadio,
                },
            },
        )

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
        self._encerrando = False
        self._outro_t = 0.0
        self._outro_duracao = 0.36
        self._acao_pos_outro: Optional[Callable[[], None]] = None
        self._fundo_zoom_cache: pygame.Surface | None = None
        self._fundo_zoom_cache_tamanho: tuple[int, int] | None = None
        self._sincronizar_com_leitor()

    def _inferir_cargo_npc(self, estado: Dict[str, object]) -> str:
        bruto = (
            estado.get("cargo")
            or self._npc.get("cargo")
            or estado.get("categoria")
            or self._npc.get("categoria")
            or estado.get("papel")
            or self._npc.get("papel")
            or ""
        )
        texto = str(bruto or "").strip()
        if texto:
            return LeitorDialogo.normalizar_cargo(texto)
        estilo = str(estado.get("estilo") or self._npc.get("estilo") or "").strip().lower()
        return "vendedor" if estilo == "vendedor" else "dissociado"

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
        try:
            linhas = carregar_csv_dict("Pokemon Global Server - Itens.csv", encoding="utf-8")
        except OSError:
            return {"Code": "", "Nome": str(nome_item), "quantidade": 1}
        for row in linhas:
                nome = str(row.get("Nome") or "").strip()
                if nome.lower() != str(nome_item or "").strip().lower():
                    continue
                item = dict(row)
                item["Nome"] = nome
                item["Code"] = str(row.get("Code") or "").strip()
                item["quantidade"] = 1
                return item
        return {"Code": "", "Nome": str(nome_item), "quantidade": 1}

    def _nivel_respeito_estadio(self, tipo_estadio: str) -> int:
        return self._leitor.nivel_respeito_estadio(tipo_estadio)

    def _pastas_dialogo(self) -> List[str]:
        mapa = {
            "vendedor": ["Vendedor", "Vendedores"],
            "dissociado": ["Dissociado", "Dissociados"],
            "lider": ["Lider", "Lideres"],
            "capitao": ["Capitao", "Capitão", "Capitaes"],
            "desafiante": ["Desafiante", "Desafiantes"],
        }
        return mapa.get(self._npc_cargo, ["Vendedor"])

    def _caminhos_dialogo_possiveis(self) -> List[Path]:
        nome = self._npc_nome.strip()
        candidatos: List[Path] = []
        for pasta in self._pastas_dialogo():
            candidatos.append(Path("Dados") / "InteracoesNPC" / pasta / f"{nome}.json")
        candidatos.append(Path("Dados") / "InteracoesNPC" / f"{nome}.json")
        return candidatos

    def _dialogo_fallback(self) -> Dict[str, object]:
        estado = self._npc.get("estado") if isinstance(self._npc.get("estado"), dict) else {}
        opcoes = [{"texto": "Até depois.", "acao": "fim"}]
        if self._npc_cargo == "vendedor":
            opcoes.insert(0, {"texto": "Quero ver seus produtos.", "destino": "abrir_loja"})
            nos_extra = {
                "abrir_loja": {
                    "fala": f"Claro. Fique à vontade para olhar meus produtos, {self._player_nome}.",
                    "saida": "loja",
                    "opcoes": [{"texto": "Fechar", "acao": "fim"}],
                }
            }
        else:
            times = estado.get("times_pokemon") if isinstance(estado.get("times_pokemon"), list) else []
            if len(times) > 1:
                for indice in range(min(3, len(times)), 0, -1):
                    opcoes.insert(0, {"texto": f"Quero batalhar contra o Time {indice}.", "acao": "batalha", "batalha": indice})
            else:
                opcoes.insert(0, {"texto": "Quero batalhar.", "acao": "batalha", "batalha": 1})
            nos_extra = {}
        return {
            "inicio": "saudacao",
            "pos_batalha": {"vitoria": "pos_batalha_vitoria", "derrota": "pos_batalha_derrota"},
            "nos": {
                "saudacao": {
                    "fala_condicional": {
                        "padrao": f"Olá, eu sou {self._npc_nome}. Ainda não tenho um diálogo configurado.",
                        "casos": [
                            {
                                "condicoes": [{"alvo": "npc.visitas_anteriores", "op": ">", "valor": 0}],
                                "valor": f"Você voltou a falar comigo, {self._player_nome}. Ainda não tenho um diálogo configurado.",
                            }
                        ],
                    },
                    "opcoes": opcoes,
                },
                **nos_extra,
                "pos_batalha_vitoria": {
                    "fala": f"Voce venceu. Bom combate, {self._player_nome}.",
                    "opcoes": [{"texto": "Encerrar conversa.", "acao": "fim"}],
                },
                "pos_batalha_derrota": {
                    "fala": f"Voce perdeu. Treine mais um pouco e volte quando estiver pronto, {self._player_nome}.",
                    "opcoes": [{"texto": "Encerrar conversa.", "acao": "fim"}],
                },
                "fallback": {
                    "fala": "Tive um problema para montar este diálogo.",
                    "opcoes": [{"texto": "Fechar", "acao": "fim"}],
                },
            },
        }

    def _carregar_dialogo(self) -> Dict[str, object]:
        for caminho in self._caminhos_dialogo_possiveis():
            if not caminho.exists():
                continue
            try:
                with caminho.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception:
                break
        return self._dialogo_fallback()

    def _tipo_interface_atual(self) -> str:
        return self._leitor.modo_interface_atual()

    def _sincronizar_com_leitor(self) -> None:
        self._texto_animado.set_texto(self._leitor.fala_atual)
        self._opcoes = self._leitor.opcoes_visiveis()
        self._hover_idx = -1
        self._loja.limpar_status()
        tipo_interface = self._tipo_interface_atual()
        if tipo_interface:
            tela = pygame.display.get_surface()
            tamanho = tela.get_size() if tela is not None else (1280, 720)
            self._loja.montar_botoes(tipo_interface, tamanho)

    def _finalizar_encerramento(self) -> None:
        self.Ativa = False
        if callable(self._acao_pos_outro):
            self._acao_pos_outro()
            self._acao_pos_outro = None
        if callable(self._ao_encerrar):
            self._ao_encerrar()

    def _encerrar(self, acao_pos_outro: Optional[Callable[[], None]] = None) -> None:
        if self._encerrando:
            return
        self._encerrando = True
        self._outro_t = 0.0
        self._acao_pos_outro = acao_pos_outro
        self._fundo_zoom_cache = None
        self._fundo_zoom_cache_tamanho = None

    def _resolver_resultado(self, resultado: Dict[str, object]) -> None:
        tipo = str(resultado.get("tipo") or "")
        if tipo == "batalha":
            contexto = resultado.get("contexto") if isinstance(resultado.get("contexto"), dict) else {}
            callback = (lambda: self._ao_iniciar_batalha(contexto)) if callable(self._ao_iniciar_batalha) else None
            self._encerrar(callback)
            return
        if tipo == "fim":
            self._encerrar()
            return
        self._sincronizar_com_leitor()

    def _selecionar_opcao(self, idx: int) -> None:
        resultado = self._leitor.selecionar_opcao(idx)
        self._resolver_resultado(resultado)

    def processar_eventos(self, _jogo, eventos: List[pygame.event.Event]) -> bool:
        if not self.Ativa:
            return False
        if self._encerrando:
            return True
        for ev in eventos:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self._encerrar()
                return True
            if not self._intro_finalizada:
                continue
            if self._tipo_interface_atual():
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
        tela = pygame.display.get_surface()
        tamanho = tela.get_size() if tela is not None else (1280, 720)
        for i, rect in enumerate(self._opcao_rects(tamanho)):
            if rect.collidepoint(mouse_pos):
                return i
        return -1

    def atualizar(self, dt: float) -> None:
        if self.Ativa:
            dt_n = max(0.0, float(dt))
            if self._encerrando:
                self._outro_t += dt_n
                if self._outro_t >= self._outro_duracao:
                    self._finalizar_encerramento()
                    return
            else:
                self._intro_t += dt_n
                if self._intro_t >= self._intro_duracao:
                    self._intro_finalizada = True
            if self._intro_finalizada and not self._encerrando:
                self._texto_animado.atualizar(dt_n)
            self._tempo_respiracao += dt_n

    def desenhar(self, tela: pygame.Surface, eventos: Optional[List[pygame.event.Event]] = None, dt: float = 0.0, JOGO=None) -> None:
        if not self.Ativa:
            return
        eventos = eventos or []
        w, h = tela.get_size()
        self._garantir_cache_fundos((w, h))
        if self._fundo_zoom_cache is None or self._fundo_zoom_cache_tamanho != (w, h):
            self._fundo_zoom_cache = tela.copy()
            self._fundo_zoom_cache_tamanho = (w, h)

        if self._encerrando:
            progresso_intro = max(0.0, min(1.0, 1.0 - (self._outro_t / max(0.001, float(self._outro_duracao)))))
        else:
            progresso_intro = max(0.0, min(1.0, self._intro_t / max(0.001, float(self._intro_duracao))))

        zoom = 1.0 + ((self._zoom_dialogo - 1.0) * progresso_intro)
        if zoom > 1.001:
            quadro = self._fundo_zoom_cache if isinstance(self._fundo_zoom_cache, pygame.Surface) else tela.copy()
            zw = max(1, int(w * zoom))
            zh = max(1, int(h * zoom))
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

        if self._texto_animado.concluido and self._tipo_interface_atual() and not self._encerrando:
            self._loja.renderizar(tela, eventos, dt, self._tipo_interface_atual(), fechar_callback=self._encerrar)
            return

        if self._texto_animado.concluido and not self._encerrando:
            self._hover_idx = self._opcao_no_mouse(pygame.mouse.get_pos())
            for i, (op, rect) in enumerate(zip(self._opcoes, self._opcao_rects((w, h)))):
                hover = i == self._hover_idx
                tamanho = 24 if hover else 22
                cor = (255, 241, 156) if hover else (228, 235, 248)
                desloc_x = 4 if hover else 0
                Texto(str(op.get("texto") or "..."), pos=(rect.x + 6 + desloc_x, rect.centery), style={"size": tamanho, "align": "midleft", "outline": True, "color": cor}).draw(tela)
        elif not self._encerrando:
            Texto("(clique para concluir o texto)", pos=(int(w * 0.5), int(h * 0.88)), style={"size": 18, "align": "midbottom", "outline": True, "color": (220, 220, 230)}).draw(tela)

    def render(self, tela, eventos, dt, JOGO=None):
        self.desenhar(tela, eventos, dt, JOGO=JOGO)
