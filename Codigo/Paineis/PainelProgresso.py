from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame

from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Texto import Texto


@dataclass(frozen=True)
class MissaoProgresso:
    id: str
    titulo: str
    alvo: int | float
    peso: float
    obter_valor: Callable[["PainelProgresso", dict[str, float]], int | float | bool]
    unidade: str = ""
    descricao: str = ""


@dataclass(frozen=True)
class RotaProgresso:
    id: str
    nome: str
    subtitulo: str
    cor: tuple[int, int, int]
    cor_clara: tuple[int, int, int]
    cor_escura: tuple[int, int, int]
    missoes: tuple[MissaoProgresso, ...]


class PainelProgresso:
    """
    Painel visual das rotas de progresso do jogador.

    A classe já tenta ler vários nomes prováveis do Perfil/Inventário para
    funcionar mesmo antes de existir um contrato final de save. O que não for
    encontrado cai para 0, sem quebrar o painel.
    """

    ROTAS_ORDEM = ("campeao", "intelectual", "magnata", "heroi", "imperador")

    def __init__(self, ator=None):
        self.Ator = ator
        self._layout_chave = None
        self._rect = pygame.Rect(0, 0, 0, 0)
        self._area_botoes = pygame.Rect(0, 0, 0, 0)
        self._area_conteudo = pygame.Rect(0, 0, 0, 0)
        self._area_missoes = pygame.Rect(0, 0, 0, 0)
        self._botao_fechar: Botao | None = None
        self._botoes_rotas: dict[str, Botao] = {}
        self._status_estilo_botoes: dict[str, bool] = {}
        self._rota_selecionada = "campeao"
        self._solicitou_fechar = False
        self._textos: dict[str, Texto] = {}
        self._rotas = self._montar_rotas()

    # ------------------------------------------------------------------
    # Dados / leitura tolerante do Perfil
    # ------------------------------------------------------------------
    def _perfil(self):
        return getattr(self.Ator, "Perfil", None) if self.Ator is not None else None

    def _inventario(self):
        return getattr(self.Ator, "Inventario", None) if self.Ator is not None else None

    @staticmethod
    def _normalizar_texto(valor) -> str:
        return str(valor or "").strip().lower().replace("í", "i").replace("é", "e")

    @staticmethod
    def _valor_numerico(obj, nomes: tuple[str, ...], padrao=None):
        if obj is None:
            return padrao
        for nome in nomes:
            if not hasattr(obj, nome):
                continue
            valor = getattr(obj, nome)
            if valor is None:
                continue
            if isinstance(valor, bool):
                return 1 if valor else 0
            if isinstance(valor, (int, float)):
                return valor
            if isinstance(valor, (list, tuple, set, dict)):
                return len(valor)
            try:
                return float(valor)
            except (TypeError, ValueError):
                return padrao
        return padrao

    @staticmethod
    def _lista_ou_dict(obj, nomes: tuple[str, ...]):
        if obj is None:
            return None
        for nome in nomes:
            if not hasattr(obj, nome):
                continue
            valor = getattr(obj, nome)
            if valor is None:
                continue
            if isinstance(valor, dict):
                return list(valor.keys())
            if isinstance(valor, (list, tuple, set)):
                return list(valor)
            if isinstance(valor, (int, float)):
                return valor
        return None

    @staticmethod
    def _quantidade_item(item) -> int:
        if not isinstance(item, dict):
            return 1 if item is not None else 0
        for chave in ("quantidade", "Quantidade", "qtd", "Qtd", "stack", "Stack"):
            try:
                return max(0, int(item.get(chave, 0) or 0)) or 1
            except (TypeError, ValueError):
                continue
        return 1

    def _contar_pokemons_inventario(self) -> int:
        inventario = self._inventario()
        pokemons = getattr(inventario, "Pokemons", []) if inventario is not None else []
        return len([p for p in list(pokemons or []) if isinstance(p, dict) or p is not None])

    def _contar_itens_inventario(self, apenas_distintos=False) -> int:
        inventario = self._inventario()
        itens = getattr(inventario, "Itens", []) if inventario is not None else []
        total = 0
        distintos = set()
        for item in list(itens or []):
            if item is None:
                continue
            if apenas_distintos:
                if isinstance(item, dict):
                    chave = item.get("Code") or item.get("code") or item.get("Nome") or item.get("nome") or id(item)
                else:
                    chave = str(item)
                distintos.add(str(chave))
            else:
                total += self._quantidade_item(item)
        return len(distintos) if apenas_distintos else total

    def _contar_registro(self, nomes: tuple[str, ...], fallback=None) -> int:
        perfil = self._perfil()
        valor = self._lista_ou_dict(perfil, nomes)
        if isinstance(valor, (int, float)):
            return max(0, int(valor))
        if isinstance(valor, list):
            return len([v for v in valor if v is not None])
        if fallback is not None:
            return int(fallback())
        return 0

    def _flag_perfil(self, nomes: tuple[str, ...]) -> int:
        perfil = self._perfil()
        if perfil is None:
            return 0
        for nome in nomes:
            if hasattr(perfil, nome):
                valor = getattr(perfil, nome)
                if isinstance(valor, bool):
                    return 1 if valor else 0
                if isinstance(valor, (int, float)):
                    return 1 if valor > 0 else 0
                if isinstance(valor, str):
                    return 1 if valor.strip().lower() in {"1", "true", "sim", "yes", "feito", "concluido", "concluído"} else 0
                return 1 if valor else 0
        return 0

    def _ouro(self) -> int:
        perfil = self._perfil()
        return int(self._valor_numerico(perfil, ("Dinheiro", "Ouro", "Gold", "Moedas"), 0) or 0)

    def _vitorias_totais(self) -> int:
        perfil = self._perfil()
        vitorias_diretas = self._valor_numerico(perfil, ("VitoriasTotais", "VitóriasTotais", "BatalhasVencidas", "Vitorias"), None)
        if vitorias_diretas is not None:
            return max(0, int(vitorias_diretas))
        pvp = int(self._valor_numerico(perfil, ("BatalhasPVPVencidas", "VitoriasPVP", "VitóriasPVP"), 0) or 0)
        bot = int(self._valor_numerico(perfil, ("BatalhasBotVencidas", "VitoriasBot", "VitóriasBot"), 0) or 0)
        return max(0, pvp + bot)

    def _insignias(self) -> int:
        perfil = self._perfil()
        valor = self._lista_ou_dict(perfil, ("Insignias", "Insígnias", "Badges"))
        if isinstance(valor, (int, float)):
            return max(0, int(valor))
        if isinstance(valor, list):
            return len([v for v in valor if v is not None])
        return 0

    def _ginasios_liderados(self) -> int:
        perfil = self._perfil()
        return int(self._valor_numerico(perfil, ("GinasiosLiderados", "GinásiosLiderados", "LiderGinasios", "LiderancasGinasio"), 0) or 0)

    def _nivel(self) -> int:
        perfil = self._perfil()
        return int(self._valor_numerico(perfil, ("Nivel", "Nível", "Level"), 0) or 0)

    def _dungeons_terminadas(self) -> int:
        perfil = self._perfil()
        return int(self._valor_numerico(perfil, ("DungeonsTerminadas", "DungeonsConcluidas", "DungeonsConcluídas"), 0) or 0)

    def _contar_recursos_miticos(self) -> int:
        perfil = self._perfil()
        direto = self._valor_numerico(
            perfil,
            ("RecursosMiticos", "RecursosMíticos", "RecursosMiticosQuantidade", "ItensRecursosMiticos"),
            None,
        )
        if direto is not None:
            return max(0, int(direto))

        inventario = self._inventario()
        itens = getattr(inventario, "Itens", []) if inventario is not None else []
        total = 0
        for item in list(itens or []):
            if not isinstance(item, dict):
                continue
            nome = self._normalizar_texto(item.get("Nome") or item.get("nome") or item.get("Code") or item.get("code"))
            tipo = self._normalizar_texto(item.get("Tipo") or item.get("tipo") or item.get("Categoria") or item.get("categoria") or item.get("Classe") or item.get("classe"))
            raridade = self._normalizar_texto(item.get("Raridade") or item.get("raridade") or item.get("Rank") or item.get("rank"))
            eh_recurso = "recurso" in tipo or "minerio" in tipo or "minério" in tipo
            eh_mitico = "mitic" in raridade or "mythic" in raridade or "mitic" in nome or "mythic" in nome
            if eh_recurso and eh_mitico:
                total += self._quantidade_item(item)
        return total

    # ------------------------------------------------------------------
    # Rotas
    # ------------------------------------------------------------------
    def _montar_rotas(self) -> dict[str, RotaProgresso]:
        rotas = {
            "intelectual": RotaProgresso(
                id="intelectual",
                nome="Intelectual",
                subtitulo="Complete registros, catálogo e descobertas do mundo.",
                cor=(92, 137, 232),
                cor_clara=(196, 219, 255),
                cor_escura=(35, 59, 118),
                missoes=(
                    MissaoProgresso("pokemons_registrados", "Registre 1000 pokémons", 1000, 40, lambda p, _: p._contar_registro(("PokemonsRegistrados", "PokémonsRegistrados", "RegistroPokemons", "Pokedex", "PokemonsConhecidos", "ConhecimentoPokemons"), p._contar_pokemons_inventario)),
                    MissaoProgresso("itens_registrados", "Registre 120 itens", 120, 20, lambda p, _: p._contar_registro(("ItensRegistrados", "RegistroItens", "ItensConhecidos", "ConhecimentoItens"), lambda: p._contar_itens_inventario(apenas_distintos=True))),
                    MissaoProgresso("efeitos_registrados", "Registre 50 efeitos", 50, 12, lambda p, _: p._contar_registro(("EfeitosRegistrados", "RegistroEfeitos", "EfeitosConhecidos", "ConhecimentoEfeitos"))),
                    MissaoProgresso("ataques_registrados", "Registre 500 ataques", 500, 20, lambda p, _: p._contar_registro(("AtaquesRegistrados", "RegistroAtaques", "AtaquesConhecidos", "ConhecimentoAtaques"))),
                    MissaoProgresso("musicas_registradas", "Registre 50 músicas", 50, 8, lambda p, _: p._contar_registro(("MusicasRegistradas", "MúsicasRegistradas", "RegistroMusicas", "MusicasConhecidas", "ConhecimentoMusicas"))),
                ),
            ),
            "campeao": RotaProgresso(
                id="campeao",
                nome="Campeão",
                subtitulo="Domine ginásios, batalhas e o caminho competitivo.",
                cor=(235, 177, 69),
                cor_clara=(255, 232, 168),
                cor_escura=(109, 73, 23),
                missoes=(
                    MissaoProgresso("insignias", "Consiga 25 insígnias", 25, 40, lambda p, _: p._insignias()),
                    MissaoProgresso("vitorias", "Consiga 1000 vitórias", 1000, 20, lambda p, _: p._vitorias_totais()),
                    MissaoProgresso("lider_ginasios", "Torne-se líder de 5 ginásios", 5, 25, lambda p, _: p._ginasios_liderados()),
                    MissaoProgresso("grande_campeao", "Derrote o grande Campeão", 1, 15, lambda p, _: p._flag_perfil(("GrandeCampeaoDerrotado", "DerrotouGrandeCampeao", "CampeaoDerrotado", "CampeãoDerrotado")), unidade="feito"),
                ),
            ),
            "magnata": RotaProgresso(
                id="magnata",
                nome="Magnata",
                subtitulo="Acumule riqueza, coleção e recursos raros.",
                cor=(91, 190, 112),
                cor_clara=(202, 255, 210),
                cor_escura=(33, 91, 49),
                missoes=(
                    MissaoProgresso("ouro", "Consiga ter 1.000.000.000 de ouro", 1_000_000_000, 70, lambda p, _: p._ouro(), unidade="ouro"),
                    MissaoProgresso("pokemons_guardados", "Consiga ter 1000 pokémons", 1000, 20, lambda p, _: p._contar_pokemons_inventario()),
                    MissaoProgresso("recursos_miticos", "Consiga ter 500 itens de recursos míticos", 500, 10, lambda p, _: p._contar_recursos_miticos()),
                ),
            ),
            "heroi": RotaProgresso(
                id="heroi",
                nome="Herói",
                subtitulo="Supere dungeons, nível máximo e ameaças finais.",
                cor=(219, 83, 113),
                cor_clara=(255, 201, 215),
                cor_escura=(105, 31, 50),
                missoes=(
                    MissaoProgresso("nivel", "Consiga chegar no nível 100", 100, 25, lambda p, _: p._nivel()),
                    MissaoProgresso("dungeons", "Termine 50 dungeons", 50, 60, lambda p, _: p._dungeons_terminadas()),
                    MissaoProgresso("eternidade", "Derrote a Eternidade", 1, 15, lambda p, _: p._flag_perfil(("EternidadeDerrotada", "DerrotouEternidade", "BossEternidadeDerrotado")), unidade="feito"),
                ),
            ),
        }

        rotas["imperador"] = RotaProgresso(
            id="imperador",
            nome="Imperador",
            subtitulo="Una as quatro grandes rotas em uma conquista final.",
            cor=(151, 105, 229),
            cor_clara=(226, 211, 255),
            cor_escura=(64, 41, 115),
            missoes=(
                MissaoProgresso("ser_magnata", "Se torne um Magnata", 1, 25, lambda p, cache: cache.get("magnata", 0.0), unidade="rota"),
                MissaoProgresso("ser_campeao", "Se torne um Campeão", 1, 25, lambda p, cache: cache.get("campeao", 0.0), unidade="rota"),
                MissaoProgresso("ser_heroi", "Se torne um Herói", 1, 25, lambda p, cache: cache.get("heroi", 0.0), unidade="rota"),
                MissaoProgresso("ser_intelectual", "Se torne um Intelectual", 1, 25, lambda p, cache: cache.get("intelectual", 0.0), unidade="rota"),
            ),
        )
        return rotas

    @staticmethod
    def _progresso_missao(valor, alvo) -> float:
        try:
            alvo = float(alvo)
            valor = float(valor)
        except (TypeError, ValueError):
            return 0.0
        if alvo <= 0:
            return 1.0
        return max(0.0, min(1.0, valor / alvo))

    def _calcular_rota(self, rota: RotaProgresso, cache_base: dict[str, float] | None = None):
        cache_base = cache_base or {}
        total = 0.0
        missoes_calc = []
        for missao in rota.missoes:
            valor = missao.obter_valor(self, cache_base)
            progresso = self._progresso_missao(valor, missao.alvo)
            total += progresso * missao.peso
            missoes_calc.append((missao, valor, progresso))
        return max(0.0, min(100.0, total)), missoes_calc

    def _calcular_todas_rotas(self):
        cache = {}
        detalhes = {}
        for rid in ("campeao", "intelectual", "magnata", "heroi"):
            progresso, missoes = self._calcular_rota(self._rotas[rid])
            cache[rid] = progresso / 100.0
            detalhes[rid] = (progresso, missoes)
        progresso, missoes = self._calcular_rota(self._rotas["imperador"], cache)
        detalhes["imperador"] = (progresso, missoes)
        return detalhes

    # ------------------------------------------------------------------
    # Layout / UI
    # ------------------------------------------------------------------
    def _texto(self, chave: str, conteudo: str, pos, style: dict):
        txt = self._textos.get(chave)
        if txt is None:
            txt = Texto(conteudo, style=style)
            self._textos[chave] = txt
        txt.set_text(conteudo)
        txt.set_pos(pos)
        txt.draw(self._tela_atual)

    @staticmethod
    def _style_texto(size=18, color=(238, 242, 255), align=None):
        style = {
            "size": size,
            "color": color,
            "outline": True,
            "outline_thickness": 1,
            "outline_color": (0, 0, 0),
            "shadow": False,
        }
        if align:
            style["align"] = align
        return style

    @staticmethod
    def _formatar_numero(valor, compactar=False) -> str:
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            valor = 0.0
        if compactar:
            abs_v = abs(valor)
            if abs_v >= 1_000_000_000:
                return f"{valor / 1_000_000_000:.1f}B".replace(".0B", "B")
            if abs_v >= 1_000_000:
                return f"{valor / 1_000_000:.1f}M".replace(".0M", "M")
            if abs_v >= 1_000:
                return f"{valor / 1_000:.1f}K".replace(".0K", "K")
        inteiro = int(round(valor))
        return f"{inteiro:,}".replace(",", ".")

    @staticmethod
    def _misturar(c1, c2, t: float):
        t = max(0.0, min(1.0, float(t)))
        return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

    def _style_botao_rota(self, rota: RotaProgresso, selecionado: bool):
        bg = rota.cor if selecionado else self._misturar(rota.cor_escura, (28, 36, 58), 0.55)
        hover = rota.cor_clara if selecionado else self._misturar(rota.cor, (35, 47, 76), 0.45)
        pressed = rota.cor_escura
        border = rota.cor_clara if selecionado else self._misturar(rota.cor, (108, 124, 158), 0.5)
        return {
            "radius": 14,
            "border_width": 2,
            "hover_scale": 1.015,
            "press_scale": 0.985,
            "bg": bg,
            "bg_hover": hover,
            "bg_pressed": pressed,
            "border": border,
            "border_hover": rota.cor_clara,
            "text_style": {
                "size": 18,
                "color": (255, 255, 255),
                "hover_color": (255, 255, 255),
                "align": "center",
                "outline": True,
                "outline_color": (0, 0, 0),
                "outline_thickness": 1,
                "shadow": False,
            },
        }

    def _reconstruir_layout(self, rect: pygame.Rect):
        chave = (rect.x, rect.y, rect.width, rect.height)
        if chave == self._layout_chave and self._botao_fechar is not None:
            return

        self._layout_chave = chave
        self._rect = pygame.Rect(rect)
        self._area_botoes = pygame.Rect(rect.x + 22, rect.y + 92, rect.width - 44, 54)
        self._area_conteudo = pygame.Rect(rect.x + 22, rect.y + 164, rect.width - 44, rect.height - 186)
        self._area_missoes = pygame.Rect(self._area_conteudo.x + 18, self._area_conteudo.y + 164, self._area_conteudo.width - 36, self._area_conteudo.height - 184)

        def _fechar(_jogo, _botao):
            self._solicitou_fechar = True

        self._botao_fechar = Botao(
            pygame.Rect(rect.right - 68, rect.y + 16, 52, 52),
            "X",
            execute=_fechar,
            style={
                "radius": 18,
                "bg": (113, 32, 45),
                "bg_hover": (145, 40, 59),
                "bg_pressed": (86, 23, 34),
                "border": (255, 195, 203),
                "border_hover": (255, 236, 240),
                "text_style": {"size": 26, "outline_thickness": 1, "shadow": False},
            },
        )

        gap = 10
        qtd = len(self.ROTAS_ORDEM)
        largura = (self._area_botoes.width - gap * (qtd - 1)) // qtd
        self._botoes_rotas = {}
        self._status_estilo_botoes = {}
        for i, rid in enumerate(self.ROTAS_ORDEM):
            rota = self._rotas[rid]
            x = self._area_botoes.x + i * (largura + gap)
            w = largura if i < qtd - 1 else self._area_botoes.right - x

            def _selecionar(_jogo, _botao, rota_id=rid):
                self._rota_selecionada = rota_id

            self._botoes_rotas[rid] = Botao(
                pygame.Rect(x, self._area_botoes.y, w, self._area_botoes.height),
                rota.nome,
                execute=_selecionar,
                style=self._style_botao_rota(rota, rid == self._rota_selecionada),
            )

    def _desenhar_fundo(self, tela):
        tela.fill((8, 12, 22), self._rect)
        camada = pygame.Surface(self._rect.size, pygame.SRCALPHA)
        pygame.draw.rect(camada, (12, 18, 32, 248), camada.get_rect(), border_radius=22)
        # brilho suave no topo, feito sem depender de imagem externa
        pygame.draw.ellipse(camada, (58, 82, 150, 42), (-120, -180, self._rect.width + 240, 310))
        pygame.draw.ellipse(camada, (22, 36, 82, 38), (self._rect.width - 360, 40, 420, 280))
        tela.blit(camada, self._rect.topleft)

    def _desenhar_barra(self, tela, rect: pygame.Rect, progresso: float, cor, cor_clara=None, texto: str | None = None, alto_brilho=False):
        progresso = max(0.0, min(1.0, float(progresso)))
        cor_clara = cor_clara or self._misturar(cor, (255, 255, 255), 0.45)
        pygame.draw.rect(tela, (20, 27, 46), rect, border_radius=rect.height // 2)
        pygame.draw.rect(tela, (69, 88, 137), rect, 1, border_radius=rect.height // 2)
        if progresso > 0:
            preenchido = pygame.Rect(rect.x + 2, rect.y + 2, max(4, int((rect.width - 4) * progresso)), rect.height - 4)
            pygame.draw.rect(tela, cor, preenchido, border_radius=preenchido.height // 2)
            if alto_brilho:
                brilho = pygame.Rect(preenchido.x + 3, preenchido.y + 3, max(0, preenchido.width - 6), max(2, preenchido.height // 3))
                pygame.draw.rect(tela, (*cor_clara, 112), brilho, border_radius=brilho.height // 2)
        if texto:
            self._texto(f"barra_{rect.x}_{rect.y}_{rect.width}", texto, rect.center, self._style_texto(16, (248, 251, 255), "center"))

    def _texto_valor_missao(self, missao: MissaoProgresso, valor, progresso: float) -> str:
        if missao.unidade == "feito":
            return "Concluído" if progresso >= 1.0 else "Pendente"
        if missao.unidade == "rota":
            return f"{int(round(progresso * 100))}% / 100%"
        compactar = missao.alvo >= 1_000_000
        return f"{self._formatar_numero(valor, compactar)} / {self._formatar_numero(missao.alvo, compactar)}"

    def _desenhar_topo(self, tela, detalhes):
        self._texto("titulo", "Progresso", (self._rect.x + 22, self._rect.y + 18), self._style_texto(34, (247, 250, 255)))
        self._texto(
            "subtitulo",
            "Escolha uma rota e acompanhe as missões que levam ao 100%.",
            (self._rect.x + 24, self._rect.y + 58),
            self._style_texto(18, (187, 207, 238)),
        )

        for rid in self.ROTAS_ORDEM:
            rota = self._rotas[rid]
            botao = self._botoes_rotas[rid]
            selecionado = rid == self._rota_selecionada
            if self._status_estilo_botoes.get(rid) != selecionado:
                botao.set_style(**self._style_botao_rota(rota, selecionado))
                self._status_estilo_botoes[rid] = selecionado
            botao.render(tela, self._eventos_frame, self._dt_frame, None)

            progresso = detalhes[rid][0] / 100.0
            mini = pygame.Rect(botao.base_rect.x + 12, botao.base_rect.bottom - 10, botao.base_rect.width - 24, 5)
            self._desenhar_barra(tela, mini, progresso, rota.cor, rota.cor_clara)

        self._botao_fechar.render(tela, self._eventos_frame, self._dt_frame, None)

    def _desenhar_card_rota(self, tela, rota: RotaProgresso, progresso_rota: float, missoes_calc):
        card = pygame.Rect(self._area_conteudo.x, self._area_conteudo.y, self._area_conteudo.width, 142)
        pygame.draw.rect(tela, (14, 22, 40), card, border_radius=18)
        pygame.draw.rect(tela, self._misturar(rota.cor, (180, 205, 255), 0.45), card, 2, border_radius=18)

        badge = pygame.Rect(card.x + 18, card.y + 20, 58, 58)
        pygame.draw.rect(tela, rota.cor_escura, badge, border_radius=17)
        pygame.draw.rect(tela, rota.cor_clara, badge, 2, border_radius=17)
        self._texto("rota_sigla", rota.nome[:2].upper(), badge.center, self._style_texto(24, (255, 255, 255), "center"))

        self._texto("rota_nome", rota.nome, (card.x + 92, card.y + 18), self._style_texto(30, (248, 250, 255)))
        self._texto("rota_sub", rota.subtitulo, (card.x + 94, card.y + 56), self._style_texto(17, (190, 210, 238)))

        pct = int(round(progresso_rota))
        self._texto("rota_pct", f"{pct}%", (card.right - 24, card.y + 22), self._style_texto(34, rota.cor_clara, "topright"))
        concluidas = sum(1 for _m, _v, prog in missoes_calc if prog >= 1.0)
        self._texto("rota_concluidas", f"{concluidas}/{len(missoes_calc)} missões concluídas", (card.right - 24, card.y + 64), self._style_texto(16, (190, 210, 238), "topright"))

        barra = pygame.Rect(card.x + 20, card.bottom - 36, card.width - 40, 22)
        self._desenhar_barra(tela, barra, progresso_rota / 100.0, rota.cor, rota.cor_clara, f"Progresso geral da rota: {pct}%", alto_brilho=True)

    def _desenhar_missoes(self, tela, rota: RotaProgresso, missoes_calc):
        titulo_y = self._area_missoes.y - 34
        self._texto("missoes_titulo", "Missões da rota", (self._area_missoes.x + 2, titulo_y), self._style_texto(22, (241, 245, 255)))
        self._texto("missoes_info", "A porcentagem ao lado é o peso dela no 100% final.", (self._area_missoes.right - 2, titulo_y + 4), self._style_texto(15, (162, 182, 218), "topright"))

        qtd = max(1, len(missoes_calc))
        gap = 12
        altura = min(82, max(58, (self._area_missoes.height - gap * (qtd - 1)) // qtd))
        for i, (missao, valor, progresso) in enumerate(missoes_calc):
            y = self._area_missoes.y + i * (altura + gap)
            card = pygame.Rect(self._area_missoes.x, y, self._area_missoes.width, altura)
            cor_card = (16, 25, 45) if progresso < 1.0 else self._misturar(rota.cor_escura, (18, 34, 30), 0.45)
            pygame.draw.rect(tela, cor_card, card, border_radius=16)
            pygame.draw.rect(tela, self._misturar(rota.cor, (78, 94, 138), 0.35), card, 1, border_radius=16)

            peso_rect = pygame.Rect(card.x + 14, card.y + 14, 58, card.height - 28)
            pygame.draw.rect(tela, self._misturar(rota.cor_escura, (16, 22, 36), 0.35), peso_rect, border_radius=12)
            pygame.draw.rect(tela, rota.cor_clara, peso_rect, 1, border_radius=12)
            self._texto(f"peso_{missao.id}", f"{int(missao.peso)}%", peso_rect.center, self._style_texto(18, rota.cor_clara, "center"))

            x_texto = card.x + 88
            self._texto(f"missao_{missao.id}", missao.titulo, (x_texto, card.y + 13), self._style_texto(19, (247, 250, 255)))
            valor_txt = self._texto_valor_missao(missao, valor, progresso)
            self._texto(f"valor_{missao.id}", valor_txt, (card.right - 18, card.y + 13), self._style_texto(18, (211, 226, 250), "topright"))

            barra = pygame.Rect(x_texto, card.bottom - 29, card.right - x_texto - 18, 18)
            pct = int(round(progresso * 100))
            self._desenhar_barra(tela, barra, progresso, rota.cor, rota.cor_clara, f"{pct}%")

    def renderizar(self, tela, rect, eventos=None, dt=0.0):
        eventos = eventos or []
        self._solicitou_fechar = False
        self._tela_atual = tela
        self._eventos_frame = eventos
        self._dt_frame = dt

        self._reconstruir_layout(pygame.Rect(rect))
        detalhes = self._calcular_todas_rotas()
        rota = self._rotas.get(self._rota_selecionada, self._rotas["campeao"])
        progresso_rota, missoes_calc = detalhes[rota.id]

        self._desenhar_fundo(tela)
        self._desenhar_topo(tela, detalhes)
        self._desenhar_card_rota(tela, rota, progresso_rota, missoes_calc)
        self._desenhar_missoes(tela, rota, missoes_calc)
        return self._solicitou_fechar
