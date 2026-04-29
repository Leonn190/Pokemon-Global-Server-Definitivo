from __future__ import annotations

from Codigo.ModulosGerais.LoaderTabelas import carregar_csv_dict
from typing import Callable

import pygame

from Codigo.Paineis.FichaItem import FichaItem
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto


class Loja:
    def __init__(
        self,
        npc_nome: str,
        npc_code: str,
        npc_estilo: str,
        ator_local=None,
        valor_coluna: Callable[..., str] | None = None,
        item_por_nome: Callable[[str], dict] | None = None,
        icone_item: Callable[[str], pygame.Surface | None] | None = None,
        nivel_respeito_estadio: Callable[[str], int] | None = None,
        tipo_estadio_npc: str = "",
        callback_ganho: Callable[[dict], None] | None = None,
        catalogo_estado: dict | None = None,
    ) -> None:
        self._npc_nome = str(npc_nome or "NPC")
        self._npc_code = str(npc_code or "")
        self._npc_estilo = str(npc_estilo or "vendedor").strip().lower()
        self._ator_local = ator_local
        self._valor_coluna = valor_coluna
        self._item_por_nome = item_por_nome
        self._icone_item = icone_item
        self._nivel_respeito_estadio = nivel_respeito_estadio
        self._tipo_estadio_npc = str(tipo_estadio_npc or "").strip().lower()
        self._callback_ganho = callback_ganho if callable(callback_ganho) else None
        self._catalogo_estado = dict(catalogo_estado or {}) if isinstance(catalogo_estado, dict) else {}

        self._catalogo = self._carregar_catalogo_npc()
        self._botoes_loja: list[dict] = []
        self._tamanho_loja_montado: tuple[int, int] | None = None
        self._status_compra = ""
        self._ficha_item_tooltip = FichaItem()

    def limpar_status(self) -> None:
        self._status_compra = ""

    @staticmethod
    def _normalizar_recurso_presente(valor: str) -> tuple[str, str]:
        nome = str(valor or "").strip()
        base = nome.lower()
        if base in {"moeda", "moedas", "dinheiro"}:
            return ("moedas", "Moedas")
        if base == "xp":
            return ("xp", "XP")
        return ("item", nome)

    def _carregar_catalogo_npc(self) -> dict:
        return {"padrao": self._carregar_loja_padrao(), "secreta": self._carregar_loja_secreta(), "presentes": self._carregar_presentes()}

    def _procurar_row_csv(self, arquivo: str) -> dict | None:
        try:
            linhas = carregar_csv_dict(arquivo, encoding="utf-8")
        except OSError:
            return None
        for idx, row in enumerate(linhas, start=1):
                code = str(row.get("Code") or idx).strip() or str(idx)
                nome = str(row.get("Nome") or "").strip().lower()
                if code == self._npc_code or nome == self._npc_nome.lower():
                    return row
        return None

    def _ler_coluna(self, row: dict, *nomes: str) -> str:
        if callable(self._valor_coluna):
            return str(self._valor_coluna(row, *nomes) or "").strip()
        for nome in nomes:
            if nome in row:
                return str(row.get(nome) or "").strip()
        return ""

    def _carregar_loja_padrao(self) -> list[dict]:
        if self._npc_estilo != "vendedor":
            return []
        ofertas_estado = self._catalogo_estado.get("padrao") if isinstance(self._catalogo_estado.get("padrao"), list) else None
        if ofertas_estado is not None:
            return [dict(o) for o in ofertas_estado if isinstance(o, dict)]
        row = self._procurar_row_csv("Pokemon Global Server - NPC Vendedor.csv")
        if not isinstance(row, dict):
            return []
        ofertas = []
        for i in range(1, 7):
            nome = self._ler_coluna(row, f"Item {i}")
            if not nome:
                continue
            preco = int(float(self._ler_coluna(row, f"Preço {i}") or 0))
            ofertas.append({"id": f"padrao_{i}", "tipo": "item", "item_nome": nome, "quantidade": 1, "preco": max(0, preco)})
        return ofertas

    def _carregar_loja_secreta(self) -> list[dict]:
        if self._npc_estilo != "vendedor":
            return []
        ofertas_estado = self._catalogo_estado.get("secreta") if isinstance(self._catalogo_estado.get("secreta"), list) else None
        if ofertas_estado is not None:
            return [dict(o) for o in ofertas_estado if isinstance(o, dict)]
        row = self._procurar_row_csv("Pokemon Global Server - NPC Vendedor.csv")
        if not isinstance(row, dict):
            return []
        ofertas = []
        for i in range(1, 3):
            nome = self._ler_coluna(row, f"Item S{i}")
            if not nome:
                continue
            preco = int(float(self._ler_coluna(row, f"Preço S{i}") or 0))
            ofertas.append({"id": f"secreta_{i}", "tipo": "item", "item_nome": nome, "quantidade": 1, "preco": max(0, preco)})
        return ofertas

    def _carregar_presentes(self) -> list[dict]:
        arquivo = "Pokemon Global Server - NPC Combatente.csv" if self._npc_estilo == "combatente" else "Pokemon Global Server - NPC Vendedor.csv"
        row = self._procurar_row_csv(arquivo)
        if not isinstance(row, dict):
            return []
        presentes = []
        for i in range(1, 4):
            nome_presente = self._ler_coluna(row, f"Presente {i}")
            if not nome_presente:
                continue
            quantidade = max(1, int(float(self._ler_coluna(row, f"Quantidade {i}") or 1)))
            rmin = max(0, int(float(self._ler_coluna(row, f"R Min {i}") or 0)))
            tipo, nome = self._normalizar_recurso_presente(nome_presente)
            presentes.append({"id": f"presente_{i}", "tipo": tipo, "item_nome": nome, "quantidade": quantidade, "preco": 0, "rmin": rmin, "limite": 1})
        return presentes

    def tipo_loja_no(self, no_atual: str, no_obj: dict | None = None) -> str:
        no = no_obj if isinstance(no_obj, dict) else {}
        loja = str(no.get("loja") or "").strip().lower()
        if loja in {"padrao", "secreta", "presente"}:
            return loja
        return "secreta" if no_atual == "loja_secreta" else "padrao" if no_atual == "loja_padrao" else ""

    def _respeito_atual_npc(self) -> int:
        if self._npc_estilo != "combatente" or not self._tipo_estadio_npc:
            return 4
        if not callable(self._nivel_respeito_estadio):
            return 0
        return int(self._nivel_respeito_estadio(self._tipo_estadio_npc) or 0)

    def _perfil(self):
        return getattr(self._ator_local, "Perfil", None)

    def _presente_ja_coletado(self, presente_id: str) -> bool:
        perfil = self._perfil()
        if perfil is None:
            return False
        return bool(getattr(perfil, "presente_npc_ja_resgatado", lambda *_: False)(self._npc_code or self._npc_nome, presente_id))

    def _registrar_presente_coletado(self, presente_id: str) -> None:
        perfil = self._perfil()
        if perfil is not None:
            registrar = getattr(perfil, "registrar_presente_npc", None)
            if callable(registrar):
                registrar(self._npc_code or self._npc_nome, presente_id)

    def status_presente(self, presente_idx: int) -> str:
        alvo = f"presente_{int(presente_idx)}"
        oferta = next((o for o in self._catalogo.get("presentes", []) if isinstance(o, dict) and str(o.get("id")) == alvo), None)
        if oferta is None:
            return "inexistente"
        if self._presente_ja_coletado(alvo):
            return "ja_coletado"
        if int(oferta.get("rmin", 0) or 0) > self._respeito_atual_npc():
            return "sem_respeito"
        return "ok"

    def _presentes_disponiveis(self) -> list[dict]:
        retorno = []
        for oferta in self._catalogo.get("presentes", []):
            if not isinstance(oferta, dict):
                continue
            oferta_id = str(oferta.get("id") or "")
            if not oferta_id.startswith("presente_"):
                continue
            try:
                idx = int(oferta_id.split("_")[-1])
            except ValueError:
                continue
            if self.status_presente(idx) == "ok":
                retorno.append(dict(oferta))
        return retorno

    def _ofertas_por_tipo(self, tipo: str) -> list[dict]:
        if tipo == "padrao":
            return [o for o in self._catalogo.get("padrao", []) if isinstance(o, dict)]
        if tipo == "secreta":
            return [o for o in self._catalogo.get("secreta", []) if isinstance(o, dict)]
        if tipo == "presente":
            return self._presentes_disponiveis()
        return []

    @staticmethod
    def _carregar_icone_moeda(size: tuple[int, int]) -> pygame.Surface | None:
        caminho = Path("Recursos") / "Visual" / "Icones" / "Diversos" / "Moeda.png"
        if not caminho.exists():
            return None
        return pygame.transform.smoothscale(pygame.image.load(str(caminho)).convert_alpha(), size)

    def montar_botoes(self, tipo: str, tela_size: tuple[int, int]) -> None:
        self._botoes_loja = []
        self._tamanho_loja_montado = tela_size
        ofertas = self._ofertas_por_tipo(tipo)
        if tipo not in {"padrao", "secreta", "presente"}:
            return

        w, h = tela_size
        cols = max(1, min(5, len(ofertas) if ofertas else 1))
        gap = 16
        lado = max(72, min(110, int(w * 0.07)))
        total_w = (cols * lado) + ((cols - 1) * gap)
        base_x = int((w - total_w) * 0.5)
        base_y = int(h * 0.74)

        for i, oferta in enumerate(ofertas):
            c = i % cols
            l = i // cols
            rect = pygame.Rect(base_x + c * (lado + gap), base_y + l * (lado + 42), lado, lado)
            self._botoes_loja.append(self._criar_entrada_visual(rect, oferta))

        fechar = Botao(pygame.Rect(int((w - 220) * 0.5), base_y + lado + 52 + (max(0, len(ofertas) - 1) // max(1, cols)) * (lado + 42), 220, 48), "Fechar conversa", execute=lambda _jogo, _botao: None, style={"radius": 12, "text_style": {"size": 18, "outline_thickness": 1, "shadow": False}})
        self._botoes_loja.append({"botao": fechar, "item": None, "oferta": None, "icone": None, "texto_centro": ""})

    def _criar_entrada_visual(self, rect: pygame.Rect, oferta: dict) -> dict:
        item = self._item_por_nome(str(oferta.get("item_nome") or "")) if str(oferta.get("tipo") or "item") == "item" and callable(self._item_por_nome) else None
        icone = self._icone_item(str(oferta.get("item_nome") or "")) if item is not None and callable(self._icone_item) else self._carregar_icone_moeda((36, 36)) if oferta.get("tipo") == "moedas" else None
        texto_centro = "XP" if oferta.get("tipo") == "xp" else ""

        def _comprar(_jogo, _botao, oferta_payload=dict(oferta), item_payload=dict(item) if isinstance(item, dict) else None):
            self._executar_oferta(oferta_payload, item_payload)

        botao = Botao(rect, "", execute=_comprar, style={"radius": 12, "border_width": 2, "bg": (35, 52, 82), "bg_hover": (51, 74, 112), "bg_pressed": (25, 39, 62), "border": (112, 138, 182), "border_hover": (201, 224, 255), "text_style": {"size": 1, "outline_thickness": 0, "shadow": False, "align": "center"}})
        return {"botao": botao, "item": item, "oferta": oferta, "icone": icone, "texto_centro": texto_centro}

    @staticmethod
    def _texto_preco(oferta: dict, tipo_loja: str) -> tuple[str, tuple[int, int, int]]:
        qtd = int(oferta.get("quantidade", 1) or 1)
        sufixo = f"x{qtd}" if qtd > 1 else ""
        if tipo_loja == "presente":
            return (f"Grátis {sufixo}".strip(), (136, 242, 168))
        return (f"{int(oferta.get('preco', 0) or 0)} dinheiro {sufixo}".strip(), (255, 223, 120))

    def _emitir_ganho(self, tipo: str, nome: str, quantidade: int) -> None:
        if callable(self._callback_ganho):
            self._callback_ganho({"tipo": tipo, "nome": nome, "quantidade": int(max(1, quantidade))})

    def _executar_oferta(self, oferta: dict, item_payload: dict | None) -> None:
        perfil = self._perfil()
        inventario = getattr(self._ator_local, "Inventario", None)
        if perfil is None:
            self._status_compra = "Falha: perfil indisponível"
            return

        tipo = str(oferta.get("tipo") or "item").lower()
        oferta_id = str(oferta.get("id") or "")
        if oferta_id.startswith("presente_") and self._presente_ja_coletado(oferta_id):
            self._status_compra = "Esse presente já foi resgatado"
            return

        preco = int(oferta.get("preco", 0) or 0)
        saldo = int(getattr(perfil, "Dinheiro", 0) or 0)
        if preco > saldo:
            self._status_compra = "Dinheiro insuficiente"
            return

        quantidade = int(max(1, int(oferta.get("quantidade", 1) or 1)))
        if tipo == "item":
            if inventario is None:
                self._status_compra = "Falha: inventário indisponível"
                return
            item = dict(item_payload or {})
            item["quantidade"] = quantidade
            if not inventario.adicionar_item(item):
                self._status_compra = "Inventário sem espaço"
                return
            perfil.Dinheiro = saldo - preco
            self._emitir_ganho("item", str(item.get("Nome") or "Item"), quantidade)
            self._status_compra = f"Recebeu {item.get('Nome', 'item')} x{quantidade}"
        elif tipo == "moedas":
            perfil.Dinheiro = saldo - preco + quantidade
            self._emitir_ganho("moedas", "Moedas", quantidade)
            self._status_compra = f"Recebeu {quantidade} moedas"
        elif tipo == "xp":
            perfil.Dinheiro = saldo - preco
            perfil.XP = int(getattr(perfil, "XP", 0) or 0) + quantidade
            perfil.normalizar_progresso_xp()
            self._emitir_ganho("xp", "XP", quantidade)
            self._status_compra = f"Recebeu {quantidade} XP"
        else:
            self._status_compra = "Oferta inválida"
            return

        if oferta_id.startswith("presente_"):
            self._registrar_presente_coletado(oferta_id)
            self.montar_botoes("presente", self._tamanho_loja_montado or (1280, 720))

    def renderizar(self, tela: pygame.Surface, eventos: list, dt: float, tipo: str, fechar_callback: Callable[[], None]) -> None:
        w, h = tela.get_size()
        if self._tamanho_loja_montado != (w, h):
            self.montar_botoes(tipo, (w, h))

        hover_entrada = None
        for entrada in self._botoes_loja:
            botao = entrada.get("botao")
            if not isinstance(botao, Botao):
                continue
            if entrada.get("oferta") is None:
                botao.execute = lambda _jogo, _botao: fechar_callback()
            botao.render(tela, eventos, dt, None)

            icone = entrada.get("icone")
            if icone is not None:
                tela.blit(icone, icone.get_rect(center=botao.rect.center))
            elif entrada.get("texto_centro"):
                Texto(str(entrada.get("texto_centro")), pos=botao.rect.center, style={"size": 20, "align": "center", "outline": True, "color": (215, 232, 255)}).draw(tela)

            oferta = entrada.get("oferta") if isinstance(entrada.get("oferta"), dict) else None
            if oferta is not None:
                txt, cor = self._texto_preco(oferta, tipo)
                Texto(txt, pos=(botao.rect.centerx, botao.rect.bottom + 8), style={"size": 18, "align": "midtop", "outline": True, "color": cor}).draw(tela)

            if bool(getattr(botao, "hover", False)) and isinstance(entrada.get("item"), dict):
                hover_entrada = entrada

        if hover_entrada is not None:
            botao = hover_entrada.get("botao")
            if isinstance(botao, Botao):
                largura_ficha = max(320, int(w * 0.28))
                ficha_rect = pygame.Rect(0, 0, largura_ficha, 72)
                ficha_rect.midbottom = (botao.rect.centerx, botao.rect.top - 8)
                ficha_rect.clamp_ip(pygame.Rect(8, 8, w - 16, h - 16))
                pygame.draw.rect(tela, (11, 17, 28), ficha_rect, border_radius=12)
                pygame.draw.rect(tela, (103, 138, 198), ficha_rect, 2, border_radius=12)
                self._ficha_item_tooltip.renderizar(tela, ficha_rect.inflate(-8, -8), hover_entrada.get("item"))

        if self._status_compra:
            Texto(self._status_compra, pos=(int(w * 0.5), int(h * 0.90)), style={"size": 18, "align": "midbottom", "outline": True, "color": (220, 235, 255)}).draw(tela)
