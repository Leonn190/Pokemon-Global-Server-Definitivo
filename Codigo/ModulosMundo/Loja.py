from __future__ import annotations

import math
import random
import unicodedata
from pathlib import Path

from Codigo.ModulosGerais.LoaderTabelas import carregar_csv_dict
from typing import Callable

import pygame

from Codigo.Paineis.FichaItem import FichaItem
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto


class Loja:
    SLOTS_POR_LINHA = 6

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
        categoria_vendedor: str = "",
        tempo_mundo: dict | None = None,
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
        self._categoria_vendedor = str(categoria_vendedor or "")
        self._tempo_mundo = dict(tempo_mundo or {}) if isinstance(tempo_mundo, dict) else {}
        self._itens_por_chave_cache: dict[str, dict] | None = None

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
        presentes = self._carregar_presentes()
        categoria = self._categoria_vendedor_normalizada()
        if categoria == "item":
            padrao = self._gerar_ofertas_compra_itens()
        elif categoria == "pokemon":
            padrao = self._gerar_ofertas_compra_pokemons()
        else:
            padrao = self._carregar_loja_padrao()
        return {
            "padrao": padrao,
            "secreta": self._carregar_loja_secreta(),
            "presentes": presentes,
            "presente_1": [dict(o) for o in presentes if str(o.get("id") or "") == "presente_1"],
            "presente_2": [dict(o) for o in presentes if str(o.get("id") or "") == "presente_2"],
        }

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

    @staticmethod
    def _normalizar_ascii(valor: object) -> str:
        texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode("ascii")
        return " ".join(texto.strip().lower().split())

    def _categoria_vendedor_normalizada(self) -> str:
        texto = self._normalizar_ascii(self._categoria_vendedor)
        if texto in {"moeda", "moedas", "dinheiro"}:
            return "moedas"
        if texto in {"item", "itens"}:
            return "item"
        if texto in {"pokemon", "pokemons"}:
            return "pokemon"
        return texto

    def _nivel_vendedor(self) -> int:
        row = self._procurar_row_csv("Pokemon Global Server - NPC Vendedor.csv")
        if not isinstance(row, dict):
            return 0
        try:
            return int(float(str(self._ler_coluna(row, "Nivel", "NÃ­vel", "Level") or 0).replace(",", ".")))
        except (TypeError, ValueError):
            return 0

    def _bucket_ofertas_3_dias(self) -> int:
        try:
            dia = int(float(self._tempo_mundo.get("dia", 0) or 0))
        except (TypeError, ValueError):
            dia = 0
        return max(0, dia) // 3

    def _player_chave_seed(self) -> str:
        ator = self._ator_local
        for nome in ("Id", "id", "ClientId", "client_id", "Nome", "nome"):
            valor = getattr(ator, nome, None) if ator is not None else None
            if valor not in (None, ""):
                return str(valor)
        return ""

    def _rng_ofertas(self, sufixo: str) -> random.Random:
        seed = ":".join(
            [
                self._npc_code or self._npc_nome,
                self._player_chave_seed(),
                self._categoria_vendedor_normalizada(),
                str(self._bucket_ofertas_3_dias()),
                str(sufixo or ""),
            ]
        )
        return random.Random(seed)

    @staticmethod
    def _float_pos(valor: object, default: float = 0.0) -> float:
        try:
            return float(str(valor).replace(",", "."))
        except (TypeError, ValueError):
            return float(default)

    def _item_chave(self, item: dict) -> str:
        code = str(item.get("Code") or item.get("code") or "").strip()
        if code:
            return f"code:{code}"
        return f"nome:{self._normalizar_ascii(item.get('Nome') or item.get('nome') or '')}"

    def _carregar_itens_por_nome(self) -> dict[str, dict]:
        if self._itens_por_chave_cache is not None:
            return self._itens_por_chave_cache
        mapa: dict[str, dict] = {}
        try:
            linhas = carregar_csv_dict("Pokemon Global Server - Itens.csv", encoding="utf-8")
        except OSError:
            linhas = []
        for row in linhas:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            chave = self._item_chave(item)
            if chave:
                mapa[chave] = item
            nome = self._normalizar_ascii(item.get("Nome") or item.get("nome") or "")
            if nome:
                mapa[f"nome:{nome}"] = item
        self._itens_por_chave_cache = mapa
        return mapa

    def _valor_item(self, item: dict) -> int:
        valor = self._float_pos(item.get("Valor", item.get("valor", 0)), 0.0)
        return int(valor) if valor > 0 else 0

    def _item_vendavel_para_comprador(self, item: dict) -> bool:
        return str(item.get("Venda", item.get("venda", "")) or "").strip().lower() == "s"

    def _multiplicador_preco(self, sufixo: str, minimo: float = 0.80, maximo: float = 1.15) -> float:
        rng = self._rng_ofertas(f"preco:{sufixo}")
        return float(minimo) + (float(maximo) - float(minimo)) * rng.random()

    def _gerar_ofertas_compra_itens(self) -> list[dict]:
        inventario = getattr(self._ator_local, "Inventario", None)
        itens_inv = list(getattr(inventario, "Itens", []) or []) if inventario is not None else []
        itens_catalogo = self._carregar_itens_por_nome()
        nivel_vendedor = max(0, self._nivel_vendedor())
        agregados: dict[str, dict] = {}
        for slot in itens_inv:
            if not isinstance(slot, dict):
                continue
            chave = self._item_chave(slot)
            base = itens_catalogo.get(chave) or itens_catalogo.get(f"nome:{self._normalizar_ascii(slot.get('Nome') or slot.get('nome') or '')}") or slot
            valor = self._valor_item(base)
            if valor <= 0 or valor > nivel_vendedor or not self._item_vendavel_para_comprador(base):
                continue
            qtd = max(1, int(self._float_pos(slot.get("quantidade", slot.get("Quantidade", 1)), 1)))
            atual = agregados.setdefault(chave, {"item": dict(base), "quantidade": 0})
            atual["quantidade"] += qtd

        candidatos = []
        for chave, dados in agregados.items():
            item = dados["item"]
            valor = self._valor_item(item)
            qtd_real = int(dados.get("quantidade", 0) or 0)
            if valor <= 0 or qtd_real <= 0:
                continue
            qtd_max = max(1, int(math.floor(nivel_vendedor / max(1, valor))))
            qtd_limite = max(1, min(qtd_real, qtd_max))
            rng_qtd = self._rng_ofertas(f"qtd_item:{chave}")
            quantidade = rng_qtd.randint(1, qtd_limite)
            mult = self._multiplicador_preco(f"item:{chave}")
            preco = max(1, int(round(quantidade * valor * mult)))
            candidatos.append(
                {
                    "ordem": self._rng_ofertas(f"ordem_item:{chave}").random(),
                    "oferta": {
                        "id": f"compra_item_{chave}",
                        "tipo": "comprar_item_player",
                        "item_nome": str(item.get("Nome") or item.get("nome") or "Item"),
                        "item_chave": chave,
                        "quantidade": quantidade,
                        "preco": preco,
                    },
                }
            )
        candidatos.sort(key=lambda c: (c["ordem"], str(c["oferta"].get("item_nome") or "")))
        return [dict(c["oferta"]) for c in candidatos[:5]]

    def _estado_pokemon(self, pokemon) -> dict:
        if not isinstance(pokemon, dict):
            return {}
        estado = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else None
        return estado if estado is not None else pokemon

    def _pokemon_valor(self, pokemon, *chaves: str, default=None):
        fontes = []
        if isinstance(pokemon, dict):
            fontes.append(pokemon)
            estado = self._estado_pokemon(pokemon)
            if estado is not pokemon:
                fontes.append(estado)
        for fonte in fontes:
            for chave in chaves:
                if chave in fonte and fonte.get(chave) not in (None, ""):
                    return fonte.get(chave)
        return default

    def _pokemon_chave_estavel(self, pokemon, indice: int | None = None, incluir_indice: bool = True) -> str:
        for chave in ("UID", "uid", "Uuid", "uuid", "IdUnico", "id_unico"):
            valor = self._pokemon_valor(pokemon, chave)
            if valor not in (None, ""):
                return f"uid:{valor}"
        for chave in ("ID", "Id", "id"):
            valor = self._pokemon_valor(pokemon, chave)
            if valor not in (None, "", 0, "0"):
                return f"id:{valor}"
        partes = [
            self._normalizar_ascii(self._pokemon_valor(pokemon, "Nome", "nome", "Especie", "especie", "Pokemon", "pokemon", default="")),
            str(self._pokemon_valor(pokemon, "Code", "code", "Numero", "numero", "Dex", "dex", default="")),
            str(self._pokemon_valor(pokemon, "Nivel", "nivel", "Level", "level", default="")),
            str(self._pokemon_valor(pokemon, "IV", "iv", default="")),
            str(self._pokemon_valor(pokemon, "Raridade", "raridade", default="")),
        ]
        if incluir_indice and indice is not None:
            partes.append(str(indice))
        return "poke:" + "|".join(partes)

    def _pokemon_nome(self, pokemon) -> str:
        return str(self._pokemon_valor(pokemon, "Apelido", "apelido", "Nome", "nome", "Especie", "especie", "Pokemon", "pokemon", default="Pokemon") or "Pokemon")

    def _pokemon_int(self, pokemon, *chaves: str, default: int = 0) -> int:
        return int(self._float_pos(self._pokemon_valor(pokemon, *chaves, default=default), default))

    def _pokemon_inicial(self, pokemon) -> bool:
        for chave in ("inicial", "Inicial", "starter", "Starter", "pokemon_inicial", "PokemonInicial"):
            valor = self._pokemon_valor(pokemon, chave)
            if isinstance(valor, str):
                if valor.strip().lower() in {"1", "s", "sim", "true", "yes", "inicial", "starter"}:
                    return True
            elif bool(valor):
                return True
        origem = self._normalizar_ascii(self._pokemon_valor(pokemon, "origem", "Origem", "source", "Source", default=""))
        return origem in {"inicial", "starter", "pokemon inicial"}

    def _preco_pokemon(self, pokemon, chave: str) -> int:
        nivel = max(0, self._pokemon_int(pokemon, "Nivel", "nivel", "Level", "level", default=0))
        raridade = max(1, self._pokemon_int(pokemon, "Raridade", "raridade", default=1))
        iv = max(0, self._pokemon_int(pokemon, "IV", "iv", default=0))
        valor = max(5.0, (float(nivel) * float(raridade) * float(iv)) / 100.0)
        if self._pokemon_inicial(pokemon):
            valor *= 1.5
        valor *= self._multiplicador_preco(f"pokemon:{chave}")
        return max(5, int(round(valor)))

    def _gerar_ofertas_compra_pokemons(self) -> list[dict]:
        inventario = getattr(self._ator_local, "Inventario", None)
        pokemons = list(getattr(inventario, "Pokemons", []) or []) if inventario is not None else []
        nivel_vendedor = max(0, self._nivel_vendedor())
        candidatos = []
        for indice, pokemon in enumerate(pokemons):
            if not isinstance(pokemon, dict):
                continue
            nivel = max(0, self._pokemon_int(pokemon, "Nivel", "nivel", "Level", "level", default=0))
            if nivel > nivel_vendedor:
                continue
            chave = self._pokemon_chave_estavel(pokemon, indice=indice, incluir_indice=True)
            fingerprint = self._pokemon_chave_estavel(pokemon, incluir_indice=False)
            nome = self._pokemon_nome(pokemon)
            preco = self._preco_pokemon(pokemon, chave)
            candidatos.append(
                {
                    "ordem": self._rng_ofertas(f"ordem_pokemon:{chave}").random(),
                    "oferta": {
                        "id": f"compra_pokemon_{chave}",
                        "tipo": "comprar_pokemon_player",
                        "pokemon_chave": chave,
                        "pokemon_fingerprint": fingerprint,
                        "pokemon_nome": nome,
                        "pokemon_nivel": nivel,
                        "quantidade": 1,
                        "preco": preco,
                    },
                }
            )
        candidatos.sort(key=lambda c: (c["ordem"], str(c["oferta"].get("pokemon_nome") or "")))
        return [dict(c["oferta"]) for c in candidatos[:5]]

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
        presentes_estado = []
        for chave in ("presente_1", "presente_2"):
            ofertas = self._catalogo_estado.get(chave) if isinstance(self._catalogo_estado.get(chave), list) else []
            presentes_estado.extend(dict(o) for o in ofertas if isinstance(o, dict))
        if presentes_estado:
            return presentes_estado
        ofertas_estado = self._catalogo_estado.get("presentes") if isinstance(self._catalogo_estado.get("presentes"), list) else None
        if ofertas_estado is not None:
            return [dict(o) for o in ofertas_estado if isinstance(o, dict)]

        arquivo = "Pokemon Global Server - NPC Combatente.csv" if self._npc_estilo == "combatente" else "Pokemon Global Server - NPC Vendedor.csv"
        row = self._procurar_row_csv(arquivo)
        if not isinstance(row, dict):
            return []
        presentes = []
        for i in range(1, 3):
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
        if loja in {"padrao", "secreta", "presente", "presente_1", "presente_2"}:
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
            categoria = self._categoria_vendedor_normalizada()
            if categoria == "item":
                self._catalogo["padrao"] = self._gerar_ofertas_compra_itens()
            elif categoria == "pokemon":
                self._catalogo["padrao"] = self._gerar_ofertas_compra_pokemons()
            return [o for o in self._catalogo.get("padrao", []) if isinstance(o, dict)]
        if tipo == "secreta":
            return [o for o in self._catalogo.get("secreta", []) if isinstance(o, dict)]
        if tipo in {"presente_1", "presente_2"}:
            try:
                idx = int(tipo.split("_")[-1])
            except ValueError:
                return []
            return [o for o in self._catalogo.get(tipo, []) if isinstance(o, dict) and self.status_presente(idx) == "ok"]
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
        if tipo not in {"padrao", "secreta", "presente", "presente_1", "presente_2"}:
            return
        if tipo == "padrao" and not ofertas and self._categoria_vendedor_normalizada() in {"item", "pokemon"} and not self._status_compra:
            self._status_compra = "Nada interessante para negociar agora."

        w, h = tela_size
        cols = max(1, min(self.SLOTS_POR_LINHA, len(ofertas) if ofertas else 1))
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
        tipo = str(oferta.get("tipo") or "item")
        item = self._item_por_nome(str(oferta.get("item_nome") or "")) if tipo in {"item", "comprar_item_player"} and callable(self._item_por_nome) else None
        icone = self._icone_item(str(oferta.get("item_nome") or "")) if item is not None and callable(self._icone_item) else self._carregar_icone_moeda((36, 36)) if oferta.get("tipo") == "moedas" else None
        texto_centro = "XP" if oferta.get("tipo") == "xp" else ""
        if tipo == "comprar_pokemon_player":
            nome = str(oferta.get("pokemon_nome") or "Pokemon")
            texto_centro = [nome[:10], f"Nv.{int(oferta.get('pokemon_nivel', 0) or 0)}"]

        def _comprar(_jogo, _botao, oferta_payload=dict(oferta), item_payload=dict(item) if isinstance(item, dict) else None):
            self._executar_oferta(oferta_payload, item_payload)

        botao = Botao(rect, "", execute=_comprar, style={"radius": 12, "border_width": 2, "bg": (35, 52, 82), "bg_hover": (51, 74, 112), "bg_pressed": (25, 39, 62), "border": (112, 138, 182), "border_hover": (201, 224, 255), "text_style": {"size": 1, "outline_thickness": 0, "shadow": False, "align": "center"}})
        return {"botao": botao, "item": item, "oferta": oferta, "icone": icone, "texto_centro": texto_centro}

    def _preco_efetivo(self, oferta: dict, tipo_loja: str) -> int:
        preco = max(0, int(oferta.get("preco", 0) or 0))
        if preco <= 0 or str(tipo_loja or "").startswith("presente"):
            return preco
        perfil = self._perfil()
        desconto = max(0.0, float(getattr(perfil, "DescontoLojasPercent", 0.0) or 0.0)) if perfil is not None else 0.0
        return max(0, int(round(preco * (1.0 - min(0.95, desconto)))))

    def _texto_preco(self, oferta: dict, tipo_loja: str) -> tuple[str, tuple[int, int, int]]:
        qtd = int(oferta.get("quantidade", 1) or 1)
        sufixo = f"x{qtd}" if qtd > 1 else ""
        if str(oferta.get("tipo") or "") in {"comprar_item_player", "comprar_pokemon_player"}:
            return (f"+{max(0, int(oferta.get('preco', 0) or 0))} moedas {sufixo}".strip(), (136, 242, 168))
        if tipo_loja.startswith("presente"):
            return (f"Grátis {sufixo}".strip(), (136, 242, 168))
        return (f"{self._preco_efetivo(oferta, tipo_loja)} dinheiro {sufixo}".strip(), (255, 223, 120))

    def _emitir_ganho(self, tipo: str, nome: str, quantidade: int) -> None:
        if callable(self._callback_ganho):
            self._callback_ganho({"tipo": tipo, "nome": nome, "quantidade": int(max(1, quantidade))})

    def _remover_quantidade_item(self, chave_item: str, quantidade: int) -> bool:
        inventario = getattr(self._ator_local, "Inventario", None)
        itens = getattr(inventario, "Itens", None) if inventario is not None else None
        if not isinstance(itens, list):
            return False
        alvo = str(chave_item or "")
        quantidade = int(max(1, quantidade))
        total = 0
        for slot in itens:
            if isinstance(slot, dict) and self._item_chave(slot) == alvo:
                total += max(1, int(self._float_pos(slot.get("quantidade", slot.get("Quantidade", 1)), 1)))
        if total < quantidade:
            return False
        restante = quantidade
        for idx, slot in enumerate(itens):
            if restante <= 0:
                break
            if not isinstance(slot, dict) or self._item_chave(slot) != alvo:
                continue
            qtd_slot = max(1, int(self._float_pos(slot.get("quantidade", slot.get("Quantidade", 1)), 1)))
            remover = min(restante, qtd_slot)
            qtd_slot -= remover
            restante -= remover
            if qtd_slot <= 0:
                itens[idx] = None
            else:
                slot["quantidade"] = qtd_slot
        return restante <= 0

    def _remover_pokemon_por_chave(self, chave_pokemon: str, fingerprint: str = "") -> bool:
        inventario = getattr(self._ator_local, "Inventario", None)
        pokemons = getattr(inventario, "Pokemons", None) if inventario is not None else None
        if not isinstance(pokemons, list):
            return False
        alvo = str(chave_pokemon or "")
        indice_remover = None
        for idx, pokemon in enumerate(pokemons):
            if self._pokemon_chave_estavel(pokemon, indice=idx, incluir_indice=True) == alvo:
                indice_remover = idx
                break
        if indice_remover is None and fingerprint:
            matches = [idx for idx, pokemon in enumerate(pokemons) if self._pokemon_chave_estavel(pokemon, incluir_indice=False) == fingerprint]
            if len(matches) == 1:
                indice_remover = matches[0]
        if indice_remover is None:
            return False
        removido = pokemons.pop(indice_remover)
        self._limpar_pokemon_dos_times(removido, fingerprint or self._pokemon_chave_estavel(removido, incluir_indice=False))
        return True

    def _limpar_pokemon_dos_times(self, pokemon_removido, fingerprint: str) -> None:
        inventario = getattr(self._ator_local, "Inventario", None)
        if inventario is None:
            return
        alvo_fingerprint = str(fingerprint or self._pokemon_chave_estavel(pokemon_removido, incluir_indice=False))
        for nome_times in ("TimesPokemon", "TimesPokemons"):
            times = getattr(inventario, nome_times, None)
            if not isinstance(times, list):
                continue
            for time in times:
                slots = None
                if isinstance(time, dict):
                    slots = time.get("Slots") if isinstance(time.get("Slots"), list) else time.get("slots") if isinstance(time.get("slots"), list) else None
                elif isinstance(time, list):
                    slots = time
                if not isinstance(slots, list):
                    continue
                for idx, slot in enumerate(slots):
                    if self._pokemon_chave_estavel(slot, incluir_indice=False) == alvo_fingerprint:
                        slots[idx] = None
                if isinstance(time, dict):
                    if "Slots" in time:
                        time["Slots"] = slots
                    if "slots" in time:
                        time["slots"] = slots

    def _pagar_moedas_player(self, valor: int) -> None:
        perfil = self._perfil()
        if perfil is None:
            return
        perfil.Dinheiro = int(getattr(perfil, "Dinheiro", 0) or 0) + int(max(0, valor))
        if hasattr(perfil, "atualizar_moedas_maximas"):
            perfil.atualizar_moedas_maximas()

    def _executar_oferta(self, oferta: dict, item_payload: dict | None) -> None:
        perfil = self._perfil()
        inventario = getattr(self._ator_local, "Inventario", None)
        if perfil is None:
            self._status_compra = "Falha: perfil indisponível"
            return

        tipo = str(oferta.get("tipo") or "item").lower()
        oferta_id = str(oferta.get("id") or "")
        if tipo == "comprar_item_player":
            quantidade = int(max(1, int(oferta.get("quantidade", 1) or 1)))
            if inventario is None or not self._remover_quantidade_item(str(oferta.get("item_chave") or ""), quantidade):
                self._status_compra = "Item indisponivel"
                self.montar_botoes("padrao", self._tamanho_loja_montado or (1280, 720))
                return
            preco = max(1, int(oferta.get("preco", 1) or 1))
            nome = str(oferta.get("item_nome") or "Item")
            self._pagar_moedas_player(preco)
            self._emitir_ganho("moedas", "Moedas", preco)
            self._status_compra = f"Vendeu {nome} x{quantidade} por {preco} moedas"
            self.montar_botoes("padrao", self._tamanho_loja_montado or (1280, 720))
            return
        if tipo == "comprar_pokemon_player":
            fingerprint = str(oferta.get("pokemon_fingerprint") or "")
            if inventario is None or not self._remover_pokemon_por_chave(str(oferta.get("pokemon_chave") or ""), fingerprint):
                self._status_compra = "Oferta indisponivel"
                self.montar_botoes("padrao", self._tamanho_loja_montado or (1280, 720))
                return
            preco = max(5, int(oferta.get("preco", 5) or 5))
            nome = str(oferta.get("pokemon_nome") or "Pokemon")
            nivel = int(oferta.get("pokemon_nivel", 0) or 0)
            self._pagar_moedas_player(preco)
            self._emitir_ganho("moedas", "Moedas", preco)
            self._status_compra = f"Vendeu {nome} Nv. {nivel} por {preco} moedas"
            self.montar_botoes("padrao", self._tamanho_loja_montado or (1280, 720))
            return
        if oferta_id.startswith("presente_") and self._presente_ja_coletado(oferta_id):
            self._status_compra = "Esse presente já foi resgatado"
            return

        tipo_loja = "presente" if oferta_id.startswith("presente_") else "padrao"
        preco = self._preco_efetivo(oferta, tipo_loja)
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
            if hasattr(perfil, "atualizar_moedas_maximas"):
                perfil.atualizar_moedas_maximas()
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
            self.montar_botoes(oferta_id if oferta_id in {"presente_1", "presente_2"} else "presente", self._tamanho_loja_montado or (1280, 720))

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
                texto_centro = entrada.get("texto_centro")
                if isinstance(texto_centro, (list, tuple)):
                    linhas = [str(l) for l in texto_centro if str(l).strip()]
                    y0 = botao.rect.centery - (len(linhas) - 1) * 10
                    for i, linha in enumerate(linhas):
                        Texto(linha, pos=(botao.rect.centerx, y0 + i * 20), style={"size": 15, "align": "center", "outline": True, "color": (215, 232, 255)}).draw(tela)
                else:
                    Texto(str(texto_centro), pos=botao.rect.center, style={"size": 20, "align": "center", "outline": True, "color": (215, 232, 255)}).draw(tela)

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
